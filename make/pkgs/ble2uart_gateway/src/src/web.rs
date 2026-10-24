use crate::config::Config;
use serde_json::{json, Value};
use std::hash::Hasher;
use std::path::{Path, PathBuf};
use std::io::{BufRead, Read, Write};
use std::os::unix::{fs::PermissionsExt, net::{UnixListener, UnixStream}};
use std::collections::BTreeMap;
use std::time::{Duration, Instant};

fn control_socket() -> PathBuf {
    std::env::var_os("BLE2UART_GATEWAY_CONTROL_SOCKET")
        .map(PathBuf::from).unwrap_or_else(|| {
            std::env::var_os("XDG_RUNTIME_DIR").map(PathBuf::from)
                .filter(|directory|directory.is_absolute())
                .map(|directory|directory.join("ble2uart-gateway/control.sock"))
                .unwrap_or_else(||std::env::temp_dir().join(format!("ble2uart-gateway-{}/control.sock",unsafe{libc::geteuid()})))
        })
}

pub struct ControlServer {
    listener: UnixListener,
    socket: PathBuf,
}

impl ControlServer {
    pub fn bind() -> Result<Self, String> {
        Self::bind_path(control_socket())
    }

    fn bind_path(socket: PathBuf) -> Result<Self, String> {
        if !socket.is_absolute() {return Err("control socket must be an absolute path".into());}
        let directory = socket.parent().ok_or("control socket requires a private directory")?;
        std::fs::create_dir_all(directory).map_err(|error| error.to_string())?;
        use std::os::unix::fs::MetadataExt;
        let metadata=std::fs::symlink_metadata(directory).map_err(|error|error.to_string())?;
        if !metadata.is_dir() || metadata.file_type().is_symlink() || metadata.uid()!=unsafe{libc::geteuid()} {
            return Err("control socket requires a private directory owned by the daemon user".into());
        }
        std::fs::set_permissions(directory, std::fs::Permissions::from_mode(0o700)).map_err(|error| error.to_string())?;
        if UnixStream::connect(&socket).is_ok() {
            return Err("another gateway control server is running".into());
        }
        match std::fs::remove_file(&socket) {
            Ok(()) => {},
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {},
            Err(error) => return Err(error.to_string()),
        }
        let listener = UnixListener::bind(&socket).map_err(|error| error.to_string())?;
        listener.set_nonblocking(true).map_err(|error| error.to_string())?;
        Ok(Self { listener, socket })
    }

    pub fn next(&self) -> Option<(UnixStream, Value)> {
        let (stream, _) = self.listener.accept().ok()?;
        stream.set_read_timeout(Some(Duration::from_millis(200))).ok()?;
        stream.set_write_timeout(Some(Duration::from_secs(2))).ok()?;
        let mut text = String::new();
        let parsed = std::io::BufReader::new(&stream).take(4097).read_line(&mut text)
            .ok().filter(|_| text.len() <= 4096).and_then(|_| serde_json::from_str(&text).ok());
        parsed.map(|request| (stream, request))
    }
}

impl Drop for ControlServer {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.socket);
    }
}

pub fn reply(mut stream: UnixStream, response: Value) {
    let _ = writeln!(stream, "{response}");
}

pub fn control_client(action: &str, seconds: u64) -> Result<Value, String> {
    control_request(&json!({"action": action, "seconds": seconds}))
}

pub fn control_request(request: &Value) -> Result<Value, String> {
    let encoded = serde_json::to_string(request).map_err(|error| error.to_string())?;
    if encoded.len() > 4096 { return Err("control request exceeds 4096 bytes".into()); }
    let mut stream = UnixStream::connect(control_socket()).map_err(|_| "gateway is not running or control socket is unavailable")?;
    stream.set_read_timeout(Some(Duration::from_secs(90))).map_err(|error| error.to_string())?;
    stream.set_write_timeout(Some(Duration::from_secs(2))).map_err(|error| error.to_string())?;
    writeln!(stream, "{encoded}").map_err(|error| error.to_string())?;
    let mut response = String::new();
    std::io::BufReader::new(stream).take(2097153).read_line(&mut response).map_err(|error| error.to_string())?;
    serde_json::from_str(&response).map_err(|_| "invalid gateway control response".into())
}

