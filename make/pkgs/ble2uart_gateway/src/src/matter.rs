use serde_json::Value;
use std::collections::BTreeMap;
use std::path::Path;
use std::sync::{Arc, Mutex};

pub const VENDOR_CLUSTER: u32 = 0xFFF1FC00;
pub const JSON_CHUNK_BYTES: usize = 256;

#[derive(Clone)]
pub struct Snapshot {
    pub version: u32,
    pub value: Value,
    pub json: Vec<u8>,
}

pub type SharedStates = Arc<Mutex<BTreeMap<String, Snapshot>>>;

pub struct MatterPublisher {
    pub states: SharedStates,
    pub(crate) stopped: Arc<std::sync::atomic::AtomicBool>,
    pub(crate) worker: Option<std::thread::JoinHandle<()>>,
    pub(crate) domoticz_bridge: Option<crate::managed_process::ManagedProcess>,
}

impl Default for MatterPublisher {
    fn default() -> Self {
        Self {
            states: Arc::new(Mutex::new(BTreeMap::new())),
            stopped: Arc::new(std::sync::atomic::AtomicBool::new(false)),
            worker: None,
            domoticz_bridge: None,
        }
    }
}

impl Drop for MatterPublisher {
    fn drop(&mut self) {
        drop(self.domoticz_bridge.take());
        self.stopped
            .store(true, std::sync::atomic::Ordering::Relaxed);
        if let Some(worker) = self.worker.take() {
            let _ = worker.join();
        }
    }
}

impl MatterPublisher {
    pub fn publish(&self, mac: &str, value: &Value) {
        let mut states = self.states.lock().unwrap();
        let version = states
            .get(mac)
            .map(|state| state.version.wrapping_add(1))
            .unwrap_or(1);
        let mut value = value.clone();
        crate::pipeline::merge_latest_values(states.get(mac).map(|state| &state.value), &mut value);
        let json = serde_json::to_vec(&value).expect("JSON state serialization");
        states.insert(
            mac.into(),
            Snapshot {
                version,
                value,
                json,
            },
        );
    }
}

