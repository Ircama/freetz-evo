use rusqlite::{params, types::Value as SqlValue, Connection, OpenFlags, TransactionBehavior};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fs::OpenOptions;
use std::os::unix::fs::OpenOptionsExt;
use std::path::Path;
use std::sync::{
    atomic::{AtomicBool, AtomicUsize, Ordering},
    mpsc::{self, Receiver, SyncSender},
    Arc, Mutex, MutexGuard, TryLockError,
};
use std::thread::JoinHandle;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const APPLICATION_ID: i64 = 0x424c4531;
pub(crate) const SCHEMA: &str = "
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

pub(crate) const HISTORY_SCHEMA: &str = "
CREATE TABLE history_devices (
    mac TEXT PRIMARY KEY,
    sensor_name TEXT NOT NULL,
    device_json TEXT NOT NULL CHECK(json_valid(device_json))
);
CREATE TABLE history_series (
    id INTEGER PRIMARY KEY,
    mac TEXT NOT NULL REFERENCES history_devices(mac),
    attribute TEXT NOT NULL,
    unit TEXT NOT NULL,
    UNIQUE(mac, attribute, unit)
);
CREATE TABLE history_samples (
    id INTEGER PRIMARY KEY,
    series_id INTEGER NOT NULL REFERENCES history_series(id),
    received_at_ns INTEGER NOT NULL,
    type TEXT NOT NULL,
    value_json TEXT NOT NULL CHECK(json_valid(value_json))
);
CREATE INDEX history_series_time ON history_samples(series_id, received_at_ns, id);
CREATE INDEX history_series_order ON history_samples(series_id, id);
CREATE VIEW history AS
    SELECT series.mac, device.sensor_name, series.attribute, series.unit,
           sample.received_at_ns, sample.type, sample.value_json
    FROM history_samples sample
    JOIN history_series series ON series.id=sample.series_id
    JOIN history_devices device ON device.mac=series.mac
    UNION ALL
    SELECT frame.mac, frame.sensor_name, measure.attribute, measure.unit,
           frame.received_at_ns, measure.type,
           CASE measure.type
             WHEN 'real' THEN printf('%!.17g',measure.value_real)
             WHEN 'integer' THEN CAST(measure.value_int AS TEXT)
             WHEN 'boolean' THEN CASE measure.value_int WHEN 0 THEN 'false' ELSE 'true' END
             WHEN 'text' THEN json_quote(measure.value_text)
             WHEN 'null' THEN 'null'
             ELSE measure.value_text
           END
    FROM measurements measure JOIN frames frame ON frame.id=measure.frame_id;
PRAGMA user_version = 2;
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
    pub maintenance: MaintenanceConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct MaintenanceConfig {
    pub enabled: bool,
    pub counter_mode: HistoryMode,
    pub interval_s: u64,
    pub batch_size: usize,
    pub max_work_ms: u64,
    pub raw_retention_s: u64,
    pub policies: Vec<HistoryPolicy>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum HistoryMode {
    #[default]
    KeepAll,
    Discard,
    Progressive,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(default, deny_unknown_fields)]
pub struct HistoryPolicy {
    pub mac: String,
    pub attribute: String,
    pub mode: HistoryMode,
    pub tiers: Vec<HistoryTier>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct HistoryTier {
    pub max_age_s: u64,
    pub sample_interval_s: u64,
}

fn discrete_attribute(attribute: &str) -> bool {
    matches!(attribute, "contact" | "door" | "opened" | "switch" | "boolean"
        | "motion" | "occupancy" | "water_leak" | "flooding" | "humidity_trigger"
        | "temp_trigger" | "out_gpio_trg_flag" | "out_gpio_trg_value" | "input_gpio_value" | "one")
}

fn counter_attribute(attribute: &str) -> bool {
    matches!(attribute, "counter" | "packet_id" | "count_id" | "count_i" | "count_s"
        | "count_m" | "count_l" | "counter8" | "counter16" | "counter32")
}

impl Default for MaintenanceConfig {
    fn default() -> Self {
        let temperature = [(600, 0), (3600, 60), (86400, 150), (604800, 3600),
            (4838400, 14400), (63072000, 21600)];
        let battery = [(3600, 900), (86400, 3600), (604800, 14400),
            (4838400, 86400), (63072000, 172800)];
        let mut policies = Vec::new();
        for (attribute, bands) in [("temperature", temperature.as_slice()),
            ("battery_level", battery.as_slice()), ("battery", battery.as_slice()),
            ("battery_v", battery.as_slice()), ("voltage", battery.as_slice())] {
            policies.push(HistoryPolicy {
                mac: String::new(), attribute: attribute.into(), mode: HistoryMode::Progressive,
                tiers: bands.iter().map(|&(max_age_s, sample_interval_s)|
                    HistoryTier { max_age_s, sample_interval_s }).collect(),
            });
        }
        Self { enabled: false, counter_mode: HistoryMode::Discard, interval_s: 300, batch_size: 100, max_work_ms: 100,
            raw_retention_s: 600, policies }
    }
}

impl MaintenanceConfig {
    pub fn validate(&self) -> Result<(), String> {
        if self.counter_mode == HistoryMode::Progressive {
            return Err("SQLite default counter history must be discard or keep_all; use a per-attribute policy for progressive retention".into());
        }
        if !(1..=86400).contains(&self.interval_s) || !(1..=1000).contains(&self.batch_size)
            || !(10..=1000).contains(&self.max_work_ms)
            || !(1..=31536000).contains(&self.raw_retention_s) || self.policies.len() > 128 {
            return Err("SQLite maintenance interval/batch/work budget/raw retention limits are invalid".into());
        }
        let mut keys = std::collections::HashSet::new();
        for policy in &self.policies {
            let mac = if policy.mac.is_empty() { None } else { Some(crate::config::parse_mac(&policy.mac)?) };
            if policy.attribute.is_empty() || policy.attribute.len() > 128
                || !policy.attribute.bytes().all(|byte| byte.is_ascii_alphanumeric() || b"_.-".contains(&byte))
                || !keys.insert((mac, policy.attribute.as_str())) {
                return Err("SQLite history policies require a unique MAC/attribute and a valid attribute name".into());
            }
            if policy.mode == HistoryMode::KeepAll { continue; }
            if discrete_attribute(&policy.attribute) {
                return Err("SQLite boolean/discrete attributes must use keep_all history".into());
            }
            if policy.mode == HistoryMode::Discard { continue; }
            if policy.tiers.is_empty() || policy.tiers.len() > 16 {
                return Err("SQLite progressive history requires 1-16 age bands".into());
            }
            let mut previous_age = 0;
            let mut previous_interval = 0;
            for tier in &policy.tiers {
                if tier.max_age_s <= previous_age || tier.max_age_s > 3155760000
                    || tier.sample_interval_s < previous_interval || tier.sample_interval_s > tier.max_age_s {
                    return Err("SQLite history ages must increase and sampling intervals must not decrease (0 = every sample)".into());
                }
                previous_age = tier.max_age_s;
                previous_interval = tier.sample_interval_s;
            }
        }
        Ok(())
    }

    fn policy(&self, mac: &str, attribute: &str) -> Option<&HistoryPolicy> {
        let address = crate::config::parse_mac(mac).ok();
        self.policies.iter().find(|policy| policy.attribute == attribute && !policy.mac.is_empty()
            && crate::config::parse_mac(&policy.mac).ok() == address)
            .or_else(|| self.policies.iter().find(|policy| policy.attribute == attribute && policy.mac.is_empty()))
    }
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
            maintenance: MaintenanceConfig::default(),
        }
    }
}

