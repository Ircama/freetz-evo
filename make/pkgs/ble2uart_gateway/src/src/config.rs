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

fn default_theengs_prefix() -> String {
    "theengs_".into()
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

/// Which decoder produces the attributes of a device.
///
/// The Theengs modes need the package option
/// `FREETZ_PACKAGE_BLE2UART_GATEWAY_THEENGS`; with a build without it the
/// configuration stays valid and the device keeps using the built-in codec.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum DecoderMode {
    /// The generated specification of this gateway (default).
    #[default]
    #[serde(alias = "default")]
    Builtin,
    /// Theengs Decoder only: it also handles formats this gateway does not
    /// know, but it cannot decrypt bindkey advertisements.
    Theengs,
    /// Both: the built-in attributes plus the Theengs ones prefixed with
    /// `theengs_prefix`.
    Both,
}

impl DecoderMode {
    fn parse(text: &str) -> Option<Self> {
        match text {
            "builtin" => Some(Self::Builtin),
            "theengs" => Some(Self::Theengs),
            "both" => Some(Self::Both),
            _ => None,
        }
    }

    pub fn uses_builtin(self) -> bool {
        matches!(self, DecoderMode::Builtin | DecoderMode::Both)
    }

    pub fn uses_theengs(self) -> bool {
        matches!(self, DecoderMode::Theengs | DecoderMode::Both)
    }

    pub fn as_str(self) -> &'static str {
        match self {
            DecoderMode::Builtin => "builtin",
            DecoderMode::Theengs => "theengs",
            DecoderMode::Both => "both",
        }
    }
}

/// A device decoder of `default` (or none) inherits the global `decoder`.
fn inherited_decoder<'de, D: serde::Deserializer<'de>>(deserializer: D) -> Result<Option<DecoderMode>, D::Error> {
    match Option::<String>::deserialize(deserializer)?.as_deref() {
        None | Some("default") => Ok(None),
        Some(text) => DecoderMode::parse(text).map(Some)
            .ok_or_else(|| serde::de::Error::custom("expected builtin, theengs, both or default")),
    }
}

/// Text settings where `default` means the same as leaving the key out.
fn default_text<'de, D: serde::Deserializer<'de>>(deserializer: D) -> Result<String, D::Error> {
    let text = String::deserialize(deserializer)?;
    let text = text.trim();
    Ok(if text == "default" { String::new() } else { text.to_string() })
}

/// `true`, `false` or `default`; `default` and an omitted key both inherit.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum Toggle {
    #[default]
    Default,
    On,
    Off,
}

impl Toggle {
    pub fn is_default(&self) -> bool {
        *self == Toggle::Default
    }

    pub fn or(self, fallback: bool) -> bool {
        match self {
            Toggle::On => true,
            Toggle::Off => false,
            Toggle::Default => fallback,
        }
    }
}

impl Serialize for Toggle {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        match self {
            Toggle::On => serializer.serialize_bool(true),
            Toggle::Off => serializer.serialize_bool(false),
            Toggle::Default => serializer.serialize_str("default"),
        }
    }
}

impl<'de> Deserialize<'de> for Toggle {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        #[derive(Deserialize)]
        #[serde(untagged)]
        enum Raw {
            Flag(bool),
            Text(String),
        }
        match Raw::deserialize(deserializer)? {
            Raw::Flag(true) => Ok(Toggle::On),
            Raw::Flag(false) => Ok(Toggle::Off),
            Raw::Text(text) => match text.as_str() {
                "default" => Ok(Toggle::Default),
                "true" => Ok(Toggle::On),
                "false" => Ok(Toggle::Off),
                _ => Err(serde::de::Error::custom("expected true, false or default")),
            },
        }
    }
}

/// What SQLite keeps of an attribute: nothing, the recent frames shown by the
/// portal, or the recent frames plus the retained history.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SqliteMode {
    #[default]
    Default,
    Off,
    Live,
    History,
}