pub fn endpoint_ids(store: &Path, keys: &[String]) -> Result<BTreeMap<String, u16>, String> {
    use std::os::unix::fs::PermissionsExt;
    std::fs::create_dir_all(store).map_err(|error| error.to_string())?;
    std::fs::set_permissions(store, std::fs::Permissions::from_mode(0o700))
        .map_err(|error| error.to_string())?;
    let path = store.join("endpoints.json");
    let mut ids: BTreeMap<String, u16> = match std::fs::read(&path) {
        Ok(data) => {
            serde_json::from_slice(&data).map_err(|_| "invalid persistent Matter endpoint map")?
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => BTreeMap::new(),
        Err(error) => return Err(error.to_string()),
    };
    let used: std::collections::HashSet<_> = ids.values().collect();
    if used.len() != ids.len() || ids.values().any(|id| *id < 2 || *id == u16::MAX) {
        return Err("duplicate or reserved Matter endpoint IDs".into());
    }
    for key in keys {
        if !ids.contains_key(key) {
            let next = ids
                .values()
                .copied()
                .max()
                .unwrap_or(1)
                .checked_add(1)
                .filter(|id| *id != u16::MAX)
                .ok_or("Matter endpoint IDs exhausted")?;
            ids.insert(key.clone(), next);
        }
    }
    let temporary = store.join("endpoints.json.new");
    let mut options = std::fs::OpenOptions::new();
    use std::io::Write;
    use std::os::unix::fs::OpenOptionsExt;
    let mut file = options
        .write(true)
        .create(true)
        .truncate(true)
        .mode(0o600)
        .open(&temporary)
        .map_err(|error| error.to_string())?;
    file.write_all(&serde_json::to_vec(&ids).map_err(|error| error.to_string())?)
        .map_err(|error| error.to_string())?;
    file.sync_all().map_err(|error| error.to_string())?;
    std::fs::rename(temporary, path).map_err(|error| error.to_string())?;
    Ok(ids)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Standard {
    Temperature,
    Humidity,
    Pressure,
    Illuminance,
    Boolean,
    Occupancy,
    BatteryPercent,
    BatteryVoltage,
}

impl Standard {
    pub fn for_attribute(name: &str) -> Option<Self> {
        match name {
            "temperature" => Some(Self::Temperature),
            "humidity" => Some(Self::Humidity),
            "pressure" => Some(Self::Pressure),
            "illuminance" | "lux" => Some(Self::Illuminance),
            "motion" => Some(Self::Occupancy),
            "battery" | "battery_level" => Some(Self::BatteryPercent),
            "battery_v" | "voltage" => Some(Self::BatteryVoltage),
            "opened" | "contact" | "door" | "water_leak" | "flooding" | "switch" | "boolean"
            | "humidity_trigger" | "temp_trigger" | "out_gpio_trg_flag" | "out_gpio_trg_value"
            | "input_gpio_value" => Some(Self::Boolean),
            _ => None,
        }
    }

    pub fn cluster(self) -> u32 {
        match self {
            Self::Temperature => 0x0402,
            Self::Humidity => 0x0405,
            Self::Pressure => 0x0403,
            Self::Illuminance => 0x0400,
            Self::Boolean => 0x0045,
            Self::Occupancy => 0x0406,
            Self::BatteryPercent | Self::BatteryVoltage => 0x002F,
        }
    }

    pub fn convert(self, value: &Value) -> Option<Value> {
        if self == Self::Boolean || self == Self::Occupancy {
            let boolean = value.as_bool().or_else(|| {
                value
                    .as_i64()
                    .filter(|number| matches!(number, 0 | 1))
                    .map(|number| number == 1)
            })?;
            return Some(if self == Self::Boolean {
                Value::Bool(boolean)
            } else {
                Value::from(u8::from(boolean))
            });
        }
        let number = value.as_f64().filter(|number| number.is_finite())?;
        let scaled = match self {
            Self::Temperature => number * 100.0,
            Self::Humidity => number * 100.0,
            Self::Pressure => number,
            Self::BatteryPercent => number * 2.0,
            Self::BatteryVoltage => number * 1000.0,
            Self::Illuminance if number == 0.0 => 0.0,
            Self::Illuminance if number > 0.0 => 10000.0 * number.log10() + 1.0,
            _ => return None,
        };
        let range = match self {
            Self::Temperature => (-27315.0, 32767.0),
            Self::Humidity => (0.0, 10000.0),
            Self::Pressure => (-32767.0, 32767.0),
            Self::Illuminance => (0.0, 65534.0),
            Self::BatteryPercent => (0.0, 200.0),
            Self::BatteryVoltage => (0.0, 4294967294.0),
            _ => return None,
        };
        if scaled < range.0 || scaled > range.1 {
            return None;
        }
        Some(Value::from(scaled.round() as i64))
    }

    pub fn convert_unit(self, value: &Value, unit: &str) -> Option<Value> {
        if matches!(self, Self::Boolean | Self::Occupancy) {
            return self.convert(value);
        }
        let number = value.as_f64().filter(|value| value.is_finite())?;
        let unit = unit.trim().to_lowercase();
        let normalized = match self {
            Self::Temperature => match unit.as_str() {
                "" | "c" | "\u{00b0}c" => number,
                "f" | "\u{00b0}f" => (number - 32.0) * 5.0 / 9.0,
                "k" => number - 273.15,
                _ => return None,
            },
            Self::Humidity | Self::BatteryPercent => match unit.as_str() {
                "" | "%" => number,
                _ => return None,
            },
            Self::Pressure => match unit.as_str() {
                "" | "hpa" | "mbar" => number,
                "pa" => number / 100.0,
                "kpa" => number * 10.0,
                "bar" => number * 1000.0,
                _ => return None,
            },
            Self::Illuminance => match unit.as_str() {
                "" | "lx" | "lux" => number,
                _ => return None,
            },
            Self::BatteryVoltage => match unit.as_str() {
                "" | "v" => number,
                "mv" => number / 1000.0,
                _ => return None,
            },
            _ => return None,
        };
        self.convert(&serde_json::json!(normalized))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matter_preserves_complete_json_and_endpoint_identity() {
        let publisher = MatterPublisher::default();
        let value = serde_json::json!({"unmapped":[null,true,12.3456789],"unicode":"\u{00e9}","large":"x".repeat(5000)});
        publisher.publish("AABBCCDDEEFF", &value);
        let states = publisher.states.lock().unwrap();
        let snapshot = &states["AABBCCDDEEFF"];
        assert_eq!(
            snapshot
                .json
                .chunks(JSON_CHUNK_BYTES)
                .flatten()
                .copied()
                .collect::<Vec<_>>(),
            serde_json::to_vec(&value).unwrap()
        );
        assert_eq!(snapshot.value, value);
        drop(states);
        let directory = std::env::temp_dir().join(format!("ble-matter-ids-{}", std::process::id()));
        let initial =
            endpoint_ids(&directory, &["MAC1".into(), "MAC2/temperature".into()]).unwrap();
        let reordered =
            endpoint_ids(&directory, &["MAC2/temperature".into(), "MAC3".into()]).unwrap();
        assert_eq!(initial["MAC2/temperature"], reordered["MAC2/temperature"]);
        assert_ne!(initial["MAC1"], reordered["MAC3"]);
        std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn standard_mapping_does_not_silently_clamp_or_round_booleans() {
        assert_eq!(
            Standard::Temperature.convert(&serde_json::json!(23.45)),
            Some(serde_json::json!(2345))
        );
        assert_eq!(Standard::Humidity.convert(&serde_json::json!(101)), None);
        assert_eq!(Standard::Boolean.convert(&serde_json::json!(2)), None);
        assert_eq!(
            Standard::Boolean.convert(&serde_json::json!(true)),
            Some(Value::Bool(true))
        );
        assert_eq!(
            Standard::Illuminance.convert(&serde_json::json!(100)),
            Some(serde_json::json!(20001))
        );
        assert_eq!(Standard::for_attribute("new_vendor_value"), None);
        assert_eq!(
            Standard::Humidity.convert(&serde_json::json!(100.00001)),
            None
        );
        assert_eq!(
            Standard::BatteryPercent.convert(&serde_json::json!(-0.001)),
            None
        );
        assert_eq!(
            Standard::Temperature.convert_unit(&serde_json::json!(77), "F"),
            Some(serde_json::json!(2500))
        );
        assert_eq!(
            Standard::Pressure.convert_unit(&serde_json::json!(101325), "Pa"),
            Some(serde_json::json!(1013))
        );
        assert_eq!(
            Standard::BatteryVoltage.convert_unit(&serde_json::json!(3020), "mV"),
            Some(serde_json::json!(3020))
        );
        assert_eq!(
            Standard::Temperature.convert_unit(&serde_json::json!(25), "unrecognized"),
            None
        );
    }
}
