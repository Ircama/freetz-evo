use serde::{Deserialize, Serialize};
use std::sync::{Arc, atomic::{AtomicBool, AtomicUsize, Ordering}, mpsc::{self, Receiver, SyncSender, TryRecvError}};
use std::thread::JoinHandle;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

#[derive(Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct InfluxConfig {
    pub enabled: bool,
    pub endpoint: String,
    pub database: String,
    pub measurement: String,
    pub token: String,
    pub batch_size: usize,
    pub queue_capacity: usize,
    pub flush_interval_ms: u64,
    pub timeout_ms: u64,
}

impl Default for InfluxConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            endpoint: "http://127.0.0.1:8181".into(),
            database: "ble".into(),
            measurement: "ble".into(),
            token: String::new(),
            batch_size: 100,
            queue_capacity: 1024,
            flush_interval_ms: 5000,
            timeout_ms: 3000,
        }
    }
}

impl std::fmt::Debug for InfluxConfig {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.debug_struct("InfluxConfig")
            .field("enabled", &self.enabled)
            .field("database", &self.database)
            .field("token_present", &!self.token.is_empty())
            .finish_non_exhaustive()
    }
}

impl InfluxConfig {
    pub fn validate(&self) -> Result<(), String> {
        let uri: ureq::http::Uri = self.endpoint.parse().map_err(|_| "Influx endpoint must be an HTTP(S) URL".to_string())?;
        let scheme = uri.scheme_str().unwrap_or("");
        let authority = uri.authority().ok_or("Influx endpoint requires a host")?;
        if !matches!(scheme, "http" | "https") || authority.as_str().contains('@') || uri.query().is_some() || self.endpoint.contains('#') {
            return Err("Influx endpoint requires HTTP(S), no URL credentials, query or fragment".into());
        }
        let host = uri.host().unwrap_or("").trim_start_matches('[').trim_end_matches(']');
        let local = host.eq_ignore_ascii_case("localhost") || host.parse::<std::net::IpAddr>().is_ok_and(|address| address.is_loopback());
        if scheme == "http" && !local && !self.token.is_empty() {
            return Err("remote Influx token authentication requires HTTPS".into());
        }
        if self.token.len() > 8192 || self.token.bytes().any(|byte| byte.is_ascii_control() || !byte.is_ascii()) {
            return Err("Influx token contains invalid header characters".into());
        }
        for value in [&self.database, &self.measurement] {
            if value.trim().is_empty() || value.len() > 128 || invalid_text(value) {
                return Err("Influx database and measurement must be nonempty, at most 128 bytes and contain no line breaks".into());
            }
        }
        if !(1..=1024).contains(&self.batch_size) || !(1..=16384).contains(&self.queue_capacity)
            || self.batch_size > self.queue_capacity || !(10..=60000).contains(&self.flush_interval_ms)
            || !(100..=30000).contains(&self.timeout_ms) {
            return Err("Influx batch/queue or flush/timeout limits are invalid".into());
        }
        Ok(())
    }
}

enum Delivery {
    Accepted,
    Retry,
    Rejected(u16),
}

fn deliver(agent: &ureq::Agent, config: &InfluxConfig, lines: &[String]) -> Delivery {
    let endpoint = format!("{}/api/v3/write_lp", config.endpoint.trim_end_matches('/'));
    let mut request = agent.post(endpoint).query("db", &config.database).query("precision", "nanosecond")
        .header("Content-Type", "text/plain; charset=utf-8");
    if !config.token.is_empty() { request = request.header("Authorization", format!("Bearer {}", config.token)); }
    match request.send(lines.join("\n")) {
        Ok(response) => {
            let status = response.status().as_u16();
            if (200..300).contains(&status) { Delivery::Accepted }
            else if status == 429 || status >= 500 { Delivery::Retry }
            else { Delivery::Rejected(status) }
        }
        Err(_) => Delivery::Retry,
    }
}

