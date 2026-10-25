//! Read-only sensor dashboard for the SQLite front-end database.
//!
//! The freetz CGI wrapper (`usr/lib/cgi-bin/ble2uart_gateway/portal.cgi`) does
//! the authentication with `/usr/lib/libmodcgi.sh` and then execs
//! `ble2uart-gateway --portal`, so this module is a plain CGI program:
//!
//! * `QUERY_STRING`/`REQUEST_METHOD` come from the environment,
//! * the response (headers and body) is written to stdout,
//! * the database is opened read-only (`PRAGMA query_only=ON`).
//!
//! Nothing in the page is hard-wired to a sensor model: devices, attributes,
//! units and value types are discovered from the database itself (the
//! `history_*` tables written by the maintenance job and the raw `frames` /
//! `measurements` tables), so a new decoder attribute appears automatically.
//!
//! Actions:
//!   `?action=page`      HTML application shell (default)
//!   `?action=catalog`   devices, series and latest values (JSON)
//!   `?action=series`    downsampled time series for one attribute (JSON)
//!   `?action=info`      database statistics and process footprint (JSON)

use crate::config::Config;
use rusqlite::{Connection, OpenFlags, params};
use serde_json::{Value, json};
use std::collections::{BTreeMap, HashMap};
use std::path::{Path, PathBuf};
use std::time::Duration;

/// Upper bound for the number of points returned for one series.
const MAX_BUCKETS: u64 = 1200;
/// Default number of points when the caller does not ask for a resolution.
const DEFAULT_BUCKETS: u64 = 300;
/// Recent measurement rows inspected per device to discover raw-only series.
const RAW_CATALOG_ROWS: i64 = 400;

// ---------------------------------------------------------------------------
// CGI plumbing
// ---------------------------------------------------------------------------

/// Entry point of `ble2uart-gateway --portal`.
pub fn run(config: &Path) -> Result<(), String> {
    let method = std::env::var("REQUEST_METHOD").unwrap_or_else(|_| "GET".into());
    if method != "GET" && method != "HEAD" {
        return reply(405, "text/plain; charset=UTF-8", "method not allowed\n");
    }
    if std::env::var("HTTP_SEC_FETCH_SITE").as_deref() == Ok("cross-site") {
        return reply(403, "text/plain; charset=UTF-8", "cross-site request denied\n");
    }
    if let Ok(origin) = std::env::var("HTTP_ORIGIN") {
        let host = std::env::var("HTTP_HOST").unwrap_or_default();
        if !host.is_empty()
            && origin != format!("http://{host}")
            && origin != format!("https://{host}")
        {
            return reply(403, "text/plain; charset=UTF-8", "origin mismatch\n");
        }
    }

    let query = std::env::var("QUERY_STRING").unwrap_or_default();
    let params = parse_query(&query);
    let action = params.get("action").map(String::as_str).unwrap_or("page");

    let head = method == "HEAD";
    match action {
        "" | "page" => reply_head(200, "text/html; charset=UTF-8", &page(), head),
        "catalog" => json_reply(catalog_action(config), head),
        "series" => json_reply(series_action(config, &params), head),
        "info" => json_reply(info_action(config), head),
        other => reply(404, "text/plain; charset=UTF-8", &format!("unknown action: {other}\n")),
    }
}

fn json_reply(result: Result<Value, String>, head: bool) -> Result<(), String> {
    let body = match result {
        Ok(value) => value.to_string(),
        Err(error) => json!({"ok": false, "error": error}).to_string(),
    };
    reply_head(200, "application/json; charset=UTF-8", &body, head)
}

fn reply(status: u16, content_type: &str, body: &str) -> Result<(), String> {
    reply_head(status, content_type, body, false)
}

fn reply_head(status: u16, content_type: &str, body: &str, head: bool) -> Result<(), String> {
    let reason = match status {
        200 => "OK",
        403 => "Forbidden",
        405 => "Method Not Allowed",
        404 => "Not Found",
        _ => "Error",
    };
    let mut out = format!(
        "Status: {status} {reason}\r\n\
         Content-Type: {content_type}\r\n\
         Content-Length: {}\r\n\
         Cache-Control: no-store\r\n\
         X-Content-Type-Options: nosniff\r\n\
         Referrer-Policy: same-origin\r\n\
         \r\n",
        body.len()
    );
    if !head {
        out.push_str(body);
    }
    print!("{out}");
    Ok(())
}

/// Percent-decoded query string parameters, last value wins.
fn parse_query(query: &str) -> BTreeMap<String, String> {
    let mut map = BTreeMap::new();
    for pair in query.split('&').filter(|pair| !pair.is_empty()) {
        let (key, value) = match pair.split_once('=') {
            Some((key, value)) => (key, value),
            None => (pair, ""),
        };
        map.insert(percent_decode(key), percent_decode(value));
    }
    map
}