impl SqliteMode {
    pub fn is_default(&self) -> bool {
        *self == SqliteMode::Default
    }

    pub fn or(self, fallback: SqliteMode) -> SqliteMode {
        match (self, fallback) {
            (SqliteMode::Default, SqliteMode::Default) => SqliteMode::Off,
            (SqliteMode::Default, fallback) => fallback,
            (mode, _) => mode,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            SqliteMode::Default => "default",
            SqliteMode::Off => "off",
            SqliteMode::Live => "live",
            SqliteMode::History => "history",
        }
    }
}

/// How one decoded attribute is named and where it is published.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct AttributeConfig {
    /// Name produced by the decoder, `theengs_prefix` included in `both` mode.
    pub source: String,
    /// Published name; empty or `default` keeps `source`.
    #[serde(default, deserialize_with = "default_text", skip_serializing_if = "String::is_empty")]
    pub name: String,
    /// Unit override; empty or `default` keeps the decoder unit.
    #[serde(default, deserialize_with = "default_text", skip_serializing_if = "String::is_empty")]
    pub unit: String,
    #[serde(default, skip_serializing_if = "Toggle::is_default")]
    pub mqtt: Toggle,
    #[serde(default, skip_serializing_if = "Toggle::is_default")]
    pub influx: Toggle,
    #[serde(default, skip_serializing_if = "Toggle::is_default")]
    pub matter: Toggle,
    #[serde(default, skip_serializing_if = "Toggle::is_default")]
    pub mysensors: Toggle,
    #[serde(default, skip_serializing_if = "SqliteMode::is_default")]
    pub sqlite: SqliteMode,
    /// Name of a `frontends.sqlite.retention_rules` entry; empty or `default` inherits.
    #[serde(default, deserialize_with = "default_text", skip_serializing_if = "String::is_empty")]
    pub retention: String,
}

impl AttributeConfig {
    pub fn name(&self) -> &str {
        if self.name.is_empty() { &self.source } else { &self.name }
    }
}

/// Publication of every attribute that a device does not list, and of the
/// `default` values of the listed ones. Everything off by default.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(default, deny_unknown_fields)]
pub struct AttributeDefaults {
    #[serde(skip_serializing_if = "Toggle::is_default")]
    pub mqtt: Toggle,
    #[serde(skip_serializing_if = "Toggle::is_default")]
    pub influx: Toggle,
    #[serde(skip_serializing_if = "Toggle::is_default")]
    pub matter: Toggle,
    #[serde(skip_serializing_if = "Toggle::is_default")]
    pub mysensors: Toggle,
    #[serde(skip_serializing_if = "SqliteMode::is_default")]
    pub sqlite: SqliteMode,
    #[serde(deserialize_with = "default_text", skip_serializing_if = "String::is_empty")]
    pub retention: String,
}

impl AttributeDefaults {
    pub fn is_default(&self) -> bool {
        *self == Self::default()
    }
}

/// Effective publication of one attribute after `default` inheritance.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Route {
    /// Published name; empty for the fallback route, which keeps the source.
    pub name: String,
    /// Unit override; empty keeps the decoder unit.
    pub unit: String,
    pub mqtt: bool,
    pub influx: bool,
    pub matter: bool,
    pub mysensors: bool,
    /// `Off`, `Live` or `History`, never `Default`.
    pub sqlite: SqliteMode,
    /// Retention rule name; empty keeps every historical sample.
    pub retention: String,
}

/// The routes of one device: the listed attributes and the fallback.
#[derive(Debug, Clone, Default)]
pub struct Routing {
    listed: Vec<(String, Route)>,
    fallback: Route,
}

