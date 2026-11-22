//! Attributes decoded per device, collected before any publication choice.
//!
//! The web interface lists them, so every decodable attribute can be renamed
//! and routed even when it is not published anywhere. The latest values stay
//! in memory; only names, units and types are written to disk, and only when
//! one of them changes, so the radio rate never turns into storage writes.

use crate::pipeline::Measurement;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value as Json};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const MAX_ATTRIBUTES: usize = 256;
const WRITE_INTERVAL: Duration = Duration::from_secs(30);

/// Protocol fields: header bits, packet counters and container metadata.
const TECHNICAL: &[&str] = &[
    "Version", "Reserved", "Reserved1", "Reserved2", "Trigger", "Encryption", "Mesh",
    "Object_Include", "Capability_Include", "MAC_Include", "isEncrypted", "Auth_Mode",
    "solicited", "registered", "packet_id", "count_id", "packet_1", "packet_2",
];

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct Known {
    pub unit: String,
    #[serde(rename = "type")]
    pub kind: String,
}

type Devices = BTreeMap<String, BTreeMap<String, Known>>;

struct Latest {
    value: Json,
    seen_ns: i64,
    count: u64,
}

pub struct Catalog {
    path: Option<PathBuf>,
    prefix: String,
    known: Devices,
    latest: BTreeMap<(String, String), Latest>,
    dirty: bool,
    written: Option<Instant>,
    failed: bool,
}

/// The catalog file next to the configuration file.
pub fn path_for(config: &Path) -> PathBuf {
    config.with_extension("attributes.json")
}

/// Persisted catalog; a missing or unreadable file is an empty catalog.
pub fn read(path: &Path) -> Devices {
    std::fs::read(path).ok()
        .and_then(|data| serde_json::from_slice::<Json>(&data).ok())
        .and_then(|document| serde_json::from_value(document["devices"].clone()).ok())
        .unwrap_or_default()
}

/// Header and counter fields hidden by default in the web interface.
pub fn technical(source: &str, prefix: &str) -> bool {
    TECHNICAL.contains(&source.strip_prefix(prefix).unwrap_or(source))
}

pub fn kind_of(measure: &Measurement) -> &'static str {
    use crate::codec::value::Value;
    match measure.value {
        Value::Float(_) => "real",
        Value::Int(_) => "integer",
        Value::Bool(_) => "boolean",
        Value::Text(_) => "text",
        Value::Bytes(_) => "bytes",
        Value::Null | Value::List(_) | Value::Map(_) => "json",
    }
}

fn now_ns() -> i64 {
    SystemTime::now().duration_since(UNIX_EPOCH).ok()
        .and_then(|time| i64::try_from(time.as_nanos()).ok()).unwrap_or(0)
}

impl Catalog {
    pub fn load(path: Option<PathBuf>, prefix: &str) -> Self {
        let known = path.as_deref().map(read).unwrap_or_default();
        Self { path, prefix: prefix.into(), known, latest: BTreeMap::new(), dirty: false, written: None, failed: false }
    }