fn percent_decode(input: &str) -> String {
    let bytes = input.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while index < bytes.len() {
        match bytes[index] {
            b'+' => {
                out.push(b' ');
                index += 1;
            }
            b'%' if index + 2 < bytes.len() => {
                match (hex(bytes[index + 1]), hex(bytes[index + 2])) {
                    (Some(high), Some(low)) => {
                        out.push(high << 4 | low);
                        index += 3;
                    }
                    _ => {
                        out.push(bytes[index]);
                        index += 1;
                    }
                }
            }
            byte => {
                out.push(byte);
                index += 1;
            }
        }
    }
    String::from_utf8_lossy(&out).into_owned()
}

fn hex(byte: u8) -> Option<u8> {
    match byte {
        b'0'..=b'9' => Some(byte - b'0'),
        b'a'..=b'f' => Some(byte - b'a' + 10),
        b'A'..=b'F' => Some(byte - b'A' + 10),
        _ => None,
    }
}

// ---------------------------------------------------------------------------
// Database access
// ---------------------------------------------------------------------------

fn database_path(config: &Path) -> Result<PathBuf, String> {
    let overridden = std::env::var_os("BLE2UART_PORTAL_DB").filter(|value| !value.is_empty());
    resolve_database_path(config, overridden.map(PathBuf::from))
}

/// Database path from the configuration, unless the caller (a test or a
/// diagnostic run) passes an explicit database.
fn resolve_database_path(config: &Path, overridden: Option<PathBuf>) -> Result<PathBuf, String> {
    if let Some(path) = overridden {
        return Ok(path);
    }
    let loaded = Config::load(config, None, None)?;
    let path = loaded.frontends.sqlite.path.trim().to_string();
    if path.is_empty() {
        return Err("the SQLite front-end has no database path in the configuration".into());
    }
    Ok(PathBuf::from(path))
}

fn open(path: &Path) -> Result<Connection, String> {
    let flags = OpenFlags::SQLITE_OPEN_READ_WRITE
        | OpenFlags::SQLITE_OPEN_URI
        | OpenFlags::SQLITE_OPEN_NO_MUTEX;
    // Read/write flags let SQLite read a WAL database even when it has to
    // create or recover the shared-memory index; `query_only` below still
    // guarantees that this process never modifies the data.
    let connection = Connection::open_with_flags(path, flags)
        .map_err(|error| format!("cannot open {}: {error}", path.display()))?;
    connection
        .busy_timeout(Duration::from_millis(2000))
        .map_err(|error| error.to_string())?;
    connection
        .execute_batch("PRAGMA query_only=ON; PRAGMA foreign_keys=ON;")
        .map_err(|error| format!("cannot read {}: {error}", path.display()))?;
    Ok(connection)
}

fn connect(config: &Path) -> Result<(Connection, PathBuf), String> {
    let path = database_path(config)?;
    if !path.is_file() {
        return Err(format!(
            "database {} does not exist (enable the SQLite front-end)",
            path.display()
        ));
    }
    let connection = open(&path)?;
    Ok((connection, path))
}

fn schema_version(connection: &Connection) -> i64 {
    connection
        .query_row("PRAGMA user_version", [], |row| row.get(0))
        .unwrap_or(0)
}

fn has_table(connection: &Connection, name: &str) -> bool {
    connection
        .query_row(
            "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?1",
            [name],
            |_| Ok(()),
        )
        .is_ok()
}

fn now_ns() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|value| value.as_nanos() as i64)
        .unwrap_or(0)
}

/// `history_samples` only exists once the maintenance job created schema 2.
fn archived(connection: &Connection) -> bool {
    has_table(connection, "history_samples") && has_table(connection, "history_series")
}

// ---------------------------------------------------------------------------
// Value conversion
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Kind {
    Numeric,
    Boolean,
    Text,
}

impl Kind {
    fn parse(text: &str) -> Option<Self> {
        match text {
            "numeric" => Some(Kind::Numeric),
            "boolean" => Some(Kind::Boolean),
            "text" => Some(Kind::Text),
            _ => None,
        }
    }

    fn as_str(self) -> &'static str {
        match self {
            Kind::Numeric => "numeric",
            Kind::Boolean => "boolean",
            Kind::Text => "text",
        }
    }

    /// Classify a measurement type (`real`, `integer`, `boolean`, ...).
    fn of_type(measurement_type: &str) -> Self {
        match measurement_type {
            "real" | "integer" | "unsigned" => Kind::Numeric,
            "boolean" => Kind::Boolean,
            _ => Kind::Text,
        }
    }

    fn merge(self, other: Kind) -> Kind {
        match (self, other) {
            (Kind::Numeric, _) | (_, Kind::Numeric) => Kind::Numeric,
            (Kind::Boolean, _) | (_, Kind::Boolean) => Kind::Boolean,
            _ => Kind::Text,
        }
    }
}

fn json_from_text(measurement_type: &str, text: &str) -> Value {
    match measurement_type {
        "real" | "unsigned" | "json" => serde_json::from_str(text).unwrap_or(Value::Null),
        "integer" => serde_json::from_str(text).unwrap_or(Value::Null),
        "boolean" => Value::Bool(text == "true"),
        "null" => Value::Null,
        _ => serde_json::from_str(text).unwrap_or_else(|_| Value::String(text.to_string())),
    }
}

