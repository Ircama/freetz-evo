# ble2uart_gateway 0.1 (MySensors/MQTT/Matter/InfluxDB 3/SQLite)
  - Package: [master/make/pkgs/ble2uart_gateway/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ble2uart_gateway/)
  - Steward: Ircama
  - Provides: `/usr/bin/ble2uart-gateway`, init script `rc.ble2uart_gateway`, web page `/cgi-bin/conf/ble2uart_gateway`, read-only sensor dashboard `/cgi-bin/extra/ble2uart_gateway/portal` (standard freetz login)
  - Configuration: `/mod/etc/conf/ble2uart_gateway.cfg` (service) and `<store>/ble2uart_gateway.yaml` (devices, bind keys, rules, front-ends); default store `/tmp/flash/ble2uart_gateway`
  - Log: `/tmp/rc.ble2uart_gateway.log`

`ble2uart_gateway` is a native Rust gateway for an ESP32-C3 USB adapter running
pvvx ADV_BLE2UART (`esp32-c3/ble50_scan`). It decodes BLE advertisements
(ATC1441, MiBeacon, BTHome v1/v2 and their encrypted variants) and publishes the
values through MySensors TCP (Domoticz), MQTT, a Matter bridge, InfluxDB 3 and
an optional local SQLite history frontend.

The expanded **Startup and storage** section displays the selected YAML path
and lets you choose its directory. **Save configuration** saves the gateway
draft without restarting and archives `/tmp/flash` using `modsave flash`; Freetz
restores that archive at boot. The separate startup/storage save confirms a
restart if the service is running. The misleading framework **Default** action
is hidden; use **Status → restart** to activate saved gateway changes.

**Devices** separates **Discover devices**, **Add manually** and the list filter.
Discovery prefills supported attributes from the selected packet; after entering
an encrypted device's bindkey, use **Detect attributes**. Device edits first enter
the configuration draft and still require **Save configuration**. Frontend groups
show their enabled state, put **Enabled** first and provide contextual **?** help.

