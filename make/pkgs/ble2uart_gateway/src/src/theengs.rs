//! Optional Theengs Decoder backend.
//!
//! [Theengs Decoder](https://github.com/theengs/decoder) is a C++ library with
//! decoders for more than 140 BLE devices. It is licensed GPL-3.0-or-later, so
//! it is compiled into the daemon only when the package option
//! `FREETZ_PACKAGE_BLE2UART_GATEWAY_THEENGS` is enabled (Cargo feature
//! `theengs`). With the feature disabled every function here still exists, so
//! the configuration and the CGI stay identical: `decode` simply returns
//! `None`.
//!
//! `decoder: builtin | theengs | both` in the YAML selects the backend for a
//! device (global default in the top-level `decoder` key).
//!
//! Nothing is decoded by hand here either: the raw advertisement is converted
//! into the JSON object the C API expects (`servicedata` + `servicedatauuid`,
//! or `manufacturerdata`) and the library returns its own JSON.

use crate::codec::value::Value;
use crate::pipeline::{default_unit, Measurement};
use serde_json::{Map, Value as Json};

/// Theengs keys that describe the advertisement instead of a measurement.
const NOT_MEASURED: &[&str] = &[
    "id",
    "mac",
    "name",
    "rssi",
    "brand",
    "model",
    "model_id",
    "type",
    "coded",
    "acts",
    "cont",
    "tracker",
    "mfr",
    "uuid",
    "major",
    "minor",
    "txpower",
    "meas_no",
    "servicedata",
    "servicedatauuid",
    "manufacturerdata",
    "data",
];

/// Theengs keys that map onto a canonical attribute of this gateway.
const ALIASES: &[(&str, &str)] = &[
    ("tempc", "temperature"),
    ("hum", "humidity"),
    ("pres", "pressure"),
    ("batt", "battery_level"),
    ("volt", "battery_v"),
    ("moi", "moisture"),
    ("lux", "illuminance"),
];

/// Explicit units for Theengs keys that are published unchanged.
const UNITS: &[(&str, &str)] = &[
    ("tempf", "°F"),
    ("temp", "°C"),
    ("hum", "%"),
    ("pres", "hPa"),
    ("batt", "%"),
    ("volt", "V"),
    ("co2", "ppm"),
    ("pm25", "µg/m³"),
    ("pm10", "µg/m³"),
    ("tvoc", "ppb"),
    ("luminous", "lx"),
    ("weight", "kg"),
    ("power", "W"),
    ("energy", "kWh"),
    ("dist", "cm"),
    ("accx", "g"),
    ("accy", "g"),
    ("accz", "g"),
    ("gyrx", "°/s"),
    ("gyry", "°/s"),
    ("gyrz", "°/s"),
];

/// True when the library was linked into this build.
pub const fn available() -> bool {
    cfg!(feature = "theengs")
}

/// Build the payload the Theengs decoder expects from a raw advertisement.
///
/// The AD structures are walked in order and the first service data (16, 32 or
/// 128 bit UUID) or manufacturer data wins, exactly like the CGI does for the
/// WebAssembly decoder. Hex is lowercase because the library compares the
/// service UUID case-sensitively.
pub fn payload(mac: &str, name: &str, rssi: i16, advertisement: &[u8]) -> Option<Json> {
    let mut object = Map::new();
    let digits: String = mac
        .chars()
        .filter(char::is_ascii_hexdigit)
        .collect::<String>()
        .to_ascii_uppercase();
    if digits.len() == 12 {
        let formatted = digits
            .as_bytes()
            .chunks(2)
            .map(|pair| String::from_utf8_lossy(pair).to_string())
            .collect::<Vec<_>>()
            .join(":");
        object.insert("id".into(), Json::String(formatted.clone()));
        object.insert("mac".into(), Json::String(formatted));
    }
    if !name.is_empty() {
        object.insert("name".into(), Json::String(name.to_string()));
    }
    object.insert("rssi".into(), Json::from(rssi));

    // The advertised local name helps a few decoders and is often the only
    // human readable field of the advertisement.
    let mut advertised = String::new();
    let mut index = 0usize;
    while index + 2 <= advertisement.len() {
        let length = advertisement[index] as usize;
        if length == 0 || index + 1 + length > advertisement.len() {
            break;
        }
        let kind = advertisement[index + 1];
        let value = &advertisement[index + 2..=index + length];
        match kind {
            0x08 | 0x09 if !value.is_empty() => {
                advertised = String::from_utf8_lossy(value).trim().to_string();
            }
            0x16 if value.len() > 2 => {
                if !advertised.is_empty() {
                    object.insert("name".into(), Json::String(advertised));
                }
                object.insert("servicedata".into(), Json::String(lower_hex(&value[2..])));
                object.insert(
                    "servicedatauuid".into(),
                    Json::String(format!("0x{}", reverse_hex(&value[..2]))),
                );
                return Some(Json::Object(object));
            }
            0x20 if value.len() > 4 => {
                if !advertised.is_empty() {
                    object.insert("name".into(), Json::String(advertised));
                }
                object.insert("servicedata".into(), Json::String(lower_hex(&value[4..])));
                object.insert(
                    "servicedatauuid".into(),
                    Json::String(format!("0x{}", reverse_hex(&value[..4]))),
                );
                return Some(Json::Object(object));
            }
            0x21 if value.len() > 16 => {
                if !advertised.is_empty() {
                    object.insert("name".into(), Json::String(advertised));
                }
                object.insert("servicedata".into(), Json::String(lower_hex(&value[16..])));
                object.insert(
                    "servicedatauuid".into(),
                    Json::String(reverse_hex(&value[..16])),
                );
                return Some(Json::Object(object));
            }
            0xff if value.len() > 2 => {
                if !advertised.is_empty() {
                    object.insert("name".into(), Json::String(advertised));
                }
                object.insert("manufacturerdata".into(), Json::String(lower_hex(value)));
                return Some(Json::Object(object));
            }
            _ => {}
        }
        index += 1 + length;
    }
    None
}