fn json_from_raw(
    measurement_type: &str,
    real: Option<f64>,
    int: Option<i64>,
    text: Option<String>,
) -> Value {
    match measurement_type {
        "real" => real.map(|value| json!(value)).unwrap_or(Value::Null),
        "integer" => int.map(|value| json!(value)).unwrap_or(Value::Null),
        "boolean" => Value::Bool(int.unwrap_or(0) != 0),
        "unsigned" => match text.as_deref().and_then(|text| text.parse::<f64>().ok()) {
            Some(value) if value.fract() == 0.0 && value.abs() < 9.0e15 => json!(value as i64),
            Some(value) => json!(value),
            None => Value::Null,
        },
        "json" => text
            .as_deref()
            .and_then(|text| serde_json::from_str(text).ok())
            .unwrap_or(Value::Null),
        "null" => Value::Null,
        _ => text.map(Value::String).unwrap_or(Value::Null),
    }
}

// ---------------------------------------------------------------------------
// Catalog: devices, series and latest values
// ---------------------------------------------------------------------------

#[derive(Debug, Default, Clone)]
struct Latest {
    timestamp_ns: i64,
    measurement_type: String,
    value: Value,
}

#[derive(Debug, Default, Clone)]
struct Series {
    series_id: Option<i64>,
    attribute: String,
    unit: String,
    kind: Option<Kind>,
    first_ns: i64,
    last: Option<Latest>,
}

#[derive(Debug, Default, Clone)]
struct Device {
    mac: String,
    name: String,
    last_ns: i64,
    series: BTreeMap<(String, String), Series>,
}

fn catalog_action(config: &Path) -> Result<Value, String> {
    let (connection, path) = connect(config)?;
    let now = now_ns();
    let devices = catalog(&connection, now)?;
    Ok(json!({
        "ok": true,
        "now_ns": now,
        "database": path.display().to_string(),
        "schema": schema_version(&connection),
        "archived": archived(&connection),
        "devices": devices.iter().map(device_json).collect::<Vec<_>>(),
    }))
}

fn catalog(connection: &Connection, now: i64) -> Result<Vec<Device>, String> {
    let mut devices: BTreeMap<String, Device> = BTreeMap::new();
    let is_archived = archived(connection);

    // Devices and their newest frame: GROUP BY on frames_mac_time(mac,
    // received_at_ns) so the scan never touches the large state_json column.
    let mut statement = connection
        .prepare("SELECT mac, MAX(received_at_ns) FROM frames GROUP BY mac")
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?))
        })
        .map_err(|error| error.to_string())?;
    for row in rows {
        let (mac, last_ns) = row.map_err(|error| error.to_string())?;
        devices.entry(mac.clone()).or_insert_with(|| Device {
            mac,
            ..Device::default()
        }).last_ns = last_ns;
    }
    drop(statement);

    if is_archived {
        if let Ok(mut statement) = connection.prepare("SELECT mac, sensor_name FROM history_devices")
        {
            if let Ok(rows) = statement.query_map([], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            }) {
                for row in rows.flatten() {
                    devices.entry(row.0.clone()).or_insert_with(|| Device {
                        mac: row.0.clone(),
                        ..Device::default()
                    }).name = row.1;
                }
            }
        }
    }

    // A device that only ever produced raw frames: take the newest name.
    for device in devices.values_mut().filter(|device| device.name.is_empty()) {
        device.name = connection
            .query_row(
                "SELECT sensor_name FROM frames INDEXED BY frames_mac_time \
                 WHERE mac=?1 ORDER BY received_at_ns DESC LIMIT 1",
                [&device.mac],
                |row| row.get::<_, String>(0),
            )
            .unwrap_or_default();
    }

    // Archived series: the maintenance job knows every attribute it kept.
    if is_archived {
        let mut statement = connection
            .prepare("SELECT id, mac, attribute, unit FROM history_series")
            .map_err(|error| error.to_string())?;
        let rows = statement
            .query_map([], |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                    row.get::<_, String>(3)?,
                ))
            })
            .map_err(|error| error.to_string())?;
        for row in rows {
            let (id, mac, attribute, unit) = row.map_err(|error| error.to_string())?;
            let device = devices.entry(mac.clone()).or_insert_with(|| Device {
                mac: mac.clone(),
                ..Device::default()
            });
            let series = device
                .series
                .entry((attribute.clone(), unit.clone()))
                .or_insert_with(|| Series {
                    attribute,
                    unit,
                    ..Series::default()
                });
            series.series_id = Some(id);
        }
        drop(statement);
    }

    // Raw-only series: attributes seen in the most recent frames of a device.
    // Bounded so the query stays cheap even when maintenance is disabled and
    // the raw tables hold the full history.
    let macs: Vec<String> = devices.keys().cloned().collect();
    for mac in macs {
        let mut statement = match connection.prepare(
            "SELECT m.attribute, m.unit, m.type \
             FROM frames f INDEXED BY frames_mac_time \
             JOIN measurements m ON m.frame_id=f.id \
             WHERE f.mac=?1 ORDER BY f.received_at_ns DESC LIMIT ?2",
        ) {
            Ok(statement) => statement,
            Err(_) => continue,
        };
        let rows = match statement.query_map(params![mac, RAW_CATALOG_ROWS], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
            ))
        }) {
            Ok(rows) => rows,
            Err(_) => continue,
        };
        for row in rows.flatten() {
            let (attribute, unit, measurement_type) = row;
            let kind = Kind::of_type(&measurement_type);
            let device = devices.entry(mac.clone()).or_insert_with(|| Device {
                mac: mac.clone(),
                ..Device::default()
            });
            let series = device
                .series
                .entry((attribute.clone(), unit.clone()))
                .or_insert_with(|| Series {
                    attribute,
                    unit,
                    ..Series::default()
                });
            series.kind = Some(match series.kind {
                Some(kind_so_far) => kind_so_far.merge(kind),
                None => kind,
            });
        }
    }

    // Latest value per series plus the first archived timestamp.
    for device in devices.values_mut() {
        device
            .series
            .retain(|_, series| series.series_id.is_some() || series.kind.is_some());
        for series in device.series.values_mut() {
            let newest = newest_value(connection, &device.mac, series).unwrap_or_default();
            if newest.timestamp_ns > 0 {
                let kind = Kind::of_type(&newest.measurement_type);
                series.kind = Some(match series.kind {
                    Some(kind_so_far) => kind_so_far.merge(kind),
                    None => kind,
                });
            }
            series.last = Some(newest).filter(|latest| latest.timestamp_ns > 0);
            series.first_ns = first_timestamp(connection, &device.mac, series).unwrap_or(0);
        }
    }

    let mut list: Vec<Device> = devices.into_values().collect();
    list.sort_by(|left, right| {
        right
            .last_ns
            .cmp(&left.last_ns)
            .then_with(|| left.mac.cmp(&right.mac))
    });
    let _ = now;
    Ok(list)
}

