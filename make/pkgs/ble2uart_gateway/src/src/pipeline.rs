//! From an advertisement report to a measurement on the front-ends.
//!
//! The chain is: advertisement report -> service data -> the format of the
//! specification that matches it -> decode (with the bindkey of the device when
//! the format is encrypted) -> canonical attributes -> MySensors messages for
//! Domoticz.
//!
//! Nothing here decodes by hand: `codec::decode` walks the generated
//! specification, so a new device is supported by adding it to the
//! configuration (and a new codec by regenerating the specification).

use crate::codec::{decode::Decoder, spec::Spec, value::Value};
use crate::config::{Config, DeviceConfig};
use crate::crypto::Params;
use crate::link::AdvReport;
use std::collections::{BTreeMap, HashMap};
use std::io::{BufRead, BufReader, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

/// A canonical attribute, ready to be published.
#[derive(Clone, Debug)]
pub struct Measurement {
    /// Canonical name, e.g. `temperature`, `humidity`, `battery`, `contact`.
    pub name: String,
    pub value: Value,
    pub unit: String,
}

impl Measurement {
    fn log_text(&self) -> String {
        let mut text = format!("{}={}", crate::config::DeviceMetadata::measurement_name(&self.name), self.text());
        if !self.unit.is_empty() {
            text.push(' ');
            text.push_str(&self.unit);
        }
        text
    }

    /// The payload form the front-ends publish: `23.45`, `1`, `0`.
    pub fn text(&self) -> String {
        match &self.value {
            Value::Float(number) => format!("{number:.2}"),
            Value::Int(number) => number.to_string(),
            Value::Bool(flag) => if *flag { "1" } else { "0" }.to_string(),
            Value::Text(text) => text.clone(),
            Value::Bytes(bytes) => crate::codec::value::hex(bytes),
            Value::Null | Value::List(_) | Value::Map(_) => String::new(),
        }
    }
}

pub fn supported_attributes() -> impl Iterator<Item = &'static str> {
    MYSENSORS_ATTRIBUTES.iter().map(|(name, _, _)| *name)
}

// S_* sensor types and V_* value types of the MySensors library.
const MYSENSORS_ATTRIBUTES: &[(&str, u8, u8)] = &[
    ("temperature", 7, 0),      // S_TEMP / V_TEMP
    ("humidity", 8, 1),         // S_HUM  / V_HUM
    ("pressure", 9, 4),         // S_BARO / V_PRESSURE
    ("battery_level", 31, 3),   // S_MULTIMETER / V_PERCENTAGE
    ("battery", 31, 3),
    ("battery_v", 31, 38),      // S_MULTIMETER / V_VOLTAGE
    ("voltage", 31, 38),
    ("illuminance", 17, 23),    // S_LIGHT_LEVEL / V_LIGHT_LEVEL
    ("lux", 17, 23),
    ("contact", 0, 16),         // S_DOOR / V_TRIPPED
    ("door", 0, 16),
    ("water_leak", 33, 16),     // S_WATER_LEAK / V_TRIPPED
    ("flooding", 33, 16),
    ("motion", 1, 16),          // S_MOTION / V_TRIPPED
    ("humidity_trigger", 3, 2),
    ("temp_trigger", 3, 2),
    ("out_gpio_trg_flag", 3, 2),
    ("out_gpio_trg_value", 3, 2),
    ("input_gpio_value", 3, 2),
    ("boolean", 3, 2),
    ("switch", 3, 2),
    ("opened", 0, 16),
    ("rssi", 34, 37),           // S_SOUND / V_LEVEL
    ("one", 3, 16),             // S_BINARY / V_TRIPPED (derived states)
];
/// MySensors (sensor type, set/req type) of a canonical attribute.
fn mysensors_kind(attribute: &str) -> Option<(u8, u8)> {
    MYSENSORS_ATTRIBUTES.iter().find(|(name, _, _)| *name == attribute).map(|(_, s, v)| (*s, *v))
}

/// A device the user configured, with its allocated MySensors node and children.
pub struct Device {
    pub mac: String,
    pub label: String,
    pub metadata: crate::config::DeviceMetadata,
    pub node: u16,
    pub params: Option<Params>,
    /// Forced format, empty to detect it from the service data.
    pub forced_format: String,
    /// attribute -> child id, in configuration order (stable across restarts).
    pub children: Vec<(String, u8)>,
}

impl Device {
    pub fn child_of(&self, attribute: &str) -> Option<u8> {
        self.children.iter().find(|(name, _)| name == attribute).map(|(_, child)| *child)
    }
}

/// Devices in configuration order plus the last seen values, so a front-end that
/// connects later receives the full presentation and the current state.
pub struct Registry {
    pub devices: Vec<Device>,
    last: HashMap<(u16, u8), String>,
    /// Unknown MACs already reported, with the time, to keep the log usable.
    unknown: HashMap<String, Instant>,
}

impl Registry {
    pub fn new(config: &Config) -> Registry {
        let mut devices = Vec::new();
        for (index, device) in config.devices.iter().enumerate() {
            if !device.enabled {
                continue;
            }
            let node = config.frontends.mysensors.node_id_base + index as u16;
            devices.push(Device {
                mac: normalize_mac(&device.mac),
                label: device.metadata().name,
                metadata: device.metadata(),
                node,
                params: bindkey_of(device),
                forced_format: device.format.clone(),
                children: children_of(device),
            });
        }
        Registry { devices, last: HashMap::new(), unknown: HashMap::new() }
    }