fn lower_hex(bytes: &[u8]) -> String {
    bytes
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>()
}

fn reverse_hex(bytes: &[u8]) -> String {
    bytes
        .iter()
        .rev()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>()
}

/// Decode one payload with the Theengs library.
///
/// Returns `None` when the library is not compiled in, when the payload cannot
/// be serialized, or when no decoder matches (the library answers with an empty
/// string in that case).
pub fn decode(payload: &Json) -> Option<Json> {
    if !available() {
        return None;
    }
    let text = serde_json::to_string(payload).ok()?;
    let answer = imp::decode(&text)?;
    serde_json::from_str(&answer).ok()
}

/// Convert a Theengs result into canonical measurements.
///
/// `prefix` is used by the `both` mode so the two attribute sets cannot
/// collide (`theengs_temperature` next to `temperature`).
pub fn measures(value: &Json, prefix: Option<&str>) -> Vec<Measurement> {
    let Some(object) = value.as_object() else {
        return Vec::new();
    };
    let mut out = Vec::new();
    for (key, item) in object {
        if NOT_MEASURED.contains(&key.as_str()) {
            continue;
        }
        let canonical = ALIASES
            .iter()
            .find(|(source, _)| source == key)
            .map(|(_, target)| *target)
            .unwrap_or(key.as_str());
        let name = match prefix {
            Some(prefix) => format!("{prefix}_{canonical}"),
            None => canonical.to_string(),
        };
        let unit = UNITS
            .iter()
            .find(|(source, _)| source == key)
            .map(|(_, unit)| (*unit).to_string())
            .or_else(|| default_unit(&name).map(str::to_string))
            .unwrap_or_default();
        let value = match item {
            Json::Bool(flag) => Value::Bool(*flag),
            Json::Number(number) => match number.as_i64() {
                Some(integer) if number.as_f64().is_some_and(|float| float.fract() == 0.0) => {
                    Value::Int(integer)
                }
                _ => Value::Float(number.as_f64().unwrap_or_default()),
            },
            Json::String(text) => Value::Text(text.clone()),
            _ => continue,
        };
        out.push(Measurement { name, value, unit });
    }
    out
}

/// The library answers with the input object extended by the decoded fields, so
/// the model is the only thing worth naming in a log line.
pub fn model(value: &Json) -> Option<&str> {
    value.get("model_id").and_then(Json::as_str).or_else(|| value.get("model").and_then(Json::as_str))
}

#[cfg(feature = "theengs")]
mod imp {
    use std::cell::RefCell;
    use std::ffi::{CStr, CString};
    use std::os::raw::{c_char, c_void};

    extern "C" {
        fn Theengs_NewDecoder() -> *mut c_void;
        fn Theengs_DecodeBLE(decoder: *mut c_void, json_data: *const c_char) -> *const c_char;
    }

    thread_local! {
        /// The library keeps per-instance state; one decoder per thread avoids
        /// sharing it between the serial reader and the web CGI.
        static DECODER: RefCell<Option<usize>> = const { RefCell::new(None) };
    }

    extern "C" {
        fn free(pointer: *mut c_void);
    }

    pub fn decode(json: &str) -> Option<String> {
        let request = CString::new(json).ok()?;
        DECODER.with(|cell| {
            let mut slot = cell.borrow_mut();
            let handle = match *slot {
                Some(handle) => handle,
                None => {
                    let created = unsafe { Theengs_NewDecoder() };
                    if created.is_null() {
                        return None;
                    }
                    *slot = Some(created as usize);
                    created as usize
                }
            };
            let answer = unsafe { Theengs_DecodeBLE(handle as *mut c_void, request.as_ptr()) };
            if answer.is_null() {
                return None;
            }
            // An empty string means "no decoder matched" and is a literal, not
            // an allocation: only a non-empty answer has to be released.
            let text = unsafe { CStr::from_ptr(answer) }.to_string_lossy().into_owned();
            if !text.is_empty() {
                unsafe { free(answer as *mut c_void) };
            }
            if text.is_empty() {
                None
            } else {
                Some(text)
            }
        })
    }
}