/// Newest sample of a series, taking the newer of the archive and raw tables.
fn newest_value(
    connection: &Connection,
    mac: &str,
    series: &Series,
) -> Result<Latest, String> {
    let mut best = Latest::default();
    if let Some(id) = series.series_id {
        if let Ok(row) = connection.query_row(
            "SELECT received_at_ns, type, value_json FROM history_samples \
             WHERE series_id=?1 ORDER BY received_at_ns DESC, id DESC LIMIT 1",
            [id],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                ))
            },
        ) {
            best = Latest {
                timestamp_ns: row.0,
                measurement_type: row.1.clone(),
                value: json_from_text(&row.1, &row.2),
            };
        }
    }
    if let Ok(row) = connection.query_row(
        "SELECT f.received_at_ns, m.type, m.value_real, m.value_int, m.value_text \
         FROM frames f INDEXED BY frames_mac_time \
         JOIN measurements m ON m.frame_id=f.id AND m.attribute=?1 AND m.unit=?2 \
         WHERE f.mac=?3 ORDER BY f.received_at_ns DESC LIMIT 1",
        params![series.attribute, series.unit, mac],
        |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, Option<f64>>(2)?,
                row.get::<_, Option<i64>>(3)?,
                row.get::<_, Option<String>>(4)?,
            ))
        },
    ) {
        if row.0 >= best.timestamp_ns {
            best = Latest {
                timestamp_ns: row.0,
                measurement_type: row.1.clone(),
                value: json_from_raw(&row.1, row.2, row.3, row.4),
            };
        }
    }
    Ok(best)
}

fn first_timestamp(connection: &Connection, mac: &str, series: &Series) -> Option<i64> {
    let mut first: Option<i64> = None;
    if let Some(id) = series.series_id {
        if let Ok(value) = connection.query_row(
            "SELECT MIN(received_at_ns) FROM history_samples WHERE series_id=?1",
            [id],
            |row| row.get::<_, Option<i64>>(0),
        ) {
            first = value;
        }
    }
    if let Ok(value) = connection.query_row(
        "SELECT MIN(f.received_at_ns) FROM frames f INDEXED BY frames_mac_time \
         JOIN measurements m ON m.frame_id=f.id AND m.attribute=?1 AND m.unit=?2 \
         WHERE f.mac=?3",
        params![series.attribute, series.unit, mac],
        |row| row.get::<_, Option<i64>>(0),
    ) {
        first = match (first, value) {
            (Some(left), Some(right)) => Some(left.min(right)),
            (None, right) => right,
            (left, None) => left,
        };
    }
    first
}

fn device_json(device: &Device) -> Value {
    let series: Vec<Value> = device
        .series
        .values()
        .map(|series| {
            json!({
                "attribute": series.attribute,
                "unit": series.unit,
                "kind": series.kind.unwrap_or(Kind::Text).as_str(),
                "type": series.last.as_ref().map(|latest| latest.measurement_type.clone()).unwrap_or_default(),
                "series_id": series.series_id,
                "first_ns": series.first_ns,
                "last_ns": series.last.as_ref().map(|latest| latest.timestamp_ns).unwrap_or(0),
                "value": series.last.as_ref().map(|latest| latest.value.clone()).unwrap_or(Value::Null),
            })
        })
        .collect();
    json!({
        "mac": device.mac,
        "name": device.name,
        "last_ns": device.last_ns,
        "series": series,
    })
}

