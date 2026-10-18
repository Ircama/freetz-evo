use rusqlite::{params, types::Value as SqlValue, Connection, OpenFlags, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs::OpenOptions;
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;
use std::sync::{
    atomic::{AtomicBool, AtomicUsize, Ordering},
    mpsc::{self, Receiver, SyncSender},
    Arc,
};
use std::thread::JoinHandle;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const APPLICATION_ID: i64 = 0x424c4531;
const SCHEMA: &str = "
CREATE TABLE frames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at_ns INTEGER NOT NULL,
    mac TEXT NOT NULL,
    sensor_name TEXT NOT NULL,
    wire_format TEXT NOT NULL,
    state_json TEXT NOT NULL
);
CREATE INDEX frames_mac_time ON frames(mac, received_at_ns);
CREATE INDEX frames_time ON frames(received_at_ns);
CREATE TABLE measurements (
    frame_id INTEGER NOT NULL REFERENCES frames(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    attribute TEXT NOT NULL,
    unit TEXT NOT NULL,
    type TEXT NOT NULL,
    value_real REAL,
    value_int INTEGER,
    value_text TEXT,
    PRIMARY KEY (frame_id, ordinal),
    CHECK (
        (type IN ('integer', 'boolean') AND value_int IS NOT NULL AND value_real IS NULL AND value_text IS NULL)
        OR (type = 'real' AND value_real IS NOT NULL AND value_int IS NULL AND value_text IS NULL)
        OR (type IN ('text', 'unsigned', 'json') AND value_text IS NOT NULL AND value_int IS NULL AND value_real IS NULL)
        OR (type = 'null' AND value_real IS NULL AND value_int IS NULL AND value_text IS NULL)
    ),
    CHECK (type != 'boolean' OR value_int IN (0, 1))
);
CREATE INDEX measurements_attribute_frame ON measurements(attribute, frame_id);
PRAGMA application_id = 0x424c4531;
PRAGMA user_version = 1;
";

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct SqliteConfig {
    pub enabled: bool,
    pub path: String,
    pub batch_size: usize,
    pub queue_capacity: usize,
    pub flush_interval_ms: u64,
    pub busy_timeout_ms: u64,
}

impl Default for SqliteConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            path: String::new(),
            batch_size: 100,
            queue_capacity: 1024,
            flush_interval_ms: 1000,
            busy_timeout_ms: 1000,
        }
    }
}

impl SqliteConfig {
    pub fn validate(&self) -> Result<(), String> {
        if !Path::new(&self.path).is_absolute() || self.path.chars().any(char::is_control) {
            return Err("SQLite path must be an absolute local file path without control characters".into());
        }
        if !(1..=1024).contains(&self.batch_size) || !(1..=16384).contains(&self.queue_capacity)
            || self.batch_size > self.queue_capacity || !(10..=60000).contains(&self.flush_interval_ms)
            || !(1..=5000).contains(&self.busy_timeout_ms)
        {
            return Err("SQLite batch/queue or flush/busy timeout limits are invalid".into());
        }
        Ok(())
    }
}

struct Frame {
    timestamp_ns: i64,
    state: Value,
}

impl Frame {
    fn new(state: &Value) -> Result<Self, String> {
        if state["mac"].as_str().is_none_or(str::is_empty) {
            return Err("SQLite frame is missing its MAC".into());
        }
        let measurements = state["measurements"].as_array().ok_or("SQLite frame is missing measurements")?;
        for measurement in measurements {
            if measurement["name"].as_str().is_none_or(str::is_empty) || measurement.get("value").is_none() {
                return Err("SQLite measurement is missing its name or value".into());
            }
        }
        let timestamp_ns = SystemTime::now().duration_since(UNIX_EPOCH)
            .map_err(|error| format!("SQLite receive timestamp unavailable: {error}"))?.as_nanos();
        let timestamp_ns = i64::try_from(timestamp_ns).map_err(|error| format!("SQLite timestamp out of range: {error}"))?;
        Ok(Self { timestamp_ns, state: state.clone() })
    }
}