impl SqliteConfig {
    pub fn validate(&self) -> Result<(), String> {
        if !Path::new(&self.path).is_absolute() || self.path.chars().any(char::is_control) {
            return Err(
                "SQLite path must be an absolute local file path without control characters".into(),
            );
        }
        if !(1..=1024).contains(&self.batch_size)
            || !(1..=16384).contains(&self.queue_capacity)
            || self.batch_size > self.queue_capacity
            || !(10..=60000).contains(&self.flush_interval_ms)
            || !(1..=5000).contains(&self.busy_timeout_ms)
        {
            return Err("SQLite batch/queue or flush/busy timeout limits are invalid".into());
        }
        self.maintenance.validate()
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
        let measurements = state["measurements"]
            .as_array()
            .ok_or("SQLite frame is missing measurements")?;
        for measurement in measurements {
            if measurement["name"].as_str().is_none_or(str::is_empty)
                || measurement.get("value").is_none()
            {
                return Err("SQLite measurement is missing its name or value".into());
            }
        }
        let timestamp_ns = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|error| format!("SQLite receive timestamp unavailable: {error}"))?
            .as_nanos();
        let timestamp_ns = i64::try_from(timestamp_ns)
            .map_err(|error| format!("SQLite timestamp out of range: {error}"))?;
        Ok(Self {
            timestamp_ns,
            state: state.clone(),
        })
    }
}

fn open(config: &SqliteConfig) -> Result<Connection, String> {
    // Do not create parent directories: an absent USB mount must fail, not fill internal flash.
    match OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(&config.path)
    {
        Ok(_) => {}
        Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {}
        Err(error) => {
            return Err(format!(
                "cannot create SQLite database {}: {error}",
                config.path
            ))
        }
    }
    let initialize = || -> rusqlite::Result<Connection> {
        let mut connection = Connection::open_with_flags(
            &config.path,
            OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_NO_MUTEX,
        )?;
        connection.busy_timeout(Duration::from_millis(config.busy_timeout_ms))?;
        let application: i64 =
            connection.query_row("PRAGMA application_id", [], |row| row.get(0))?;
        let version: i64 = connection.query_row("PRAGMA user_version", [], |row| row.get(0))?;
        let tables: i64 = connection.query_row(
            "SELECT count(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'",
            [],
            |row| row.get(0),
        )?;
        if !((application == APPLICATION_ID && matches!(version, 1 | 2))
            || (application == 0 && version == 0 && tables == 0))
        {
            return Err(rusqlite::Error::InvalidParameterName(
                format!("not a supported ble2uart-gateway database (application_id={application}, version={version})"),
            ));
        }
        let mode: String = connection.query_row("PRAGMA journal_mode=WAL", [], |row| row.get(0))?;
        if !mode.eq_ignore_ascii_case("wal") {
            return Err(rusqlite::Error::InvalidParameterName(format!(
                "WAL unavailable: {mode}"
            )));
        }
        connection.execute_batch("PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;")?;
        if version == 0 {
            let transaction =
                connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
            transaction.execute_batch(SCHEMA)?;
            transaction.commit()?;
        }
        if config.maintenance.enabled {
            let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
            let current: i64 = transaction.query_row("PRAGMA user_version", [], |row| row.get(0))?;
            if current == 1 { transaction.execute_batch(HISTORY_SCHEMA)?; }
            else { transaction.execute_batch("CREATE INDEX IF NOT EXISTS history_series_order ON history_samples(series_id,id)")?; }
            transaction.commit()?;
        }
        Ok(connection)
    };
    initialize()
        .map_err(|error| format!("cannot initialize SQLite database {}: {error}", config.path))
}

fn typed_value(value: &Value) -> (&'static str, SqlValue, SqlValue, SqlValue) {
    let null = SqlValue::Null;
    match value {
        Value::Bool(value) => (
            "boolean",
            null.clone(),
            SqlValue::Integer(i64::from(*value)),
            null,
        ),
        Value::Number(value) => {
            if let Some(value) = value.as_i64() {
                ("integer", null.clone(), SqlValue::Integer(value), null)
            } else if let Some(value) = value.as_u64() {
                (
                    "unsigned",
                    null.clone(),
                    null,
                    SqlValue::Text(value.to_string()),
                )
            } else {
                (
                    "real",
                    SqlValue::Real(value.as_f64().expect("JSON floating point number")),
                    null.clone(),
                    null,
                )
            }
        }
        Value::String(value) => ("text", null.clone(), null, SqlValue::Text(value.clone())),
        Value::Null => ("null", null.clone(), null.clone(), null),
        Value::Array(_) | Value::Object(_) => (
            "json",
            null.clone(),
            null,
            SqlValue::Text(value.to_string()),
        ),
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
                frame.timestamp_ns,
                state["mac"].as_str(),
                state["label"].as_str().unwrap_or(""),
                state["wire_format"].as_str().unwrap_or(""),
                state.to_string(),
            ])?;
            let id = transaction.last_insert_rowid();
            for (ordinal, measurement) in state["measurements"]
                .as_array()
                .expect("validated frame")
                .iter()
                .enumerate()
            {
                let (kind, real, integer, text) = typed_value(&measurement["value"]);
                insert_measurement.execute(params![
                    id,
                    ordinal as i64,
                    measurement["name"].as_str(),
                    measurement["unit"].as_str().unwrap_or(""),
                    kind,
                    real,
                    integer,
                    text,
                ])?;
            }
        }
    }
    transaction.commit()
}

const SECOND_NS: i64 = 1_000_000_000;