impl Routing {
    /// Published name and route of a decoded attribute. A source shadowed by a
    /// listed attribute that already publishes its name is dropped.
    pub fn route<'a>(&'a self, source: &'a str) -> Option<(&'a str, &'a Route)> {
        if let Some((_, route)) = self.listed.iter().find(|(listed, _)| listed == source) {
            return Some((&route.name, route));
        }
        if self.listed.iter().any(|(_, route)| route.name == source) {
            return None;
        }
        Some((source, &self.fallback))
    }

    pub fn listed(&self) -> impl Iterator<Item = &Route> {
        self.listed.iter().map(|(_, route)| route)
    }

    /// Whether the device configures this decoded attribute explicitly.
    pub fn is_listed(&self, source: &str) -> bool {
        self.listed.iter().any(|(listed, _)| listed == source)
    }

    /// Effective SQLite mode and rule of a stored (published) name.
    pub fn stored(&self, name: &str) -> (SqliteMode, &str) {
        if let Some(route) = self.listed().find(|route| route.name == name) {
            return (route.sqlite, &route.retention);
        }
        if self.listed.iter().any(|(source, _)| source == name) {
            return (SqliteMode::Off, "");
        }
        (self.fallback.sqlite, &self.fallback.retention)
    }
}

fn valid_name(name: &str, limit: usize) -> bool {
    !name.is_empty() && name.len() <= limit
        && name.bytes().all(|byte| byte.is_ascii_alphanumeric() || b"_.-".contains(&byte))
}

/// A device the user cares about. `bindkey` is the AES-128 key of the
/// encrypted formats and is never written to logs or to the web interface in
/// clear.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DeviceConfig {
    pub mac: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub manufacturer: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub model: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub firmware_version: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub label: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub bindkey: String,
    #[serde(default = "default_true")]
    pub enabled: bool,
    /// Force a codec format when the advertisement UUID is ambiguous, e.g.
    /// "atc1441_enc" or "bt_home_v2". Empty: detect from the service data.
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub format: String,
    /// Overrides the global `decoder`; omitted or `default` inherits it.
    #[serde(default, deserialize_with = "inherited_decoder", skip_serializing_if = "Option::is_none")]
    pub decoder: Option<DecoderMode>,
    /// Attributes whose name or publication differs from `attribute_defaults`.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub attributes: Vec<AttributeConfig>,
    /// Per-device missing-reading monitors with independent HTTPS destinations.
    #[serde(default, deserialize_with = "crate::automation::deserialize_rules", skip_serializing_if = "Vec::is_empty")]
    pub rules: Vec<crate::automation::AutomationRule>,
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

    #[cfg(feature="matter")]
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
    #[cfg(any(feature="matter",test))]
    pub fn effective_mdns_backend(&self) -> MdnsBackend {
        if self.advertise { self.mdns_backend } else { MdnsBackend::Disabled }
    }

    #[cfg(any(feature="matter",test))]
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
    pub sqlite: crate::sqlite::SqliteConfig,
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
#[serde(default, deny_unknown_fields)]
pub struct LoggingConfig {
    pub max_size_kb: u32,
    pub history: u8,
}

impl Default for LoggingConfig {
    fn default() -> Self {
        Self {
            max_size_kb: 128,
            history: 2,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default = "default_version")]
    pub version: u32,
    #[serde(default)]
    pub serial: SerialConfig,
    #[serde(default)]
    pub scanner: ScannerConfig,
    /// Publication of the attributes a device does not list.
    #[serde(default, skip_serializing_if = "AttributeDefaults::is_default")]
    pub attribute_defaults: AttributeDefaults,
    #[serde(default)]
    pub devices: Vec<DeviceConfig>,
    #[serde(default)]
    pub frontends: Frontends,
    #[serde(default)]
    pub log_level: String,
    #[serde(default)]
    pub logging: LoggingConfig,
    #[serde(default)]
    pub diagnostics: DiagnosticsConfig,
    #[serde(default)]
    #[serde(skip_serializing)]
    pub automation: Option<crate::automation::LegacyAutomationConfig>,
    #[serde(default)]
    pub availability_state_file: String,
    /// Decoder shared by every device; `builtin` keeps the historical
    /// behaviour.
    #[serde(default)]
    pub decoder: DecoderMode,
    #[serde(default = "default_theengs_prefix")]
    pub theengs_prefix: String,
}

