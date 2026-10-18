//! Configuration: one structured YAML file owned by the daemon.
//!
//! The daemon is the only writer: the web interface asks it for changes with
//! `--set KEY=VALUE` / `--check` / `--dump`, so the schema is validated in one
//! place and the file is always written atomically (temporary file + rename)
//! after a timestamped backup. The bind keys are secrets: the file lives in the
//! store directory with mode 0600.

use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::Write;
use std::path::{Path, PathBuf};

pub const CONFIG_VERSION: u32 = 1;

fn default_version() -> u32 {
    CONFIG_VERSION
}
fn default_serial() -> String {
    "/dev/ttyACM0".into()
}
fn default_baudrate() -> u32 {
    115200
}
fn default_command_timeout() -> u64 {
    2000
}
fn default_reconnect_delay() -> u64 {
    3000
}
fn default_true() -> bool {
    true
}
fn default_window_1m() -> u16 {
    320 // 200 ms (1 unit = 0.625 ms)
}
fn default_window_coded() -> u16 {
    64
}
fn default_node_base() -> u16 {
    10
}
fn default_mysensors_port() -> u16 {
    5003
}
fn default_mqtt_port() -> u16 {
    1883
}
fn default_matter_port() -> u16 {
    5541
}
fn default_matter_bind() -> String {
    "::".into()
}
fn default_base_topic() -> String {
    crate::profile::default_name()
}
fn default_discovery_prefix() -> String {
    "homeassistant".into()
}
fn default_frontend_bind() -> String {
    "127.0.0.1".into()
}

/// Serial link parameters (the firmware ignores the baud rate: it uses the
/// ESP32-C3 native USB Serial/JTAG, but a serial stack needs a baud rate to
/// open the port, hence it is kept in the configuration).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SerialConfig {
    #[serde(default = "default_serial")]
    pub port: String,
    #[serde(default = "default_baudrate")]
    pub baudrate: u32,
    #[serde(default = "default_command_timeout")]
    pub command_timeout_ms: u64,
    #[serde(default = "default_reconnect_delay")]
    pub reconnect_delay_ms: u64,
    /// Pulse DTR/RTS on open: the ESP32-C3 Super Mini resets when the host does
    /// it. Off by default, so a running module is not disturbed.
    #[serde(default)]
    pub reset_on_open: bool,
}

impl Default for SerialConfig {
    fn default() -> Self {
        SerialConfig {
            port: default_serial(),
            baudrate: default_baudrate(),
            command_timeout_ms: default_command_timeout(),
            reconnect_delay_ms: default_reconnect_delay(),
            reset_on_open: false,
        }
    }
}

/// Scanner parameters, mapped one to one to the firmware SCAN command.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScannerConfig {
    #[serde(default = "default_true")]
    pub filter_known_devices: bool,
    #[serde(default = "default_true")]
    pub phy_1m: bool,
    #[serde(default = "default_true")]
    pub phy_coded: bool,
    #[serde(default = "default_window_1m")]
    pub window_1m: u16,
    #[serde(default = "default_window_coded")]
    pub window_coded: u16,
    #[serde(default)]
    pub active_scan: bool,
    #[serde(default = "default_true")]
    pub dup_filter: bool,
    #[serde(default)]
    pub discard_random: bool,
    #[serde(default)]
    pub discard_rpa: bool,
    /// MAC or MAC-prefix filters, synchronised with the firmware WMAC/BMAC
    /// commands (64 entries per list, the firmware does not allow both at once).
    #[serde(default)]
    pub whitelist: Vec<String>,
    #[serde(default)]
    pub blacklist: Vec<String>,
}

impl Default for ScannerConfig {
    fn default() -> Self {
        ScannerConfig {
            filter_known_devices: true,
            phy_1m: true,
            phy_coded: true,
            window_1m: default_window_1m(),
            window_coded: default_window_coded(),
            active_scan: false,
            dup_filter: true,
            discard_random: false,
            discard_rpa: false,
            whitelist: Vec::new(),
            blacklist: Vec::new(),
        }
    }
}

/// A device the user cares about. `bindkey` is the AES-128 key of the
/// encrypted formats and is never written to logs or to the web interface in
/// clear.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceConfig {
    pub mac: String,
    #[serde(default)]
    pub manufacturer: String,
    #[serde(default)]
    pub model: String,
    #[serde(default)]
    pub firmware_version: String,
    #[serde(default)]
    pub label: String,
    #[serde(default)]
    pub bindkey: String,
    #[serde(default = "default_true")]
    pub enabled: bool,
    /// Force a codec format when the advertisement UUID is ambiguous, e.g.
    /// "atc1441_enc" or "bt_home_v2". Empty: detect from the service data.
    #[serde(default)]
    pub format: String,
    /// Which canonical attributes to expose, and optionally the fixed
    /// (node, child) pair of the MySensors front-end. Attributes that are not
    /// listed are decoded but only kept in memory for rules.
    #[serde(default)]
    pub expose: Vec<ExposeConfig>,
    /// Per-device derived states (door left open, stale values, ...).
    #[serde(default)]
    pub rules: Vec<RuleConfig>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(default)]