fn open(config: &SqliteConfig) -> Result<Connection, String> {
    // Do not create parent directories: an absent USB mount must fail, not fill internal flash.
    match OpenOptions::new().write(true).create_new(true).mode(0o600).open(&config.path) {
        Ok(_) => {}
        Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {}
        Err(error) => return Err(format!("cannot create SQLite database {}: {error}", config.path)),
    }
    let initialize = || -> rusqlite::Result<Connection> {
        let mut connection = Connection::open_with_flags(
            &config.path, OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_NO_MUTEX,
        )?;
        connection.busy_timeout(Duration::from_millis(config.busy_timeout_ms))?;
        let application: i64 = connection.query_row("PRAGMA application_id", [], |row| row.get(0))?;
        let version: i64 = connection.query_row("PRAGMA user_version", [], |row| row.get(0))?;
        let tables: i64 = connection.query_row(
            "SELECT count(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'", [], |row| row.get(0),
        )?;
        if !((application == APPLICATION_ID && version == 1) || (application == 0 && version == 0 && tables == 0)) {
            return Err(rusqlite::Error::InvalidParameterName(
                format!("not a supported ble2uart-gateway database (application_id={application}, version={version})"),
            ));
        }
        let mode: String = connection.query_row("PRAGMA journal_mode=WAL", [], |row| row.get(0))?;
        if !mode.eq_ignore_ascii_case("wal") {
            return Err(rusqlite::Error::InvalidParameterName(format!("WAL unavailable: {mode}")));
        }
        connection.execute_batch("PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;")?;
        if version == 0 {
            let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
            transaction.execute_batch(SCHEMA)?;
            transaction.commit()?;
        }
        Ok(connection)
    };
    initialize().map_err(|error| format!("cannot initialize SQLite database {}: {error}", config.path))
}

fn typed_value(value: &Value) -> (&'static str, SqlValue, SqlValue, SqlValue) {
    let null = SqlValue::Null;
    match value {
        Value::Bool(value) => ("boolean", null.clone(), SqlValue::Integer(i64::from(*value)), null),
        Value::Number(value) => {
            if let Some(value) = value.as_i64() {
                ("integer", null.clone(), SqlValue::Integer(value), null)
            } else if let Some(value) = value.as_u64() {
                ("unsigned", null.clone(), null, SqlValue::Text(value.to_string()))
            } else {
                ("real", SqlValue::Real(value.as_f64().expect("JSON floating point number")), null.clone(), null)
            }
        }
        Value::String(value) => ("text", null.clone(), null, SqlValue::Text(value.clone())),
        Value::Null => ("null", null.clone(), null.clone(), null),
        Value::Array(_) | Value::Object(_) => ("json", null.clone(), null, SqlValue::Text(value.to_string())),
    }
}

fn write_batch(connection: &mut Connection, frames: &[Frame]) -> rusqlite::Result<()> {
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    {
        let mut insert_frame = transaction.prepare_cached(
            "INSERT INTO frames(received_at_ns,mac,sensor_name,wire_format,state_json) VALUES (?1,?2,?3,?4,?5)",
        )?;
        let mut insert_measurement = transaction.prepare_cached(
            "INSERT INTO measurements(frame_id,ordinal,attribute,unit,type,value_real,value_int,value_text)
             VALUES (?1,?2,?3,?4,?5,?6,?7,?8)",
        )?;
        for frame in frames {
            let state = &frame.state;
            insert_frame.execute(params![
                frame.timestamp_ns, state["mac"].as_str(), state["label"].as_str().unwrap_or(""),
                state["wire_format"].as_str().unwrap_or(""), state.to_string(),
            ])?;
            let id = transaction.last_insert_rowid();
            for (ordinal, measurement) in state["measurements"].as_array().expect("validated frame").iter().enumerate() {
                let (kind, real, integer, text) = typed_value(&measurement["value"]);
                insert_measurement.execute(params![
                    id, ordinal as i64, measurement["name"].as_str(),
                    measurement["unit"].as_str().unwrap_or(""), kind, real, integer, text,
                ])?;
            }
        }
    }
    transaction.commit()
}