#[derive(Default)]
pub struct Discovery {
    pub until: Option<Instant>,
    paused_at: Option<Instant>,
    devices: BTreeMap<String, Value>,
    reports: u64,
    overflow: u64,
    pub error: String,
    advertisement_sequence: u64,
    advertisements: std::collections::VecDeque<Value>,
}

impl Discovery {
    pub fn start(&mut self, seconds: u64) -> Result<(), String> {
        if !(1..=300).contains(&seconds) {
            return Err("discovery duration must be between 1 and 300 seconds".into());
        }
        self.devices.clear();
        self.reports = 0;
        self.overflow = 0;
        self.error.clear();
        self.until = Some(Instant::now() + Duration::from_secs(seconds));
        self.paused_at = None;
        Ok(())
    }

    pub fn pause(&mut self) {
        if self.until.is_some() && self.paused_at.is_none() { self.paused_at = Some(Instant::now()); }
    }

    pub fn resume(&mut self) {
        if let Some(paused) = self.paused_at.take() {
            if let Some(until) = self.until.as_mut() { *until += paused.elapsed(); }
        }
    }

    pub fn cancel(&mut self) { self.until = None; self.paused_at = None; }

    pub fn expired(&self) -> bool {
        self.paused_at.is_none() && self.until.is_some_and(|until| Instant::now() >= until)
    }

    pub fn snapshot(&self, connected: bool) -> Value {
        json!({"success":true, "connected": connected, "active":self.until.is_some(), "paused":self.paused_at.is_some(), "remaining_s":self.until.map(|until| until.saturating_duration_since(self.paused_at.unwrap_or_else(Instant::now)).as_secs() + 1).unwrap_or(0), "reports": self.reports, "overflow":self.overflow, "error":self.error, "devices":self.devices.values().collect::<Vec<_>>()})
    }

    pub fn observe(&mut self, report: &crate::link::AdvReport, spec: &crate::codec::spec::Spec, config: &Config) {
        self.advertisement_sequence += 1;
        self.advertisements.push_back(json!({
            "sequence":self.advertisement_sequence, "mac":report.mac_string(),
            "rssi":report.rssi, "addr_type":report.addr_type,
            "data":crate::codec::value::hex(&report.data)
        }));
        if self.advertisements.len() > 256 { self.advertisements.pop_front(); }
        if self.until.is_none() { return; }
        self.reports += 1;
        let mac = report.mac_string();
        if !self.devices.contains_key(&mac) && self.devices.len() >= 1024 {
            self.overflow += 1;
            return;
        }
        let mut name = String::new();
        let mut index = 0;
        while index < report.data.len() {
            let length = report.data[index] as usize;
            if length < 1 || index + length >= report.data.len() { break; }
            if matches!(report.data[index + 1], 8 | 9) {
                name = String::from_utf8_lossy(&report.data[index + 2..index + 1 + length]).chars().filter(|character| !character.is_control()).collect();
            }
            index += length + 1;
        }
        let format = crate::pipeline::detect_format(report, spec).map(|(name, _)| name).unwrap_or_default();
        let old = self.devices.get(&mac);
        let count = old.and_then(|device| device["count"].as_u64()).unwrap_or(0) + 1;
        if name.is_empty() { name = old.and_then(|device| device["name"].as_str()).unwrap_or("").to_string(); }
        let configured = config.devices.iter().any(|device| crate::config::parse_mac(&device.mac).is_ok_and(|address| address.iter().rev().eq(report.mac.iter())));
        self.devices.insert(mac.clone(), json!({"mac":mac, "name":name, "vendor":vendor(&report.mac, report.addr_type), "format":format, "rssi":report.rssi, "phy":report.phy_summary(), "addr_type":report.addr_type, "count":count, "last_seen":crate::logger::timestamp(), "configured":configured, "data":crate::codec::value::hex(&report.data)}));
    }

