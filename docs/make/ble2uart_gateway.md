# ble2uart_gateway 0.1 (MySensors/MQTT/Matter/InfluxDB 3/SQLite)
  - Package: [master/make/pkgs/ble2uart_gateway/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/ble2uart_gateway/)
  - Steward: Ircama
  - Provides: `/usr/bin/ble2uart-gateway`, init script `rc.ble2uart_gateway`, web page `/cgi-bin/conf/ble2uart_gateway`
  - Configuration: `/mod/etc/conf/ble2uart_gateway.cfg` (service) and `<store>/ble2uart_gateway.yaml` (devices, bind keys, rules, front-ends); default store `/tmp/flash/ble2uart_gateway`
  - Log: `/tmp/rc.ble2uart_gateway.log`

`ble2uart_gateway` is a native Rust gateway for an ESP32-C3 USB adapter running
pvvx ADV_BLE2UART (`esp32-c3/ble50_scan`). It decodes BLE advertisements
(ATC1441, MiBeacon, BTHome v1/v2 and their encrypted variants) and publishes the
values through MySensors TCP (Domoticz), MQTT, a Matter bridge, InfluxDB 3 and
an optional local SQLite history frontend.

The package documentation lives next to the sources:

  - [Freetz-EVO integration](../../make/pkgs/ble2uart_gateway/README.md): web
    interface, service settings, front-ends, MAC filters, diagnostics.
  - [Portable daemon](../../make/pkgs/ble2uart_gateway/src/README.md): the
    standalone `ble2uart-gateway` for ordinary Linux hosts, Cargo features,
    Matter DNS-SD backends, logging options.

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
