//! Read the FRITZ!Box data that the Matter device exposes.
//!
//! The temperature chain mirrors what Freetz-EVO's own
//! `make/pkgs/mod/files/root/usr/lib/cgi-bin/mod/box_info.cgi` does, so the
//! value shown by the web UI and the value reported over Matter come from the
//! same source, in the same priority order.
//!
//! Not every helper is used by the current endpoint set; they are kept because
//! they are the building blocks for the further endpoints listed in the package
//! documentation.
#![allow(dead_code)]

use std::fs;
use std::process::Command;
use std::sync::{Arc, Condvar, Mutex, OnceLock};

/// Read the first readable file in the list.
fn first_readable(paths: &[&str]) -> Option<String> {
    paths
        .iter()
        .find_map(|p| fs::read_to_string(p).ok())
        .map(|s| s.trim().to_string())
}

/// Extract `prefix<number>` handling an optional decimal point.
fn parse_float(text: &str) -> Option<f32> {
    let digits: String = text
        .chars()
        .take_while(|c| c.is_ascii_digit() || *c == '.')
        .collect();

    digits.parse::<f32>().ok()
}

/// Box temperature in degrees Celsius.
///
/// Priority order (same as `box_info.cgi`):
/// 1. `/proc/chip_temperature` — `Channel N: 42.50 ...`, highest channel wins
/// 2. `/sys/devices/virtual/thermal/thermal_zone0/temp` — millidegrees
/// 3. `/proc/avm/powermanagmentressourceinfo/powerdevice_temperature`
/// 4. `/proc/avm/temp_sensors` — `CPU: 42.50`
pub fn temperature_celsius() -> Option<f32> {
    if let Ok(text) = fs::read_to_string("/proc/chip_temperature") {
        let mut best: Option<f32> = None;
        for line in text.lines() {
            let lower = line.to_ascii_lowercase();
            let Some(pos) = lower.find("channel") else {
                continue;
            };
            // "Channel 1: 42.50" -> take what follows the colon
            let rest = &line[pos..];
            let value = match rest.split_once(':') {
                Some((_, v)) => parse_float(v.trim()),
                None => None,
            };
            if let Some(v) = value {
                if best.map(|b| v > b).unwrap_or(true) {
                    best = Some(v);
                }
            }
        }
        if best.is_some() {
            return best;
        }
    }

    if let Some(text) = first_readable(&["/sys/devices/virtual/thermal/thermal_zone0/temp"]) {
        if let Some(milli) = parse_float(&text) {
            // The sysfs attribute is in millidegrees; AVM's own CGI inserts the
            // decimal point after two digits.
            return Some(milli / 1000.0);
        }
    }

    if let Some(text) =
        first_readable(&["/proc/avm/powermanagmentressourceinfo/powerdevice_temperature"])
    {
        if let Some(v) = parse_float(&text) {
            if v != 0.0 {
                return Some(v);
            }
        }
    }

    if let Ok(text) = fs::read_to_string("/proc/avm/temp_sensors") {
        for line in text.lines() {
            let lower = line.to_ascii_lowercase();
            if lower.starts_with("cpu") || lower.starts_with("cpu-thermal") {
                if let Some((_, v)) = line.split_once(':') {
                    if let Some(value) = parse_float(v.trim()) {
                        return Some(value);
                    }
                }
            }
        }
    }

    None
}

/// Firmware version from `/etc/version` (`export FIRMWARE_VERSION="..."`).
pub fn firmware_version() -> String {
    if let Some(text) = first_readable(&["/etc/version"]) {
        for line in text.lines() {
            let line = line.trim();
            if let Some(rest) = line.strip_prefix("export FIRMWARE_VERSION=") {
                return rest.trim_matches('"').to_string();
            }
        }
    }

    first_readable(&["/etc/.revision"]).unwrap_or_else(|| "unknown".to_string())
}

/// AVM revision string (`/etc/.revision`).
pub fn firmware_revision() -> String {
    first_readable(&["/etc/.revision"]).unwrap_or_else(|| "unknown".to_string())
}

/// Build/manufacturing date as `YYYYMMDD` (Matter requires that format).
pub fn manufacturing_date() -> String {
    if let Some(text) = first_readable(&["/etc/version"]) {
        for line in text.lines() {
            if let Some(rest) = line.trim().strip_prefix("export FIRMWARE_DATE=") {
                // German format `dd.mm.yyyy`
                let date = rest.trim_matches('"');
                let parts: Vec<&str> = date.split('.').collect();
                if parts.len() == 3 && parts[2].len() == 4 {
                    return format!("{}{:0>2}{:0>2}", parts[2], parts[1], parts[0]);
                }
            }
        }
    }

    "20240101".to_string()
}

/// Box model, e.g. `FRITZ!Box 7590 AX`.
pub fn box_model() -> String {
    // `/proc/cpuinfo` carries the AVM hardware name ("GRX5" etc.); `/var/env`
    // carries the marketing name on most firmwares.
    first_readable(&["/proc/device-tree/model", "/sys/firmware/devicetree/base/model"])
        .or_else(|| {
            let text = first_readable(&["/proc/cpuinfo"])?;
            for line in text.lines() {
                if let Some((key, value)) = line.split_once(':') {
                    let key = key.trim().to_ascii_lowercase();
                    if key == "system type" || key == "hardware" || key == "machine" {
                        return Some(value.trim().split(' ').next().unwrap_or(value).to_string());
                    }
                }
            }
            None
        })
        .unwrap_or_else(|| "FRITZ!Box".to_string())
}