    fn find(&self, mac: &str) -> Option<&Device> {
        self.devices.iter().find(|device| device.mac == mac)
    }

    /// Remember a published value so a new front-end connection can replay it.
    fn remember(&mut self, node: u16, child: u8, text: String) {
        self.last.insert((node, child), text);
    }

    /// Every (node, child, value) published so far.
    pub fn state(&self) -> Vec<(u16, u8, String)> {
        let mut out: Vec<(u16, u8, String)> = self
            .last
            .iter()
            .map(|((node, child), text)| (*node, *child, text.clone()))
            .collect();
        out.sort();
        out
    }
}

/// Normalise any MAC spelling to `AABBCCDDEEFF`.
pub fn normalize_mac(text: &str) -> String {
    text.chars().filter(|c| c.is_ascii_hexdigit()).take(12).collect::<String>().to_uppercase()
}

fn mysensors_text(text: &str) -> String {
    let text = text.replace([';', '\r', '\n', '\0'], " ");
    crate::config::truncate_utf8(&text, 25).to_string()
}

fn mysensors_child_name(metadata: &crate::config::DeviceMetadata, attribute: &str) -> String {
    let suffix = mysensors_text(&crate::config::DeviceMetadata::measurement_name(attribute));
    let prefix = mysensors_text(&metadata.name);
    let available = 25usize.saturating_sub(suffix.len() + 1);
    let prefix = crate::config::truncate_utf8(&prefix, available).trim_end();
    if prefix.is_empty() { suffix } else { format!("{prefix} {suffix}") }
}

/// The AES key of a device. A malformed key is refused here rather than making
/// every frame of that device fail silently later.
fn bindkey_of(device: &DeviceConfig) -> Option<Params> {
    let key: Vec<u8> = {
        let digits: String =
            device.bindkey.chars().filter(|c| c.is_ascii_hexdigit()).collect();
        (0..digits.len() / 2)
            .map(|index| {
                u8::from_str_radix(&digits[index * 2..index * 2 + 2], 16).unwrap_or(0)
            })
            .collect()
    };
    if key.len() != 16 {
        return None;
    }
    let mac = normalize_mac(&device.mac);
    let raw: Vec<u8> = (0..6)
        .map(|index| u8::from_str_radix(&mac[index * 2..index * 2 + 2], 16).unwrap_or(0))
        .collect();
    let mut mac_bytes = [0u8; 6];
    mac_bytes.copy_from_slice(&raw);
    let mut bindkey = [0u8; 16];
    bindkey.copy_from_slice(&key);
    Some(Params::new(&mac_bytes, &bindkey))
}

fn children_of(device: &DeviceConfig) -> Vec<(String, u8)> {
    let mut children = Vec::new();
    let mut next = 0u8;
    for expose in &device.expose {
        let child = expose.child.unwrap_or_else(|| {
            let value = next;
            next = next.saturating_add(1);
            value
        });
        children.push((expose.attribute.clone(), child));
    }
    children
}

/// The service data of an advertisement, with the media access address.
/// Returns the format name from the specification that matches UUID and length.
pub fn detect_format<'a>(
    report: &'a AdvReport,
    spec: &Spec,
) -> Option<(String, &'a [u8])> {
    let mut index = 0usize;
    while index < report.data.len() {
        let length = report.data[index] as usize;
        if length == 0 || index + 1 + length > report.data.len() {
            break;
        }
        let kind = report.data[index + 1];
        let payload = &report.data[index + 2..index + 1 + length];
        // 0x16: service data with a 16 bit UUID, the only shape the ATC/Xiaomi
        // formats use.
        if kind == 0x16 && payload.len() >= 2 {
            let uuid = format!("{:02X}{:02X}", payload[1], payload[0]);
            for (name, format) in &spec.formats {
                if !format.detect || format.uuid != uuid {
                    continue;
                }
                if let Some(expected) = format.length {
                    if payload.len() - 2 != expected {
                        continue;
                    }
                }
                return Some((name.clone(), payload));
            }
        }
        index += 1 + length;
    }
    None
}

/// Decode one advertisement for one device.
pub fn decode(
    spec: &Spec,
    device: &Device,
    format: &str,
    service_data: &[u8],
    report: &AdvReport,
) -> Result<Value, String> {
    let format = if device.forced_format.is_empty() {
        format.to_string()
    } else {
        device.forced_format.clone()
    };
    let uuid = [service_data[0], service_data[1]];
    let decoder = match &device.params {
        Some(params) => Decoder::with_key(spec, service_data, params, uuid),
        None => Decoder::new(spec, service_data),
    };
    let _ = report;
    decoder.decode(&format).map_err(|error| error.0)
}

/// Canonical attributes of a decoded structure.
///
/// The names come from the codec (the specification carries the real field
/// names and the units), so a device is published with the units the reference
/// reports instead of a table maintained by hand.
pub fn measurements(decoded: &Value) -> Vec<Measurement> {
    let mut out = Vec::new();
    collect(decoded, None, &mut out);
    out
}

/// Field names that are part of the frame but not measurements.
const NOT_MEASURED: &[&str] = &[
    "version", "UUID", "MAC", "mac_vendor", "counter", "device_id", "flags", "ctrl",
    "DevInfo", "data_point", "bt_home_data", "_io", "type", "bt_home_type",
    "bt_home_v2_type", "data", "battery_v_unit", "temperature_unit", "humidity_unit",
    "section_header",
];