fn archive_frames(connection: &mut Connection, config: &MaintenanceConfig, now: i64) -> rusqlite::Result<usize> {
    let cutoff = now.saturating_sub(config.raw_retention_s as i64 * SECOND_NS);
    let deadline = Instant::now() + Duration::from_millis(config.max_work_ms / 2);
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let frames: Vec<(i64, i64, String, String, String)> = transaction.prepare(
        "SELECT id,received_at_ns,mac,sensor_name,state_json FROM frames
         WHERE received_at_ns < ?1 ORDER BY received_at_ns,id LIMIT ?2",
    )?.query_map(params![cutoff, config.batch_size as i64], |row|
        Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?, row.get(4)?)))?
        .collect::<rusqlite::Result<_>>()?;
    let mut moved = 0;
    for (id, timestamp, mac, name, state) in frames {
        transaction.execute(
            "INSERT INTO history_devices(mac,sensor_name,device_json)
             VALUES (?1,?2,COALESCE(json_extract(?3,'$.device'),'{}'))
             ON CONFLICT(mac) DO UPDATE SET sensor_name=excluded.sensor_name,device_json=excluded.device_json",
            params![mac, name, state],
        )?;
        transaction.execute(
            "INSERT OR IGNORE INTO history_series(mac,attribute,unit)
             SELECT ?1,attribute,unit FROM measurements WHERE frame_id=?2",
            params![mac, id],
        )?;
        transaction.execute(
            "INSERT INTO history_samples(series_id,received_at_ns,type,value_json)
             SELECT series.id,?1,measure.type,
               CASE measure.type
                 WHEN 'real' THEN printf('%!.17g',measure.value_real)
                 WHEN 'integer' THEN CAST(measure.value_int AS TEXT)
                 WHEN 'boolean' THEN CASE measure.value_int WHEN 0 THEN 'false' ELSE 'true' END
                 WHEN 'text' THEN json_quote(measure.value_text)
                 WHEN 'null' THEN 'null' ELSE measure.value_text END
             FROM measurements measure JOIN history_series series
               ON series.mac=?2 AND series.attribute=measure.attribute AND series.unit=measure.unit
             WHERE measure.frame_id=?3 ORDER BY measure.ordinal",
            params![timestamp, mac, id],
        )?;
        transaction.execute("DELETE FROM frames WHERE id=?1", [id])?;
        moved += 1;
        if Instant::now() >= deadline { break; }
    }
    transaction.commit()?;
    Ok(moved)
}

fn reduce_series(connection: &mut Connection, config: &MaintenanceConfig, now: i64,
    series: i64, mac: &str, attribute: &str, after: i64) -> rusqlite::Result<(i64, bool)> {
    if discrete_attribute(attribute) { return Ok((after, true)); }
    let policy = config.policy(mac, attribute);
    let mode = policy.map(|policy| policy.mode).unwrap_or_else(||
        if counter_attribute(attribute) { config.counter_mode } else { HistoryMode::KeepAll });
    if mode == HistoryMode::KeepAll { return Ok((after, true)); }
    let deadline = Instant::now() + Duration::from_millis(config.max_work_ms / 2);
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let raw_cutoff = now.saturating_sub(config.raw_retention_s as i64 * SECOND_NS);
    let samples: Vec<(i64,i64,String)> = transaction.prepare(
        "SELECT id,received_at_ns,type FROM history_samples WHERE series_id=?1 AND id>?2 ORDER BY id LIMIT ?3",
    )?.query_map(params![series,after,config.batch_size as i64],|row|Ok((row.get(0)?,row.get(1)?,row.get(2)?)))?
        .collect::<rusqlite::Result<_>>()?;
    let mut last = after;
    let mut processed = 0;
    for (id,timestamp,kind) in &samples {
        if *timestamp < raw_cutoff && (matches!(kind.as_str(),"integer"|"real")
            || (mode == HistoryMode::Discard && kind == "unsigned")) {
            let tier = policy.into_iter().flat_map(|policy| policy.tiers.iter().enumerate()).find(|(_,tier)|
                *timestamp >= now.saturating_sub(tier.max_age_s as i64 * SECOND_NS));
            let remove = if mode == HistoryMode::Discard { true } else if let Some((index,tier)) = tier {
                if tier.sample_interval_s == 0 { false } else {
                    let width = tier.sample_interval_s as i64 * SECOND_NS;
                    let previous_age = if index == 0 {0} else {policy.unwrap().tiers[index-1].max_age_s};
                    let upper = now.saturating_sub(previous_age as i64 * SECOND_NS).min(raw_cutoff)
                        .min((timestamp / width).saturating_add(1).saturating_mul(width));
                    transaction.query_row(
                        "SELECT EXISTS(SELECT 1 FROM history_samples WHERE series_id=?1
                         AND type IN ('integer','real') AND received_at_ns >= ?2 AND received_at_ns < ?3
                         AND (received_at_ns > ?2 OR id > ?4))",
                        params![series,timestamp,upper,id],|row|row.get::<_,bool>(0))?
                }
            } else { true };
            if remove { transaction.execute("DELETE FROM history_samples WHERE id=?1",[id])?; }
        }
        last = *id;
        processed += 1;
        if Instant::now() >= deadline { break; }
    }
    transaction.commit()?;
    Ok((last, samples.len() < config.batch_size && processed == samples.len()))
}

#[derive(Default)]
struct MaintenanceCursor {
    series: i64,
    sample: i64,
}

#[derive(Default)]
struct WriteGate {
    mutex: Mutex<()>,
    waiting_writers: AtomicUsize,
}

impl WriteGate {
    fn writer(&self) -> MutexGuard<'_,()> {
        self.waiting_writers.fetch_add(1,Ordering::Relaxed);
        let guard=self.mutex.lock().unwrap_or_else(|error|error.into_inner());
        self.waiting_writers.fetch_sub(1,Ordering::Relaxed);
        guard
    }

    fn maintenance(&self) -> Option<MutexGuard<'_,()>> {
        if self.waiting_writers.load(Ordering::Relaxed)>0 {return None;}
        let guard=match self.mutex.try_lock() {
            Ok(guard)=>guard,
            Err(TryLockError::Poisoned(error))=>error.into_inner(),
            Err(TryLockError::WouldBlock)=>return None,
        };
        if self.waiting_writers.load(Ordering::Relaxed)>0 {return None;}
        Some(guard)
    }
}

fn maintenance_warning_due(last: &mut Option<Instant>,now: Instant) -> bool {
    if last.is_none_or(|previous|now.saturating_duration_since(previous)>=Duration::from_secs(60)) {
        *last=Some(now);true
    } else {false}
}