    pub fn advertisement_events(&self, after: u64) -> Value {
        let first = self.advertisements.front()
            .and_then(|event| event["sequence"].as_u64())
            .unwrap_or(self.advertisement_sequence.saturating_add(1));
        json!({"success":true, "cursor":self.advertisement_sequence,
            "dropped":first.saturating_sub(after.saturating_add(1)),
            "events":self.advertisements.iter()
                .filter(|event| event["sequence"].as_u64().is_some_and(|sequence|sequence > after))
                .collect::<Vec<_>>()})
    }
}

fn vendor(wire_mac: &[u8; 6], addr_type: u8) -> &'static str {
    if addr_type != 0 || wire_mac[5] & 2 != 0 { return "Random / local address"; }
    static VENDORS: std::sync::OnceLock<std::collections::HashMap<&'static str, &'static str>> = std::sync::OnceLock::new();
    let vendors = VENDORS.get_or_init(|| include_str!("../spec/oui.tsv").lines().filter_map(|line| line.split_once('\t')).collect());
    let prefix = format!("{:02X}{:02X}{:02X}", wire_mac[5], wire_mac[4], wire_mac[3]);
    vendors.get(prefix.as_str()).copied().unwrap_or("Unknown OUI")
}

fn revision(path: &Path) -> Result<String, String> {
    let content = std::fs::read(path).map_err(|error| error.to_string())?;
    let mut hash = std::collections::hash_map::DefaultHasher::new();
    hash.write(&content);
    Ok(format!("{:016x}", hash.finish()))
}

pub fn inspect(path: &Path, spec: &crate::codec::spec::Spec, input: &str) -> Result<Value, String> {
    inspect_limited(path, spec, input, crate::link::ADV_DATA_MAX)
}

pub fn inspect_capture(path: &Path, spec: &crate::codec::spec::Spec, input: &str) -> Result<Value, String> {
    inspect_limited(path, spec, input, 4096)
}

fn inspect_limited(path: &Path, spec: &crate::codec::spec::Spec, input: &str, maximum: usize) -> Result<Value, String> {
    let request: Value = serde_json::from_str(input).map_err(|_| "invalid inspection request")?;
    let observation = &request["observation"];
    let mac = crate::config::parse_mac(observation["mac"].as_str().ok_or("missing observation MAC")?)?;
    let digits: String = observation["data"].as_str().ok_or("missing advertisement data")?.chars().filter(|character| !character.is_ascii_whitespace()).collect();
    if !digits.is_ascii() || digits.len() % 2 != 0 || digits.len() > maximum * 2 {
        return Err("invalid advertisement length or hexadecimal encoding".into());
    }
    let data = (0..digits.len()).step_by(2).map(|index| u8::from_str_radix(&digits[index..index + 2], 16)).collect::<Result<Vec<_>, _>>().map_err(|_| "invalid advertisement hexadecimal input")?;
    let mut configured = Config::load(path, None, None)?;
    let device = if let Some(device) = request.get("device").filter(|device| !device.is_null()) {
        serde_json::from_value(device.clone()).map_err(|_| "invalid inspection device configuration")?
    } else {
        configured.devices.iter().find(|device| crate::config::parse_mac(&device.mac).is_ok_and(|address| address == mac)).cloned()
            .unwrap_or(serde_json::from_value(json!({"mac":observation["mac"]})).map_err(|_| "invalid inspection MAC")?)
    };
    configured.devices = vec![device];
    if crate::config::parse_mac(&configured.devices[0].mac)? != mac { return Err("inspection device MAC does not match the advertisement".into()); }
    configured.devices[0].enabled = true;
    configured.validate()?;
    let device = crate::pipeline::Registry::new(&configured).devices.pop().ok_or("inspection device unavailable")?;
    let mut wire_mac = mac;
    wire_mac.reverse();
    let report = crate::link::AdvReport {rssi:0, event_type:0, addr_type:0, directed:false, phys:0, mac:wire_mac, data};
    let Some((detected, service)) = crate::pipeline::detect_format(&report, spec) else {
        return Ok(json!({"success":true,"decode_status":"unsupported_format","wire_format":null,"decoded":null,"error":"No supported service-data format in this advertisement"}));
    };
    let format = if device.forced_format.is_empty() { detected } else { device.forced_format.clone() };
    match crate::pipeline::decode(spec, &device, &format, service, &report) {
        Ok(decoded) => {
            let measurements = crate::pipeline::measurements(&decoded).into_iter().map(|measure| (measure.name.clone(), json!(measure.text()))).collect::<serde_json::Map<_, _>>();
            Ok(json!({"success":true,"decode_status":"ok","wire_format":format,"decoded":decoded.to_json(),"measurements":measurements}))
        },
        Err(error) => Ok(json!({"success":true,"decode_status":"failed","wire_format":format,"decoded":null,"error":error})),
    }
}