fn run_worker(mut connection: Connection, config: SqliteConfig, receiver: Receiver<Frame>, stopped: Arc<AtomicBool>) {
    let interval = Duration::from_millis(config.flush_interval_ms);
    let mut deadline = Instant::now() + interval;
    let mut pending = Vec::with_capacity(config.batch_size);
    let mut failures = 0usize;
    while !stopped.load(Ordering::Relaxed) {
        if pending.len() < config.batch_size {
            let timeout = deadline.saturating_duration_since(Instant::now()).min(Duration::from_millis(100));
            match receiver.recv_timeout(timeout) {
                Ok(frame) => pending.push(frame),
                Err(mpsc::RecvTimeoutError::Timeout) => {}
                Err(mpsc::RecvTimeoutError::Disconnected) => break,
            }
        } else if failures > 0 && Instant::now() < deadline {
            std::thread::park_timeout(deadline.saturating_duration_since(Instant::now()).min(Duration::from_millis(100)));
        }
        if pending.is_empty() {
            deadline = Instant::now() + interval;
            continue;
        }
        if Instant::now() < deadline && (failures > 0 || pending.len() < config.batch_size) { continue; }
        match write_batch(&mut connection, &pending) {
            Ok(()) => {
                if failures > 0 { log::info!("SQLite writer recovered; {} pending frames committed", pending.len()); }
                pending.clear();
                failures = 0;
            }
            Err(error) => {
                if failures % 30 == 0 {
                    log::error!("SQLite write failed: {error}; retaining {} frames for retry", pending.len());
                }
                failures = failures.saturating_add(1);
            }
        }
        deadline = Instant::now() + interval;
    }
    pending.extend(receiver.try_iter());
    if !pending.is_empty() {
        if let Err(error) = write_batch(&mut connection, &pending) {
            log::error!("SQLite shutdown lost {} uncommitted frames: {error}; memory queue is not a persistent spool", pending.len());
        }
    }
}

pub struct SqlitePublisher {
    sender: SyncSender<Frame>,
    stopped: Arc<AtomicBool>,
    worker: Option<JoinHandle<()>>,
    dropped: AtomicUsize,
}

impl SqlitePublisher {
    pub fn start(config: &SqliteConfig) -> Result<Self, String> {
        config.validate()?;
        if !config.enabled { return Err("SQLite frontend is disabled".into()); }
        let connection = open(config)?;
        let (sender, receiver) = mpsc::sync_channel(config.queue_capacity);
        let stopped = Arc::new(AtomicBool::new(false));
        let worker_stopped = Arc::clone(&stopped);
        let worker_config = config.clone();
        let worker = std::thread::Builder::new().name("ble-sqlite".into())
            .spawn(move || run_worker(connection, worker_config, receiver, worker_stopped))
            .map_err(|error| format!("cannot start SQLite writer: {error}"))?;
        log::info!("SQLite recording to {} (WAL, schema 1)", config.path);
        Ok(Self { sender, stopped, worker: Some(worker), dropped: AtomicUsize::new(0) })
    }

    pub fn publish(&self, state: &Value) {
        let frame = match Frame::new(state) {
            Ok(frame) => frame,
            Err(error) => { log::error!("SQLite frame rejected: {error}"); return; }
        };
        if let Err(error) = self.sender.try_send(frame) {
            let dropped = self.dropped.fetch_add(1, Ordering::Relaxed) + 1;
            if dropped == 1 || dropped % 100 == 0 {
                log::error!("SQLite frame not queued ({error}); {dropped} frames dropped");
            }
        }
    }
}