fn collect(value: &Value, prefix: Option<&str>, out: &mut Vec<Measurement>) {
    match value {
    Value::Null => {},
        Value::Map(entries) => {
            for (name, item) in entries {
                let key = match prefix {
                    Some(prefix) => format!("{prefix}.{name}"),
                    None => name.clone(),
                };
                if matches!(item, Value::Map(_) | Value::List(_)) {
                    collect(item, Some(name), out);
                    continue;
                }
                if matches!(item, Value::Null) || NOT_MEASURED.contains(&name.as_str()) || name.ends_with("_unit") {
                    continue;
                }
                let unit = entries
                    .iter()
                    .find(|(other, _)| *other == format!("{name}_unit"))
                    .and_then(|(_, value)| value.as_text().map(str::to_string))
                    .or_else(|| default_unit(&key).map(str::to_string))
                    .unwrap_or_default();
                out.push(Measurement { name: name.clone(), value: item.clone(), unit });
            }
        }
        Value::List(items) => {
            for item in items {
                collect(item, prefix, out);
            }
        }
        Value::Bytes(bytes) => out.push(Measurement {
            name: prefix.unwrap_or("raw").to_string(),
            value: Value::Bytes(bytes.clone()),
            unit: String::new(),
        }),
        Value::Bool(flag) => out.push(Measurement {
            name: prefix.unwrap_or("state").to_string(),
            value: Value::Bool(*flag),
            unit: String::new(),
        }),
        Value::Int(number) => out.push(Measurement {
            name: prefix.unwrap_or("value").to_string(),
            value: Value::Int(*number),
            unit: default_unit(prefix.unwrap_or("")).unwrap_or("").to_string(),
        }),
        Value::Float(number) => out.push(Measurement {
            name: prefix.unwrap_or("value").to_string(),
            value: Value::Float(*number),
            unit: default_unit(prefix.unwrap_or("")).unwrap_or("").to_string(),
        }),
        Value::Text(text) => out.push(Measurement {
            name: prefix.unwrap_or("text").to_string(),
            value: Value::Text(text.clone()),
            unit: String::new(),
        }),
    }
}

/// Units for the decoded fields whose unit is not carried by the codec (the
/// generic TLV payloads of `mi_like` and `bt_home`).
fn default_unit(name: &str) -> Option<&'static str> {
    let last = name.rsplit('.').next().unwrap_or(name);
    match last {
        "temperature" | "dew_point" => Some("°C"),
        "humidity" | "battery_level" | "battery" => Some("%"),
        "battery_v" | "voltage" => Some("V"),
        "pressure" => Some("hPa"),
        "rssi" => Some("dBm"),
        "lux" | "illuminance" => Some("lx"),
        "conductivity" => Some("µS/cm"),
        "moisture" => Some("%"),
        "weight" => Some("kg"),
        "power" | "watt" => Some("W"),
        "energy" => Some("kWh"),
        _ => None,
    }
}

/// The MySensors TCP gateway Domoticz talks to.
pub struct MySensors {
    clients: Arc<Mutex<Vec<Arc<Mutex<TcpStream>>>>>,
    snapshot: Arc<Mutex<BTreeMap<String, String>>>,
}

fn replay_lines(state: &BTreeMap<String, String>) -> Vec<String> {
    let mut lines: Vec<_> = state.values().cloned().collect();
    lines.sort_by_key(|line| {
        let fields: Vec<_> = line.splitn(6, ';').collect();
        match (fields.get(1), fields.get(2), fields.get(4)) {
            (_, Some(&"3"), Some(&"14")) => 0,
            (Some(&"255"), Some(&"0"), _) => 1,
            (_, Some(&"0"), _) => 3,
            (_, Some(&"1"), _) => 4,
            (_, Some(&"3"), Some(&"0")) => 5,
            _ => 2,
        }
    });
    lines
}

fn controller_replies(line: &str, state: &BTreeMap<String, String>, uptime: u64) -> Vec<String> {
    let fields: Vec<_> = line.splitn(6, ';').collect();
    if fields.len() != 6 || fields[0].parse::<u16>().is_err() || fields[1].parse::<u8>().is_err() {
        return Vec::new();
    }
    let header = format!("{};{};3;0", fields[0], fields[1]);
    match (fields[2], fields[4]) {
        ("3", "2") => vec![format!("{header};2;2.3.2")],
        ("3", "18") => vec![format!("{header};22;{uptime}")],
        ("3", "24") => vec![format!("{header};25;{}", fields[5])],
        ("3", "19") => replay_lines(state),
        ("2", subtype) => state.get(&format!("{};{};1;0;{subtype}", fields[0], fields[1])).cloned().into_iter().collect(),
        _ => Vec::new(),
    }
}