fn maintenance_step(connection: &mut Connection, config: &MaintenanceConfig, now: i64,
    cursor: &mut MaintenanceCursor, stopped: &Arc<AtomicBool>) -> rusqlite::Result<bool> {
    let deadline = Instant::now() + Duration::from_millis(config.max_work_ms);
    let cancelled = Arc::clone(stopped);
    connection.progress_handler(1000, Some(move || cancelled.load(Ordering::Relaxed) || Instant::now() >= deadline));
    let result = (|| {
        let moved = archive_frames(connection, config, now)?;
        if moved > 0 { *cursor = MaintenanceCursor::default(); return Ok(true); }
        let next: Option<(i64, String, String)> = {
            let mut statement = connection.prepare("SELECT id,mac,attribute FROM history_series WHERE id>?1 ORDER BY id LIMIT 1")?;
            let mut rows = statement.query([cursor.series])?;
            rows.next()?.map(|row| -> rusqlite::Result<_> { Ok((row.get(0)?, row.get(1)?, row.get(2)?)) }).transpose()?
        };
        if let Some((series, mac, attribute)) = next {
            let (last,done) = reduce_series(connection, config, now, series, &mac, &attribute,cursor.sample)?;
            if done { cursor.series=series;cursor.sample=0; } else { cursor.sample=last; }
            Ok(true)
        } else {
            *cursor = MaintenanceCursor::default();
            Ok(moved > 0)
        }
    })();
    connection.progress_handler(0, None::<fn() -> bool>);
    if !connection.is_autocommit() {connection.execute_batch("ROLLBACK")?;}
    result
}

fn maintenance_attempt(connection: &mut Connection,config: &MaintenanceConfig,now: i64,
    cursor: &mut MaintenanceCursor,stopped: &Arc<AtomicBool>,gate: &WriteGate) -> rusqlite::Result<Option<bool>> {
    let Some(_permit)=gate.maintenance() else {return Ok(None);};
    match maintenance_step(connection,config,now,cursor,stopped) {
        Err(rusqlite::Error::SqliteFailure(error,_))
            if matches!(error.code,rusqlite::ErrorCode::DatabaseBusy|rusqlite::ErrorCode::DatabaseLocked)=>Ok(None),
        result=>result.map(Some),
    }
}

fn run_maintenance(mut connection: Connection, config: MaintenanceConfig, stopped: Arc<AtomicBool>,gate: Arc<WriteGate>) {
    let mut cursor = MaintenanceCursor::default();
    let mut last_warning=None;
    let mut waiting_since=None;
    while !stopped.load(Ordering::Relaxed) {
        let now = SystemTime::now().duration_since(UNIX_EPOCH).ok()
            .filter(|time| time.as_secs() >= 1577836800)
            .and_then(|time| i64::try_from(time.as_nanos()).ok());
        let result = now.ok_or_else(|| "system time is not synchronized".to_string())
            .and_then(|now| maintenance_attempt(&mut connection, &config, now, &mut cursor, &stopped,&gate).map_err(|error| error.to_string()));
        let wait = match result {
            Ok(Some(more)) => {
                waiting_since=None;
                if more { Duration::from_millis(20) } else { Duration::from_secs(config.interval_s) }
            }
            Ok(None)=>{
                let now=Instant::now();
                let since=waiting_since.get_or_insert(now);
                if now.saturating_duration_since(*since)>=Duration::from_secs(30)
                    && !stopped.load(Ordering::Relaxed) && maintenance_warning_due(&mut last_warning,now) {
                    log::warn!("SQLite maintenance waiting for write access; receiver remains prioritized");
                }
                Duration::from_millis(100)
            }
            Err(error) => {
                if !stopped.load(Ordering::Relaxed) && maintenance_warning_due(&mut last_warning,Instant::now()) {
                    log::warn!("SQLite maintenance deferred: {error}; completed transactions retained, incomplete work rolled back");
                }
                Duration::from_secs(1)
            }
        };
        if !stopped.load(Ordering::Relaxed) { std::thread::park_timeout(wait); }
    }
}

fn run_worker(
    mut connection: Connection,
    config: SqliteConfig,
    receiver: Receiver<Frame>,
    stopped: Arc<AtomicBool>,
    gate: Arc<WriteGate>,
) {
    let interval = Duration::from_millis(config.flush_interval_ms);
    let mut deadline = Instant::now() + interval;
    let mut pending = Vec::with_capacity(config.batch_size);
    let mut failures = 0usize;
    while !stopped.load(Ordering::Relaxed) {
        if pending.len() < config.batch_size {
            let timeout = deadline
                .saturating_duration_since(Instant::now())
                .min(Duration::from_millis(100));
            match receiver.recv_timeout(timeout) {
                Ok(frame) => pending.push(frame),
                Err(mpsc::RecvTimeoutError::Timeout) => {}
                Err(mpsc::RecvTimeoutError::Disconnected) => break,
            }
        } else if failures > 0 && Instant::now() < deadline {
            std::thread::park_timeout(
                deadline
                    .saturating_duration_since(Instant::now())
                    .min(Duration::from_millis(100)),
            );
        }
        if pending.is_empty() {
            deadline = Instant::now() + interval;
            continue;
        }
        if Instant::now() < deadline && (failures > 0 || pending.len() < config.batch_size) {
            continue;
        }
        let result={let _permit=gate.writer();write_batch(&mut connection,&pending)};
        match result {
            Ok(()) => {
                if failures > 0 {
                    log::info!(
                        "SQLite writer recovered; {} pending frames committed",
                        pending.len()
                    );
                }
                pending.clear();
                failures = 0;
            }
            Err(error) => {
                if failures % 30 == 0 {
                    log::error!(
                        "SQLite write failed: {error}; retaining {} frames for retry",
                        pending.len()
                    );
                }
                failures = failures.saturating_add(1);
            }
        }
        deadline = Instant::now() + interval;
    }
    pending.extend(receiver.try_iter());
    if !pending.is_empty() {
        let _permit=gate.writer();
        if let Err(error) = write_batch(&mut connection, &pending) {
            log::error!("SQLite shutdown lost {} uncommitted frames: {error}; memory queue is not a persistent spool", pending.len());
        }
    }
}

pub struct SqlitePublisher {
    sender: SyncSender<Frame>,
    stopped: Arc<AtomicBool>,
    worker: Option<JoinHandle<()>>,
    maintenance_worker: Option<JoinHandle<()>>,
    dropped: AtomicUsize,
}

