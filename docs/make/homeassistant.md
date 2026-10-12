# Home Assistant (setup helper + autorun)
  - Package: [master/make/pkgs/homeassistant/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/homeassistant/)
  - Steward: -
  - Provides: `/usr/bin/ha-setup`, init script `rc.homeassistant`
  - Configuration: `/mod/etc/default.homeassistant/homeassistant.cfg`
  - Category: Home Automation
  - Status: helper package — Home Assistant itself is installed on demand, not cross-compiled

`homeassistant` does not ship Home Assistant: it ships everything needed to **install, update and autostart** it on the FRITZ!Box, plus the Kconfig selection of the Python interpreter modules and libraries the application needs. This is the same approach used for other big Python applications that cannot be cross-compiled in a reproducible way: the *runtime* stays on external storage, the *integration* (init script, web-configurable settings, validation hooks) lives in the firmware.

## Why a helper instead of a port

Home Assistant is a moving target (monthly releases, thousands of dependencies, many of them native wheels). Cross-compiling it would mean rebuilding the whole dependency tree at every upstream release, and the resulting image would still be one version behind. The helper keeps the firmware small and lets the user choose the version:

```bash
ha-setup --check                                  # verify python, storage, swap
ha-setup --basedir /var/media/ftp/homeassistant   # install latest release
ha-setup --version 2026.10.4                      # or a pinned version
ha-setup --update                                 # upgrade later
ha-setup --status                                 # what is installed
ha-setup --uninstall                              # remove python/ and pip/, keep config/
```

## Layout on the box

| Path | Content |
|---|---|
| `<basedir>/python/lib/python3.x/site-packages` | Python packages installed with `pip --prefix` |
| `<basedir>/python/bin/hass` | Home Assistant launcher |
| `<basedir>/config/configuration.yaml` | starter configuration created by the helper |
| `<basedir>/config/home-assistant_v2.db` | recorder database (kept off the flash) |
| `<basedir>/pip/get-pip.py` | pip bootstrap, kept for later upgrades |

Freetz builds Python with `--with-ensurepip=no`, therefore the helper downloads `https://bootstrap.pypa.io/get-pip.py` (Internet access is required during the setup) and installs pip into the prefix. The init script runs the launcher with `PYTHONPATH` pointing at that prefix, so no `venv` module is needed.

## Requirements

| Requirement | Detail |
|---|---|
| Python | 3.13 or newer, with `ssl`, `ctypes` and `sqlite3` (`FREETZ_PACKAGE_PYTHON3` plus the *Minimal* or *Full* Python support selected by this package) |
| Storage | ext4 USB stick or NAS, ~1.5 GB free; the recorder database is placed there explicitly |
| Memory | 1 GB recommended, swap strongly advised — Python plus the integration stack is memory hungry |
| Internet | needed by `ha-setup` (PyPI) and by the integrations that fetch data from the cloud |

On a FRITZ!Box with 256–512 MB RAM Home Assistant starts but is only usable with swap and a small integration set. For a permanent installation the recommended split is: **Home Assistant on a NAS/Raspberry Pi**, `matter-bridge`/`otbr-agent`/`rtl_433` on the FRITZ!Box (see [HOME-AUTOMATION.md](../HOME-AUTOMATION.md)).

## Configuration

Defaults live in `/etc/default.homeassistant/homeassistant.cfg`, saved values in `/mod/etc/conf/homeassistant.cfg`; every variable is exported so it appears in the Freetz web interface.

| Variable | Default | Meaning |
|---|---|---|
| `HOMEASSISTANT_ENABLED` | `no` | start Home Assistant at boot |
| `HOMEASSISTANT_BASEDIR` | `/var/media/ftp/homeassistant` | installation root on external storage |
| `HOMEASSISTANT_PYTHON_PREFIX` | *(empty)* | override the Python prefix (default `<basedir>/python`) |
| `HOMEASSISTANT_CONFIG` | *(empty)* | override the config directory (default `<basedir>/config`) |
| `HOMEASSISTANT_HTTP_PORT` | `8123` | port written into the starter `configuration.yaml` |
| `HOMEASSISTANT_VERSION` | *(empty)* | version installed by the helper (empty = latest) |
| `HOMEASSISTANT_PIP_INDEX_URL` | *(empty)* | alternative PyPI index/mirror |
| `HOMEASSISTANT_LOG_TO_FILE` | `yes` | log to `<config>/home-assistant.log` |
| `HOMEASSISTANT_NICE` | `5` | nice level |
| `HOMEASSISTANT_CONFIG_WAIT` | `120` | seconds to wait for the storage at boot (0 = no wait) |
| `HOMEASSISTANT_VERBOSE` | `no` | `PYTHONVERBOSE=1` |
| `HOMEASSISTANT_EXTRA_ARGS` | *(empty)* | extra arguments for `hass` |

The save hook validates that the nice level, the boot wait and the HTTP port are numeric, warns when the base directory is not on external storage and reminds the user when Home Assistant is not installed yet.

## Init script

`rc.homeassistant` follows the standard modlib pattern (`modreg daemon`, `modlib_start`/`modlib_stop`/`modlib_restart`/`modlib_status`, `modlib_startdaemon start-stop-daemon`). Because the installation becomes available only after the USB stick or the NAS is mounted, at boot the script waits **in a background subshell** for `<prefix>/bin/hass` and then starts the service; the boot sequence is never blocked. The extra `setup` action forwards to the helper:

```bash
/etc/init.d/rc.homeassistant setup --basedir /var/media/ftp/homeassistant
/etc/init.d/rc.homeassistant start
```

## Interaction with the other Freetz-EVO packages

The starter `configuration.yaml` contains commented-out examples for the local services:

* `matter:` → `ws://127.0.0.1:5580/ws`, the native `matter-bridge` (no Node.js), see [MATTER.md](../MATTER.md)
* `domoticz:` → a local Domoticz instance on port 8080
* `mqtt:` → the local `mosquitto` broker used by ESPHome/Tasmota/Zigbee2MQTT gateways

## See also

* [Home Automation overview](../HOME-AUTOMATION.md) — the whole subsystem
* [MATTER.md](../MATTER.md) — Node-free Matter architecture
* [matter-bridge](matter-bridge.md) — the native Matter WebSocket server
* [domoticz](domoticz.md) — the alternative, fully built-in hub