// ---------------------------------------------------------------------------
// Time series
// ---------------------------------------------------------------------------

fn series_action(config: &Path, params: &BTreeMap<String, String>) -> Result<Value, String> {
    let mac = params.get("mac").map(String::as_str).unwrap_or("").trim();
    let attribute = params.get("attribute").map(String::as_str).unwrap_or("").trim();
    let unit = params.get("unit").map(String::as_str).unwrap_or("").trim();
    if mac.is_empty() || attribute.is_empty() {
        return Err("mac and attribute are required".into());
    }
    let kind = params
        .get("kind")
        .and_then(|value| Kind::parse(value))
        .unwrap_or(Kind::Numeric);
    if kind == Kind::Text {
        return Err("text values have no time series".into());
    }

    let window = params
        .get("range")
        .and_then(|value| value.parse::<u64>().ok())
        .unwrap_or(86_400);
    let buckets = params
        .get("buckets")
        .and_then(|value| value.parse::<u64>().ok())
        .unwrap_or(DEFAULT_BUCKETS)
        .clamp(8, MAX_BUCKETS);

    let (connection, _) = connect(config)?;
    let now = now_ns();
    let to = params
        .get("to")
        .and_then(|value| value.parse::<i64>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(now);

    let mut series = Series {
        attribute: attribute.to_string(),
        unit: unit.to_string(),
        kind: Some(kind),
        ..Series::default()
    };
    if archived(&connection) {
        if let Ok(id) = connection.query_row(
            "SELECT id FROM history_series WHERE mac=?1 AND attribute=?2 AND unit=?3",
            params![mac, attribute, unit],
            |row| row.get::<_, i64>(0),
        ) {
            series.series_id = Some(id);
        }
    }

    // "range=0" means the whole history of this series. An explicit `from`
    // wins: the browser sends it after a zoom selection.
    let requested_from = params
        .get("from")
        .and_then(|value| value.parse::<i64>().ok())
        .filter(|value| *value > 0 && *value < to);
    let (from, to) = if let Some(from) = requested_from {
        (from, to)
    } else if window == 0 {
        let first = first_timestamp(&connection, mac, &series).unwrap_or(to);
        (first, to.max(first + 1))
    } else {
        (to - window as i64 * 1_000_000_000, to)
    };

    let bucket_ns = ((to - from).max(1) / buckets as i64).max(1_000_000_000);
    let points = buckets_between(&connection, mac, &series, kind, from, to, bucket_ns)?;

    Ok(json!({
        "ok": true,
        "mac": mac,
        "attribute": attribute,
        "unit": unit,
        "kind": kind.as_str(),
        "from_ns": from,
        "to_ns": to,
        "bucket_ns": bucket_ns,
        "points": points.iter().map(|(timestamp, value, count)| json!([timestamp / 1_000_000, value, count])).collect::<Vec<_>>(),
    }))
}

/// Average per bucket, merging the archive and the raw tables.
fn buckets_between(
    connection: &Connection,
    mac: &str,
    series: &Series,
    kind: Kind,
    from: i64,
    to: i64,
    bucket_ns: i64,
) -> Result<Vec<(i64, f64, i64)>, String> {
    let mut buckets: HashMap<i64, (f64, i64)> = HashMap::new();
    let column = match kind {
        Kind::Numeric => "CAST(value_json AS REAL)",
        _ => "CASE WHEN value_json='true' THEN 1.0 ELSE 0.0 END",
    };
    if let Some(id) = series.series_id {
        let filter = match kind {
            Kind::Numeric => "type IN ('real','integer','unsigned')",
            _ => "type='boolean'",
        };
        let sql = format!(
            "SELECT (received_at_ns / ?1) * ?1 AS bucket, AVG({column}), COUNT(*) \
             FROM history_samples WHERE series_id=?2 AND received_at_ns>=?3 AND received_at_ns<=?4 \
             AND {filter} GROUP BY bucket"
        );
        let mut statement = connection.prepare(&sql).map_err(|error| error.to_string())?;
        let rows = statement
            .query_map(params![bucket_ns, id, from, to], |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, f64>(1)?,
                    row.get::<_, i64>(2)?,
                ))
            })
            .map_err(|error| error.to_string())?;
        for row in rows.flatten() {
            merge_bucket(&mut buckets, row);
        }
    }

    let (value_column, filter) = match kind {
        Kind::Numeric => (
            "COALESCE(m.value_real, CAST(m.value_int AS REAL), CAST(m.value_text AS REAL))",
            "m.type IN ('real','integer','unsigned')",
        ),
        _ => (
            "CASE WHEN m.value_int<>0 THEN 1.0 ELSE 0.0 END",
            "m.type='boolean'",
        ),
    };
    let sql = format!(
        "SELECT (f.received_at_ns / ?1) * ?1 AS bucket, AVG({value_column}), COUNT(*) \
         FROM frames f INDEXED BY frames_mac_time \
         JOIN measurements m ON m.frame_id=f.id AND m.attribute=?2 AND m.unit=?3 \
         WHERE f.mac=?4 AND f.received_at_ns>=?5 AND f.received_at_ns<=?6 AND {filter} \
         GROUP BY bucket"
    );
    let mut statement = connection.prepare(&sql).map_err(|error| error.to_string())?;
    let rows = statement
        .query_map(
            params![bucket_ns, series.attribute, series.unit, mac, from, to],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, f64>(1)?,
                    row.get::<_, i64>(2)?,
                ))
            },
        )
        .map_err(|error| error.to_string())?;
    for row in rows.flatten() {
        merge_bucket(&mut buckets, row);
    }

    let mut points: Vec<(i64, f64, i64)> = buckets
        .into_iter()
        .map(|(bucket, (sum, count))| {
            let value = sum / count as f64;
            (bucket, (value * 1000.0).round() / 1000.0, count)
        })
        .collect();
    points.sort_by_key(|point| point.0);
    Ok(points)
}