impl MySensors {
    /// Bind and accept in the background; a front-end that is not enabled must
    /// never keep the daemon from scanning.
    pub fn start(bind: &str, port: u16) -> Result<MySensors, String> {
        let listener = TcpListener::bind((bind, port))
            .map_err(|error| format!("cannot bind {bind}:{port}: {error}"))?;
        let clients: Arc<Mutex<Vec<Arc<Mutex<TcpStream>>>>> = Arc::new(Mutex::new(Vec::new()));
        let accepted = Arc::clone(&clients);
        let snapshot: Arc<Mutex<BTreeMap<String, String>>> = Arc::new(Mutex::new(BTreeMap::new()));
        let replay = Arc::clone(&snapshot);
        let started = Instant::now();
        std::thread::spawn(move || {
            for stream in listener.incoming() {
                match stream {
                    Ok(mut stream) => {
                        log::info!("MySensors client connected");
                        let _ = stream.set_write_timeout(Some(Duration::from_secs(2)));
                        let reader = stream.try_clone();
                        let writer;
                        {
                            let state = replay.lock().unwrap();
                            for line in replay_lines(&state) {
                                if writeln!(stream, "{line}").is_err() {
                                    break;
                                }
                            }
                            writer = Arc::new(Mutex::new(stream));
                            let mut guard = accepted.lock().unwrap();
                            guard.push(Arc::clone(&writer));
                        }
                        if let Ok(reader) = reader {
                            let state = Arc::clone(&replay);
                            std::thread::spawn(move || {
                                for line in BufReader::new(reader).lines().map_while(Result::ok) {
                                    let replies = controller_replies(&line, &state.lock().unwrap(), started.elapsed().as_millis() as u64);
                                    let mut output = writer.lock().unwrap();
                                    for response in replies {
                                        if writeln!(output, "{response}").is_err() { return; }
                                    }
                                }
                                log::info!("MySensors client disconnected");
                            });
                        }
                    }
                    Err(error) => log::warn!("MySensors accept failed: {error}"),
                }
            }
        });
        Ok(MySensors { clients, snapshot })
    }

    /// Send one line to every connected controller, dropping the ones that
    /// disappeared (Domoticz restarts its gateway connection regularly).
    pub fn send(&self, line: &str) {
        let mut state = self.snapshot.lock().unwrap();
        if let Some((key, _)) = line.rsplit_once(';') {
            state.insert(key.to_string(), line.to_string());
        }
        let mut guard = self.clients.lock().unwrap();
        guard.retain_mut(|stream| {
            let mut stream = stream.lock().unwrap();
            stream.write_all(line.as_bytes()).is_ok() && stream.write_all(b"\n").is_ok()
        });
    }

    /// Presentation of every configured device and child, followed by the
    /// current values: a controller that connects later starts with the full
    /// picture instead of waiting for the next advertisement.
    pub fn present(&self, registry: &Registry) {
        self.send(&format!("0;255;3;0;14;{}",crate::profile::READY_MESSAGE));
        for device in &registry.devices {
            self.send(&format!("{};255;0;0;17;2.3.2", device.node));
            let identity = if device.metadata.model.is_empty() {
                device.metadata.name.clone()
            } else {
                format!("{} {}", device.metadata.manufacturer, device.metadata.model).trim().to_string()
            };
            self.send(&format!("{};255;3;0;11;{}", device.node, mysensors_text(&identity)));
            if !device.metadata.firmware_version.is_empty() {
                self.send(&format!("{};255;3;0;12;{}", device.node, mysensors_text(&device.metadata.firmware_version)));
            }
            for (attribute, child) in &device.children {
                if let Some((sensor, _)) = mysensors_kind(attribute) {
                    self.send(&format!(
                        "{};{};0;0;{};{}",
                        device.node, child, sensor, mysensors_child_name(&device.metadata, attribute)
                    ));
                }
            }
        }
        for (node, child, value) in registry.state() {
            if let Some(attribute) = registry.devices.iter().find(|device| device.node == node)
                .and_then(|device| device.children.iter().find(|(_, id)| *id == child))
                .and_then(|(attribute, _)| mysensors_kind(attribute)) {
                self.send(&format!("{node};{child};1;0;{};{value}", attribute.1));
            }
        }
    }
}

/// Complete decoded state, independent of a frontend's native sensor types.
pub fn merge_latest_values(previous: Option<&serde_json::Value>, current: &mut serde_json::Value) {
    let Some(measurements) = current.get("measurements").and_then(serde_json::Value::as_array) else { return; };
    let mut latest = previous.and_then(|value| value.get("latest_values")).and_then(serde_json::Value::as_object).cloned().unwrap_or_default();
    for measurement in measurements {
        if let Some(name) = measurement["name"].as_str() {
            latest.insert(name.into(), serde_json::json!({"value":measurement["value"],"unit":measurement["unit"],"received_at":current["received_at"]}));
        }
    }
    current["latest_values"] = latest.into();
}

/// Complete decoded state, independent of a frontend's native sensor types.
pub fn decoded_state(device: &Device, report: &AdvReport, format: &str, decoded: &Value) -> serde_json::Value {
    serde_json::json!({
        "schema": 1,
        "mac": device.mac,
        "label": device.label,
        "device": device.metadata,
        "wire_format": format,
        "received_at": crate::logger::timestamp(),
        "radio": {"rssi": report.rssi, "phy_raw": report.phys, "phy": report.phy_summary(),
                  "event_type": report.event_type, "addr_type": report.addr_type, "directed": report.directed},
        "decoded": decoded.to_json(),
        "measurements": measurements(decoded).into_iter().map(|measure| serde_json::json!({
            "name": measure.name, "value": measure.value.to_json(), "unit": measure.unit
        })).collect::<Vec<_>>()
    })
}

/// The running gateway: specification, devices and front-ends.
pub struct Gateway {
    pub spec: Spec,
    pub registry: Registry,
    pub mysensors: Option<MySensors>,
    pub mqtt: Option<crate::mqtt::MqttPublisher>,
    pub influx: Option<crate::influx::InfluxPublisher>,
    pub matter: Option<crate::matter::MatterPublisher>,
    /// Statistics for the log, so a silent gateway can be told apart from an
    /// empty radio.
    pub decoded: u64,
    pub skipped: u64,
}