impl Default for Config {
    /// The configuration written on first start: MySensors enabled on loopback
    /// (the Domoticz path), the rest off.
    fn default() -> Self {
        Config {
            version: CONFIG_VERSION,
            serial: SerialConfig::default(),
            scanner: ScannerConfig::default(),
            attribute_defaults: AttributeDefaults::default(),
            devices: Vec::new(),
            frontends: Frontends {
                sqlite: crate::sqlite::SqliteConfig::default(),
                influx: crate::influx::InfluxConfig::default(),
                mysensors: MySensorsConfig {
                    enabled: true,
                    ..MySensorsConfig::default()
                },
                mqtt: MqttConfig::default(),
                matter: MatterConfig::default(),
            },
            log_level: "info".into(),
            logging: LoggingConfig::default(),
            diagnostics: DiagnosticsConfig::default(),
            automation: None,
            availability_state_file: String::new(),
            decoder: DecoderMode::default(),
            theengs_prefix: default_theengs_prefix(),
        }
    }
}

impl Config {
    /// Routes of a device after `default` inheritance.
    pub fn routing(&self, device: &DeviceConfig) -> Routing {
        let defaults = &self.attribute_defaults;
        let fallback = Route {
            name: String::new(),
            unit: String::new(),
            mqtt: defaults.mqtt.or(false),
            influx: defaults.influx.or(false),
            matter: defaults.matter.or(false),
            mysensors: defaults.mysensors.or(false),
            sqlite: defaults.sqlite.or(SqliteMode::Off),
            retention: defaults.retention.clone(),
        };
        let listed = device.attributes.iter().map(|attribute| {
            let sqlite = attribute.sqlite.or(fallback.sqlite);
            (attribute.source.clone(), Route {
                name: attribute.name().to_string(),
                unit: attribute.unit.clone(),
                mqtt: attribute.mqtt.or(fallback.mqtt),
                influx: attribute.influx.or(fallback.influx),
                matter: attribute.matter.or(fallback.matter),
                mysensors: attribute.mysensors.or(fallback.mysensors),
                sqlite,
                retention: if attribute.retention.is_empty() { fallback.retention.clone() } else { attribute.retention.clone() },
            })
        }).collect();
        Routing { listed, fallback }
    }

    fn validate_attributes(&self) -> Result<(), String> {
        let sqlite = &self.frontends.sqlite;
        sqlite.validate_rules()?;
        let rule = |name: &str| name.is_empty() || sqlite.retention_rules.contains_key(name);
        let defaults = &self.attribute_defaults;
        if !rule(&defaults.retention) {
            return Err(format!("attribute_defaults: unknown retention rule {}", defaults.retention));
        }
        if sqlite.enabled && sqlite.recent_frames_s == 0 && defaults.sqlite == SqliteMode::Live {
            return Err("attribute_defaults: sqlite live needs recent frames (frontends.sqlite.recent_frames_s > 0)".into());
        }
        for device in &self.devices {
            if device.attributes.len() > 256 {
                return Err(format!("{}: at most 256 attributes per device", device.mac));
            }
            let mut sources = std::collections::BTreeSet::new();
            let mut names = std::collections::BTreeSet::new();
            for attribute in &device.attributes {
                let context = format!("{} {}", device.mac, attribute.source);
                if !valid_name(&attribute.source, 128) || !valid_name(attribute.name(), 128) {
                    return Err(format!("{context}: source and name need 1-128 ASCII letters, digits, '_', '.' or '-'"));
                }
                if !sources.insert(attribute.source.as_str()) {
                    return Err(format!("{context}: attribute listed twice"));
                }
                if !names.insert(attribute.name()) {
                    return Err(format!("{context}: published name {} is used twice", attribute.name()));
                }
                if attribute.unit.len() > 32 || attribute.unit.chars().any(char::is_control) {
                    return Err(format!("{context}: unit must be at most 32 characters without control characters"));
                }
                if !rule(&attribute.retention) {
                    return Err(format!("{context}: unknown retention rule {}", attribute.retention));
                }
                let mode = attribute.sqlite.or(defaults.sqlite);
                if !attribute.retention.is_empty() && mode != SqliteMode::History {
                    return Err(format!("{context}: a retention rule needs sqlite history"));
                }
                if sqlite.enabled && sqlite.recent_frames_s == 0 && mode == SqliteMode::Live {
                    return Err(format!("{context}: sqlite live needs recent frames (frontends.sqlite.recent_frames_s > 0)"));
                }
                if attribute.mysensors == Toggle::On && crate::pipeline::mysensors_child(attribute.name()).is_none() {
                    return Err(format!("{context}: MySensors has no sensor type for {}", attribute.name()));
                }
            }
        }
        Ok(())
    }

