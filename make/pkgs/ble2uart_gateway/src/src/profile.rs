//! Build-time platform profile.
//!
//! Runtime identifiers (MQTT client ID and base topic, mDNS host name, Matter
//! vendor) are the same on every platform. The `freetz` Cargo feature (enabled
//! by the Freetz-EVO package makefile) only adds the FRITZ!Box helper paths and
//! network interface preferences.

use std::path::{Path, PathBuf};

pub const FREETZ: bool = cfg!(feature = "freetz");

pub const NAME: &str = "ble2uart-gateway";

/// Default MQTT client ID / base topic and built-in mDNS host name.
pub fn default_name() -> String {
    NAME.into()
}

#[cfg_attr(not(feature = "matter"), allow(dead_code))]
pub const MATTER_VENDOR_NAME: &str = "ble2uart";

pub const READY_MESSAGE: &str = "ble2uart-gateway ready";

/// Absolute path of an external helper (mosquitto, matter-bridge): the
/// standard locations, the Freetz external storage, then `$PATH`.
pub fn find_helper(name: &str) -> Option<PathBuf> {
    let mut candidates = vec![Path::new("/usr/bin").join(name)];
    if FREETZ {
        candidates.push(Path::new("/mod/external/usr/bin").join(name));
    }
    if let Some(path) = std::env::var_os("PATH") {
        candidates.extend(std::env::split_paths(&path).filter(|directory| directory.is_absolute()).map(|directory| directory.join(name)));
    }
    candidates.into_iter().find(|path| path.is_file())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn profile_names_match_the_build() {
        assert_eq!(default_name(), "ble2uart-gateway");
        assert!(find_helper("sh").is_some_and(|path| path.is_absolute()));
        assert!(find_helper("definitely-not-an-installed-helper").is_none());
    }
}
