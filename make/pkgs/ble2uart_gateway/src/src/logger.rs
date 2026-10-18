//! A minimal `log` backend: the daemon must not pull a formatting stack into a
//! router firmware, and the log format follows the usual env_logger layout
//! ("[2026-10-16T00:12:34Z INFO  target] message").
//!
//! Diagnostic payload dumps are opt-in and independent from ordinary verbosity.

use log::{Level, LevelFilter, Log, Metadata, Record};
use std::io::{IsTerminal, Write};
use std::sync::atomic::{AtomicBool, Ordering};

static STDOUT: AtomicBool = AtomicBool::new(false);
static COLOR: AtomicBool = AtomicBool::new(false);
static TX_HEX: AtomicBool = AtomicBool::new(false);
static RX_HEX: AtomicBool = AtomicBool::new(false);
static DECODE: AtomicBool = AtomicBool::new(false);
static PHY: AtomicBool = AtomicBool::new(false);

struct GatewayLogger;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ColorMode {
    Auto,
    Always,
    Never,
}

pub fn parse_color_mode(value: &str) -> Result<ColorMode, String> {
    match value.to_ascii_lowercase().as_str() {
        "auto" => Ok(ColorMode::Auto),
        "always" => Ok(ColorMode::Always),
        "never" => Ok(ColorMode::Never),
        _ => Err("log color must be auto, always or never".into()),
    }
}

fn use_color(mode: ColorMode, terminal: bool, term: Option<&str>, no_color: bool) -> bool {
    match mode {
        ColorMode::Auto => terminal && term != Some("dumb") && !no_color,
        ColorMode::Always => true,
        ColorMode::Never => false,
    }
}

pub fn configure_color(mode: ColorMode) {
    let terminal = if STDOUT.load(Ordering::Relaxed) {
        std::io::stdout().is_terminal()
    } else {
        std::io::stderr().is_terminal()
    };
    let term = std::env::var("TERM").ok();
    let no_color = std::env::var_os("NO_COLOR").is_some_and(|value| !value.is_empty());
    COLOR.store(use_color(mode, terminal, term.as_deref(), no_color), Ordering::Relaxed);
}

fn format_record(record: &Record, timestamp: &str, color: bool) -> String {
    let level = format!("{:<5}", record.level());
    let level = if color {
        let ansi = match record.level() {
            Level::Error => "\x1b[31m",
            Level::Warn => "\x1b[33m",
            Level::Info => "\x1b[32m",
            Level::Debug => "\x1b[36m",
            Level::Trace => "\x1b[90m",
        };
        format!("{ansi}{level}\x1b[0m")
    } else {
        level
    };
    format!("[{timestamp} {level} {}] {}\n", record.target(), record.args())
}

/// `value` is `name=VALUE[ unit]`; with colors only `VALUE` is bold.
fn format_measurement(mac: &str, label: &str, child: u8, value: &str, color: bool) -> String {
    if !color {
        return format!("{mac} ({label}) child {child}: {value}");
    }
    let value = match value.split_once('=') {
        Some((name, rest)) => {
            let (number, unit) = rest.split_once(' ').map_or((rest, ""), |(number, unit)| (number, unit));
            let unit = if unit.is_empty() { String::new() } else { format!(" {unit}") };
            format!("{name}=\x1b[1;33m{number}\x1b[0m{unit}")
        }
        None => format!("\x1b[1;33m{value}\x1b[0m"),
    };
    format!("{mac} (\x1b[1;36m{label}\x1b[0m) child {child}: {value}")
}

pub fn measurement(mac: &str, label: &str, child: u8, value: &str) -> String {
    format_measurement(mac, label, child, value, COLOR.load(Ordering::Relaxed))
}

impl Log for GatewayLogger {
    fn enabled(&self, metadata: &Metadata) -> bool {
        metadata.level() <= log::max_level()
    }

    fn log(&self, record: &Record) {
        if !self.enabled(record.metadata()) {
            return;
        }
        let message = format_record(record, &timestamp(), COLOR.load(Ordering::Relaxed));
        if STDOUT.load(Ordering::Relaxed) {
            let mut output = std::io::stdout().lock();
            let _ = output.write_all(message.as_bytes());
            let _ = output.flush();
        } else {
            let _ = std::io::stderr().lock().write_all(message.as_bytes());
        }
    }