#[cfg(not(feature = "theengs"))]
mod imp {
    pub fn decode(_json: &str) -> Option<String> {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn hex(text: &str) -> Vec<u8> {
        (0..text.len())
            .step_by(2)
            .map(|index| u8::from_str_radix(&text[index..index + 2], 16).unwrap())
            .collect()
    }

    #[test]
    fn service_data_is_split_into_uuid_and_payload() {
        let advertisement = hex("0201021616F1FC04C0F93E63D135A2DF465A744042FF9E5279A5");
        let built = payload("01:17:BA:FE:80:A2", "", -74, &advertisement).unwrap();
        assert_eq!(built["servicedatauuid"], "0xfcf1");
        assert_eq!(
            built["servicedata"],
            "04c0f93e63d135a2df465a744042ff9e5279a5"
        );
        assert_eq!(built["id"], "01:17:BA:FE:80:A2");
        assert_eq!(built["rssi"], -74);
    }

    #[test]
    fn atc_service_data_and_manufacturer_data_are_understood() {
        let atc = hex("0201060D16D2FC4000EB0C3E0B10001101");
        let built = payload("A4C1383406CE", "Termometro", -60, &atc).unwrap();
        assert_eq!(built["servicedatauuid"], "0xfcd2");
        assert_eq!(built["servicedata"], "4000eb0c3e0b10001101");
        assert_eq!(built["name"], "Termometro");

        let manufacturer = hex("05FF5900AABB");
        let built = payload("A4C138B3326C", "", -70, &manufacturer).unwrap();
        assert_eq!(built["manufacturerdata"], "5900aabb");
        assert!(built.get("servicedata").is_none());
    }

    #[test]
    fn the_advertised_name_is_used_when_none_is_given() {
        let advertisement = hex("02010606095465726D6F0D16D2FC4000EB0C3E0B10001101");
        let built = payload("A4C1383406CE", "", -60, &advertisement).unwrap();
        assert_eq!(built["name"], "Termo");
        assert_eq!(built["servicedatauuid"], "0xfcd2");
    }

    #[test]
    fn advertisements_without_service_or_manufacturer_data_are_rejected() {
        assert!(payload("A4C138B3326C", "", -70, &hex("0201060B09446576696365")).is_none());
        assert!(payload("A4C138B3326C", "", -70, &[]).is_none());
        assert!(payload("A4C138B3326C", "", -70, &hex("1A00")).is_none());
    }

    #[test]
    fn decoded_values_become_canonical_measurements() {
        let decoded = serde_json::json!({
            "id": "A4:C1:38:B3:32:6C",
            "model_id": "LYWSD03MMC/MJWSD05MMC_PVVX",
            "brand": "Xiaomi",
            "tempc": 14.75,
            "tempf": 58.55,
            "hum": 65.93,
            "batt": 100,
            "volt": 2.971,
            "pres": 1015.4,
        });
        let measures = measures(&decoded, None);
        let by_name = |name: &str| measures.iter().find(|measure| measure.name == name).cloned();
        let temperature = by_name("temperature").unwrap();
        assert_eq!(temperature.unit, "°C");
        assert!(matches!(temperature.value, Value::Float(value) if (value - 14.75).abs() < 0.001));
        let battery = by_name("battery_level").unwrap();
        assert_eq!(battery.unit, "%");
        assert!(matches!(battery.value, Value::Int(100)));
        let voltage = by_name("battery_v").unwrap();
        assert_eq!(voltage.unit, "V");
        assert!(by_name("pressure").is_some());
        // The informational fields are not measurements.
        for absent in ["id", "model_id", "brand", "rssi"] {
            assert!(by_name(absent).is_none(), "{absent} must not be a measurement");
        }
        // Fahrenheit stays a separate attribute with its own unit.
        assert_eq!(by_name("tempf").unwrap().unit, "°F");
    }

    #[test]
    fn the_both_prefix_separates_the_attribute_sets() {
        let decoded = serde_json::json!({"tempc": 21.5, "hum": 40, "motion": true});
        let measures = measures(&decoded, Some("theengs"));
        let names: Vec<_> = measures.iter().map(|measure| measure.name.as_str()).collect();
        assert!(names.contains(&"theengs_temperature"));
        assert!(names.contains(&"theengs_humidity"));
        assert!(names.contains(&"theengs_motion"));
    }

    #[test]
    fn model_helpers_read_the_decoded_model() {
        let decoded = serde_json::json!({"model_id": "CGP1W", "model": "Weather Station"});
        assert_eq!(model(&decoded), Some("CGP1W"));
        assert_eq!(model(&serde_json::json!({"model": "X"})), Some("X"));
        assert_eq!(model(&serde_json::json!({})), None);
    }

    #[test]
    fn decoding_without_the_feature_is_a_no_op() {
        let payload = serde_json::json!({"servicedata": "6c32b338c1a4c305c1199b0b64a10e", "servicedatauuid": "0x181a"});
        if available() {
            assert!(decode(&payload).is_some());
        } else {
            assert!(decode(&payload).is_none());
        }
    }
}