fn run_worker(config: InfluxConfig, receiver: Receiver<String>, stopped: Arc<AtomicBool>) {
    let agent: ureq::Agent = ureq::Agent::config_builder()
        .timeout_global(Some(Duration::from_millis(config.timeout_ms)))
        .max_redirects(0).proxy(None).http_status_as_error(false).build().into();
    let interval = Duration::from_millis(config.flush_interval_ms);
    let mut deadline = Instant::now() + interval;
    let mut pending = Vec::with_capacity(config.batch_size);
    let mut retrying = false;
    let mut failures = 0usize;
    while !stopped.load(Ordering::Relaxed) {
        if pending.len() < config.batch_size {
            let timeout = deadline.saturating_duration_since(Instant::now()).min(Duration::from_millis(100));
            match receiver.recv_timeout(timeout) {
                Ok(line) => pending.push(line),
                Err(mpsc::RecvTimeoutError::Disconnected) => break,
                Err(mpsc::RecvTimeoutError::Timeout) => {},
            }
        } else if retrying && Instant::now() < deadline {
            std::thread::park_timeout(deadline.saturating_duration_since(Instant::now()).min(Duration::from_millis(100)));
        }
        if pending.is_empty() {
            deadline = Instant::now() + interval;
            continue;
        }
        if Instant::now() < deadline && (retrying || pending.len() < config.batch_size) { continue; }
        match deliver(&agent, &config, &pending) {
            Delivery::Accepted => { pending.clear(); retrying = false; failures = 0; }
            Delivery::Rejected(status) => {
                log::warn!("Influx rejected {} measurements with HTTP {status}; batch discarded", pending.len());
                pending.clear(); retrying = false;
            }
            Delivery::Retry => {
                if failures % 30 == 0 { log::warn!("Influx unavailable; retrying a bounded batch of {} measurements", pending.len()); }
                failures = failures.saturating_add(1); retrying = true;
            }
        }
        deadline = Instant::now() + interval;
    }
    while pending.len() < config.batch_size {
        match receiver.try_recv() {
            Ok(line) => pending.push(line),
            Err(TryRecvError::Empty | TryRecvError::Disconnected) => break,
        }
    }
    if !pending.is_empty() && !matches!(deliver(&agent, &config, &pending), Delivery::Accepted) {
        log::warn!("Influx final batch not delivered; in-memory samples are not a persistent spool");
    }
    let discarded = receiver.try_iter().count();
    if discarded > 0 { log::warn!("Influx shutdown discarded {discarded} queued measurements; queue is not a persistent spool"); }
}

pub struct InfluxPublisher {
    config: InfluxConfig,
    sender: SyncSender<String>,
    stopped: Arc<AtomicBool>,
    worker: Option<JoinHandle<()>>,
    dropped: AtomicUsize,
}

impl InfluxPublisher {
    pub fn start(config: &InfluxConfig) -> Result<Self, String> {
        config.validate()?;
        if !config.enabled { return Err("Influx frontend is disabled".into()); }
        let (sender, receiver) = mpsc::sync_channel(config.queue_capacity);
        let stopped = Arc::new(AtomicBool::new(false));
        let worker_stopped = Arc::clone(&stopped);
        let worker_config = config.clone();
        let worker = std::thread::Builder::new().name("ble-influx".into())
            .spawn(move || run_worker(worker_config, receiver, worker_stopped)).map_err(|_| "cannot start Influx worker".to_string())?;
        Ok(Self { config: config.clone(), sender, stopped, worker: Some(worker), dropped: AtomicUsize::new(0) })
    }

    pub fn publish(&self, state: &serde_json::Value) {
        let Some(timestamp) = SystemTime::now().duration_since(UNIX_EPOCH).ok().and_then(|time| i64::try_from(time.as_nanos()).ok()) else { return; };
        for line in encode_lines(&self.config, state, timestamp) {
            if line.len() > 4096 || self.sender.try_send(line).is_err() {
                let dropped = self.dropped.fetch_add(1, Ordering::Relaxed) + 1;
                if dropped == 1 || dropped % 100 == 0 { log::warn!("Influx queue full or sample oversized; {dropped} measurements dropped"); }
            }
        }
    }
}

impl Drop for InfluxPublisher {
    fn drop(&mut self) {
        self.stopped.store(true, Ordering::Relaxed);
        if let Some(worker) = self.worker.take() { worker.thread().unpark(); let _ = worker.join(); }
    }
}

fn invalid_text(value: &str) -> bool {
    value.contains(['\r', '\n', '\0'])
}

fn escape_tag(value: &str) -> String {
    value.replace('\\', "\\\\").replace(',', "\\,").replace(' ', "\\ ").replace('=', "\\=")
}