impl Drop for SqlitePublisher {
    fn drop(&mut self) {
        self.stopped.store(true, Ordering::Relaxed);
        if let Some(worker) = self.worker.take() {
            if worker.join().is_err() { log::error!("SQLite writer thread panicked"); }
        }

        #[cfg(test)]
        mod tests {
            use super::*;
            use std::os::unix::fs::PermissionsExt;

            struct Database {
                directory: std::path::PathBuf,
                config: SqliteConfig,
            }

            impl Database {
                fn new() -> Self {
                    static NEXT: AtomicUsize = AtomicUsize::new(0);
                    let directory = std::env::temp_dir().join(format!(
                        "ble-sqlite-{}-{}", std::process::id(), NEXT.fetch_add(1, Ordering::Relaxed),
                    ));
                    std::fs::create_dir(&directory).unwrap();
                    let config = SqliteConfig {
                        enabled: true, path: directory.join("readings.sqlite3").to_str().unwrap().into(),
                        batch_size: 1, flush_interval_ms: 10, busy_timeout_ms: 20,
                        ..Default::default()
                    };
                    Self { directory, config }
                }
            }

            impl Drop for Database {
                fn drop(&mut self) {
                    std::fs::remove_dir_all(&self.directory).unwrap();
                }
            }

            fn state() -> Value {
                serde_json::json!({
                    "mac": "AABBCCDDEEFF", "label": "Outside", "wire_format": "bt_home_v2",
                    "device": {"manufacturer": "Test", "model": "Multi"},
                    "radio": {"rssi": -65},
                    "measurements": [
                        {"name": "temperature", "value": 16.34, "unit": "C"},
                        {"name": "humidity", "value": 82.89, "unit": "%"},
                        {"name": "battery_level", "value": 100, "unit": "%"},
                        {"name": "opened", "value": false, "unit": ""},
                        {"name": "counter", "value": -9007199254740993_i64, "unit": ""},
                        {"name": "unsigned", "value": u64::MAX, "unit": ""},
                        {"name": "message", "value": "ready", "unit": ""},
                        {"name": "raw", "value": [0, 255], "unit": ""},
                        {"name": "missing", "value": null, "unit": ""},
                        {"name": "temperature", "value": 17.34, "unit": "C"}
                    ]
                })
            }

            #[test]
            fn sqlite_configuration_defaults_validation_and_roundtrip() {
                let mut config = crate::config::Config::default();
                assert!(!config.frontends.sqlite.enabled);
                config.validate().unwrap();
                config.frontends.sqlite.enabled = true;
                assert!(config.validate().is_err());
                config.frontends.sqlite.path = "/tmp/readings.sqlite3".into();
                config.validate().unwrap();
                let yaml = serde_yaml::to_string(&config).unwrap();
                let restored: crate::config::Config = serde_yaml::from_str(&yaml).unwrap();
                assert!(restored.frontends.sqlite.enabled);
                assert_eq!(restored.frontends.sqlite.path, "/tmp/readings.sqlite3");
                for path in ["", ":memory:", "file:/tmp/a", "relative.db", "/tmp/bad\n.db"] {
                    config.frontends.sqlite.path = path.into();
                    assert!(config.validate().is_err(), "{path}");
                }
                config.frontends.sqlite.path = "/tmp/readings.sqlite3".into();
                config.frontends.sqlite.batch_size = config.frontends.sqlite.queue_capacity + 1;
                assert!(config.validate().is_err());
                assert!(serde_yaml::from_str::<SqliteConfig>("unknown: true").is_err());
                assert!(Frame::new(&serde_json::json!({"mac":"A","measurements":[{"name":"x"}]})).is_err());
            }

            #[test]
            fn sqlite_preserves_complete_multimeasure_frames_and_exact_types_after_reopen() {
                let database = Database::new();
                {
                    let mut connection = open(&database.config).unwrap();
                    let mut frame = Frame::new(&state()).unwrap();
                    frame.timestamp_ns = 1792356358293394316;
                    write_batch(&mut connection, &[frame]).unwrap();
                }
                let connection = open(&database.config).unwrap();
                let (timestamp, mac, name, format, json): (i64, String, String, String, String) = connection.query_row(
                    "SELECT received_at_ns,mac,sensor_name,wire_format,state_json FROM frames", [],
                    |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?, row.get(4)?)),
                ).unwrap();
                assert_eq!(timestamp, 1792356358293394316);
                assert_eq!((mac.as_str(), name.as_str(), format.as_str()), ("AABBCCDDEEFF", "Outside", "bt_home_v2"));
                assert_eq!(serde_json::from_str::<Value>(&json).unwrap(), state());
                let rows: Vec<(String, SqlValue, SqlValue, SqlValue)> = connection.prepare(
                    "SELECT type,value_real,value_int,value_text FROM measurements ORDER BY ordinal",
                ).unwrap().query_map([], |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)))
                    .unwrap().collect::<rusqlite::Result<_>>().unwrap();
                let null = SqlValue::Null;
                assert_eq!(rows, vec![
                    ("real".into(), SqlValue::Real(16.34), null.clone(), null.clone()),
                    ("real".into(), SqlValue::Real(82.89), null.clone(), null.clone()),
                    ("integer".into(), null.clone(), SqlValue::Integer(100), null.clone()),
                    ("boolean".into(), null.clone(), SqlValue::Integer(0), null.clone()),
                    ("integer".into(), null.clone(), SqlValue::Integer(-9007199254740993), null.clone()),
                    ("unsigned".into(), null.clone(), null.clone(), SqlValue::Text(u64::MAX.to_string())),
                    ("text".into(), null.clone(), null.clone(), SqlValue::Text("ready".into())),
                    ("json".into(), null.clone(), null.clone(), SqlValue::Text("[0,255]".into())),
                    ("null".into(), null.clone(), null.clone(), null.clone()),
                    ("real".into(), SqlValue::Real(17.34), null.clone(), null),
                ]);
                assert_eq!(std::fs::metadata(&database.config.path).unwrap().permissions().mode() & 0o777, 0o600);
                assert!(connection.execute(
                    "UPDATE measurements SET value_int=5 WHERE ordinal=0", [],
                ).is_err());
                connection.execute("DELETE FROM frames", []).unwrap();
                assert_eq!(connection.query_row("SELECT count(*) FROM measurements", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
            }

            #[test]
            fn sqlite_failed_batch_rolls_back_frames_and_all_measurements() {
                let database = Database::new();
                let mut connection = open(&database.config).unwrap();
                connection.execute_batch(
                    "CREATE TRIGGER reject_frame BEFORE INSERT ON measurements WHEN NEW.attribute='bad'
                     BEGIN SELECT RAISE(ABORT, 'test failure'); END;",
                ).unwrap();
                let good = Frame::new(&state()).unwrap();
                let mut bad = state();
                bad["measurements"][1]["name"] = "bad".into();
                assert!(write_batch(&mut connection, &[good, Frame::new(&bad).unwrap()]).is_err());
                for table in ["frames", "measurements"] {
                    assert_eq!(connection.query_row(&format!("SELECT count(*) FROM {table}"), [], |row| row.get::<_, i64>(0)).unwrap(), 0);
                }
            }

            #[test]
            fn sqlite_wal_reader_keeps_consistent_snapshot_without_blocking_writer() {
                let database = Database::new();
                let mut writer = open(&database.config).unwrap();
                write_batch(&mut writer, &[Frame::new(&state()).unwrap()]).unwrap();
                let reader = Connection::open_with_flags(&database.config.path, OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap();
                reader.execute_batch("BEGIN").unwrap();
                assert_eq!(reader.query_row("SELECT count(*) FROM frames", [], |row| row.get::<_, i64>(0)).unwrap(), 1);
                write_batch(&mut writer, &[Frame::new(&state()).unwrap()]).unwrap();
                assert_eq!(reader.query_row("SELECT count(*) FROM frames", [], |row| row.get::<_, i64>(0)).unwrap(), 1);
                reader.execute_batch("COMMIT").unwrap();
                assert_eq!(reader.query_row("SELECT count(*) FROM frames", [], |row| row.get::<_, i64>(0)).unwrap(), 2);
                assert_eq!(reader.query_row("SELECT count(*) FROM measurements", [], |row| row.get::<_, i64>(0)).unwrap(), 20);
            }

            #[test]
            fn sqlite_worker_retries_locked_database_and_flushes_on_shutdown() {
                let database = Database::new();
                let publisher = SqlitePublisher::start(&database.config).unwrap();
                let lock = Connection::open(&database.config.path).unwrap();
                lock.execute_batch("BEGIN IMMEDIATE").unwrap();
                publisher.publish(&state());
                std::thread::sleep(Duration::from_millis(100));
                assert_eq!(lock.query_row("SELECT count(*) FROM frames", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
                lock.execute_batch("ROLLBACK").unwrap();
                let deadline = Instant::now() + Duration::from_secs(3);
                loop {
                    let count: i64 = lock.query_row("SELECT count(*) FROM frames", [], |row| row.get(0)).unwrap();
                    if count == 1 { break; }
                    assert!(Instant::now() < deadline, "writer did not recover");
                    std::thread::sleep(Duration::from_millis(10));
                }
                publisher.publish(&state());
                drop(publisher);
                assert_eq!(lock.query_row("SELECT count(*) FROM frames", [], |row| row.get::<_, i64>(0)).unwrap(), 2);
            }

            #[test]
            fn sqlite_queue_is_bounded_and_missing_storage_or_foreign_database_is_rejected() {
                let (sender, receiver) = mpsc::sync_channel(1);
                let publisher = SqlitePublisher {
                    sender, stopped: Arc::new(AtomicBool::new(false)), worker: None, dropped: AtomicUsize::new(0),
                };
                publisher.publish(&state());
                publisher.publish(&state());
                assert_eq!(publisher.dropped.load(Ordering::Relaxed), 1);
                assert!(receiver.try_recv().is_ok());
                assert!(receiver.try_recv().is_err());
                let mut database = Database::new();
                database.config.path = database.directory.join("absent/readings.db").to_str().unwrap().into();
                assert!(SqlitePublisher::start(&database.config).is_err());
                assert!(!database.directory.join("absent").exists());
                database.config.path = database.directory.join("other.db").to_str().unwrap().into();
                let other = Connection::open(&database.config.path).unwrap();
                other.execute_batch("CREATE TABLE unrelated(value TEXT)").unwrap();
                drop(other);
                assert!(SqlitePublisher::start(&database.config).is_err());
            }
        }
    }
}