    /// Decoder names seen for a device, including earlier runs.
    pub fn sources<'a>(&'a self, mac: &str) -> impl Iterator<Item = &'a str> {
        self.known.get(mac).into_iter().flat_map(|device| device.keys().map(String::as_str))
    }

    pub fn observe(&mut self, mac: &str, measures: &[Measurement]) {
        let now = now_ns();
        let device = self.known.entry(mac.to_string()).or_default();
        for measure in measures {
            let known = Known { unit: measure.unit.clone(), kind: kind_of(measure).into() };
            if let Some(previous) = device.get_mut(&measure.name) {
                if *previous != known {
                    *previous = known;
                    self.dirty = true;
                }
            } else if device.len() < MAX_ATTRIBUTES {
                device.insert(measure.name.clone(), known);
                self.dirty = true;
            } else {
                continue;
            }
            let latest = self.latest.entry((mac.to_string(), measure.name.clone()))
                .or_insert(Latest { value: Json::Null, seen_ns: 0, count: 0 });
            latest.value = measure.value.to_json();
            latest.seen_ns = now;
            latest.count += 1;
        }
        if self.dirty && self.written.is_none_or(|written| written.elapsed() >= WRITE_INTERVAL) {
            self.flush();
        }
    }

    fn flush(&mut self) {
        let Some(path) = &self.path else { self.dirty = false; return; };
        self.written = Some(Instant::now());
        let temporary = path.with_extension("json.tmp");
        let result = serde_json::to_vec(&json!({"version": 1, "devices": self.known}))
            .map_err(|error| error.to_string())
            .and_then(|data| std::fs::write(&temporary, data).map_err(|error| error.to_string()))
            .and_then(|_| std::fs::rename(&temporary, path).map_err(|error| error.to_string()));
        match result {
            Ok(()) => { self.dirty = false; self.failed = false; }
            Err(error) if !self.failed => {
                self.failed = true;
                log::warn!("cannot save the attribute catalog {}: {error}", path.display());
            }
            Err(_) => {}
        }
    }

    /// Every collected attribute with its latest value, for the control socket.
    pub fn snapshot(&self) -> Json {
        let devices: serde_json::Map<String, Json> = self.known.iter().map(|(mac, attributes)| {
            let rows = attributes.iter().map(|(source, known)| {
                let mut row = json!({"source": source, "unit": known.unit, "type": known.kind,
                    "technical": technical(source, &self.prefix)});
                if let Some(latest) = self.latest.get(&(mac.clone(), source.clone())) {
                    row["value"] = latest.value.clone();
                    row["last_seen_ns"] = latest.seen_ns.into();
                    row["count"] = latest.count.into();
                }
                row
            }).collect::<Vec<_>>();
            (mac.clone(), Json::Array(rows))
        }).collect();
        json!({"success": true, "devices": devices})
    }
}

impl Drop for Catalog {
    fn drop(&mut self) {
        if self.dirty {
            self.flush();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::codec::value::Value;

    fn measure(name: &str, value: Value, unit: &str) -> Measurement {
        Measurement { name: name.into(), value, unit: unit.into() }
    }

    #[test]
    fn collects_every_attribute_and_persists_only_new_names() {
        let directory = std::env::temp_dir().join(format!("ble-catalog-{}", std::process::id()));
        std::fs::create_dir_all(&directory).unwrap();
        let path = path_for(&directory.join("gateway.yaml"));
        assert_eq!(path.file_name().unwrap(), "gateway.attributes.json");
        let mut catalog = Catalog::load(Some(path.clone()), "theengs_");
        catalog.observe("AABBCCDDEEFF", &[
            measure("temperature", Value::Float(21.5), "°C"),
            measure("Version", Value::Int(2), ""),
            measure("theengs_packet_1", Value::Int(7), ""),
        ]);
        assert_eq!(read(&path)["AABBCCDDEEFF"]["temperature"], Known { unit: "°C".into(), kind: "real".into() });
        let written = std::fs::metadata(&path).unwrap().modified().unwrap();
        catalog.observe("AABBCCDDEEFF", &[measure("temperature", Value::Float(22.0), "°C")]);
        assert_eq!(std::fs::metadata(&path).unwrap().modified().unwrap(), written);
        let snapshot = catalog.snapshot();
        let rows = snapshot["devices"]["AABBCCDDEEFF"].as_array().unwrap();
        let row = |source: &str| rows.iter().find(|row| row["source"] == source).unwrap().clone();
        assert_eq!(row("temperature")["value"], 22.0);
        assert_eq!(row("temperature")["count"], 2);
        assert_eq!(row("Version")["technical"], true);
        assert_eq!(row("theengs_packet_1")["technical"], true);
        assert_eq!(row("temperature")["technical"], false);
        catalog.observe("AABBCCDDEEFF", &[measure("humidity", Value::Float(50.0), "%")]);
        assert!(!read(&path)["AABBCCDDEEFF"].contains_key("humidity"), "writes are throttled");
        drop(catalog);
        let reloaded = Catalog::load(Some(path), "theengs_");
        assert_eq!(reloaded.sources("AABBCCDDEEFF").collect::<Vec<_>>(), ["Version", "humidity", "temperature", "theengs_packet_1"]);
        assert!(reloaded.snapshot()["devices"]["AABBCCDDEEFF"][0].get("value").is_none());
        std::fs::remove_dir_all(directory).unwrap();
    }
}