impl SqlitePublisher {
    pub fn start(config: &SqliteConfig) -> Result<Self, String> {
        config.validate()?;
        if !config.enabled {
            return Err("SQLite frontend is disabled".into());
        }
        let connection = open(config)?;
        let maintenance_connection = if config.maintenance.enabled {
            let connection = Connection::open_with_flags(&config.path,
                OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_NO_MUTEX).map_err(|error| error.to_string())?;
            connection.busy_timeout(Duration::ZERO).map_err(|error| error.to_string())?;
            connection.execute_batch("PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;").map_err(|error| error.to_string())?;
            Some(connection)
        } else { None };
        let (sender, receiver) = mpsc::sync_channel(config.queue_capacity);
        let stopped = Arc::new(AtomicBool::new(false));
        let worker_stopped = Arc::clone(&stopped);
        let gate=Arc::new(WriteGate::default());
        let writer_gate=Arc::clone(&gate);
        let worker_config = config.clone();
        let worker = std::thread::Builder::new()
            .name("ble-sqlite".into())
            .spawn(move || run_worker(connection, worker_config, receiver, worker_stopped,writer_gate))
            .map_err(|error| format!("cannot start SQLite writer: {error}"))?;
        log::info!("SQLite recording to {} (WAL)", config.path);
        let mut publisher = Self {
            sender,
            stopped,
            worker: Some(worker),
            maintenance_worker: None,
            dropped: AtomicUsize::new(0),
        };
        if let Some(connection) = maintenance_connection {
            let maintenance = config.maintenance.clone();
            let maintenance_stopped = Arc::clone(&publisher.stopped);
            publisher.maintenance_worker = Some(std::thread::Builder::new().name("ble-sqlite-history".into())
                .spawn(move || run_maintenance(connection, maintenance, maintenance_stopped,gate))
                .map_err(|error| format!("cannot start SQLite maintenance: {error}"))?);
            log::info!("SQLite history maintenance enabled ({} s cadence, {} ms work budget)",
                config.maintenance.interval_s, config.maintenance.max_work_ms);
        }
        Ok(publisher)
    }