**Devices → Edit → Availability monitoring** manages simple per-device rules.
Each rule has its own enable switch, missing-reading timeout, complete HTTPS
ntfy/Gotify configuration and confirmed test button. No global ITTT/workflow
engine or webhook controls appear in Settings. Persistent episode state prevents
repeated stale/recovery alerts; older global configurations migrate to devices.
See the [monitoring guide](../../make/pkgs/ble2uart_gateway/src/README.md#device-availability-monitoring)
for retry/deduplication semantics and private CA support.

The package documentation lives next to the sources:

  - [Freetz-EVO integration](../../make/pkgs/ble2uart_gateway/README.md): web
    interface, service settings, front-ends, MAC filters, diagnostics.
  - [Portable daemon](../../make/pkgs/ble2uart_gateway/src/README.md): the
    standalone `ble2uart-gateway` for ordinary Linux hosts, Cargo features,
    Matter DNS-SD backends, logging options.
  - [ATC parameters and patches (Italian)](../../make/pkgs/ble2uart_gateway/ATC_PARAMETERS.md):
    firmware C/JavaScript comparison, field-by-field examples, version/model
    differences, persistence and codec compatibility.
  - [ATC Construct schema review (Italian)](../../make/pkgs/ble2uart_gateway/ATC_CONSTRUCT_REVIEW.md):
    native Xiaomi versus ATC profiles, required Python schema revisions,
    missing command layouts and reproduced decoding errors.
  - [ATC Python package (Italian)](../../atc_mi_interface/README.md):
    declarative firmware layouts and one Bleak application API with native,
    dedicated UART and shared daemon backends.

Live diagnostic, GATT and TXADV commands are available through the **Commands**
web tab or `ble2uart-gateway --command '<JSON>'`; both use the running daemon's
serial link without stopping or restarting the service. ATC read/patch buttons
send directly after confirmation; the patch is editable in Ace and request/
response JSON is shown in read-only Ace views. GATT supports token-owned
interactive sessions, full attribute
discovery, arbitrary subscriptions, typed ATT completions and filtered
notification request/reply exchanges. Scan, Discovery time and daemon-configured
TXADV are suspended and restored on close, timeout or error. Codec-backed patches
read/modify/verify configuration in one connection, including ATC `0x55`.
TXADV start instead leaves scanning disabled until an explicit `scan-start`
request (or service restart); TXADV stop alone never resumes it.
See the [command reference](../../make/pkgs/ble2uart_gateway/src/README.md#firmware-commands-while-the-daemon-is-running)
for the required host-managed firmware features, payload limits and the
ATC/Coded PHY example. ATT completion and actual Coded advertisement reception
are distinct from the sensor's application response.

## Host build for testing

The daemon also builds and runs on the development host, without the Freetz
toolchain. This is the quickest way to test codec, configuration or front-end
changes, and it is required by the capture replay tool:

```sh
cargo build --offline --manifest-path make/pkgs/ble2uart_gateway/src/Cargo.toml
```

The `--offline` build uses the crates already in the local Cargo cache (filled
by a previous build or by `cargo fetch --manifest-path ...`); drop `--offline`
on the first build. Add `--features freetz` to reproduce the Freetz-EVO profile
(FRITZ!Box interface preference and `/mod/external/usr/bin` helper lookup). The
unit tests run with:

```sh
cargo test --offline --manifest-path make/pkgs/ble2uart_gateway/src/Cargo.toml
```

After building the host binary, the command/scan lifecycle can also be checked
end-to-end without hardware:

```sh
python3 make/pkgs/ble2uart_gateway/tools/test_commands.py
```

The host binary is `make/pkgs/ble2uart_gateway/src/target/debug/ble2uart-gateway`.
`tools/replay_capture.py` feeds it a recorded serial capture through a PTY, so no
ESP32 module is needed:

```sh
python3 make/pkgs/ble2uart_gateway/tools/replay_capture.py /path/to/trace.pickle \
  --binary make/pkgs/ble2uart_gateway/src/target/debug/ble2uart-gateway \
  --interval 0.02 --speed 20 --import-bindkeys --expose-all \
  -- --trace-decode
```

Options after `--` are passed to the gateway. `--expose-all` decodes every
supported attribute and reports missing device configuration (unknown MAC,
missing bind key).

## Firmware build

```sh
make ble2uart_gateway-precompiled
```

The cross build uses the Freetz Rust toolchain (`-Z build-std` for
`mips-unknown-linux-uclibc`) and enables the `freetz` Cargo feature.

### Warnings and completion output

Unused GPIO/GATT protocol helpers are retained with narrowly scoped, documented
`dead_code` exceptions. Other compiler warnings remain enabled.

`make ble2uart_gateway-recompile` runs the package's `-distclean` and
`-precompiled` targets. The latter calls the framework's `_ECHO_DONE`; Cargo's
`Finished release` message only confirms compilation, not staging.

The framework prints `done.` only while its shared `source/.echo_item_1st`,
`source/.echo_item_new` and `source/.echo_item_end` markers all exist. An
up-to-date package can finish without printing it, and simultaneous Freetz
builds in the same tree can clear or consume each other's markers. Avoid
concurrent builds in one checkout. Check the exit status of `make` rather than
using `done.` as a success indicator; the staged executable is under
`packages/target-<toolchain>/ble2uart_gateway-0.1/root/usr/bin/ble2uart-gateway`.
SQLite is bundled and cross-compiled with the target C compiler; no SQLite
server or target shared library is required. Configure its file path explicitly
in Settings/YAML; see the [SQLite frontend guide](../../make/pkgs/ble2uart_gateway/src/README.md#sqlite-history).
SQLite commits a full batch or flushes at the configured interval (default one
second), not only when `batch_size` is reached. Queries of the live database see
committed WAL rows even if the main `.db` modification time is older. Finish a
long-lived read transaction to refresh its snapshot; use the SQLite backup API,
not a copy of `.db` alone, to obtain a consistent database while recording.

Optional **Settings → Frontends → SQLite → History maintenance** starts an
internal maintenance thread, disabled by default. Per-measurement/MAC policies
and all age bands are editable graphically. Temperature has progressive presets;
battery/voltage use much coarser sampling. Recognized counters are discarded
from consolidated history by default; per-attribute/MAC overrides are available.
Other unconfigured readings and discrete states keep every sample. Consolidation retains real samples,
without min/max columns, in related per-measurement series. Back up before
enabling: old full frames are replaced and discarded samples cannot be restored.
Use the schema-2 `history` view for both recent and consolidated readings; see
the [maintenance guide](../../make/pkgs/ble2uart_gateway/src/README.md#progressive-history-maintenance).