pub fn config_action(path: &Path, action: &str, input: &str) -> Result<Value, String> {
    if matches!(action,"availability-presets"|"automation-presets") {
        return Ok(json!({"success":true,"rule":crate::automation::AutomationRule::default()}));
    }
    if matches!(action,"availability-status"|"automation-status") {
        let config=Config::load(path,None,None)?;
        return crate::automation::status(&config.availability_state_file,&config.devices);
    }
    if matches!(action,"availability-test"|"automation-test") {
        let request:Value=serde_json::from_str(input).map_err(|_|"invalid webhook test request")?;
        if let Some(rule)=request.get("rule") {
            let rule=serde_json::from_value(rule.clone()).map_err(|_|"invalid availability test rule")?;
            return crate::automation::test_rule(&rule);
        }
        let webhook=request.get("rule").and_then(|rule|rule.get("webhook"))
            .or_else(||request.get("webhook")).or_else(||request.get("automation").and_then(|automation|automation.get("webhook")))
            .ok_or("missing availability webhook configuration")?;
        let webhook=serde_json::from_value(webhook.clone()).map_err(|_|"invalid availability webhook configuration")?;
        return crate::automation::test_webhook(&webhook);
    }
    if action == "history-presets" {
        return Ok(json!({"success":true,"maintenance":crate::sqlite::MaintenanceConfig::default()}));
    }
    if action == "attributes" {
        return Ok(json!({"success":true,"attributes":crate::pipeline::supported_attributes().collect::<Vec<_>>()}));
    }
    if action == "backups" {
        let prefix = format!("{}.", path.file_name().ok_or("invalid config path")?.to_string_lossy());
        let mut backups = Vec::new();
        for entry in std::fs::read_dir(path.parent().ok_or("invalid config path")?).map_err(|error| error.to_string())? {
            let entry = entry.map_err(|error| error.to_string())?;
            let name = entry.file_name().to_string_lossy().to_string();
            if name.starts_with(&prefix) && name[prefix.len()..].chars().all(|character| character.is_ascii_digit() || character == '-') && entry.file_type().is_ok_and(|kind| kind.is_file()) {
                backups.push(name);
            }
        }
        backups.sort();
        backups.reverse();
        return Ok(json!({"success":true,"backups":backups}));
    }
    if action == "restore" {
        let request: Value = serde_json::from_str(input).map_err(|_| "invalid JSON request")?;
        let name = request["backup"].as_str().ok_or("missing backup name")?;
        let backups = config_action(path, "backups", "")?;
        if !backups["backups"].as_array().unwrap().iter().any(|entry| entry.as_str() == Some(name)) { return Err("invalid backup selection".into()); }
        let config = Config::load(&path.parent().unwrap().join(name), None, None)?;
        return Ok(json!({"success":true,"config":config,"revision":revision(path)?,"yaml":serde_yaml::to_string(&config).map_err(|error| error.to_string())?}));
    }
    if action == "read" {
        let config = Config::load(path, None, None)?;
        return Ok(json!({"success": true, "config": config, "revision": revision(path)?, "yaml": serde_yaml::to_string(&config).map_err(|error| error.to_string())?}));
    }
    if !matches!(action, "check" | "save") {
        return Err("unknown configuration action".into());
    }
    let request: Value = serde_json::from_str(input).map_err(|_| "invalid JSON request")?;
    let mut config: Config = if let Some(config) = request.get("config") {
        serde_json::from_value(config.clone()).map_err(|_| "invalid configuration structure")?
    } else if let Some(yaml) = request.get("yaml").and_then(Value::as_str) {
        serde_yaml::from_str(yaml).map_err(|_| "invalid YAML configuration")?
    } else {
        return Err("missing configuration".into());
    };
    config.prepare_availability(path)?;
    config.validate()?;
    if action == "save" {
        if request.get("revision").and_then(Value::as_str) != Some(revision(path)?.as_str()) {
            return Err("configuration changed on disk; reload before saving".into());
        }
        config.save(path)?;
    }
    Ok(json!({"success": true, "config": config, "revision": revision(path)?, "yaml": serde_yaml::to_string(&config).map_err(|error| error.to_string())?}))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn control_socket_refuses_symlinked_private_directory() {
        let directory=std::env::temp_dir().join(format!("ble2uart-control-owner-{}",std::process::id()));
        std::fs::create_dir_all(directory.join("real")).unwrap();
        std::os::unix::fs::symlink(directory.join("real"),directory.join("linked")).unwrap();
        let before=std::fs::metadata(directory.join("real")).unwrap().permissions().mode();
        assert!(ControlServer::bind_path(directory.join("linked/control.sock")).is_err());
        assert_eq!(std::fs::metadata(directory.join("real")).unwrap().permissions().mode(),before);
        std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn isolated_control_sockets_do_not_interfere() {
        let directory=std::env::temp_dir().join(format!("ble-control-isolation-{}",std::process::id()));
        let first=directory.join("first/control.sock");
        let second=directory.join("second/control.sock");
        let owner=ControlServer::bind_path(first.clone()).unwrap();
        let isolated=ControlServer::bind_path(second.clone()).unwrap();
        assert!(first.exists()&&second.exists());
        assert!(ControlServer::bind_path(first.clone()).is_err());
        drop(isolated);
        assert!(first.exists()&&!second.exists());
        drop(owner);
        assert!(!first.exists());
        std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn supported_attributes_are_available_without_a_configuration() {
        let response = config_action(Path::new("/dev/null/config.yaml"), "attributes", "").unwrap();
        assert_eq!(response["success"], true);
        let attributes = response["attributes"].as_array().unwrap();
        assert!(attributes.contains(&json!("flooding")));
        assert!(attributes.contains(&json!("battery_level")));
        let names: std::collections::HashSet<_> = attributes.iter().map(|name| name.as_str().unwrap()).collect();
        assert_eq!(names.len(), attributes.len());
        assert_eq!(names.len(), crate::pipeline::supported_attributes().count());
    }

    #[test]
    fn inspection_decodes_native_advertisements_without_exposing_keys() {
        let directory = std::env::temp_dir().join(format!("ble-inspect-{}", std::process::id()));
        std::fs::create_dir_all(&directory).unwrap();
        let path = directory.join("config.yaml");
        Config::default().save(&path).unwrap();
        let spec = crate::codec::spec::Spec::embedded().unwrap();
        let request = json!({"observation":{"mac":"A4C1383406CE","data":"0D16D2FC4000EB0C3E0B10001101"},"device":{"mac":"A4C1383406CE","enabled":false,"bindkey":"11111111111111111111111111111111"}});
        let decoded = inspect(&path, &spec, &request.to_string()).unwrap();
        assert_eq!(decoded["decode_status"], "ok");
        assert_eq!(decoded["wire_format"], "bt_home_v2");
        assert_eq!(decoded["measurements"]["switch"], "0");
        assert_eq!(decoded["measurements"]["opened"], "1");
        assert!(!decoded.to_string().contains("11111111111111111111111111111111"));
        assert!(!decoded["decoded"].is_null());
        let unsupported = json!({"observation":{"mac":"A4C1383406CE","data":"020106"}});
        assert_eq!(inspect(&path, &spec, &unsupported.to_string()).unwrap()["decode_status"], "unsupported_format");
        let mut invalid = request.clone();
        invalid["observation"]["data"] = json!("not hex");
        assert!(inspect(&path, &spec, &invalid.to_string()).is_err());
        invalid = request;
        invalid["device"]["mac"] = json!("AABBCCDDEEFF");
        assert!(inspect(&path, &spec, &invalid.to_string()).is_err());
        let mut oversized = vec![229, 0x16, 0xD2, 0xFC, 0x40];
        oversized.extend(vec![0; 222]);
        oversized.extend([2, 0, 0]);
        let offline = json!({"observation":{"mac":"A4C1383406CE","data":crate::codec::value::hex(&oversized)}});
        assert!(inspect(&path, &spec, &offline.to_string()).is_err());
        assert_eq!(inspect_capture(&path, &spec, &offline.to_string()).unwrap()["decode_status"], "ok");
        std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn advertisement_cursors_are_independent_bounded_and_work_without_discovery() {
        let spec = crate::codec::spec::Spec::embedded().unwrap();
        let mut discovery = Discovery::default();
        let config = Config::default();
        let report = crate::link::AdvReport {rssi:-70, event_type:1, addr_type:0,
            directed:false, phys:0x33, mac:[0xCE,0x06,0x34,0x38,0xC1,0xA4],
            data:vec![2,1,6]};
        for _ in 0..300 { discovery.observe(&report, &spec, &config); }
        let first = discovery.advertisement_events(0);
        assert_eq!(first["cursor"], 300);
        assert_eq!(first["dropped"], 44);
        assert_eq!(first["events"].as_array().unwrap().len(), 256);
        assert_eq!(first, discovery.advertisement_events(0));
        assert_eq!(discovery.advertisement_events(299)["events"].as_array().unwrap().len(), 1);
        assert_eq!(discovery.advertisement_events(300)["events"], json!([]));
        assert!(discovery.until.is_none());
    }

    #[test]
    fn discovery_tracks_mac_name_format_vendor_and_deadline() {
        let spec = crate::codec::spec::Spec::embedded().unwrap();
        let mut discovery = Discovery::default();
        assert!(discovery.start(0).is_err());
        assert!(discovery.start(301).is_err());
        discovery.start(10).unwrap();
        let mut config = Config::default();
        config.devices.push(serde_yaml::from_str("mac: A4C1383406CE").unwrap());
        let mut report = crate::link::AdvReport {rssi:-70, event_type:1, addr_type:0, directed:false, phys:0x33, mac:[0xCE,0x06,0x34,0x38,0xC1,0xA4], data:vec![4,9,b'A',b'T',b'C',5,0x16,0xD2,0xFC,0x40,0]};
        discovery.observe(&report, &spec, &config);
        report.data = vec![5,0x16,0xD2,0xFC,0x40,0];
        discovery.observe(&report, &spec, &config);
        let status = discovery.snapshot(true);
        assert_eq!(status["devices"][0]["name"], "ATC");
        assert_eq!(status["devices"][0]["format"], "bt_home_v2");
        assert_eq!(status["devices"][0]["count"], 2);
        assert_eq!(status["devices"][0]["configured"], true);
        assert!(status["devices"][0]["vendor"].as_str().unwrap().contains("Telink"));
        assert_eq!(vendor(&report.mac, 1), "Random / local address");
        assert!(!discovery.expired());
        discovery.until = Some(Instant::now());
        assert!(discovery.expired());
        for index in 0..1024 { discovery.devices.insert(format!("random{index}"), json!({})); }
        report.mac[0] = 0xDD;
        discovery.observe(&report, &spec, &config);
        assert_eq!(discovery.overflow, 1);
        discovery.until = None;
        discovery.observe(&report, &spec, &config);
        assert_eq!(discovery.overflow, 1);
    }

    #[test]
    fn web_configuration_exposes_all_frontends_for_legacy_yaml() {
        let directory = std::env::temp_dir().join(format!("ble-web-frontends-{}", std::process::id()));
        std::fs::create_dir_all(&directory).unwrap();
        let path = directory.join("config.yaml");
        let legacy = "frontends:\n  mqtt: {enabled: false}\n  mysensors: {enabled: false}\n  matter: {enabled: false}\n  influx: {enabled: false}\n";
        std::fs::write(&path, legacy).unwrap();
        let mut request = config_action(&path, "read", "").unwrap();
        let frontends = request["config"]["frontends"].as_object().unwrap();
        assert_eq!(frontends.len(), 5);
        for name in ["mysensors", "mqtt", "matter", "influx", "sqlite"] {
            assert!(frontends.contains_key(name), "missing frontend {name}");
        }
        assert_eq!(frontends["sqlite"], serde_json::to_value(crate::sqlite::SqliteConfig::default()).unwrap());
        assert_eq!(std::fs::read_to_string(&path).unwrap(), legacy);
        request["config"]["frontends"]["sqlite"]["enabled"] = json!(true);
        request["config"]["frontends"]["sqlite"]["path"] = json!(directory.join("readings.sqlite3"));
        let checked = config_action(&path, "check", &request.to_string()).unwrap();
        assert_eq!(checked["config"]["frontends"]["sqlite"], request["config"]["frontends"]["sqlite"]);
        config_action(&path, "save", &request.to_string()).unwrap();
        let loaded = config_action(&path, "read", "").unwrap();
        assert_eq!(loaded["config"]["frontends"]["sqlite"], request["config"]["frontends"]["sqlite"]);
        let presets = config_action(&path, "history-presets", "").unwrap();
        request["revision"] = loaded["revision"].clone();
        request["config"]["frontends"]["sqlite"]["maintenance"] = presets["maintenance"].clone();
        request["config"]["frontends"]["sqlite"]["maintenance"]["enabled"] = json!(true);
        config_action(&path, "save", &request.to_string()).unwrap();
        let history = config_action(&path, "read", "").unwrap();
        assert_eq!(history["config"]["frontends"]["sqlite"]["maintenance"], request["config"]["frontends"]["sqlite"]["maintenance"]);
        request["config"]["frontends"]["sqlite"]["maintenance"]["policies"][0]["tiers"][1]["max_age_s"] = json!(1);
        assert!(config_action(&path, "check", &request.to_string()).is_err());
        std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn web_configuration_is_validated_atomic_and_conflict_checked() {
        let directory = std::env::temp_dir().join(format!("ble-web-config-{}", std::process::id()));
        std::fs::create_dir_all(&directory).unwrap();
        let path = directory.join("config.yaml");
        Config::default().save(&path).unwrap();
        let mut request = config_action(&path, "read", "").unwrap();
        request["config"]["devices"] = json!([{"mac":"AABBCCDDEEFF", "label":"Test } </pre> \" device", "enabled":true}]);
        request["config"]["devices"][0]["manufacturer"] = json!("Xiaomi");
        request["config"]["devices"][0]["model"] = json!("LYWSD03MMC");
        request["config"]["devices"][0]["firmware_version"] = json!("custom build");
        let checked = config_action(&path, "check", &request.to_string()).unwrap();
        assert_eq!(checked["config"]["devices"][0]["label"], "Test } </pre> \" device");
        assert_eq!(checked["config"]["devices"][0]["manufacturer"], "Xiaomi");
        assert!(Config::load(&path, None, None).unwrap().devices.is_empty());
        let saved = config_action(&path, "save", &request.to_string()).unwrap();
        assert_eq!(Config::load(&path, None, None).unwrap().devices[0].metadata().model, "LYWSD03MMC");
        assert_eq!(saved["config"]["devices"][0]["firmware_version"], "custom build");
        assert_ne!(saved["revision"], request["revision"]);
        assert!(config_action(&path, "save", &request.to_string()).is_err());
        request["revision"] = saved["revision"].clone();
        request["config"]["devices"][0]["bindkey"] = json!("invalid secret");
        assert!(config_action(&path, "save", &request.to_string()).is_err());
        assert_eq!(Config::load(&path, None, None).unwrap().devices.len(), 1);
        let history = config_action(&path, "backups", "").unwrap();
        let restored = config_action(&path, "restore", &json!({"backup":history["backups"][0]}).to_string()).unwrap();
        assert!(restored["config"]["devices"].as_array().unwrap().is_empty());
        assert_eq!(Config::load(&path, None, None).unwrap().devices.len(), 1);
        assert!(config_action(&path, "restore", "{\"backup\":\"../config.yaml\"}").is_err());
        std::fs::remove_dir_all(directory).unwrap();
    }
}