    pub fn publish(&self, state: &Value) {
        let frame = match Frame::new(state) {
            Ok(frame) => frame,
            Err(error) => {
                log::error!("SQLite frame rejected: {error}");
                return;
            }
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
        if let Some(worker) = self.maintenance_worker.take() {
            worker.thread().unpark();
            if worker.join().is_err() { log::error!("SQLite maintenance thread panicked"); }
        }
        if let Some(worker) = self.worker.take() {
            if worker.join().is_err() {
                log::error!("SQLite writer thread panicked");
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::PermissionsExt;

    #[test]
    fn maintenance_yields_to_internal_and_external_writers_and_resumes() {
        let mut database=Database::new();database.config.maintenance.enabled=true;
        let mut maintenance=open(&database.config).unwrap();maintenance.busy_timeout(Duration::ZERO).unwrap();
        let mut writer=open(&database.config).unwrap();
        let now=1_800_000_000*SECOND_NS;
        let mut frame=Frame::new(&state()).unwrap();frame.timestamp_ns=now-7200*SECOND_NS;
        write_batch(&mut writer,&[frame]).unwrap();
        let gate=WriteGate::default();let stopped=Arc::new(AtomicBool::new(false));let mut cursor=MaintenanceCursor::default();
        let receiver=gate.writer();
        assert_eq!(maintenance_attempt(&mut maintenance,&database.config.maintenance,now,&mut cursor,&stopped,&gate).unwrap(),None);
        assert!(maintenance.is_autocommit());drop(receiver);
        writer.execute_batch("BEGIN IMMEDIATE").unwrap();
        assert_eq!(maintenance_attempt(&mut maintenance,&database.config.maintenance,now,&mut cursor,&stopped,&gate).unwrap(),None);
        assert!(maintenance.is_autocommit());writer.execute_batch("ROLLBACK").unwrap();
        assert_eq!(maintenance_attempt(&mut maintenance,&database.config.maintenance,now,&mut cursor,&stopped,&gate).unwrap(),Some(true));
        assert!(maintenance.is_autocommit());
        assert_eq!(writer.query_row("SELECT count(*) FROM frames",[],|row|row.get::<_,i64>(0)).unwrap(),0);
        write_batch(&mut writer,&[Frame::new(&state()).unwrap()]).unwrap();
    }

    #[test]
    fn maintenance_warning_throttle_is_time_based_not_reset_by_success() {
        let now=Instant::now();let mut last=None;
        assert!(maintenance_warning_due(&mut last,now));
        assert!(!maintenance_warning_due(&mut last,now+Duration::from_secs(2)));
        assert!(!maintenance_warning_due(&mut last,now+Duration::from_secs(59)));
        assert!(maintenance_warning_due(&mut last,now+Duration::from_secs(60)));
    }

    #[test]
    fn waiting_receiver_gets_priority_over_another_maintenance_chunk() {
        let gate=Arc::new(WriteGate::default());
        let maintenance=gate.maintenance().unwrap();
        let (acquired,receiver)=mpsc::channel();let (release,released)=mpsc::channel();
        let writer_gate=Arc::clone(&gate);
        let writer=std::thread::spawn(move||{
            let _permit=writer_gate.writer();acquired.send(()).unwrap();released.recv().unwrap();
        });
        let deadline=Instant::now()+Duration::from_secs(2);
        while gate.waiting_writers.load(Ordering::Relaxed)==0 {
            assert!(Instant::now()<deadline,"receiver never entered the write queue");std::thread::yield_now();
        }
        assert!(gate.maintenance().is_none());drop(maintenance);
        receiver.recv_timeout(Duration::from_secs(2)).unwrap();
        assert!(gate.maintenance().is_none());release.send(()).unwrap();writer.join().unwrap();
        assert!(gate.maintenance().is_some());
    }

    #[test]
    fn maintenance_defaults_and_policy_validation() {
        let mut config = MaintenanceConfig::default();
        assert!(!config.enabled);
        config.validate().unwrap();
        assert_eq!(config.policy("AABBCCDDEEFF", "temperature").unwrap().tiers[2].sample_interval_s, 150);
        assert!(config.policy("AABBCCDDEEFF", "packet_id").is_none());
        assert_eq!(config.counter_mode,HistoryMode::Discard);
        assert!(config.policy("AABBCCDDEEFF", "opened").is_none());
        let mut override_policy = config.policies[0].clone();
        override_policy.mac = "AA:BB:CC:DD:EE:FF".into();
        override_policy.mode = HistoryMode::KeepAll;
        config.policies.push(override_policy.clone());
        config.validate().unwrap();
        assert_eq!(config.policy("AABBCCDDEEFF", "temperature").unwrap().mode, HistoryMode::KeepAll);
        override_policy.mac = "AABBCCDDEEFF".into();
        config.policies.push(override_policy);
        assert!(config.validate().is_err());
        config.policies.pop();
        config.policies[0].tiers[2].max_age_s = 10;
        assert!(config.validate().is_err());
        config.policies[0] = MaintenanceConfig::default().policies.remove(0);
        config.policies[0].attribute = "opened".into();
        assert!(config.validate().is_err());
    }

    struct Database {
        directory: std::path::PathBuf,
        config: SqliteConfig,
    }

    impl Database {
        fn new() -> Self {
            static NEXT: AtomicUsize = AtomicUsize::new(0);
            let directory = std::env::temp_dir().join(format!(
                "ble-sqlite-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed),
            ));
            std::fs::create_dir(&directory).unwrap();
            let config = SqliteConfig {
                enabled: true,
                path: directory.join("readings.sqlite3").to_str().unwrap().into(),
                batch_size: 1,
                flush_interval_ms: 10,
                busy_timeout_ms: 20,
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
        for path in [
            "",
            ":memory:",
            "file:/tmp/a",
            "relative.db",
            "/tmp/bad\n.db",
        ] {
            config.frontends.sqlite.path = path.into();
            assert!(config.validate().is_err(), "{path}");
        }
        config.frontends.sqlite.path = "/tmp/readings.sqlite3".into();
        config.frontends.sqlite.batch_size = config.frontends.sqlite.queue_capacity + 1;
        assert!(config.validate().is_err());
        assert!(serde_yaml::from_str::<SqliteConfig>("unknown: true").is_err());
        assert!(Frame::new(&serde_json::json!({"mac":"A","measurements":[{"name":"x"}]})).is_err());
    }

    fn drain_history(connection: &mut Connection, config: &MaintenanceConfig, now: i64) {
        let mut cursor = MaintenanceCursor::default();
        let stopped = Arc::new(AtomicBool::new(false));
        for _ in 0..1000 {
            if !maintenance_step(connection, config, now, &mut cursor, &stopped).unwrap() { return; }
        }
        panic!("maintenance did not finish its bounded chunks");
    }

    #[test]
    fn maintenance_normalizes_legacy_frames_atomically_and_preserves_exact_values() {
        let mut database = Database::new();
        let now = 1_800_000_000 * SECOND_NS;
        let mut connection = open(&database.config).unwrap();
        let mut frame = Frame::new(&state()).unwrap();
        frame.timestamp_ns = now - 7200 * SECOND_NS;
        write_batch(&mut connection, &[frame]).unwrap();
        drop(connection);
        database.config.maintenance.enabled = true;
        let mut connection = open(&database.config).unwrap();
        assert_eq!(connection.query_row("PRAGMA user_version", [], |row| row.get::<_, i64>(0)).unwrap(), 2);
        assert_eq!(connection.query_row("SELECT count(*) FROM history", [], |row| row.get::<_, i64>(0)).unwrap(), 10);
        connection.execute_batch("CREATE TRIGGER fail_archive BEFORE INSERT ON history_samples
            BEGIN SELECT RAISE(ABORT,'test archive failure'); END;").unwrap();
        assert!(archive_frames(&mut connection, &database.config.maintenance, now).is_err());
        assert_eq!(connection.query_row("SELECT count(*) FROM frames", [], |row| row.get::<_, i64>(0)).unwrap(), 1);
        assert_eq!(connection.query_row("SELECT count(*) FROM history_samples", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
        connection.execute_batch("DROP TRIGGER fail_archive").unwrap();
        archive_frames(&mut connection, &database.config.maintenance, now).unwrap();
        assert_eq!(connection.query_row("SELECT count(*) FROM frames", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
        let stored: Vec<(String, String)> = connection.prepare("SELECT type,value_json FROM history_samples ORDER BY id")
            .unwrap().query_map([], |row| Ok((row.get(0)?,row.get(1)?))).unwrap().collect::<rusqlite::Result<_>>().unwrap();
        for (entry, original) in stored.iter().zip(state()["measurements"].as_array().unwrap()) {
            assert_eq!(serde_json::from_str::<Value>(&entry.1).unwrap(), original["value"]);
        }
        drain_history(&mut connection, &database.config.maintenance, now);
        let once: i64 = connection.query_row("SELECT count(*) FROM history", [], |row| row.get(0)).unwrap();
        drain_history(&mut connection, &database.config.maintenance, now);
        assert_eq!(connection.query_row("SELECT count(*) FROM history", [], |row| row.get::<_, i64>(0)).unwrap(), once);
        assert_eq!(connection.query_row("SELECT count(*) FROM pragma_foreign_key_check", [], |row| row.get::<_, i64>(0)).unwrap(), 0);
        drop(connection);
        database.config.maintenance.enabled = false;
        open(&database.config).unwrap();
    }

    #[test]
    fn maintenance_uses_independent_tiers_and_never_deletes_discrete_or_counter_samples() {
        let mut database = Database::new();
        let now = 1_800_000_000 * SECOND_NS;
        database.config.maintenance.enabled = true;
        database.config.maintenance.raw_retention_s = 1;
        database.config.maintenance.batch_size = 3;
        database.config.maintenance.policies = vec![
            HistoryPolicy { attribute: "temperature".into(), mode: HistoryMode::Progressive,
                tiers: vec![HistoryTier {max_age_s:10,sample_interval_s:0},HistoryTier {max_age_s:60,sample_interval_s:10},HistoryTier {max_age_s:120,sample_interval_s:30}], ..Default::default() },
            HistoryPolicy { attribute: "battery_level".into(), mode: HistoryMode::Progressive,
                tiers: vec![HistoryTier {max_age_s:120,sample_interval_s:60}], ..Default::default() },
            HistoryPolicy { mac:"112233445566".into(), attribute:"temperature".into(), ..Default::default() },
        ];
        database.config.validate().unwrap();
        let mut connection = open(&database.config).unwrap();
        for mac in ["AABBCCDDEEFF", "112233445566"] {
            for age in [5, 15, 16, 25, 26, 80, 85, 200] {
                let data = serde_json::json!({"mac":mac,"measurements":[
                    {"name":"temperature","value":age,"unit":"C"},
                    {"name":"battery_level","value":90,"unit":"%"},
                    {"name":"opened","value":age%2,"unit":""},
                    {"name":"custom_contact","value":true,"unit":""},
                    {"name":"counter","value":age,"unit":""}]});
                let mut frame = Frame::new(&data).unwrap();frame.timestamp_ns=now-age*SECOND_NS;
                write_batch(&mut connection, &[frame]).unwrap();
            }
        }
        drain_history(&mut connection, &database.config.maintenance, now);
        let count = |mac: &str, attribute: &str| connection.query_row(
            "SELECT count(*) FROM history WHERE mac=?1 AND attribute=?2", params![mac,attribute], |row| row.get::<_, i64>(0)).unwrap();
        assert_eq!(count("AABBCCDDEEFF","temperature"),4);
        assert_eq!(count("112233445566","temperature"),8);
        for mac in ["AABBCCDDEEFF", "112233445566"] {
            assert_eq!(count(mac,"battery_level"),2);
            for attribute in ["opened","custom_contact"] { assert_eq!(count(mac,attribute),8); }
            assert_eq!(count(mac,"counter"),0);
        }
        let values: Vec<i64> = connection.prepare("SELECT CAST(value_json AS INTEGER) FROM history WHERE mac='AABBCCDDEEFF' AND attribute='temperature' ORDER BY received_at_ns DESC")
            .unwrap().query_map([],|row|row.get(0)).unwrap().collect::<rusqlite::Result<_>>().unwrap();
        assert_eq!(values,vec![5,15,25,80]);
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
        let (timestamp, mac, name, format, json): (i64, String, String, String, String) =
            connection
                .query_row(
                    "SELECT received_at_ns,mac,sensor_name,wire_format,state_json FROM frames",
                    [],
                    |row| {
                        Ok((
                            row.get(0)?,
                            row.get(1)?,
                            row.get(2)?,
                            row.get(3)?,
                            row.get(4)?,
                        ))
                    },
                )
                .unwrap();
        assert_eq!(timestamp, 1792356358293394316);
        assert_eq!(
            (mac.as_str(), name.as_str(), format.as_str()),
            ("AABBCCDDEEFF", "Outside", "bt_home_v2")
        );
        assert_eq!(serde_json::from_str::<Value>(&json).unwrap(), state());
        let rows: Vec<(String, SqlValue, SqlValue, SqlValue)> = connection
            .prepare(
                "SELECT type,value_real,value_int,value_text FROM measurements ORDER BY ordinal",
            )
            .unwrap()
            .query_map([], |row| {
                Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?))
            })
            .unwrap()
            .collect::<rusqlite::Result<_>>()
            .unwrap();
        let null = SqlValue::Null;
        assert_eq!(
            rows,
            vec![
                (
                    "real".into(),
                    SqlValue::Real(16.34),
                    null.clone(),
                    null.clone()
                ),
                (
                    "real".into(),
                    SqlValue::Real(82.89),
                    null.clone(),
                    null.clone()
                ),
                (
                    "integer".into(),
                    null.clone(),
                    SqlValue::Integer(100),
                    null.clone()
                ),
                (
                    "boolean".into(),
                    null.clone(),
                    SqlValue::Integer(0),
                    null.clone()
                ),
                (
                    "integer".into(),
                    null.clone(),
                    SqlValue::Integer(-9007199254740993),
                    null.clone()
                ),
                (
                    "unsigned".into(),
                    null.clone(),
                    null.clone(),
                    SqlValue::Text(u64::MAX.to_string())
                ),
                (
                    "text".into(),
                    null.clone(),
                    null.clone(),
                    SqlValue::Text("ready".into())
                ),
                (
                    "json".into(),
                    null.clone(),
                    null.clone(),
                    SqlValue::Text("[0,255]".into())
                ),
                ("null".into(), null.clone(), null.clone(), null.clone()),
                ("real".into(), SqlValue::Real(17.34), null.clone(), null),
            ]
        );
        assert_eq!(
            std::fs::metadata(&database.config.path)
                .unwrap()
                .permissions()
                .mode()
                & 0o777,
            0o600
        );
        assert!(connection
            .execute("UPDATE measurements SET value_int=5 WHERE ordinal=0", [],)
            .is_err());
        connection.execute("DELETE FROM frames", []).unwrap();
        assert_eq!(
            connection
                .query_row("SELECT count(*) FROM measurements", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            0
        );
    }

    #[test]
    fn sqlite_failed_batch_rolls_back_frames_and_all_measurements() {
        let database = Database::new();
        let mut connection = open(&database.config).unwrap();
        connection
            .execute_batch(
                "CREATE TRIGGER reject_frame BEFORE INSERT ON measurements WHEN NEW.attribute='bad'
                     BEGIN SELECT RAISE(ABORT, 'test failure'); END;",
            )
            .unwrap();
        let good = Frame::new(&state()).unwrap();
        let mut bad = state();
        bad["measurements"][1]["name"] = "bad".into();
        assert!(write_batch(&mut connection, &[good, Frame::new(&bad).unwrap()]).is_err());
        for table in ["frames", "measurements"] {
            assert_eq!(
                connection
                    .query_row(&format!("SELECT count(*) FROM {table}"), [], |row| row
                        .get::<_, i64>(0))
                    .unwrap(),
                0
            );
        }
    }

    #[test]
    fn sqlite_wal_reader_keeps_consistent_snapshot_without_blocking_writer() {
        let database = Database::new();
        let mut writer = open(&database.config).unwrap();
        write_batch(&mut writer, &[Frame::new(&state()).unwrap()]).unwrap();
        let reader =
            Connection::open_with_flags(&database.config.path, OpenFlags::SQLITE_OPEN_READ_ONLY)
                .unwrap();
        reader.execute_batch("BEGIN").unwrap();
        assert_eq!(
            reader
                .query_row("SELECT count(*) FROM frames", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            1
        );
        write_batch(&mut writer, &[Frame::new(&state()).unwrap()]).unwrap();
        assert_eq!(
            reader
                .query_row("SELECT count(*) FROM frames", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            1
        );
        reader.execute_batch("COMMIT").unwrap();
        assert_eq!(
            reader
                .query_row("SELECT count(*) FROM frames", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            2
        );
        assert_eq!(
            reader
                .query_row("SELECT count(*) FROM measurements", [], |row| row
                    .get::<_, i64>(0))
                .unwrap(),
            20
        );
    }

    #[test]
    fn sqlite_worker_retries_locked_database_and_flushes_on_shutdown() {
        let database = Database::new();
        let publisher = SqlitePublisher::start(&database.config).unwrap();
        let lock = Connection::open(&database.config.path).unwrap();
        lock.execute_batch("BEGIN IMMEDIATE").unwrap();
        publisher.publish(&state());
        std::thread::sleep(Duration::from_millis(100));
        assert_eq!(
            lock.query_row("SELECT count(*) FROM frames", [], |row| row
                .get::<_, i64>(0))
                .unwrap(),
            0
        );
        lock.execute_batch("ROLLBACK").unwrap();
        let deadline = Instant::now() + Duration::from_secs(3);
        loop {
            let count: i64 = lock
                .query_row("SELECT count(*) FROM frames", [], |row| row.get(0))
                .unwrap();
            if count == 1 {
                break;
            }
            assert!(Instant::now() < deadline, "writer did not recover");
            std::thread::sleep(Duration::from_millis(10));
        }
        publisher.publish(&state());
        drop(publisher);
        assert_eq!(
            lock.query_row("SELECT count(*) FROM frames", [], |row| row
                .get::<_, i64>(0))
                .unwrap(),
            2
        );
    }

    #[test]
    fn sqlite_queue_is_bounded_and_missing_storage_or_foreign_database_is_rejected() {
        let (sender, receiver) = mpsc::sync_channel(1);
        let publisher = SqlitePublisher {
            sender,
            stopped: Arc::new(AtomicBool::new(false)),
            worker: None,
            maintenance_worker: None,
            dropped: AtomicUsize::new(0),
        };
        publisher.publish(&state());
        publisher.publish(&state());
        assert_eq!(publisher.dropped.load(Ordering::Relaxed), 1);
        assert!(receiver.try_recv().is_ok());
        assert!(receiver.try_recv().is_err());
        let mut database = Database::new();
        database.config.path = database
            .directory
            .join("absent/readings.db")
            .to_str()
            .unwrap()
            .into();
        assert!(SqlitePublisher::start(&database.config).is_err());
        assert!(!database.directory.join("absent").exists());
        database.config.path = database.directory.join("other.db").to_str().unwrap().into();
        let other = Connection::open(&database.config.path).unwrap();
        other
            .execute_batch("CREATE TABLE unrelated(value TEXT)")
            .unwrap();
        drop(other);
        assert!(SqlitePublisher::start(&database.config).is_err());
    }

    #[test]
    fn maintenance_thread_runs_with_receiver_and_stops_without_waiting_for_schedule() {
        let mut database = Database::new();
        let mut connection = open(&database.config).unwrap();
        let mut old = Frame::new(&state()).unwrap();
        old.timestamp_ns -= 7200 * SECOND_NS;
        write_batch(&mut connection, &[old]).unwrap();
        drop(connection);
        database.config.maintenance.enabled = true;
        database.config.maintenance.interval_s = 86400;
        let publisher = SqlitePublisher::start(&database.config).unwrap();
        let reader = Connection::open(&database.config.path).unwrap();
        for _ in 0..10 { publisher.publish(&state()); }
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            let raw: i64 = reader.query_row("SELECT count(*) FROM frames", [], |row| row.get(0)).unwrap();
            let archived: i64 = reader.query_row("SELECT count(*) FROM history_samples", [], |row| row.get(0)).unwrap();
            if raw == 10 && archived >= 8 { break; }
            assert!(Instant::now() < deadline, "receiver/maintenance did not progress");
            std::thread::sleep(Duration::from_millis(10));
        }
        assert_eq!(publisher.dropped.load(Ordering::Relaxed), 0);
        let shutdown = Instant::now();
        drop(publisher);
        assert!(shutdown.elapsed() < Duration::from_secs(2));
    }

    #[test]
    fn maintenance_separates_units_preserves_boolean_values_and_yields_to_writer_locks() {
        let mut database = Database::new();
        database.config.maintenance.enabled = true;
        database.config.maintenance.raw_retention_s = 1;
        database.config.maintenance.policies = vec![HistoryPolicy {
            attribute:"temperature".into(),mode:HistoryMode::Progressive,
            tiers:vec![HistoryTier {max_age_s:120,sample_interval_s:60}],..Default::default()
        }];
        let now = 1_800_000_000 * SECOND_NS;
        let mut connection = open(&database.config).unwrap();
        for age in [5,10,200] {
            let value = serde_json::json!({"mac":"AABBCCDDEEFF","measurements":[
                {"name":"temperature","unit":"C","value":20},
                {"name":"temperature","unit":"F","value":68},
                {"name":"temperature","unit":"","value":true}
            ]});
            let mut frame = Frame::new(&value).unwrap();frame.timestamp_ns=now-age*SECOND_NS;
            write_batch(&mut connection,&[frame]).unwrap();
        }
        let writer = Connection::open(&database.config.path).unwrap();
        writer.execute_batch("BEGIN IMMEDIATE").unwrap();
        connection.busy_timeout(Duration::ZERO).unwrap();
        let before = Instant::now();
        assert!(archive_frames(&mut connection,&database.config.maintenance,now).is_err());
        assert!(before.elapsed()<Duration::from_secs(1));
        writer.execute_batch("ROLLBACK").unwrap();
        drain_history(&mut connection,&database.config.maintenance,now);
        let rows: Vec<(String,i64)> = connection.prepare("SELECT unit,count(*) FROM history GROUP BY unit ORDER BY unit")
            .unwrap().query_map([],|row|Ok((row.get(0)?,row.get(1)?))).unwrap().collect::<rusqlite::Result<_>>().unwrap();
        assert_eq!(rows,vec![("".into(),3),("C".into(),1),("F".into(),1)]);
    }

    #[test]
    fn maintenance_bounds_scanned_samples_even_when_nothing_can_be_deleted() {
        let mut database=Database::new();
        database.config.maintenance.enabled=true;
        database.config.maintenance.batch_size=3;
        let now=1_800_000_000*SECOND_NS;
        let mut connection=open(&database.config).unwrap();
        connection.execute_batch("INSERT INTO history_devices VALUES ('AABBCCDDEEFF','Test','{}');
            INSERT INTO history_series VALUES (1,'AABBCCDDEEFF','temperature','C');
            WITH RECURSIVE sample(id) AS (SELECT 1 UNION ALL SELECT id+1 FROM sample WHERE id<20)
            INSERT INTO history_samples SELECT id,1,1800000000000000000-id*3600000000000,'real','20.0' FROM sample;").unwrap();
        let (last,done)=reduce_series(&mut connection,&database.config.maintenance,now,1,"AABBCCDDEEFF","temperature",0).unwrap();
        assert_eq!((last,done),(3,false));
        drain_history(&mut connection,&database.config.maintenance,now);
        assert_eq!(connection.query_row("SELECT count(*) FROM history_samples",[],|row|row.get::<_,i64>(0)).unwrap(),20);
    }

    #[test]
    fn counter_history_discards_by_default_with_explicit_keep_override() {
        let mut database=Database::new();
        database.config.maintenance.enabled=true;
        database.config.maintenance.raw_retention_s=1;
        database.config.maintenance.policies.push(HistoryPolicy {
            mac:"112233445566".into(),attribute:"packet_id".into(),mode:HistoryMode::KeepAll,tiers:vec![],
        });
        let now=1_800_000_000*SECOND_NS;
        let mut connection=open(&database.config).unwrap();
        for mac in ["AABBCCDDEEFF","112233445566"] {
            let data=serde_json::json!({"mac":mac,"measurements":[
                {"name":"packet_id","value":7,"unit":""},
                {"name":"counter32","value":u64::MAX,"unit":""},
                {"name":"opened","value":1,"unit":""}]});
            let mut frame=Frame::new(&data).unwrap();frame.timestamp_ns=now-100*SECOND_NS;
            write_batch(&mut connection,&[frame]).unwrap();
        }
        drain_history(&mut connection,&database.config.maintenance,now);
        let rows: Vec<(String,String)>=connection.prepare("SELECT mac,attribute FROM history ORDER BY mac,attribute")
            .unwrap().query_map([],|row|Ok((row.get(0)?,row.get(1)?))).unwrap().collect::<rusqlite::Result<_>>().unwrap();
        assert_eq!(rows,vec![("112233445566".into(),"opened".into()),("112233445566".into(),"packet_id".into()),("AABBCCDDEEFF".into(),"opened".into())]);
    }
}