impl Gateway {
    pub fn new(config: &Config, spec: Spec) -> Result<Gateway, String> {
        let registry = Registry::new(config);
        let mysensors = if config.frontends.mysensors.enabled {
            Some(MySensors::start(
                &config.frontends.mysensors.bind,
                config.frontends.mysensors.port,
            )?)
        } else {
            None
        };
        let mqtt = if config.frontends.mqtt.enabled {
            Some(crate::mqtt::MqttPublisher::start(&config.frontends.mqtt, config.devices.len())?)
        } else { None };
        let influx = if config.frontends.influx.enabled {
            Some(crate::influx::InfluxPublisher::start(&config.frontends.influx)?)
        } else { None };
        #[cfg(feature = "matter")]
        let matter = if config.frontends.matter.enabled {Some(crate::matter_server::start(&config.frontends.matter,&config.devices)?)} else {None};
        #[cfg(not(feature = "matter"))]
        let matter = {
            if config.frontends.matter.enabled {return Err("Matter support is not built into this binary".into());}
            None
        };
        let gateway = Gateway { spec, registry, mysensors, mqtt, influx, matter, decoded: 0, skipped: 0 };
        if let Some(frontend) = &gateway.mysensors {
            frontend.present(&gateway.registry);
        }
        log::info!(
            "gateway ready: {} devices configured{}, {} formats in the specification",
            gateway.registry.devices.len(),
            if gateway.mysensors.is_some() {
                format!(", MySensors on {}:{}", config.frontends.mysensors.bind, config.frontends.mysensors.port)
            } else {
                String::new()
            },
            gateway.spec.formats.len()
        );
        Ok(gateway)
    }