pub struct DeviceMetadata {
    pub name: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub manufacturer: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub model: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub firmware_version: String,
}

impl DeviceMetadata {
    pub fn measurement_name(attribute: &str) -> String {
        attribute.replace('_', " ")
    }

    pub fn resource_name(&self, attribute: &str) -> String {
        format!("{} {}", self.name, Self::measurement_name(attribute))
    }
}

pub fn truncate_utf8(text: &str, limit: usize) -> &str {
    let mut end = text.len().min(limit);
    while !text.is_char_boundary(end) {
        end -= 1;
    }
    &text[..end]
}

impl DeviceConfig {
    pub fn metadata(&self) -> DeviceMetadata {
        let name = if !self.label.trim().is_empty() {
            self.label.trim().to_string()
        } else if !self.model.trim().is_empty() {
            self.model.trim().to_string()
        } else {
            self.mac.chars().filter(|character| character.is_ascii_hexdigit()).collect::<String>().to_uppercase()
        };
        DeviceMetadata {
            name,
            manufacturer: self.manufacturer.trim().to_string(),
            model: self.model.trim().to_string(),
            firmware_version: self.firmware_version.trim().to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExposeConfig {
    /// Canonical attribute name, e.g. "temperature", "humidity", "battery".
    pub attribute: String,
    /// MySensors child id (0..=255). Fixed when given, allocated and persisted
    /// otherwise, so Domoticz devices never move.
    #[serde(default)]
    pub child: Option<u8>,
    #[serde(default)]
    pub kind: Option<String>,
}

/// A derived state: a timer or a condition evaluated on the decoded values.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RuleConfig {
    /// Name of the derived attribute, e.g. "door_timeout".
    pub name: String,
    #[serde(default)]
    pub label: String,
    /// Attribute the rule watches.
    pub source: String,
    /// Value of `source` that starts the rule (empty: any change).
    #[serde(default)]
    pub equals: String,
    /// Seconds to wait before the derived attribute becomes true.
    #[serde(default)]
    pub after_s: u64,
    /// When true the derived attribute mirrors `source == equals` (no timer).
    #[serde(default)]
    pub mirror: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MySensorsConfig {
    #[serde(default)]
    pub enabled: bool,
    #[serde(default = "default_frontend_bind")]
    pub bind: String,
    #[serde(default = "default_mysensors_port")]
    pub port: u16,
    /// First node id used for the BLE devices; each device gets one node.
    #[serde(default = "default_node_base")]
    pub node_id_base: u16,
}

impl Default for MySensorsConfig {
    fn default() -> Self {
        MySensorsConfig {
            enabled: false,
            bind: default_frontend_bind(),
            port: default_mysensors_port(),
            node_id_base: default_node_base(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MqttConfig {
    #[serde(default)]
    pub local_broker: bool,
    #[serde(default)]
    pub domoticz_discovery: bool,
    #[serde(default = "default_discovery_prefix")]
    pub discovery_prefix: String,
    #[serde(default = "default_base_topic")]
    pub client_id: String,
    #[serde(default)]
    pub enabled: bool,
    #[serde(default = "default_frontend_bind")]
    pub host: String,
    #[serde(default = "default_mqtt_port")]
    pub port: u16,
    #[serde(default = "default_base_topic")]
    pub base_topic: String,
    #[serde(default)]
    pub username: String,
    #[serde(default)]
    pub password: String,
    #[serde(default = "default_true")]
    pub retain: bool,
}

impl Default for MqttConfig {
    fn default() -> Self {
        MqttConfig {
            local_broker: false,
            domoticz_discovery: false,
            discovery_prefix: default_discovery_prefix(),
            client_id: default_base_topic(),
            enabled: false,
            host: default_frontend_bind(),
            port: default_mqtt_port(),
            base_topic: default_base_topic(),
            username: String::new(),
            password: String::new(),
            retain: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MatterConfig {
    #[serde(default)]
    pub domoticz_port: u16,
    #[serde(default = "default_matter_bind")]
    pub bind: String,
    #[serde(default = "default_true")]
    pub advertise: bool,
    #[serde(default)]
    pub mdns_interface: String,
    /// DNS-SD publisher: auto, builtin, avahi, resolved, zeroconf, astro or
    /// disabled. Backends other than builtin must be compiled in.
    #[serde(default)]
    pub mdns_backend: MdnsBackend,
    /// Host name announced by the builtin responder (empty = build default).
    #[serde(default)]
    pub mdns_hostname: String,
    #[serde(default)]
    pub enabled: bool,
    #[serde(default = "default_matter_port")]
    pub port: u16,
    /// Directory of the Matter fabric/state (never the bind keys).
    #[serde(default)]
    pub store: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum MdnsBackend {
    /// First available system daemon compiled in, otherwise builtin.
    #[default]
    Auto,
    Builtin,
    Avahi,
    Resolved,
    Zeroconf,
    Astro,
    Disabled,
}

impl MdnsBackend {
    pub const ALL: [MdnsBackend; 7] = [
        MdnsBackend::Auto,
        MdnsBackend::Builtin,
        MdnsBackend::Avahi,
        MdnsBackend::Resolved,
        MdnsBackend::Zeroconf,
        MdnsBackend::Astro,
        MdnsBackend::Disabled,
    ];

    pub fn name(self) -> &'static str {
        match self {
            MdnsBackend::Auto => "auto",
            MdnsBackend::Builtin => "builtin",
            MdnsBackend::Avahi => "avahi",
            MdnsBackend::Resolved => "resolved",
            MdnsBackend::Zeroconf => "zeroconf",
            MdnsBackend::Astro => "astro",
            MdnsBackend::Disabled => "disabled",
        }
    }

    pub fn compiled(self) -> bool {
        match self {
            MdnsBackend::Auto | MdnsBackend::Builtin | MdnsBackend::Disabled => true,
            MdnsBackend::Avahi => cfg!(feature = "mdns-avahi"),
            MdnsBackend::Resolved => cfg!(feature = "mdns-resolved"),
            MdnsBackend::Zeroconf => cfg!(feature = "mdns-zeroconf"),
            MdnsBackend::Astro => cfg!(feature = "mdns-astro"),
        }
    }

    pub fn available() -> Vec<&'static str> {
        Self::ALL.into_iter().filter(|backend| backend.compiled()).map(Self::name).collect()
    }
}

impl MatterConfig {
    /// Effective backend: `advertise: false` (legacy switch) disables DNS-SD.
    pub fn effective_mdns_backend(&self) -> MdnsBackend {
        if self.advertise { self.mdns_backend } else { MdnsBackend::Disabled }
    }

    pub fn effective_mdns_hostname(&self) -> String {
        if self.mdns_hostname.is_empty() { crate::profile::default_name() } else { self.mdns_hostname.clone() }
    }

    pub fn validate_mdns(&self) -> Result<(), String> {
        let backend = self.mdns_backend;
        if !backend.compiled() {
            return Err(format!(
                "frontends.matter.mdns_backend '{}' is not compiled in (rebuild with Cargo feature mdns-{}); available: {}",
                backend.name(), backend.name(), MdnsBackend::available().join(", ")
            ));
        }
        let host = &self.mdns_hostname;
        if !host.is_empty()
            && (host.len() > 63
                || host.starts_with('-')
                || host.ends_with('-')
                || !host.bytes().all(|byte| byte.is_ascii_alphanumeric() || byte == b'-'))
        {
            return Err("frontends.matter.mdns_hostname must be a single DNS label (letters, digits, '-', at most 63 characters, no '.local')".into());
        }
        if self.mdns_interface.len() >= 16 || self.mdns_interface.contains(['/', '\0']) || self.mdns_interface.chars().any(char::is_whitespace) {
            return Err("frontends.matter.mdns_interface must be a network interface name".into());
        }
        Ok(())
    }
}

impl Default for MatterConfig {
    fn default() -> Self {
        MatterConfig {
            domoticz_port: 0,
            bind: default_matter_bind(),
            advertise: true,
            mdns_interface: String::new(),
            mdns_backend: MdnsBackend::Auto,
            mdns_hostname: String::new(),
            enabled: false,
            port: default_matter_port(),
            store: String::new(),
        }
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Frontends {
    #[serde(default)]
    pub influx: crate::influx::InfluxConfig,
    #[serde(default)]
    pub mysensors: MySensorsConfig,
    #[serde(default)]
    pub mqtt: MqttConfig,
    #[serde(default)]
    pub matter: MatterConfig,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DiagnosticsConfig {
    #[serde(default)]
    pub tx_hex: bool,
    #[serde(default)]
    pub rx_hex: bool,
    #[serde(default)]
    pub decode: bool,
    #[serde(default)]
    pub phy: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default = "default_version")]
    pub version: u32,
    #[serde(default)]
    pub serial: SerialConfig,
    #[serde(default)]
    pub scanner: ScannerConfig,
    #[serde(default)]
    pub devices: Vec<DeviceConfig>,
    #[serde(default)]
    pub rules: Vec<RuleConfig>,
    #[serde(default)]
    pub frontends: Frontends,
    #[serde(default)]
    pub log_level: String,
    #[serde(default)]
    pub diagnostics: DiagnosticsConfig,
}

impl Default for Config {
    /// The configuration written on first start: MySensors enabled on loopback
    /// (the Domoticz path), the rest off.
    fn default() -> Self {
        Config {
            version: CONFIG_VERSION,
            serial: SerialConfig::default(),
            scanner: ScannerConfig::default(),
            devices: Vec::new(),
            rules: Vec::new(),
            frontends: Frontends {
                influx: crate::influx::InfluxConfig::default(),
                mysensors: MySensorsConfig {
                    enabled: true,
                    ..MySensorsConfig::default()
                },
                mqtt: MqttConfig::default(),
                matter: MatterConfig::default(),
            },
            log_level: "info".into(),
            diagnostics: DiagnosticsConfig::default(),
        }
    }
}

impl Config {
    pub fn mac_filters(&self) -> Result<(bool, Vec<Vec<u8>>), String> {
        let whitelist = self.scanner.whitelist.iter().map(|value| parse_mac_prefix(value)).collect::<Result<Vec<_>, _>>()?;
        let blacklist = self.scanner.blacklist.iter().map(|value| parse_mac_prefix(value)).collect::<Result<Vec<_>, _>>()?;
        let (white, addresses) = if self.scanner.filter_known_devices {
            let mut addresses = Vec::new();
            for device in self.devices.iter().filter(|device| device.enabled) {
                let mac = parse_mac(&device.mac)?;
                if (whitelist.is_empty() || whitelist.iter().any(|prefix| mac.starts_with(prefix)))
                    && !blacklist.iter().any(|prefix| mac.starts_with(prefix)) {
                    addresses.push(mac.to_vec());
                }
            }
            (true, addresses)
        } else if !blacklist.is_empty() {
            (false, blacklist)
        } else {
            (true, whitelist)
        };
        if addresses.len() > 64 {
            return Err("the effective firmware MAC filter exceeds 64 entries".into());
        }
        Ok((white, addresses))
    }

    /// Load and validate. `port_override` comes from the command line
    /// (`--serial`), so the init script keeps working when the web interface
    /// configuration is broken.
    pub fn load(path: &Path, port_override: Option<&str>, baud_override: Option<u32>) -> Result<Config, String> {
        let text = std::fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
        let mut config: Config = serde_yaml::from_str(&text).map_err(|e| format!("{}: {e}", path.display()))?;
        if let Some(port) = port_override {
            if !port.is_empty() {
                config.serial.port = port.to_string();
            }
        }
        if let Some(baud) = baud_override {
            config.serial.baudrate = baud;
        }
        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> Result<(), String> {
        crate::logger::parse_level(&self.log_level)?;
        if self.version != CONFIG_VERSION {
            return Err(format!(
                "unsupported configuration version {} (this build understands {CONFIG_VERSION})",
                self.version
            ));
        }
        if self.serial.baudrate == 0 {
            return Err("serial.baudrate must not be zero".into());
        }
        if !self.serial.port.is_empty() && !self.serial.port.starts_with("/dev/") {
            return Err("serial.port must be an absolute path below /dev or empty".into());
        }
        if self.scanner.whitelist.len() > 64 || self.scanner.blacklist.len() > 64 {
            return Err("the firmware holds at most 64 entries per MAC list".into());
        }
        if !self.scanner.whitelist.is_empty() && !self.scanner.blacklist.is_empty() {
            return Err(
                "whitelist and blacklist are mutually exclusive in the firmware: fill only one".into(),
            );
        }
        for filter in self.scanner.whitelist.iter().chain(self.scanner.blacklist.iter()) {
            parse_mac_prefix(filter)?;
        }
        let mut seen = std::collections::HashSet::new();
        for device in &self.devices {
            let mac = parse_mac(&device.mac)?;
            if !seen.insert(mac) {
                return Err(format!("device {} is listed twice", device.mac));
            }
            if !device.bindkey.is_empty() {
                parse_key(&device.bindkey)?;
            }
            for expose in &device.expose {
                if expose.attribute.trim().is_empty() {
                    return Err(format!("device {mac:02X?}: expose.attribute must not be empty"));
                }
            }
        }
        self.mac_filters()?;
        if self.frontends.influx.enabled { self.frontends.influx.validate()?; }
        if self.frontends.matter.enabled { self.frontends.matter.validate_mdns()?; }
        for rule in self.rules.iter().chain(self.devices.iter().flat_map(|d| d.rules.iter())) {
            if rule.name.trim().is_empty() || rule.source.trim().is_empty() {
                return Err("every rule needs a name and a source attribute".into());
            }
            if !rule.mirror && rule.after_s == 0 {
                return Err(format!("rule {}: after_s must be > 0 unless mirror is set", rule.name));
            }
        }
        if self.frontends.mqtt.enabled && self.frontends.mqtt.base_topic.trim().is_empty() {
            return Err("frontends.mqtt.base_topic must not be empty".into());
        }
        if self.frontends.mqtt.enabled && (self.frontends.mqtt.client_id.is_empty() || self.frontends.mqtt.client_id.contains('\0') || self.frontends.mqtt.host.trim().is_empty() || self.frontends.mqtt.port == 0 || self.frontends.mqtt.base_topic.contains(['+', '#', '\0'])) {
            return Err("MQTT requires a client_id, host, nonzero port and a base_topic without wildcards or NUL".into());
        }
        if self.frontends.mqtt.enabled && !self.frontends.mqtt.password.is_empty() && self.frontends.mqtt.username.is_empty() {
            return Err("MQTT password requires a username".into());
        }
        if self.frontends.mqtt.enabled && self.frontends.mqtt.domoticz_discovery && (self.frontends.mqtt.discovery_prefix.trim_matches('/').is_empty() || self.frontends.mqtt.discovery_prefix.contains(['+', '#', '\0'])) {
            return Err("MQTT discovery_prefix must be nonempty and contain no wildcards or NUL".into());
        }
        if self.frontends.mqtt.enabled && self.frontends.mqtt.local_broker && (self.frontends.mqtt.host!="127.0.0.1" || !self.frontends.mqtt.username.is_empty() || !self.frontends.mqtt.password.is_empty()) {
            return Err("managed MQTT broker requires host 127.0.0.1 and empty credentials; authenticated/external brokers must use local_broker=false".into());
        }
        if self.frontends.mysensors.enabled && self.frontends.mysensors.node_id_base == 0 {
            return Err("frontends.mysensors.node_id_base must not be zero".into());
        }
        if self.frontends.matter.enabled && (self.frontends.matter.port == 0 || self.frontends.matter.bind.parse::<std::net::IpAddr>().is_err() || !Path::new(&self.frontends.matter.store).is_absolute() || Path::new(&self.frontends.matter.store).parent().is_none()) {
            return Err("Matter requires a bind IP, nonzero port and an absolute persistent store".into());
        }
        let children: usize = self.devices.iter().map(|d| d.expose.len()).sum();
        if children > 200 {
            return Err("at most 200 exposed attributes are supported".into());
        }
        Ok(())
    }

    /// Atomic write with a timestamped backup: the web interface and the CLI
    /// both go through here, so a truncated file can never happen.
    pub fn save(&self, path: &Path) -> Result<(), String> {
        self.validate()?;
        let dir = path.parent().ok_or("configuration path has no directory")?;
        std::fs::create_dir_all(dir).map_err(|e| format!("{}: {e}", dir.display()))?;
        if path.exists() {
            let stamp = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_secs())
                .unwrap_or(0);
            let backup = PathBuf::from(format!("{}.{}", path.display(), stamp));
            let _ = std::fs::copy(path, &backup);
        }
        let text = serde_yaml::to_string(self).map_err(|e| e.to_string())?;
        let tmp = PathBuf::from(format!("{}.tmp", path.display()));
        {
            let mut file = File::create(&tmp).map_err(|e| format!("{}: {e}", tmp.display()))?;
            file.write_all(text.as_bytes())
                .map_err(|e| format!("{}: {e}", tmp.display()))?;
            file.sync_all().ok();
        }
        std::fs::rename(&tmp, path).map_err(|e| format!("{}: {e}", path.display()))?;
        let _ = set_mode(path, 0o600);
        Ok(())
    }

    /// `--get key` / `--set key=value` support for the CGI, so that the shell
    /// never parses YAML. Keys are dotted paths, e.g.
    /// `serial.port`, `frontends.mysensors.enabled`, `devices.0.label`.
    pub fn get(&self, key: &str) -> Result<String, String> {
        let value = serde_yaml::to_value(self).map_err(|e| e.to_string())?;
        let mut node = &value;
        for part in key.split('.') {
            node = match node {
                serde_yaml::Value::Mapping(map) => map
                    .get(&serde_yaml::Value::String(part.to_string()))
                    .ok_or_else(|| format!("unknown key {key}"))?,
                serde_yaml::Value::Sequence(seq) => {
                    let index: usize = part.parse().map_err(|_| format!("unknown key {key}"))?;
                    seq.get(index).ok_or_else(|| format!("unknown key {key}"))?
                }
                _ => return Err(format!("key {key} is not a container")),
            };
        }
        Ok(match node {
            serde_yaml::Value::String(text) => text.clone(),
            serde_yaml::Value::Bool(flag) => if *flag { "yes" } else { "no" }.to_string(),
            serde_yaml::Value::Null => String::new(),
            other => serde_yaml::to_string(other)
                .unwrap_or_default()
                .trim()
                .to_string(),
        })
    }

    pub fn set(&mut self, key: &str, value: &str) -> Result<(), String> {
        let mut doc = serde_yaml::to_value(&*self).map_err(|e| e.to_string())?;
        let parts: Vec<&str> = key.split('.').collect();
        if parts.is_empty() {
            return Err("empty key".into());
        }
        set_in(&mut doc, &parts, value)?;
        *self = serde_yaml::from_value(doc).map_err(|e| format!("{key}: {e}"))?;
        self.validate()
    }
}

fn set_in(node: &mut serde_yaml::Value, parts: &[&str], value: &str) -> Result<(), String> {
    if let serde_yaml::Value::Sequence(sequence) = node {
        let index: usize = parts[0].parse().map_err(|_| format!("invalid list index {}", parts[0]))?;
        let child = sequence.get_mut(index).ok_or_else(|| format!("list index {index} out of range"))?;
        if parts.len() == 1 {
            *child = serde_yaml::from_str(value).map_err(|error| error.to_string())?;
            return Ok(());
        }
        return set_in(child, &parts[1..], value);
    }
    if parts.len() == 1 {
        let key = parts[0];
        let mapping = node
            .as_mapping_mut()
            .ok_or_else(|| format!("{key}: not a mapping"))?;
        let yaml_key = serde_yaml::Value::String(key.to_string());
        let current = mapping.get(&yaml_key).cloned();
        let new = match current {
            Some(serde_yaml::Value::Bool(_)) => serde_yaml::Value::Bool(matches!(
                value.to_ascii_lowercase().as_str(),
                "yes" | "true" | "1" | "on" | "enabled"
            )),
            Some(serde_yaml::Value::Number(number)) => {
                if number.is_i64() || number.is_u64() {
                    let parsed: i64 = value
                        .trim()
                        .parse()
                        .map_err(|_| format!("{key}: expected an integer"))?;
                    serde_yaml::Value::Number(parsed.into())
                } else {
                    let parsed: f64 = value
                        .trim()
                        .parse()
                        .map_err(|_| format!("{key}: expected a number"))?;
                    serde_yaml::Value::Number(parsed.into())
                }
            }
            Some(serde_yaml::Value::Sequence(_)) => serde_yaml::from_str(value).map_err(|error| format!("{key}: {error}"))?,
            _ => serde_yaml::Value::String(value.to_string()),
        };
        mapping.insert(yaml_key, new);
        return Ok(());
    }
    let mapping = node.as_mapping_mut().ok_or("not a mapping")?;
    let key = serde_yaml::Value::String(parts[0].to_string());
    if !mapping.contains_key(&key) {
        return Err(format!("unknown key {}", parts[0]));
    }
    let child = mapping.get_mut(&key).unwrap();
    set_in(child, &parts[1..], value)
}

#[cfg(unix)]
pub fn set_mode(path: &Path, mode: u32) -> std::io::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    std::fs::set_permissions(path, std::fs::Permissions::from_mode(mode))
}

#[cfg(not(unix))]
pub fn set_mode(_path: &Path, _mode: u32) -> std::io::Result<()> {
    Ok(())
}

/// Parse "AABBCCDDEEFF", "AA:BB:CC:DD:EE:FF" or a shorter prefix.
pub fn parse_mac_prefix(text: &str) -> Result<Vec<u8>, String> {
    let cleaned: String = text
        .chars()
        .filter(|c| c.is_ascii_hexdigit())
        .collect::<String>()
        .to_ascii_uppercase();
    if cleaned.len() % 2 != 0 || cleaned.is_empty() || cleaned.len() > 12 {
        return Err(format!("{text}: expected 1 to 6 bytes of hexadecimal MAC"));
    }
    let mut bytes = Vec::with_capacity(6);
    for index in (0..cleaned.len()).step_by(2) {
        bytes.push(
            u8::from_str_radix(&cleaned[index..index + 2], 16)
                .map_err(|_| format!("{text}: not hexadecimal"))?,
        );
    }
    Ok(bytes)
}

/// A full 6-byte MAC address, normalised to the wire order (little endian).
pub fn parse_mac(text: &str) -> Result<[u8; 6], String> {
    let bytes = parse_mac_prefix(text)?;
    if bytes.len() != 6 {
        return Err(format!("{text}: expected a full 6-byte MAC address"));
    }
    let mut mac = [0u8; 6];
    mac.copy_from_slice(&bytes);
    Ok(mac)
}

/// Normalise a MAC to the "AABBCCDDEEFF" form used in the configuration.
pub fn mac_string(mac: &[u8]) -> String {
    mac.iter().map(|b| format!("{b:02X}")).collect()
}

/// A 16-byte AES key ("bindkey") given as 32 hexadecimal characters.
pub fn parse_key(text: &str) -> Result<[u8; 16], String> {
    let cleaned: String = text.chars().filter(|c| c.is_ascii_hexdigit()).collect();
    if cleaned.len() != 32 {
        return Err("a bind key must contain 32 hexadecimal characters".into());
    }
    let mut key = [0u8; 16];
    for index in 0..16 {
        key[index] = u8::from_str_radix(&cleaned[index * 2..index * 2 + 2], 16)
            .map_err(|_| "a bind key must be hexadecimal".to_string())?;
    }
    Ok(key)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn matter_mdns_backend_options_are_validated_and_backward_compatible() {
        let legacy: MatterConfig = serde_yaml::from_str("enabled: true\nadvertise: true\n").unwrap();
        assert_eq!(legacy.mdns_backend, MdnsBackend::Auto);
        assert_eq!(legacy.effective_mdns_hostname(), crate::profile::default_name());
        let off: MatterConfig = serde_yaml::from_str("advertise: false\nmdns_backend: builtin\n").unwrap();
        assert_eq!(off.effective_mdns_backend(), MdnsBackend::Disabled);
        for backend in MdnsBackend::ALL {
            let config: MatterConfig = serde_yaml::from_str(&format!("mdns_backend: {}\n", backend.name())).unwrap();
            assert_eq!(config.validate_mdns().is_ok(), backend.compiled(), "{}", backend.name());
        }
        assert!(serde_yaml::from_str::<MatterConfig>("mdns_backend: bonjour\n").is_err());
        let named: MatterConfig = serde_yaml::from_str("mdns_hostname: ble-lab-2\nmdns_interface: eth0\n").unwrap();
        assert!(named.validate_mdns().is_ok());
        assert_eq!(named.effective_mdns_hostname(), "ble-lab-2");
        for invalid in ["mdns_hostname: gw.local", "mdns_hostname: -gw", "mdns_hostname: 'g w'", "mdns_interface: 'eth0 lan'"] {
            assert!(serde_yaml::from_str::<MatterConfig>(invalid).unwrap().validate_mdns().is_err(), "{invalid}");
        }
    }

    #[test]
    fn metadata_is_optional_and_independent_of_ble_format() {
        let mut device: DeviceConfig = serde_yaml::from_str("mac: 'AA:BB:CC:DD:EE:FF'\nformat: bt_home_v2\n").unwrap();
        assert_eq!(serde_json::to_value(device.metadata()).unwrap(), serde_json::json!({"name":"AABBCCDDEEFF"}));
        device.manufacturer = " Xiaomi ".into();
        device.model = "LYWSD03MMC".into();
        device.firmware_version = "PVVX custom build".into();
        assert_eq!(device.metadata().name, "LYWSD03MMC");
        device.label = "Living room".into();
        let metadata = device.metadata();
        assert_eq!(metadata.name, "Living room");
        assert_eq!(metadata.manufacturer, "Xiaomi");
        assert_eq!(metadata.model, "LYWSD03MMC");
        assert_eq!(metadata.firmware_version, "PVVX custom build");
        assert_eq!(device.format, "bt_home_v2");
        let roundtrip: DeviceConfig = serde_yaml::from_str(&serde_yaml::to_string(&device).unwrap()).unwrap();
        assert_eq!(roundtrip.metadata(), metadata);
        assert!(!serde_json::to_value(metadata).unwrap().to_string().contains("bindkey"));
    }

    #[test]
    fn mac_and_key_parsing() {
        assert_eq!(parse_mac("aa:bb:cc:dd:ee:ff").unwrap(), [0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF]);
        assert_eq!(parse_mac_prefix("30F94B").unwrap(), vec![0x30, 0xF9, 0x4B]);
        assert!(parse_mac("AABBCC").is_err());
        let key = parse_key("9EF35BFD252659747191ED20F9B2B07D").unwrap();
        assert_eq!(key[0], 0x9E);
        assert_eq!(key[15], 0x7D);
        assert!(parse_key("nope").is_err());
    }

    #[test]
    fn defaults_validate() {
        Config::default().validate().unwrap();
        assert!(Config::default().scanner.filter_known_devices);
    }

    #[test]
    fn dotted_get_set_roundtrip() {
        let mut config = Config::default();
        assert_eq!(config.get("frontends.mysensors.enabled").unwrap(), "yes");
        config.set("frontends.mysensors.enabled", "no").unwrap();
        assert_eq!(config.get("frontends.mysensors.enabled").unwrap(), "no");
        config.set("serial.port", "/dev/ttyACM1").unwrap();
        assert_eq!(config.get("serial.port").unwrap(), "/dev/ttyACM1");
        config.set("frontends.mysensors.port", "5004").unwrap();
        assert_eq!(config.get("frontends.mysensors.port").unwrap(), "5004");
        assert!(config.set("does.not.exist", "x").is_err());
        config.set("diagnostics.tx_hex", "true").unwrap();
        config.set("diagnostics.rx_hex", "true").unwrap();
        config.set("diagnostics.decode", "true").unwrap();
        config.set("diagnostics.phy", "true").unwrap();
        config.set("log_level", "off").unwrap();
        assert!(config.diagnostics.tx_hex && config.diagnostics.rx_hex && config.diagnostics.decode);
        assert!(config.diagnostics.phy);
        assert_eq!(config.log_level, "off");
        assert!(config.set("log_level", "typo").is_err());
    }

    #[test]
    fn rejects_both_filter_lists() {
        let mut config = Config::default();
        config.scanner.whitelist.push("AABBCC".into());
        config.scanner.blacklist.push("DDEEFF".into());
        assert!(config.validate().is_err());
        config.scanner.whitelist.clear();
        config.validate().unwrap();
    }

    #[test]
    fn parses_the_portal_yaml() {
        let text = "version: 1\ndevices:\n  - mac: 582D343B8A1D\n    bindkey: 9EF35BFD252659747191ED20F9B2B07D\n    model: Mi Temperature and Humidity Monitor 2\n    expose:\n      - attribute: temperature\n      - attribute: humidity\n";
        let config: Config = serde_yaml::from_str(text).unwrap();
        config.validate().unwrap();
        assert_eq!(config.devices.len(), 1);
        assert_eq!(config.devices[0].expose.len(), 2);
    }

    #[test]
    fn malformed_key_errors_do_not_echo_secrets() {
        let malformed = "00112233445566778899AABBCCDDEE";
        assert!(!parse_key(malformed).unwrap_err().contains(malformed));
    }

    #[test]
    fn edits_device_exposure_lists_with_structured_yaml() {
        let mut config = Config::default();
        config.set("devices", "[{mac: AABBCCDDEEFF}]").unwrap();
        config.set("devices.0.label", "PVVX").unwrap();
        config.set("devices.0.expose", "[{attribute: input_gpio_value, child: 4}]").unwrap();
        assert_eq!(config.devices[0].label, "PVVX");
        assert_eq!(config.devices[0].expose[0].attribute, "input_gpio_value");
        assert_eq!(config.devices[0].expose[0].child, Some(4));
        assert!(config.set("devices.1.label", "missing").is_err());
    }

    #[test]
    fn default_mac_filter_contains_only_enabled_registered_devices() {
        let mut config: Config = serde_yaml::from_str("devices:\n- {mac: AABBCCDDEEFF}\n- {mac: '112233445566', enabled: false}\n- {mac: AABBCC112233}\n").unwrap();
        config.validate().unwrap();
        assert!(config.scanner.filter_known_devices);
        assert_eq!(config.mac_filters().unwrap(), (true, vec![vec![0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF], vec![0xAA, 0xBB, 0xCC, 0x11, 0x22, 0x33]]));
        config.scanner.whitelist = vec!["AABBCCDD".into()];
        assert_eq!(config.mac_filters().unwrap().1.len(), 1);
        config.scanner.whitelist.clear();
        config.scanner.blacklist = vec!["AABBCCDD".into()];
        assert_eq!(config.mac_filters().unwrap().1, vec![vec![0xAA, 0xBB, 0xCC, 0x11, 0x22, 0x33]]);
        config.scanner.filter_known_devices = false;
        assert_eq!(config.mac_filters().unwrap(), (false, vec![vec![0xAA, 0xBB, 0xCC, 0xDD]]));
        config.scanner.blacklist.clear();
        assert_eq!(config.mac_filters().unwrap(), (true, Vec::new()));
        config.scanner.whitelist = vec!["AABBCC".into()];
        assert_eq!(config.mac_filters().unwrap(), (true, vec![vec![0xAA, 0xBB, 0xCC]]));
    }

    #[test]
    fn rejects_automatic_mac_filters_exceeding_firmware_capacity() {
        let mut config = Config::default();
        for index in 0..65 {
            config.devices.push(serde_yaml::from_str(&format!("mac: 'AABBCCDD{index:04X}'")).unwrap());
        }
        assert!(config.validate().unwrap_err().contains("64"));
        config.devices[64].enabled = false;
        config.validate().unwrap();
        config.devices[64].enabled = true;
        config.scanner.filter_known_devices = false;
        config.validate().unwrap();
    }
}