/// Accumulate `(sum, count)` so archived and raw averages are weighted.
fn merge_bucket(buckets: &mut HashMap<i64, (f64, i64)>, (bucket, average, count): (i64, f64, i64)) {
    let entry = buckets.entry(bucket).or_insert((0.0, 0));
    entry.0 += average * count as f64;
    entry.1 += count;
}

// ---------------------------------------------------------------------------
// Database statistics
// ---------------------------------------------------------------------------

fn info_action(config: &Path) -> Result<Value, String> {
    let (connection, path) = connect(config)?;
    let count = |sql: &str, table: &str| -> i64 {
        if has_table(&connection, table) {
            connection.query_row(sql, [], |row| row.get::<_, i64>(0)).unwrap_or(0)
        } else {
            0
        }
    };
    let metadata = std::fs::metadata(&path).ok();
    let size = metadata.as_ref().map(|value| value.len()).unwrap_or(0);
    let modified_ms = metadata
        .and_then(|value| value.modified().ok())
        .and_then(|value| value.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|value| value.as_millis() as i64)
        .unwrap_or(0);
    let wal = std::fs::metadata(format!("{}-wal", path.display()))
        .map(|value| value.len())
        .unwrap_or(0);

    let newest = if has_table(&connection, "history") {
        connection
            .query_row("SELECT MAX(received_at_ns) FROM history", [], |row| {
                row.get::<_, Option<i64>>(0)
            })
            .unwrap_or(None)
    } else {
        None
    };

    Ok(json!({
        "ok": true,
        "now_ns": now_ns(),
        "database": path.display().to_string(),
        "schema": schema_version(&connection),
        "archived": archived(&connection),
        "size_bytes": size,
        "wal_bytes": wal,
        "modified_ms": modified_ms,
        "frames": count("SELECT COUNT(*) FROM frames", "frames"),
        "measurements": count("SELECT COUNT(*) FROM measurements", "measurements"),
        "samples": count("SELECT COUNT(*) FROM history_samples", "history_samples"),
        "devices": count("SELECT COUNT(*) FROM history_devices", "history_devices"),
        "series": count("SELECT COUNT(*) FROM history_series", "history_series"),
        "newest_ns": newest,
        "process": process_json(),
    }))
}

/// Own memory footprint, useful to compare this CGI with a PHP equivalent.
fn process_json() -> Value {
    let status = std::fs::read_to_string("/proc/self/status").unwrap_or_default();
    let field = |name: &str| -> u64 {
        status
            .lines()
            .find(|line| line.starts_with(name))
            .and_then(|line| line.split_whitespace().nth(1))
            .and_then(|value| value.parse::<u64>().ok())
            .unwrap_or(0)
    };
    json!({
        "rss_kb": field("VmRSS:"),
        "peak_kb": field("VmHWM:"),
        "threads": field("Threads:"),
    })
}

// ---------------------------------------------------------------------------
// HTML shell
// ---------------------------------------------------------------------------

fn page() -> String {
    r#"<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ble2uart_gateway &middot; Sensori</title>
<link rel="stylesheet" href="/ble2uart_gateway/portal.css?v={v}">
</head>
<body>
<header class="ptop">
  <div class="ptitle"><span class="pdot"></span><h1 id="title">ble2uart_gateway</h1><span class="psub" id="subtitle">Sensori</span></div>
  <nav class="pactions">
    <span class="pstamp" id="stamp">&mdash;</span>
    <button class="pbtn" id="reload" type="button" title="Aggiorna">&#8635;</button>
    <a class="pbtn" id="config" href="/cgi-bin/conf/ble2uart_gateway" title="Configurazione">&#9881;</a>
  </nav>
</header>
<main class="pmain">
  <section class="pkpis" id="kpis"></section>
  <div class="playout">
    <section class="pdevices" id="devices"><p class="pempty">Caricamento&hellip;</p></section>
    <aside class="pchart">
      <div class="pcharthead">
        <h2 id="charttitle">&mdash;</h2>
        <div class="pcontrols">
          <div class="pranges" id="ranges"></div>
          <div class="pzoom">
            <button type="button" id="panleft" title="Pan">&lsaquo;</button>
            <button type="button" id="panright" title="Pan">&rsaquo;</button>
            <button type="button" id="zoomin" title="Zoom +">+</button>
            <button type="button" id="zoomout" title="Zoom &minus;">&minus;</button>
            <button type="button" id="zoomreset" title="Reset">&#8634;</button>
            <button type="button" id="fullscreen" title="Fullscreen">&#9974;</button>
            <button type="button" id="help" title="Help">?</button>
          </div>
        </div>
      </div>
      <div class="pzoominfo" id="zoominfo" hidden></div>
      <div class="pcanvas"><canvas id="canvas"></canvas><div class="pempty" id="chartempty"></div></div>
      <div class="plegend" id="legend"></div>
      <p class="phint"><span id="chartinfo"></span><button type="button" class="plink" id="helplink"></button></p>
      <div class="ptip" id="tip" hidden></div>
      <dialog class="phelp" id="helpbox" aria-labelledby="helptitle">
        <h3 id="helptitle"></h3>
        <dl id="helpbody"></dl>
        <p class="phelpnote" id="helpnote"></p>
        <form method="dialog"><button type="submit" id="helpclose"></button></form>
      </dialog>
    </aside>
  </div>
</main>
<noscript><p>JavaScript richiesto.</p></noscript>
<script src="/ble2uart_gateway/portal.js?v={v}"></script>
</body>
</html>
"#
    .replace("{v}", ASSET_VERSION)
}