    /// One advertisement report through the whole chain.
    pub fn on_advertisement(&mut self, report: &AdvReport) {
        let mac = report.mac_string();
        let Some(device_index) = self
            .registry
            .devices
            .iter()
            .position(|device| device.mac == mac)
        else {
            crate::logger::phy(report, "decode", "unconfigured", "unknown");
            // Unknown devices are normal in a busy radio (the old portal logged
            // one warning per packet, thousands per hour): report each MAC at
            // most once every ten minutes.
            let now = Instant::now();
            let seen = self.registry.unknown.get(&mac).copied();
            if seen.map(|when| now.duration_since(when) > Duration::from_secs(600)).unwrap_or(true) {
                log::debug!("unknown device {mac} ({} bytes)", report.data.len());
                self.registry.unknown.insert(mac, now);
            }
            self.skipped += 1;
            return;
        };

        let Some((format, service_data)) = detect_format(report, &self.spec) else {
            crate::logger::phy(report, "decode", "unsupported_format", "unknown");
            log::debug!("{mac}: no known service data in {} bytes", report.data.len());
            self.skipped += 1;
            return;
        };

        let device = &self.registry.devices[device_index];
        let format = if device.forced_format.is_empty() { format } else { device.forced_format.clone() };
        if crate::logger::decode_enabled() {
            log::info!(target: "ble.decode", "mac={mac} wire_format={format} service_hex={}", crate::codec::value::hex(service_data));
        }
        let decoded = match decode(&self.spec, device, &format, service_data, report) {
            Ok(value) => value,
            Err(error) => {
                crate::logger::phy(report, "decode", "failed", &format);
                log::warn!("{mac} ({format}): {error}");
                self.skipped += 1;
                return;
            }
        };
        self.decoded += 1;
        crate::logger::phy(report, "decode", "ok", &format);

        if self.mqtt.is_some() || self.matter.is_some() || self.influx.is_some() {
            let state=decoded_state(device,report,&format,&decoded);
            if let Some(mqtt)=&self.mqtt {mqtt.publish(&mac,&state);}
            if let Some(influx)=&self.influx {influx.publish(&state);}
            if let Some(matter)=&self.matter {matter.publish(&mac,&state);}
        }

        let measures = measurements(&decoded);
        if crate::logger::decode_enabled() {
            log::info!(target: "ble.decode", "mac={mac} wire_format={format} measurements=[{}]", measures.iter().map(|measure| format!("{}={}", measure.name, measure.text())).collect::<Vec<_>>().join(","));
        }
        let mut published = Vec::new();
        for measure in &measures {
            let Some(child) = device
                .children
                .iter()
                .find(|(attribute, _)| *attribute == measure.name)
                .map(|(_, child)| *child)
            else {
                continue;
            };
            let Some((_, set)) = mysensors_kind(&measure.name) else {
                continue;
            };
            published.push((child, set, measure.text(), measure.log_text()));
        }
        let label = device.label.clone();

        if published.is_empty() {
            log::debug!(
                "{mac} ({label}, wire_format={format}): decoded attributes=[{}], none exposed",
                measures.iter().map(|measure| measure.name.as_str()).collect::<Vec<_>>().join(",")
            );
            return;
        }

        // Send first, then remember: the front-end borrow and the registry
        // update must not overlap, and the state must not be replayed twice.
        let node = self.registry.devices[device_index].node;
        let mut lines = Vec::with_capacity(published.len());
        for (child, set, text, description) in published {
            log::info!("{}", crate::logger::measurement(&mac, &label, child, &description));
            lines.push((child, format!("{node};{child};1;0;{set};{text}"), text));
        }
        if let Some(frontend) = &self.mysensors {
            for measure in measures.iter().filter(|measure| matches!(measure.name.as_str(), "battery" | "battery_level")) {
                if let Some(level) = measure.value.as_f64().filter(|level| (0.0..=100.0).contains(level)) {
                    frontend.send(&format!("{node};255;3;0;0;{level:.0}"));
                }
            }
            for (_, line, _) in &lines {
                frontend.send(line);
            }
        }
        for (child, _, text) in lines {
            self.registry.remember(node, child, text);
        }
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn measurement_logs_include_names_units_and_unchanged_payloads() {
        let temperature = super::Measurement {
            name: "temperature".into(),
            value: crate::codec::value::Value::Float(16.08),
            unit: "°C".into(),
        };
        assert_eq!(temperature.log_text(), "temperature=16.08 °C");
        assert_eq!(temperature.text(), "16.08");
        let voltage = super::Measurement {
            name: "battery_v".into(),
            value: crate::codec::value::Value::Float(3.01),
            unit: "V".into(),
        };
        assert_eq!(voltage.log_text(), "battery v=3.01 V");
        let gpio = super::Measurement {
            name: "input_gpio_value".into(),
            value: crate::codec::value::Value::Bool(true),
            unit: String::new(),
        };
        assert_eq!(gpio.log_text(), "input gpio value=1");
        assert_eq!(gpio.text(), "1");
    }

    use super::*;
    use crate::codec::spec::Spec;

    #[test]
    fn mysensors_fans_out_to_two_controllers_without_exclusivity() {
        let probe = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = probe.local_addr().unwrap().port();
        drop(probe);
        let server = MySensors::start("127.0.0.1", port).unwrap();
        let mut first = TcpStream::connect(("127.0.0.1", port)).unwrap();
        let mut second = TcpStream::connect(("127.0.0.1", port)).unwrap();
        first.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        second.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
        let mut first_reader = BufReader::new(first.try_clone().unwrap());
        let mut second_reader = BufReader::new(second.try_clone().unwrap());
        for (stream, reader) in [(&mut first, &mut first_reader), (&mut second, &mut second_reader)] {
            writeln!(stream, "0;255;3;0;24;ping").unwrap();
            let mut line = String::new();
            reader.read_line(&mut line).unwrap();
            assert_eq!(line.trim(), "0;255;3;0;25;ping");
        }
        server.send("10;0;1;0;0;21.5");
        for reader in [&mut first_reader, &mut second_reader] {
            let mut line = String::new();
            reader.read_line(&mut line).unwrap();
            assert_eq!(line.trim(), "10;0;1;0;0;21.5");
        }
        drop(first_reader);
        drop(first);
        server.send("10;0;1;0;0;22.5");
        let mut line = String::new();
        second_reader.read_line(&mut line).unwrap();
        assert_eq!(line.trim(), "10;0;1;0;0;22.5");
    }

    #[test]
    fn metadata_reaches_state_and_standard_mysensors_presentation_without_new_ids() {
        let mut config = Config::default();
        config.devices.push(serde_yaml::from_str("mac: AABBCCDDEEFF\nlabel: 'Living;room'\nmanufacturer: Xiaomi\nmodel: LYWSD03MMC\nfirmware_version: 'custom;build'\nexpose:\n - attribute: temperature\n   child: 7\n - attribute: humidity\n   child: 8\n").unwrap());
        let registry = Registry::new(&config);
        let device = &registry.devices[0];
        let server = MySensors { clients: Default::default(), snapshot: Default::default() };
        server.present(&registry);
        let snapshot = server.snapshot.lock().unwrap();
        let node = device.node;
        assert_eq!(snapshot[&format!("{node};255;3;0;11")], format!("{node};255;3;0;11;Xiaomi LYWSD03MMC"));
        assert_eq!(snapshot[&format!("{node};255;3;0;12")], format!("{node};255;3;0;12;custom build"));
        let temperature_kind = mysensors_kind("temperature").unwrap().0;
        let humidity_kind = mysensors_kind("humidity").unwrap().0;
        assert!(snapshot[&format!("{node};7;0;0;{temperature_kind}")].ends_with("Living room temperature"));
        assert!(snapshot[&format!("{node};8;0;0;{humidity_kind}")].ends_with("Living room humidity"));
        drop(snapshot);
        let advertisement = report(&device.mac, &[]);
        let state = decoded_state(device, &advertisement, "bt_home_v2", &Value::Null);
        assert_eq!(state["device"]["model"], "LYWSD03MMC");
        assert_eq!(state["device"]["manufacturer"], "Xiaomi");
        assert_eq!(state["device"]["firmware_version"], "custom;build");
        let before = (device.node, device.children.clone());
        config.devices[0].label = "Renamed".into();
        config.devices[0].model = "Updated model".into();
        let updated = Registry::new(&config);
        assert_eq!((updated.devices[0].node, updated.devices[0].children.clone()), before);
        assert_eq!(mysensors_text("ééééééééééééé").len(), 24);
        assert!(mysensors_child_name(&device.metadata, "very_long_attribute_name_that_will_not_fit").len() <= 25);
    }

    #[test]
    fn null_fields_are_not_measurements() {
        let decoded = Value::Map(vec![("data".into(), Value::Null), ("temperature".into(), Value::Int(20))]);
        let actual = measurements(&decoded);
        assert_eq!(actual.len(), 1);
        assert_eq!(actual[0].name, "temperature");
        assert!(measurements(&Value::Null).is_empty());
    }

    #[test]
    fn generic_state_preserves_unmapped_nested_values_without_expose_filters() {
        let mut config = Config::default();
        config.devices.push(serde_yaml::from_str("mac: AABBCCDDEEFF").unwrap());
        let device = Registry::new(&config).devices.remove(0);
        let decoded = Value::Map(vec![
            ("unmapped_sensor".into(), Value::Float(12.3456789)),
            ("vendor_flags".into(), Value::Map(vec![("active".into(), Value::Bool(true))])),
            ("objects".into(), Value::List(vec![Value::Int(1), Value::Null, Value::Bytes(vec![0xAB])])),
        ]);
        let report = AdvReport {rssi:-65, event_type:0, addr_type:0, directed:false, phys:0x33,
                                mac:[0xFF,0xEE,0xDD,0xCC,0xBB,0xAA], data:Vec::new()};
        let state = decoded_state(&device, &report, "vendor_extension", &decoded);
        assert_eq!(state["decoded"], decoded.to_json());
        assert_eq!(state["decoded"]["unmapped_sensor"], 12.3456789);
        assert_eq!(state["decoded"]["objects"][1], serde_json::Value::Null);
        assert!(!state["measurements"].as_array().unwrap().is_empty());
        assert!(device.children.is_empty());
        assert!(mysensors_kind("unmapped_sensor").is_none());
    }

    fn spec_for_tests() -> Spec {
        Spec::embedded().expect("the embedded specification must parse")
    }

    fn report(mac: &str, service_data: &[u8]) -> AdvReport {
        let raw: Vec<u8> = (0..6)
            .map(|index| u8::from_str_radix(&mac[index * 2..index * 2 + 2], 16).unwrap_or(0))
            .collect();
        let mut wire = [0u8; 6];
        for (index, byte) in raw.iter().rev().enumerate() {
            wire[index] = *byte;
        }
        let mut data = vec![(service_data.len() + 1) as u8, 0x16];
        data.extend_from_slice(service_data);
        AdvReport {
            rssi: -60,
            event_type: 0,
            addr_type: 0,
            directed: false,
            phys: 0x01,
            mac: wire,
            data,
        }
    }

    #[test]
    fn detects_the_format_of_a_service_data_advertisement() {
        let spec = spec_for_tests();
        let payload = [0x1Au8, 0x18, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15];
        let advertisement = report("A4C138B3326C", &payload);
        let (format, data) = detect_format(&advertisement, &spec).expect("custom format detected");
        assert_eq!(format, "custom");
        assert_eq!(data, &payload[..]);
        for (name, length) in [("custom", 15), ("custom_enc", 11), ("atc1441", 13), ("atc1441_enc", 8)] {
            let mut payload = vec![0x1A, 0x18];
            payload.resize(length + 2, 0);
            let report = report("AABBCCDDEEFF", &payload);
            assert_eq!(detect_format(&report, &spec).unwrap().0, name);
        }
    }

    #[test]
    fn general_format_recognition_agrees_with_detection_on_every_phy() {
        let spec = spec_for_tests();
        let document: serde_json::Value = serde_json::from_str(include_str!("../tests/vectors.json")).unwrap();
        let params = Params::new(&[0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF], &[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]);
        let device = Device { mac: "AABBCCDDEEFF".into(), label: "test".into(), metadata: crate::config::DeviceMetadata { name: "test".into(), ..Default::default() }, node: 1, params: Some(params.clone()), forced_format: String::new(), children: Vec::new() };
        let mut covered = std::collections::BTreeSet::new();
        let publisher=crate::matter::MatterPublisher::default();
        let mut count = 0;
        for vector in document["roundtrips"].as_array().unwrap() {
            let structure = vector["format"].as_str().unwrap();
            let Some((expected, _)) = spec.formats.iter().find(|(_, format)| format.structure == structure || format.structure == format!("{structure}_format")) else { continue };
            let encoded = vector["encoded"].as_str().unwrap();
            let payload: Vec<u8> = (0..encoded.len()).step_by(2).map(|index| u8::from_str_radix(&encoded[index..index + 2], 16).unwrap()).collect();
            let general = Decoder::with_key(&spec, &payload, &params, [payload[0], payload[1]]).decode("general_format").unwrap();
            let Value::Map(entries) = general else { panic!("general_format must return a map") };
            let recognized: Vec<_> = entries.iter().filter_map(|(name, value)| match value {
                Value::List(items) if !items.is_empty() => Some(name.as_str()),
                _ => None,
            }).collect();
            assert_eq!(recognized, vec![spec.formats[expected].structure.as_str()], "{expected}: {encoded}");
            for phy in [0x01, 0x03, 0x21, 0x31, 0x33] {
                let mut report = report("AABBCCDDEEFF", &payload);
                report.phys = phy;
                let (format, service) = detect_format(&report, &spec).unwrap_or_else(|| panic!("no format: {expected}: {encoded}"));
                assert_eq!(&format, expected);
                let decoded=decode(&spec, &device, &format, service, &report).unwrap();
                let state=decoded_state(&device,&report,&format,&decoded);
                assert_eq!(state["decoded"],decoded.to_json());
                assert_eq!(serde_json::from_slice::<serde_json::Value>(&serde_json::to_vec(&state).unwrap()).unwrap()["decoded"],decoded.to_json());
                publisher.publish(&device.mac,&state);
                assert_eq!(publisher.states.lock().unwrap()[&device.mac].value["decoded"],decoded.to_json());
            }
            covered.insert(expected.as_str());
            count += 1;
        }
        assert_eq!(covered.len(), 8);
        assert_eq!(count, 304);
    }

    #[test]
    fn canonical_measurements_carry_their_unit() {
        let mut entries = vec![
            ("temperature".to_string(), Value::Float(23.45)),
            ("temperature_unit".to_string(), Value::Text("°C".into())),
            ("humidity".to_string(), Value::Int(56)),
            ("battery_level".to_string(), Value::Int(87)),
        ];
        entries.push(("MAC".to_string(), Value::Text("A4:C1:38:B3:32:6C".into())));
        let measures = measurements(&Value::Map(entries));
        let by_name = |name: &str| measures.iter().find(|m| m.name == name);
        assert_eq!(by_name("temperature").unwrap().unit, "°C");
        assert_eq!(by_name("temperature").unwrap().text(), "23.45");
        assert_eq!(by_name("humidity").unwrap().unit, "%");
        assert!(by_name("MAC").is_none(), "the address is not a measurement");
        assert_eq!(mysensors_kind("temperature"), Some((7, 0)));
        assert_eq!(mysensors_kind("contact"), Some((0, 16)));
    }

    #[test]
    fn pvvx_gpio_flags_and_bthome_binary_objects_are_exposable() {
        let spec = spec_for_tests();
        let payload = [0x1A, 0x18, 0xFF, 0xEE, 0xDD, 0xCC, 0xBB, 0xAA, 0x34, 0x08, 0x30, 0x15, 0x54, 0x0B, 85, 1, 0x1F];
        let decoded = Decoder::new(&spec, &payload).decode("custom").unwrap();
        let measures = measurements(&decoded);
        for name in ["humidity_trigger", "temp_trigger", "out_gpio_trg_flag", "out_gpio_trg_value", "input_gpio_value"] {
            assert_eq!(measures.iter().find(|measure| measure.name == name).unwrap().text(), "1");
            assert_eq!(mysensors_kind(name), Some((3, 2)));
        }
        let payload = [0xD2, 0xFC, 0x40, 0x0F, 1, 0x11, 1];
        let decoded = Decoder::new(&spec, &payload).decode("bt_home_v2").unwrap();
        let measures = measurements(&decoded);
        assert_eq!(measures.iter().find(|measure| measure.name == "boolean").unwrap().text(), "1");
        assert_eq!(measures.iter().find(|measure| measure.name == "opened").unwrap().text(), "1");
        assert_eq!(mysensors_kind("boolean"), Some((3, 2)));
        assert_eq!(mysensors_kind("opened"), Some((0, 16)));
        let payload = [0xD2, 0xFC, 0x40, 0x00, 0xEB, 0x0C, 0x3E, 0x0B, 0x10, 0x00, 0x11, 0x01];
        let decoded = Decoder::new(&spec, &payload).decode("bt_home_v2").unwrap();
        let measures = measurements(&decoded);
        for (name, expected) in [("packet_id", "235"), ("battery_v", "2.88"), ("switch", "0"), ("opened", "1")] {
            assert_eq!(measures.iter().find(|measure| measure.name == name).unwrap().text(), expected);
        }
    }

    #[test]
    fn controller_requests_receive_version_heartbeat_and_latest_values() {
        let mut state = BTreeMap::new();
        state.insert("13;0;1;0;0".into(), "13;0;1;0;0;22.71".into());
        assert_eq!(controller_replies("0;0;3;0;2;Get Version", &state, 123), vec!["0;0;3;0;2;2.3.2"]);
        assert_eq!(controller_replies("0;0;3;0;18;PING", &state, 123), vec!["0;0;3;0;22;123"]);
        assert_eq!(controller_replies("13;0;2;0;0;", &state, 123), vec!["13;0;1;0;0;22.71"]);
        assert_eq!(controller_replies("0;0;3;0;19;", &state, 123), vec!["13;0;1;0;0;22.71"]);
        assert!(controller_replies("13;0;1;0;0;5", &state, 123).is_empty());
        assert!(controller_replies("invalid", &state, 123).is_empty());
        state.insert("13;255;3;0;0".into(), "13;255;3;0;0;85".into());
        state.insert("13;255;0;0;17".into(), "13;255;0;0;17;2.3.2".into());
        state.insert("13;0;0;0;7".into(), "13;0;0;0;7;Thermometer".into());
        assert_eq!(replay_lines(&state), vec!["13;255;0;0;17;2.3.2", "13;0;0;0;7;Thermometer", "13;0;1;0;0;22.71", "13;255;3;0;0;85"]);
    }

    #[test]
    fn node_and_child_ids_are_stable() {
        let mut config = Config::default();
        config.frontends.mysensors.node_id_base = 1;
        config.devices = vec![
            DeviceConfig {
                mac: "A4:C1:38:B3:32:6C".into(),
                label: "esterno".into(),
                bindkey: "000102030405060708090A0B0C0D0E0F".into(),
                manufacturer: String::new(),
                model: String::new(),
                firmware_version: String::new(),
                enabled: true,
                format: String::new(),
                expose: vec![
                    crate::config::ExposeConfig {
                        attribute: "temperature".into(),
                        child: None,
                        kind: None,
                    },
                    crate::config::ExposeConfig {
                        attribute: "humidity".into(),
                        child: None,
                        kind: None,
                    },
                ],
                rules: Vec::new(),
            },
            DeviceConfig {
                mac: "54:EF:44:C6:33:6B".into(),
                label: "flood".into(),
                bindkey: "000102030405060708090A0B0C0D0E0F".into(),
                manufacturer: String::new(),
                model: String::new(),
                firmware_version: String::new(),
                enabled: true,
                format: String::new(),
                expose: Vec::new(),
                rules: Vec::new(),
            },
        ];
        let registry = Registry::new(&config);
        assert_eq!(registry.devices[0].node, 1);
        assert_eq!(registry.devices[1].node, 2);
        assert_eq!(registry.devices[0].child_of("temperature"), Some(0));
        assert_eq!(registry.devices[0].child_of("humidity"), Some(1));
        assert!(registry.devices[0].params.is_some(), "the bindkey is parsed");
        assert!(registry.devices[1].params.is_some());
    }
}