fn string_field(value: &str) -> String {
    format!("\"{}\"", value.replace('\\', "\\\\").replace('"', "\\\""))
}

fn encode_lines(config: &InfluxConfig, state: &serde_json::Value, timestamp_ns: i64) -> Vec<String> {
    let Some(mac) = state["mac"].as_str().filter(|value| !value.is_empty() && !invalid_text(value)) else { return Vec::new(); };
    let Some(measurements) = state["measurements"].as_array() else { return Vec::new(); };
    let label = state["label"].as_str().unwrap_or("");
    let measurement = config.measurement.replace('\\', "\\\\").replace(',', "\\,").replace(' ', "\\ ");
    let mut lines = Vec::new();
    for entry in measurements {
        let Some(attribute) = entry["name"].as_str().filter(|value| !value.is_empty() && !invalid_text(value)) else { continue; };
        let unit = entry["unit"].as_str().unwrap_or("");
        if invalid_text(label) || invalid_text(unit) { continue; }
        let value = &entry["value"];
        let field = if let Some(value) = value.as_bool() {
            format!("value_bool={value}")
        } else if let Some(value) = value.as_i64() {
            format!("value_int={value}i")
        } else if let Some(value) = value.as_u64() {
            format!("value_uint={value}u")
        } else if let Some(value) = value.as_f64().filter(|value| value.is_finite()) {
            format!("value_float={value}")
        } else if let Some(value) = value.as_str().filter(|value| !invalid_text(value)) {
            format!("value_text={}", string_field(value))
        } else { continue; };
        lines.push(format!("{measurement},mac={},attribute={} {field},unit={},label={} {timestamp_ns}",
            escape_tag(mac), escape_tag(attribute), string_field(unit), string_field(label)));
    }
    lines
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_state(value: i64) -> serde_json::Value {
        serde_json::json!({"mac":"AABBCCDDEEFF","label":"Test","measurements":[{"name":"count","value":value,"unit":""}]})
    }

    fn http_receiver(statuses: Vec<u16>) -> (String, mpsc::Receiver<(String, Vec<u8>)>, JoinHandle<()>) {
        use std::io::{BufRead, Read, Write};
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let endpoint = format!("http://{}", listener.local_addr().unwrap());
        let (sender, receiver) = mpsc::channel();
        let worker = std::thread::spawn(move || {
            for status in statuses {
                let (stream, _) = listener.accept().unwrap();
                stream.set_read_timeout(Some(Duration::from_secs(4))).unwrap();
                let mut reader = std::io::BufReader::new(stream);
                let mut header = String::new();
                let mut length = None;
                loop {
                    let mut line = String::new();
                    assert_ne!(reader.read_line(&mut line).unwrap(), 0);
                    header.push_str(&line);
                    if let Some((name, value)) = line.split_once(':') {
                        if name.eq_ignore_ascii_case("content-length") { length = Some(value.trim().parse::<usize>().unwrap()); }
                    }
                    if line == "\r\n" { break; }
                }
                let mut body = vec![0; length.expect("bounded request content length")];
                reader.read_exact(&mut body).unwrap();
                write!(reader.get_mut(), "HTTP/1.1 {status} Test\r\nContent-Length: 0\r\nConnection: close\r\n\r\n").unwrap();
                sender.send((header, body)).unwrap();
            }
        });
        (endpoint, receiver, worker)
    }

    #[test]
    fn influx_validates_remote_transport_limits_and_headers() {
        let mut config = InfluxConfig::default();
        config.validate().unwrap();
        for endpoint in ["ftp://example.org", "http://user:password@example.org", "http://example.org?key=x", "http://example.org/#secret"] {
            config.endpoint = endpoint.into();
            assert!(config.validate().is_err());
        }
        config.endpoint = "http://example.org".into(); config.token = "private".into();
        assert!(config.validate().is_err());
        config.endpoint = "https://example.org/influx".into(); config.validate().unwrap();
        config.token = "bad\r\nheader".into(); assert!(config.validate().is_err());
        config = InfluxConfig::default(); config.batch_size = 0; assert!(config.validate().is_err());
        config = InfluxConfig::default(); config.measurement = "bad\nline".into(); assert!(config.validate().is_err());
    }

    #[test]
    fn influx_sends_authenticated_http_batches_and_encoded_database() {
        let (endpoint, received, server) = http_receiver(vec![204]);
        let config = InfluxConfig { enabled: true, endpoint, database: "room & one".into(), token: "private-token".into(), batch_size: 2, flush_interval_ms: 20, ..Default::default() };
        let publisher = InfluxPublisher::start(&config).unwrap();
        publisher.publish(&test_state(1)); publisher.publish(&test_state(2));
        let (header, body) = received.recv_timeout(Duration::from_secs(5)).unwrap();
        assert!(header.starts_with("POST /api/v3/write_lp?db=room%20%26%20one&precision=nanosecond HTTP/1.1\r\n"), "{header}");
        assert!(header.to_ascii_lowercase().contains("authorization: bearer private-token"));
        let body = String::from_utf8(body).unwrap();
        assert_eq!(body.lines().count(), 2);
        assert!(body.contains("value_int=1i")); assert!(body.contains("value_int=2i"));
        drop(publisher); server.join().unwrap();
    }

    #[test]
    fn influx_retries_preserve_original_sample_timestamps() {
        let (endpoint, received, server) = http_receiver(vec![503, 204]);
        let config = InfluxConfig { enabled: true, endpoint, batch_size: 1, flush_interval_ms: 20, ..Default::default() };
        let publisher = InfluxPublisher::start(&config).unwrap(); publisher.publish(&test_state(42));
        let first = received.recv_timeout(Duration::from_secs(5)).unwrap();
        let second = received.recv_timeout(Duration::from_secs(5)).unwrap();
        assert_eq!(first.1, second.1);
        drop(publisher); server.join().unwrap();
    }

    #[test]
    fn influx_queue_overflow_is_nonblocking_and_counted() {
        let (sender, receiver) = mpsc::sync_channel(1);
        let publisher = InfluxPublisher { config: InfluxConfig::default(), sender, stopped: Arc::new(AtomicBool::new(false)), worker: None, dropped: AtomicUsize::new(0) };
        publisher.publish(&test_state(1)); publisher.publish(&test_state(2)); publisher.publish(&test_state(3));
        assert_eq!(publisher.dropped.load(Ordering::Relaxed), 2);
        assert!(receiver.try_recv().unwrap().contains("value_int=1i"));
        assert!(receiver.try_recv().is_err());
    }

    #[test]
    fn influx_defaults_are_disabled_and_token_is_redacted() {
        let config: InfluxConfig = serde_yaml::from_str("{}").unwrap();
        assert!(!config.enabled);
        assert_eq!(config.batch_size, 100);
        let config = InfluxConfig { token: "private-token".into(), ..config };
        assert!(!format!("{config:?}").contains("private-token"));
    }

    #[test]
    fn influx_encodes_exact_types_metadata_and_receive_timestamp() {
        let state = serde_json::json!({"mac":"AABBCCDDEEFF","label":"Outside","measurements":[
            {"name":"temperature","value":16.08,"unit":"C"},
            {"name":"counter","value":9007199254740993_i64,"unit":""},
            {"name":"opened","value":true,"unit":""},
            {"name":"message","value":"ready","unit":""},
            {"name":"missing","value":null,"unit":""}
        ]});
        let lines = encode_lines(&InfluxConfig::default(), &state, 123456789);
        assert_eq!(lines.len(), 4);
        assert!(lines[0].contains("value_float=16.08,unit=\"C\",label=\"Outside\" 123456789"));
        assert!(lines[1].contains("value_int=9007199254740993i"));
        assert!(lines[2].contains("value_bool=true"));
        assert!(lines[3].contains("value_text=\"ready\""));
    }

    #[test]
    fn influx_escapes_protocol_fields_and_rejects_injected_lines() {
        let config = InfluxConfig { measurement: "ble readings".into(), ..Default::default() };
        let state = serde_json::json!({"mac":"AA,BB","label":"Room \"one\"","measurements":[
            {"name":"a=b c","value":-4,"unit":"m/s"},
            {"name":"bad\nfield","value":1,"unit":""}
        ]});
        let lines = encode_lines(&config, &state, 42);
        assert_eq!(lines, ["ble\\ readings,mac=AA\\,BB,attribute=a\\=b\\ c value_int=-4i,unit=\"m/s\",label=\"Room \\\"one\\\"\" 42"]);
    }
}