/// Serial number: the LAN MAC address, as AVM prints it in `box_info`.
pub fn serial_number() -> String {
    if let Ok(text) = fs::read_to_string("/var/env") {
        for line in text.lines() {
            if let Some(mac) = line.strip_prefix("maca ") {
                let mac = mac.trim();
                if !mac.is_empty() {
                    return mac.to_string();
                }
            }
        }
    }

    first_readable(&["/sys/class/net/eth0/address"])
        .map(|mac| mac.to_uppercase())
        .unwrap_or_else(|| "000000000000".to_string())
}

/// Hardware version string: AVM revision when available.
pub fn hardware_version() -> String {
    first_readable(&["/etc/.revision", "/proc/sys/kernel/osrelease"])
        .unwrap_or_else(|| "1".to_string())
}

/// CPU temperature sensor availability, used for logging.
pub fn temperature_source() -> &'static str {
    for path in [
        "/proc/chip_temperature",
        "/sys/devices/virtual/thermal/thermal_zone0/temp",
        "/proc/avm/powermanagmentressourceinfo/powerdevice_temperature",
        "/proc/avm/temp_sensors",
    ] {
        if fs::metadata(path).is_ok() {
            return path;
        }
    }

    "none"
}

/* ------------------------------------------------------------------ audio */

/// Sound cards known to ALSA (`/proc/asound/cards`), one entry per card.
pub fn alsa_cards() -> Vec<String> {
    let Ok(text) = fs::read_to_string("/proc/asound/cards") else {
        return Vec::new();
    };

    text.lines()
        .filter(|line| line.trim_start().starts_with(char::is_numeric))
        .map(|line| line.trim().to_string())
        .collect()
}

fn amixer(args: &[&str]) -> bool {
    Command::new("amixer")
        .args(args)
        .output()
        .map(|out| out.status.success())
        .unwrap_or(false)
}

#[derive(Default)]
struct MixerUpdate {
    volume: Option<u8>,
    muted: Option<bool>,
}

type MixerQueue = Arc<(Mutex<MixerUpdate>, Condvar)>;

fn mixer_queue() -> &'static MixerQueue {
    static QUEUE: OnceLock<MixerQueue> = OnceLock::new();
    QUEUE.get_or_init(|| {
        let queue = Arc::new((Mutex::new(MixerUpdate::default()), Condvar::new()));
        let worker_queue = Arc::clone(&queue);
        std::thread::Builder::new().name("matter-alsa".into()).spawn(move || loop {
            let (pending, ready) = &*worker_queue;
            let mut update = pending.lock().unwrap();
            while update.volume.is_none() && update.muted.is_none() {
                update = ready.wait(update).unwrap();
            }
            let batch = std::mem::take(&mut *update);
            drop(update);
            if let Some(percent) = batch.volume {
                let arg = format!("{}%", percent);
                if !amixer(&["set", "PCM", &arg, "unmute"]) && !amixer(&["set", "Master", &arg, "unmute"]) {
                    log::warn!("speaker: ALSA volume update failed");
                }
            }
            if let Some(muted) = batch.muted {
                let action = if muted { "mute" } else { "unmute" };
                if !amixer(&["set", "PCM", action]) && !amixer(&["set", "Master", action]) {
                    log::warn!("speaker: ALSA mute update failed");
                }
            }
        }).expect("could not start ALSA worker");
        queue
    })
}

/// Queue the latest PCM playback volume without blocking the Matter executor.
pub fn set_volume_percent(percent: u8) -> bool {
    let (pending, ready) = &**mixer_queue();
    pending.lock().unwrap().volume = Some(percent.min(100));
    ready.notify_one();
    true
}

/// Queue mute/unmute without waiting for the ALSA subprocess.
pub fn set_muted(muted: bool) -> bool {
    let (pending, ready) = &**mixer_queue();
    pending.lock().unwrap().muted = Some(muted);
    ready.notify_one();
    true
}

/// Current playback volume in percent, when `amixer` can report it.
pub fn volume_percent() -> Option<u8> {
    let output = Command::new("amixer")
        .args(["get", "PCM"])
        .output()
        .or_else(|_| Command::new("amixer").args(["get", "Master"]).output())
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let text = String::from_utf8_lossy(&output.stdout);
    for line in text.lines() {
        if let Some(pos) = line.find('[') {
            let rest = &line[pos + 1..];
            let digits: String = rest.chars().take_while(|c| c.is_ascii_digit()).collect();
            if let Ok(value) = digits.parse::<u8>() {
                return Some(value);
            }
        }
    }

    None
}

/// Whether the playback path is currently muted.
pub fn is_muted() -> Option<bool> {
    let output = Command::new("amixer")
        .args(["get", "PCM"])
        .output()
        .or_else(|_| Command::new("amixer").args(["get", "Master"]).output())
        .ok()?;

    let text = String::from_utf8_lossy(&output.stdout);
    let lower = text.to_ascii_lowercase();
    if lower.contains("[off]") {
        Some(true)
    } else if lower.contains("[on]") {
        Some(false)
    } else {
        None
    }
}
