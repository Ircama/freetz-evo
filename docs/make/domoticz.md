# Domoticz 2026.4
  - Homepage: [https://www.domoticz.com/](https://www.domoticz.com/)
  - Changelog: [https://github.com/domoticz/domoticz/blob/development/History.txt](https://github.com/domoticz/domoticz/blob/development/History.txt)
  - Repository: [https://github.com/domoticz/domoticz](https://github.com/domoticz/domoticz)
  - Package: [master/make/pkgs/domoticz/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/domoticz/)
  - Steward: Ircama

  - Depends on: boost (`libboost_thread`), zlib, curl, openssl, sqlite, lua, libusb 0.1 (`libusb-0.1.so.4`), libatomic, mosquitto (`libmosquitto`), python3
  - Provides: `/usr/bin/domoticz` plus the web UI assets in `/usr/share/domoticz/` (`www`, `dzVents`, `plugins`, `scripts`)
  - Web interface: `http://fritz.box:8080/` (port configurable)
  - Externalization: supported for the binary

Domoticz is a lightweight home automation system. It lets you monitor and control lights, switches, sensors, thermostats, media players and many other devices from a web browser, with automations written in Lua (dzVents event scripts) or in Python (plugins).

## Freetz integration

### Configuration

The package uses the Freetz configuration framework. Defaults live in `/etc/default.domoticz/domoticz.cfg` (linked to `/mod/etc/default.domoticz/domoticz.cfg`), the values saved from the web interface end up in `/mod/etc/conf/domoticz.cfg`. Every variable is exported, so all of them appear in the Freetz configuration page.

| Variable | Default | Meaning |
|---|---|---|
| `DOMOTICZ_ENABLED` | `no` | Start the daemon when the box boots |
| `DOMOTICZ_USERDATA` | `/var/media/ftp/domoticz` | Folder for `domoticz.db`, logs and the self-signed SSL certificate. Must be on persistent storage |
| `DOMOTICZ_WWW_PORT` | `8080` | HTTP port of the web interface (`0` disables HTTP) |
| `DOMOTICZ_SSL_PORT` | `0` | HTTPS port (`0` disables HTTPS); the certificate is generated inside `DOMOTICZ_USERDATA` |
| `DOMOTICZ_LOGLEVEL` | *(empty)* | Value passed to `-loglevel` |
| `DOMOTICZ_CONFIG_WAIT` | `120` | Seconds to wait for `DOMOTICZ_USERDATA` at boot (`0` = start immediately), see below |
| `DOMOTICZ_EXTRA_ARGS` | *(empty)* | Extra Domoticz command line options, e.g. `-wwwbind 0.0.0.0` |

`domoticz.save` validates the values before they are stored (ports must be numeric and within 1-49151, `DOMOTICZ_CONFIG_WAIT` must be numeric, a user data folder is required when the daemon is enabled) and warns when the user data folder is not on USB/NAS storage. It deliberately does **not** restart the daemon: the settings are applied on the next start, so editing the configuration never interrupts a running installation.

### Runtime layout

The binary is installed in `/usr/bin/domoticz`, the assets stay in the image below `/usr/share/domoticz/`. The init script always passes the paths explicitly:

```
/usr/bin/domoticz -approot /usr/share/domoticz -wwwroot /usr/share/domoticz/www \
                  -userdata <DOMOTICZ_USERDATA> -log /var/log/domoticz.log \
                  -www <DOMOTICZ_WWW_PORT> [...]
```

This is required because Domoticz derives its startup folder from `/proc/self/exe`: with an externalized binary that path resolves to `/mod/external/usr/bin/`, where neither `www/` nor `dzVents/runtime/` exist. `-approot` and `-wwwroot` override that detection, therefore externalization of `/usr/bin/domoticz` is safe.

The writable state is kept completely separate from the read-only assets:

| Path | Content |
|---|---|
| `/usr/share/domoticz/www` | web interface, jQuery/ACE resources (`-wwwroot`) |
| `/usr/share/domoticz/dzVents/runtime` | dzVents Lua runtime (`-approot`) |
| `<DOMOTICZ_USERDATA>/domoticz.db` | database |
| `<DOMOTICZ_USERDATA>/scripts/dzVents` | user event scripts |
| `<DOMOTICZ_USERDATA>/plugins` | user Python plugins |
| `/var/log/domoticz.log` | daemon log (tmpfs) |

### Boot behaviour

`rc.domoticz` uses the standard modlib helpers (`modlib_start`, `modlib_stop`, `modlib_restart`, `modlib_status`) and registers a daemon entry for the Freetz services page. When `DOMOTICZ_USERDATA` is on `/var/media/ftp/` and `DOMOTICZ_CONFIG_WAIT` is greater than zero, the init script waits for the storage device in a background subshell (the sub-shell re-sources the configuration and calls `rc.domoticz start` afterwards), so a missing or slow USB stick never blocks the boot sequence. With `DOMOTICZ_CONFIG_WAIT=0` the daemon is started immediately.

## Build notes

- Domoticz is built with CMake and requires **Boost** through `find_package(Boost CONFIG REQUIRED COMPONENTS thread)`: the `boost` package also installs a hand-written `BoostConfig.cmake`, because CMake 4 removed the `FindBoost` module.
- The source archive of the `2026.4` tag does not contain the git submodules, but `CMakeLists.txt` adds `extern/{jsoncpp,minizip,jwtcpp,libwebem}` unconditionally. The package downloads the exact commits referenced by the tag as separate tarballs and unpacks them into `extern/`; `-DGIT_SUBMODULE=OFF` keeps CMake from invoking git.
- External libraries come from the tree: SQLite (`USE_BUILTIN_SQLITE=NO`), OpenSSL, zlib, libcurl, libusb, Lua 5.4 (headers below `usr/include/lua`) and `libmosquitto`. `WITH_HTTP_API` of mosquitto is disabled because the tree's libmicrohttpd no longer provides the deprecated basic-auth API.
- Domoticz uses the **libusb 0.1 API** (`libusb-0.1.so.4`, provided by `FREETZ_LIB_libusb0`, whose "current" implementation is the libusb-1.0 compat layer) — upstream prefers the `usb` library over `usb-1.0`, so the config selects `FREETZ_LIB_libusb0`.
- The link needs **`-latomic`**: `libpython3.14.so.1.0` and `libcurl.so.4` list `libatomic.so.1` in `DT_NEEDED`, and ld defaults to `--no-copy-dt-needed-entries`, so the DSO has to be named on the command line. The package therefore passes `-DCMAKE_EXE_LINKER_FLAGS="-latomic"` and selects `FREETZ_LIB_libatomic` (the same workaround used by ffmpeg, cmus and openssl in this tree).
- Feature switches: `-DUSE_PYTHON=YES` (embeds the target `libpython3.14`, built with the host Python 3.14 as `Python3_EXECUTABLE`), `-DWITH_LIBUSB=YES`, `-DINCLUDE_LINUX_I2C=YES`, `-DINCLUDE_SPI=YES`.
- **OpenZWave** (`libopenzwave`, Z-Wave sticks) and **Telldus** (`libtelldus-core`, Tellstick 433 MHz sticks) are enabled: both are optional upstream and their detection aborts the configure step when it fails, so the package points them at the staging tree explicitly (`-DOpenZWave`, `-DOPENZWAVE_INCLUDE_DIRS`, `-DTELLDUSCORE_INCLUDE`, `-DTELLDUS_LIBRARIES`). OpenZWave needs this in any case, because its headers live in `usr/include/openzwave`, a subdirectory that CMake never searches; the library has to be the **master** commit and not the `v1.6` release, because `hardware/OpenZWave.cpp` includes `ValueIDIndexesDefines.h`, a header the release predates. See [`openzwave`](../../docs/libs/openzwave.md) and [`telldus-core`](../../docs/libs/telldus-core.md).
- Domoticz reads the **OpenZWave device database** from `<approot>/Config`, so the `Config` directory of the source tree (855 files, 7.8 MB of XML, about 1 MB in the compressed image) is installed into `/usr/share/domoticz/Config`. The network state is written to `DOMOTICZ_USERDATA` instead, which is why the read-only root filesystem is not a problem.
- A Tellstick needs the daemon of the [`telldus`](../../docs/make/telldus.md) package: `libtelldus-core` is only the client that connects to `telldusd` through the Unix socket `TelldusClient`.
- Python plugins are separate packages and land in `<approot>/plugins`, without touching the Domoticz build: this tree packages **54** of them (energy meters and PV, presence detection, cameras, climate and air, LED and AV devices, MQTT bridges, utilities), one page per plugin under `docs/make/domoticz-*.md`, and it also provides the Python modules some of them need (`python3-urllib3`, `python3-requests`, `python3-paho-mqtt`, `python3-fritzconnection`, `python3-paramiko`, `python3-pynetgear`, `python3-pyserial`, `python3-minimalmodbus`, `python3-feedparser` and the `python-miio` stack with its eleven dependencies). They are all moved to external storage together with `/usr/share/domoticz`. Plugins that would only duplicate a native driver of the Domoticz build are **not** packaged: Onkyo (`HTYPE_OnkyoAVTCP`), Daikin (`HTYPE_Daikin`), LimitlessLED/Milight (`HTYPE_LimitlessLights`), Kodi (`HTYPE_Kodi`) and the Xiaomi gateway (`HTYPE_XiaomiGateway`) are handled by the hub itself; `domoticz-linky` is kept, because it reads the Enedis cloud API and not the local teleinformation stream that `HTYPE_TeleinfoMeter` covers.
- `-DDISABLE_UPDATER=YES` removes the self-updater, which would download host binaries.
- The package needs a device with enough free space (binary ≈ 20 MB unstripped, assets ≈ 25 MB). Externalizing `/usr/bin/domoticz` is recommended.