    fn flush(&self) {}
}

/// UTC timestamp without a chrono/time dependency: the firmware logs of the
/// other packages (env_logger) use the same shape.
pub fn timestamp() -> String {
    let seconds = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0);
    format_utc(seconds)
}

/// Format seconds since the epoch as `YYYY-MM-DDTHH:MM:SSZ`.
pub fn format_utc(seconds: u64) -> String {
    let days = seconds / 86_400;
    let rest = seconds % 86_400;
    let (hour, minute, second) = (rest / 3600, (rest % 3600) / 60, rest % 60);
    let (year, month, day) = civil_from_days(days as i64);
    format!("{year:04}-{month:02}-{day:02}T{hour:02}:{minute:02}:{second:02}Z")
}

/// Howard Hinnant's `civil_from_days`: days since 1970-01-01 to y/m/d.
fn civil_from_days(days: i64) -> (i64, u32, u32) {
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64; // [0, 146096]
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365; // [0, 399]
    let year = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100); // [0, 365]
    let mp = (5 * doy + 2) / 153; // [0, 11]
    let day = (doy - (153 * mp + 2) / 5 + 1) as u32; // [1, 31]
    let month = if mp < 10 { mp + 3 } else { mp - 9 } as u32; // [1, 12]
    (if month <= 2 { year + 1 } else { year }, month, day)
}

pub fn parse_level(value: &str) -> Result<LevelFilter, String> {
    match value.to_ascii_lowercase().as_str() {
        "off" => Ok(LevelFilter::Off),
        "error" => Ok(LevelFilter::Error),
        "warn" => Ok(LevelFilter::Warn),
        "info" | "" => Ok(LevelFilter::Info),
        "debug" => Ok(LevelFilter::Debug),
        "trace" => Ok(LevelFilter::Trace),
        _ => Err("log level must be off, error, warn, info, debug or trace".into()),
    }
}

pub fn level_from_env() -> u8 {
    match std::env::var("RUST_LOG").ok().and_then(|value| parse_level(&value).ok()) {
        Some(LevelFilter::Off) => 5,
        Some(LevelFilter::Error) => 0,
        Some(LevelFilter::Warn) => 1,
        Some(LevelFilter::Debug) => 3,
        Some(LevelFilter::Trace) => 4,
        _ => 2,
    }
}

pub fn configure(level: LevelFilter, stdout: bool, tx_hex: bool, rx_hex: bool, decode: bool, phy: bool) {
    STDOUT.store(stdout, Ordering::Relaxed);
    TX_HEX.store(tx_hex, Ordering::Relaxed);
    RX_HEX.store(rx_hex, Ordering::Relaxed);
    DECODE.store(decode, Ordering::Relaxed);
    PHY.store(phy, Ordering::Relaxed);
    log::set_max_level(level);
}

pub fn phy(report: &crate::link::AdvReport, stage: &str, status: &str, format: &str) {
    if PHY.load(Ordering::Relaxed) {
        let family = match format {
            "custom" | "custom_enc" => "pvvx",
            "bt_home" | "bt_home_enc" | "bt_home_v2" => "bthome",
            other => other,
        };
        log::info!(target: "ble.phy", "mac={} {} rssi={} event=0x{:02X} addr_type={} directed={} len={} stage={stage} status={status} wire_format={format} family={family}", report.mac_string(), report.phy_summary(), report.rssi, report.event_type, report.addr_type, report.directed, report.data.len());
    }
}

pub fn decode_enabled() -> bool {
    DECODE.load(Ordering::Relaxed) && log::log_enabled!(log::Level::Info)
}

pub fn tx(bytes: &[u8]) {
    if TX_HEX.load(Ordering::Relaxed) {
        log::info!(target: "ble.tx", "TX len={} hex={}", bytes.len(), crate::codec::value::hex(bytes));
    }
}

pub fn rx(bytes: &[u8]) {
    if RX_HEX.load(Ordering::Relaxed) {
        log::info!(target: "ble.rx", "RX len={} hex={}", bytes.len(), crate::codec::value::hex(bytes));
    }
}