/// Bumped whenever `portal.css` or `portal.js` change, so a router that
/// caches static files still serves the new version.
const ASSET_VERSION: &str = "4";

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::Connection;

    fn database() -> Connection {
        let connection = Connection::open_in_memory().unwrap();
        connection.execute_batch(crate::sqlite::SCHEMA).unwrap();
        connection
            .execute_batch(crate::sqlite::HISTORY_SCHEMA)
            .unwrap();
        connection
    }

    fn frame(connection: &Connection, id: i64, mac: &str, name: &str, ns: i64) {
        connection
            .execute(
                "INSERT INTO frames (id, received_at_ns, mac, sensor_name, wire_format, state_json) \
                 VALUES (?1, ?2, ?3, ?4, 'bthome', '{}')",
                params![id, ns, mac, name],
            )
            .unwrap();
    }

    fn measurement(
        connection: &Connection,
        frame_id: i64,
        ordinal: i64,
        attribute: &str,
        unit: &str,
        kind: &str,
        value: f64,
    ) {
        connection
            .execute(
                "INSERT INTO measurements (frame_id, ordinal, attribute, unit, type, value_real, value_int) \
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
                params![
                    frame_id,
                    ordinal,
                    attribute,
                    unit,
                    if kind == "boolean" { "boolean" } else { "real" },
                    if kind == "boolean" { None } else { Some(value) },
                    if kind == "boolean" { Some(value as i64) } else { None },
                ],
            )
            .unwrap();
    }

    #[test]
    fn query_string_is_percent_decoded() {
        let params = parse_query("action=series&attribute=temperature&unit=%C2%B0C&mac=A4C1383406CE&x=a+b");
        assert_eq!(params.get("action").unwrap(), "series");
        assert_eq!(params.get("unit").unwrap(), "°C");
        assert_eq!(params.get("x").unwrap(), "a b");
        assert!(params.get("missing").is_none());
    }

    #[test]
    fn unknown_kind_is_rejected() {
        assert_eq!(Kind::parse("numeric"), Some(Kind::Numeric));
        assert_eq!(Kind::parse("Text"), None);
        assert_eq!(Kind::of_type("boolean"), Kind::Boolean);
        assert_eq!(Kind::of_type("unsigned"), Kind::Numeric);
        assert_eq!(Kind::of_type("str"), Kind::Text);
    }

    #[test]
    fn raw_values_become_json() {
        assert_eq!(json_from_raw("real", Some(21.5), None, None), json!(21.5));
        assert_eq!(json_from_raw("integer", None, Some(7), None), json!(7));
        assert_eq!(json_from_raw("boolean", None, Some(0), None), json!(false));
        assert_eq!(
            json_from_raw("text", None, None, Some("ok".into())),
            json!("ok")
        );
        assert_eq!(json_from_raw("null", None, None, None), Value::Null);
    }

    #[test]
    fn catalog_discovers_raw_series_dynamically() {
        let connection = database();
        let now = 1_700_000_000_000_000_000_i64;
        frame(&connection, 1, "AABBCCDDEEFF", "Sonda", now - 5_000_000_000);
        measurement(&connection, 1, 0, "temperature", "°C", "real", 20.5);
        measurement(&connection, 1, 1, "humidity", "%", "real", 48.0);
        measurement(&connection, 1, 2, "opened", "", "boolean", 1.0);

        let devices = catalog(&connection, now).unwrap();
        assert_eq!(devices.len(), 1);
        let device = &devices[0];
        assert_eq!(device.mac, "AABBCCDDEEFF");
        assert_eq!(device.name, "Sonda");
        assert_eq!(device.last_ns, now - 5_000_000_000);
        assert_eq!(device.series.len(), 3);
        let temperature = &device.series[&("temperature".to_string(), "°C".to_string())];
        assert_eq!(temperature.kind, Some(Kind::Numeric));
        assert_eq!(temperature.last.as_ref().unwrap().value, json!(20.5));
        let opened = &device.series[&("opened".to_string(), String::new())];
        assert_eq!(opened.kind, Some(Kind::Boolean));
        assert_eq!(opened.last.as_ref().unwrap().value, json!(true));
    }

    #[test]
    fn archived_series_are_merged_with_raw_ones() {
        let connection = database();
        let now = 1_700_000_000_000_000_000_i64;
        connection
            .execute(
                "INSERT INTO history_devices (mac, sensor_name, device_json) VALUES ('AABBCCDDEEFF','Sonda','{}')",
                [],
            )
            .unwrap();
        connection
            .execute(
                "INSERT INTO history_series (id, mac, attribute, unit) VALUES (1,'AABBCCDDEEFF','temperature','°C')",
                [],
            )
            .unwrap();
        connection
            .execute(
                "INSERT INTO history_samples (series_id, received_at_ns, type, value_json) VALUES (1, ?1, 'real', '19.5')",
                [now - 60_000_000_000],
            )
            .unwrap();
        // A raw-only attribute next to the archived one.
        frame(&connection, 1, "AABBCCDDEEFF", "Sonda", now - 1_000_000_000);
        measurement(&connection, 1, 0, "humidity", "%", "real", 50.0);

        let devices = catalog(&connection, now).unwrap();
        assert_eq!(devices.len(), 1);
        let device = &devices[0];
        assert_eq!(device.name, "Sonda");
        let temperature = &device.series[&("temperature".to_string(), "°C".to_string())];
        assert_eq!(temperature.series_id, Some(1));
        assert_eq!(temperature.last.as_ref().unwrap().value, json!(19.5));
        assert_eq!(temperature.first_ns, now - 60_000_000_000);
        let humidity = &device.series[&("humidity".to_string(), "%".to_string())];
        assert_eq!(humidity.series_id, None);
        assert_eq!(humidity.last.as_ref().unwrap().value, json!(50.0));
    }

    #[test]
    fn buckets_average_archive_and_raw() {
        let connection = database();
        let now = 1_700_000_000_000_000_000_i64;
        let series = {
            connection
                .execute(
                    "INSERT INTO history_devices (mac, sensor_name, device_json) VALUES ('AABBCCDDEEFF','Sonda','{}')",
                    [],
                )
                .unwrap();
            connection
                .execute(
                    "INSERT INTO history_series (id, mac, attribute, unit) VALUES (1,'AABBCCDDEEFF','temperature','°C')",
                    [],
                )
                .unwrap();
            // Two archived samples in the same 60 s bucket.
            for (offset, value) in [(30_000_000_000_i64, "20.0"), (40_000_000_000, "22.0")] {
                connection
                    .execute(
                        "INSERT INTO history_samples (series_id, received_at_ns, type, value_json) VALUES (1, ?1, 'real', ?2)",
                        params![now - offset, value],
                    )
                    .unwrap();
            }
            Series {
                series_id: Some(1),
                attribute: "temperature".into(),
                unit: "°C".into(),
                kind: Some(Kind::Numeric),
                ..Series::default()
            }
        };
        // One raw sample in the same bucket.
        frame(&connection, 1, "AABBCCDDEEFF", "Sonda", now - 45_000_000_000);
        measurement(&connection, 1, 0, "temperature", "°C", "real", 24.0);

        let points = buckets_between(
            &connection,
            "AABBCCDDEEFF",
            &series,
            Kind::Numeric,
            now - 120_000_000_000,
            now,
            60_000_000_000,
        )
        .unwrap();
        assert_eq!(points.len(), 1);
        assert_eq!(points[0].2, 3);
        assert!((points[0].1 - 22.0).abs() < 0.001, "{:?}", points);
    }

    #[test]
    fn boolean_series_are_averaged_as_zero_and_one() {
        let connection = database();
        let now = 1_700_000_000_000_000_000_i64;
        let series = Series {
            series_id: None,
            attribute: "opened".into(),
            unit: String::new(),
            kind: Some(Kind::Boolean),
            ..Series::default()
        };
        frame(&connection, 1, "AABBCCDDEEFF", "Sonda", now - 10_000_000_000);
        measurement(&connection, 1, 0, "opened", "", "boolean", 0.0);
        frame(&connection, 2, "AABBCCDDEEFF", "Sonda", now - 20_000_000_000);
        measurement(&connection, 2, 0, "opened", "", "boolean", 1.0);

        let points = buckets_between(
            &connection,
            "AABBCCDDEEFF",
            &series,
            Kind::Boolean,
            now - 60_000_000_000,
            now,
            60_000_000_000,
        )
        .unwrap();
        assert_eq!(points.len(), 1);
        assert_eq!(points[0].2, 2);
        assert!((points[0].1 - 0.5).abs() < 0.001);
    }

    #[test]
    fn missing_database_is_reported() {
        let error = resolve_database_path(Path::new("/nonexistent/config.yaml"), None).unwrap_err();
        assert!(!error.is_empty());
        let explicit = resolve_database_path(
            Path::new("/nonexistent/config.yaml"),
            Some(PathBuf::from("/tmp/example.db")),
        )
        .unwrap();
        assert_eq!(explicit, PathBuf::from("/tmp/example.db"));
    }
}