    pub fn prepare_availability(&mut self,path: &Path) -> Result<(),String> {
        if let Some(legacy)=self.automation.take() {
            if self.availability_state_file.is_empty() {self.availability_state_file=legacy.state_file;}
            for device in &mut self.devices {
                let address=parse_mac(&device.mac)?;
                for old in &legacy.rules {
                    if !old.mac.is_empty() && parse_mac(&old.mac)?!=address {continue;}
                    if device.rules.iter().any(|rule|rule.id==old.id) {continue;}
                    device.rules.push(crate::automation::AutomationRule {
                        id:old.id.clone(),enabled:legacy.enabled&&old.enabled&&legacy.webhook.enabled,
                        attribute:old.attribute.clone(),stale_after_s:old.stale_after_s,
                        notify_recovery:old.notify_recovery,webhook:legacy.webhook.clone(),
                        ..Default::default()
                    });
                }
            }
        }
        if self.availability_state_file.is_empty() {
            let absolute=if path.is_absolute() {path.to_owned()} else {std::env::current_dir().map_err(|error|error.to_string())?.join(path)};
            self.availability_state_file=absolute.parent().unwrap_or(Path::new("/")).join("automation-state.json").to_string_lossy().into_owned();
        }
        Ok(())
    }

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
        config.prepare_availability(path)?;
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
        if self.theengs_prefix.is_empty() || self.theengs_prefix.len() > 64
            || !self.theengs_prefix.bytes().all(|byte| byte.is_ascii_alphanumeric() || b"_.-".contains(&byte))
        {
            return Err("Theengs prefix must contain 1-64 ASCII letters, digits, underscores, dots or hyphens".into());
        }
        crate::logger::parse_level(&self.log_level)?;
        if !(16..=4096).contains(&self.logging.max_size_kb) {
            return Err("logging.max_size_kb must be between 16 and 4096".into());
        }
        if self.logging.history > 10 {
            return Err("logging.history must be between 0 and 10".into());
        }
        if !crate::theengs::available()
            && (self.decoder != DecoderMode::Builtin
                || self.devices.iter().any(|device| {
                    matches!(device.decoder, Some(mode) if mode != DecoderMode::Builtin)
                }))
        {
            return Err(
                "decoder theengs/both needs a build with FREETZ_PACKAGE_BLE2UART_GATEWAY_THEENGS"
                    .into(),
            );
        }
        if self.devices.iter().map(|device|device.rules.len()).sum::<usize>()>4096 {
            return Err("at most 4096 automation device/rule watches are supported".into());
        }
        if !self.availability_state_file.is_empty() && (!Path::new(&self.availability_state_file).is_absolute()||self.availability_state_file.chars().any(char::is_control)) {
            return Err("availability state file must be an absolute path".into());
        }
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
            if device.rules.len()>32 {return Err("at most 32 availability rules per device are supported".into());}
            let mut rule_ids=std::collections::HashSet::new();
            for rule in &device.rules {
                rule.validate()?;
                if !rule_ids.insert(&rule.id) {return Err("availability rule IDs must be unique within each device".into());}
            }
        }
        self.validate_attributes()?;
        self.mac_filters()?;
        if self.frontends.influx.enabled { self.frontends.influx.validate()?; }
        if self.frontends.sqlite.enabled { self.frontends.sqlite.validate()?; }
        if self.frontends.matter.enabled { self.frontends.matter.validate_mdns()?; }
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
            // Omitted optional lists and maps (for example empty attributes) take YAML.
            None if value.trim_start().starts_with(['[', '{']) => serde_yaml::from_str(value).map_err(|error| format!("{key}: {error}"))?,
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
    fn theengs_prefix_defaults_and_roundtrips() {
        let mut config: Config = serde_yaml::from_str("version: 1\n").unwrap();
        assert_eq!(config.theengs_prefix, "theengs_");
        config.set("theengs_prefix", "td_").unwrap();
        let restored: Config = serde_yaml::from_str(&serde_yaml::to_string(&config).unwrap()).unwrap();
        assert_eq!(restored.theengs_prefix, "td_");
        for prefix in ["", "bad prefix", "bad/prefix", "\n"] {
            config.theengs_prefix = prefix.into();
            assert!(config.validate().is_err());
        }
    }

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
        config.set("logging.max_size_kb", "256").unwrap();
        config.set("logging.history", "3").unwrap();
        assert!(config.diagnostics.tx_hex && config.diagnostics.rx_hex && config.diagnostics.decode);
        assert!(config.diagnostics.phy);
        assert_eq!(config.log_level, "off");
        assert_eq!(config.logging.max_size_kb, 256);
        assert_eq!(config.logging.history, 3);
        assert!(config.set("log_level", "typo").is_err());
        assert!(config.set("logging.max_size_kb", "8").is_err());
        assert!(config.set("logging.history", "11").is_err());
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
        let text = "version: 1\ndevices:\n  - mac: 582D343B8A1D\n    bindkey: 9EF35BFD252659747191ED20F9B2B07D\n    model: Mi Temperature and Humidity Monitor 2\n    attributes:\n      - {source: temperature, mqtt: true}\n      - {source: humidity, sqlite: history}\n";
        let config: Config = serde_yaml::from_str(text).unwrap();
        config.validate().unwrap();
        assert_eq!(config.devices.len(), 1);
        assert_eq!(config.devices[0].attributes.len(), 2);
        assert!(serde_yaml::from_str::<DeviceConfig>("mac: 582D343B8A1D\nexpose: []\n").is_err(), "removed keys are reported");
    }

    #[test]
    fn malformed_key_errors_do_not_echo_secrets() {
        let malformed = "00112233445566778899AABBCCDDEE";
        assert!(!parse_key(malformed).unwrap_err().contains(malformed));
    }

    #[test]
    fn edits_device_attribute_lists_with_structured_yaml() {
        let mut config = Config::default();
        config.set("devices", "[{mac: AABBCCDDEEFF}]").unwrap();
        config.set("devices.0.label", "PVVX").unwrap();
        config.set("devices.0.attributes", "[{source: input_gpio_value, mysensors: true}]").unwrap();
        assert_eq!(config.devices[0].label, "PVVX");
        assert_eq!(config.devices[0].attributes[0].source, "input_gpio_value");
        assert_eq!(config.devices[0].attributes[0].mysensors, Toggle::On);
        assert!(config.set("devices.1.label", "missing").is_err());
    }

    #[test]
    fn default_values_are_omitted_and_inherited() {
        let yaml = concat!(
            "attribute_defaults: {mqtt: default, sqlite: history, retention: climate}\n",
            "frontends: {sqlite: {retention_rules: {climate: {mode: progressive, tiers: [{max_age_s: 60, sample_interval_s: 0}]}, ",
            "everything: {mode: default}}}}\n",
            "devices:\n- mac: AABBCCDDEEFF\n  decoder: default\n  attributes:\n",
            "  - {source: temperature, name: default, unit: default, mqtt: default, influx: true, sqlite: default, retention: default}\n",
            "  - {source: humidity, sqlite: off, matter: false}\n",
            "  - {source: battery_level, retention: everything}\n",
        );
        let config: Config = serde_yaml::from_str(yaml).unwrap();
        config.validate().unwrap();
        let device = &config.devices[0];
        assert_eq!(device.decoder, None);
        let temperature = &device.attributes[0];
        assert_eq!((temperature.name.as_str(), temperature.unit.as_str(), temperature.mqtt), ("", "", Toggle::Default));
        assert_eq!(temperature.sqlite, SqliteMode::Default);
        let routing = config.routing(device);
        assert_eq!(routing.route("temperature").unwrap().1.retention, "climate");
        assert!(routing.route("temperature").unwrap().1.influx);
        assert_eq!(routing.route("humidity").unwrap().1.sqlite, SqliteMode::Off);
        assert_eq!(routing.route("battery_level").unwrap().1.retention, "everything");
        let saved = serde_yaml::to_string(&config).unwrap();
        assert!(saved.contains("- source: temperature\n    influx: true\n"), "{saved}");
        assert!(!saved.contains(": default"), "{saved}");
        assert!(serde_yaml::from_str::<Config>("attribute_defaults: {mqtt: maybe}\n").is_err());
        assert!(serde_yaml::from_str::<Config>("devices:\n- {mac: AABBCCDDEEFF, attributes: [{source: x, unknown: 1}]}\n").is_err());
    }

    #[test]
    fn attribute_validation_reports_inconsistent_routes() {
        let base = Config::default();
        let invalid = [
            "devices:\n- {mac: AABBCCDDEEFF, attributes: [{source: a}, {source: a}]}\n",
            "devices:\n- {mac: AABBCCDDEEFF, attributes: [{source: a, name: x}, {source: b, name: x}]}\n",
            "devices:\n- {mac: AABBCCDDEEFF, attributes: [{source: 'a b'}]}\n",
            "devices:\n- {mac: AABBCCDDEEFF, attributes: [{source: a, sqlite: history, retention: missing}]}\n",
            "devices:\n- {mac: AABBCCDDEEFF, attributes: [{source: a, sqlite: live, retention: climate}]}\n",
            "devices:\n- {mac: AABBCCDDEEFF, attributes: [{source: packet_id, mysensors: true}]}\n",
            "attribute_defaults: {retention: missing}\n",
            "frontends: {sqlite: {retention_rules: {bad: {tiers: [{max_age_s: 60, sample_interval_s: 0}]}}}}\n",
            "frontends: {sqlite: {retention_rules: {default: {}}}}\n",
            "frontends: {sqlite: {enabled: true, path: /tmp/x.db, recent_frames_s: 0}}\ndevices:\n- {mac: AABBCCDDEEFF, attributes: [{source: a, sqlite: live}]}\n",
        ];
        for yaml in invalid {
            let config: Config = serde_yaml::from_str(yaml).unwrap();
            assert!(config.validate().is_err(), "{yaml}");
        }
        base.validate().unwrap();
        let valid: Config = serde_yaml::from_str("frontends: {sqlite: {enabled: true, path: /tmp/x.db, recent_frames_s: default}}\ndevices:\n- {mac: AABBCCDDEEFF, attributes: [{source: a, sqlite: history, retention: climate}]}\n").unwrap();
        valid.validate().unwrap();
        assert_eq!(valid.frontends.sqlite.recent_frames_s, 600);
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