pub fn init(verbosity: u8) {
    let level = match verbosity {
        0 => LevelFilter::Error,
        1 => LevelFilter::Warn,
        3 => LevelFilter::Debug,
        4 => LevelFilter::Trace,
        5 => LevelFilter::Off,
        _ => LevelFilter::Info,
    };
    let logger = Box::new(GatewayLogger);
    if log::set_boxed_logger(logger).is_ok() {
        log::set_max_level(level);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn color_policy_respects_terminals_and_no_color() {
        assert!(use_color(ColorMode::Auto, true, Some("xterm"), false));
        assert!(!use_color(ColorMode::Auto, false, Some("xterm"), false));
        assert!(!use_color(ColorMode::Auto, true, Some("dumb"), false));
        assert!(!use_color(ColorMode::Auto, true, Some("xterm"), true));
        assert!(use_color(ColorMode::Always, false, Some("dumb"), true));
        assert!(!use_color(ColorMode::Never, true, Some("xterm"), false));
        assert_eq!(parse_color_mode("AUTO").unwrap(), ColorMode::Auto);
        assert!(parse_color_mode("typo").is_err());
    }

    #[test]
    fn colored_levels_leave_plain_log_content_unchanged() {
        for (level, ansi) in [
            (Level::Error, "\x1b[31m"),
            (Level::Warn, "\x1b[33m"),
            (Level::Info, "\x1b[32m"),
            (Level::Debug, "\x1b[36m"),
            (Level::Trace, "\x1b[90m"),
        ] {
            let record = Record::builder().level(level).target("gateway").args(format_args!("temperature=16.08")).build();
            let plain = format_record(&record, "2026-10-18T06:22:13Z", false);
            assert_eq!(plain, format!("[2026-10-18T06:22:13Z {level:<5} gateway] temperature=16.08\n"));
            assert!(!plain.contains('\x1b'));
            let colored = format_record(&record, "2026-10-18T06:22:13Z", true);
            assert!(colored.contains(ansi));
            assert_eq!(colored.replace(ansi, "").replace("\x1b[0m", ""), plain);
        }
    }

    #[test]
    fn measurement_colors_highlight_device_and_bold_value_only() {
        let mac = "A4C138B3326C";
        let label = "Termometro esterno senza display";
        let value = "battery level=100 %";
        let plain = format_measurement(mac, label, 2, value, false);
        assert_eq!(plain, "A4C138B3326C (Termometro esterno senza display) child 2: battery level=100 %");
        assert!(!plain.contains('\x1b'));
        let colored = format_measurement(mac, label, 2, value, true);
        assert!(colored.contains("(\x1b[1;36mTermometro esterno senza display\x1b[0m)"));
        assert!(colored.ends_with("battery level=\x1b[1;33m100\x1b[0m %"));
        let temperature = format_measurement(mac, label, 0, "temperature=15.65 °C", true);
        assert!(temperature.ends_with("temperature=\x1b[1;33m15.65\x1b[0m °C"));
        assert!(format_measurement(mac, label, 4, "opened=1", true).ends_with("opened=\x1b[1;33m1\x1b[0m"));
        assert_eq!(colored.replace("\x1b[1;36m", "").replace("\x1b[1;33m", "").replace("\x1b[0m", ""), plain);
        let punctuation = format_measurement(mac, "Termometro (esterno): USB", 3, "battery v=3.01 V", false);
        assert_eq!(punctuation, "A4C138B3326C (Termometro (esterno): USB) child 3: battery v=3.01 V");
    }

    #[test]
    fn formats_utc_timestamps() {
        assert_eq!(format_utc(0), "1970-01-01T00:00:00Z");
        assert_eq!(format_utc(1_700_000_000), "2023-11-14T22:13:20Z");
        // A leap day, to exercise the civil-from-days conversion.
        assert_eq!(format_utc(1_582_934_400), "2020-02-29T00:00:00Z");
    }

    #[test]
    fn levels_are_explicit_and_include_off() {
        assert_eq!(parse_level("off").unwrap(), LevelFilter::Off);
        assert_eq!(parse_level("DEBUG").unwrap(), LevelFilter::Debug);
        assert_eq!(parse_level("trace").unwrap(), LevelFilter::Trace);
        assert!(parse_level("typo").is_err());
    }
}
