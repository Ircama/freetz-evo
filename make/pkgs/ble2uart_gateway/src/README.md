# BLE2UART Gateway

A standalone Linux daemon for ESP32 adapters running ADV_BLE2UART
(`ble50_scan`). It decodes BLE advertisements and publishes MySensors TCP,
MQTT, standard Matter sensors plus a complete vendor-specific state, and
InfluxDB 3 line protocol and SQLite history.

## Build And Run

Use a current Rust toolchain on Linux with serial-device access, usually through
the `dialout` group. The default build includes Matter; disable default features
for a smaller binary without Matter. SQLite is bundled and needs a C compiler
at build time, but no separate SQLite installation or server at runtime.

```sh
cargo build --release
target/release/ble2uart-gateway --write-default-config ./config.yaml
target/release/ble2uart-gateway --config ./config.yaml --foreground
```

Edit the serial path, enabled devices and frontends before starting. Explicit
`--config` works as an unprivileged user; the default system configuration is
`/etc/ble2uart-gateway/config.yaml`. The private control socket uses
`$XDG_RUNTIME_DIR/ble2uart-gateway` or a per-user temporary directory, and can
be overridden with `BLE2UART_GATEWAY_CONTROL_SOCKET`.

Optional managed broker/controller modes require Mosquitto or matter-bridge;
ordinary MQTT publication and the Matter server do not require those services.
Matter uses development attestation, not certified product credentials.

The Matter SDK is reproducibly pinned to `rs-matter` revision
`c69916a5a78957d46500145486df375acf4ab490`, upstream `main` checked on 2026-10-17.
### Matter DNS-SD Backends

`frontends.matter.mdns_backend` selects the publisher of the Matter DNS-SD
services; `disabled` (or the legacy `advertise: false`) turns it off, for
example for isolated loopback simulations. Direct-IP access stays available in
every mode, and a failing backend is retried every 10 seconds.

| Value | Cargo feature | Notes |
|-------|---------------|-------|
| `builtin` | always built | rs-matter responder on UDP 5353, no system service needed |
| `avahi` | `mdns-avahi` | Avahi daemon over the D-Bus system bus (pure Rust) |
| `resolved` | `mdns-resolved` | systemd-resolved with `MulticastDNS=yes` (pure Rust D-Bus) |
| `zeroconf` | `mdns-zeroconf` | links native Avahi/Bonjour client libraries (`libavahi-client-dev` and libclang to build on Linux) |
| `astro` | `mdns-astro` | macOS/Bonjour `dns_sd` |
| `auto` | default | first compiled backend whose service is reachable (Avahi, resolved, zeroconf, astro), otherwise builtin; a failing backend falls back on the next retry |

`mdns-linux` enables `mdns-avahi` and `mdns-resolved`:

```sh
cargo build --release --features mdns-linux
```

Selecting a backend that was not compiled in is a configuration error that
lists the available ones. With a system daemon, the daemon announces its own
host name; `mdns_hostname` (one DNS label, default `ble2uart-gateway`) applies
to the builtin responder. Builtin interface autodetection prefers interfaces
with a default route and skips container/VPN interfaces such as `docker*`,
`veth*`, `br-*`, `tun*` and `wg*`; set `mdns_interface` to override it. The
builtin responder uses IP TTL/hop limit 255.

The Cargo feature `freetz` selects the Freetz-EVO profile (enabled by the
Freetz package build): FRITZ!Box interface preference and helper lookup in
`/mod/external/usr/bin`. Runtime identifiers are the same in both builds. Without it, helpers such as
`mosquitto` and `matter-bridge` are searched in `/usr/bin` and `$PATH`.

## SQLite History

SQLite is an independent frontend, disabled by default, and can run together
with any of the network frontends. Configure `frontends.sqlite` through the
same YAML/CLI controls as the others:

```yaml
frontends:
  sqlite:
    enabled: true
    path: /absolute/path/on/local-storage/readings.sqlite3
    batch_size: 100
    queue_capacity: 1024
    flush_interval_ms: 1000
    busy_timeout_ms: 1000
```

The path has no default: explicitly select storage before enabling it. Its
parent directory must already exist and be writable. The gateway does not
create parent directories, which avoids silently creating a missing mount
directory on internal storage. New database files are private (0600).
Existing databases must have this gateway's application ID and schema version;
unrelated databases are rejected. Startup fails explicitly if storage or WAL
initialization is unavailable.

Each successfully decoded advertisement for an enabled configured device
creates one `frames` row, independent of `expose`:

| Column | Meaning |
|--------|---------|
| `id` | Monotonically allocated frame ID, not reused after retention deletes |
| `received_at_ns` | Unix nanoseconds captured before enqueueing, not a sensor-provided clock |
| `mac`, `sensor_name`, `wire_format` | Sensor identity and format at reception |
| `state_json` | Complete decoded state, including device metadata, radio/RSSI, decoded payload and measurements; no bindkeys |

All measurements from that frame are stored in `measurements`, linked by
`frame_id`. `ordinal` preserves their order and permits repeated attribute names
in one frame. `attribute` and `unit` identify the measure. `type` selects exactly
one value representation:

| `type` | Column |
|--------|--------|
| `real` | `value_real` (SQLite REAL / double) |
| `integer` | `value_int` (exact signed 64-bit integer) |
| `boolean` | `value_int` (0 or 1, distinguished from integers by `type`) |
| `unsigned` | `value_text` (decimal string for integers above signed 64-bit range, without precision loss) |
| `text`, `json` | `value_text` |
| `null` | All value columns NULL |

Other value columns are NULL by design. CHECK constraints prevent incompatible
combinations. There is no last-value carry-forward: an absent attribute stays
absent from that frame. Complete JSON retains the decoder's representation,
including calculated attributes, rather than labelling them all as raw readings.
Successfully decoded repeats are separate receptions, not timestamp upserts.

For example, query complete frames and typed values:

```sql
SELECT f.id, f.received_at_ns, f.sensor_name, f.mac, f.wire_format,
       m.ordinal, m.attribute, m.type,
       m.value_real, m.value_int, m.value_text, m.unit
FROM frames AS f
JOIN measurements AS m ON m.frame_id = f.id
ORDER BY f.received_at_ns DESC, f.id DESC, m.ordinal
LIMIT 100;
```

A dedicated worker writes bounded batches in transactions. Batch size and
queue capacity count **frames**, not individual measures. Frame metadata and
all its measurements commit together. Write errors retain the pending batch
for retry and are logged; a full queue drops whole incoming frames, with a
logged counter, without blocking serial reception or other frontends. Pending
frames are flushed on orderly shutdown. The memory queue is not a persistent
spool: crashes, forced stops and persistent storage errors can lose uncommitted
frames. Busy timeout is 1-5000 ms; flush interval is 10-60000 ms; batch size is
1-1024 and must not exceed queue capacity (1-16384).

The writer uses WAL and `synchronous=FULL`. Other local processes may query the
same tables, ideally through read-only connections, with a busy timeout and
short read transactions. They see committed frames only. One writer at a time
is allowed: an external maintenance writer must use short transactions and
handle contention. Set `PRAGMA foreign_keys=ON` on maintenance connections so
deleting a frame also deletes its measurements. Use SQLite's backup API rather
than copying only the main file of a live database; do not delete its WAL/SHM.

Prefer local USB ext4 storage with reliable locking/shared memory, not a network
share or continuous writes to router internal flash. WAL does not bypass
filesystem requirements. Retention, downsampling and rendering are **not**
performed automatically by this frontend; without maintenance the DB grows.

## Logging

Measurement logs include the configured child number, parameter name and decoded
unit, for example `child 0: temperature=16.08 °C` or
`child 3: battery v=3.01 V`. Unitless values such as GPIO states have no invented
unit. Child numbers are per-device mappings from `expose`; logging does not
change child IDs or any MySensors, MQTT or Matter payload.

`--log-color auto|always|never` colors severity levels, device labels (cyan)
and complete parameter/value/unit descriptions (yellow). The default `auto`
colors only the selected output terminal, not files or pipes, and respects
nonempty `NO_COLOR` and `TERM=dumb`. `always` explicitly forces ANSI output;
`never` disables it. `BLE2UART_LOG_COLOR` supplies the same setting when the
command-line option is absent. Ordinary redirected service logs stay plain;
following an existing plain log with `tail` does not add colors.

Use `--foreground --log-color auto` for an interactive instance, or
`--log-color always` when the receiving terminal/viewer explicitly supports
ANSI colors. Do not start a second instance on the production serial device.

## Parallel Applications

MySensors accepts multiple TCP controllers and replays presentation/latest
values to newcomers. MQTT supports multiple subscribers through the configured
broker; every application must use a distinct MQTT client ID. Multiple
applications can share the optional matter-bridge WebSocket controller.
Independent Matter controllers need authorized commissioning and separate
fabrics, subject to SDK session/subscription limits. A connected Domoticz does
not take an exclusive frontend connection. The physical serial device itself
must have only one gateway owner; do not run two daemon instances on it.

## Capture Replay

The standard-library Python tools `replay_capture.py` and `capture_trace.py`
live beside the Freetz integration in this repository. They create a PTY,
emulate scanner commands/CRC/MAC filters and replay the archived advertisement
bytes through the normal daemon, with no alternate decoder.

```sh
python3 tools/replay_capture.py trace.pickle --binary ./target/release/ble2uart-gateway --interval 1 --speed 2
python3 tools/replay_capture.py trace.pickle --binary ./target/release/ble2uart-gateway --config ./config.yaml --timing recorded
python3 tools/replay_capture.py trace.pickle --no-launch --pty-link /tmp/ble-replay.tty --repeat 0
```

In PTY-only mode start the daemon separately with `--serial /tmp/ble-replay.tty`.
Recorded timing requires actual monotonic timestamps in every record; gallery
archives without times use explicit fixed intervals. `--repeat 0` repeats until
interrupted. Missing MACs require `--mac`; oversized packets are rejected, not
truncated. Pickles use a restricted type whitelist, not unrestricted unpickling.

The supervisor copies configuration privately and disables all frontends unless
`--allow-frontends` is explicitly supplied. Enabling them can publish simulated
values: use isolated brokers/ports, never production automation. Matter always
uses a private simulation fabric without mDNS or the managed Domoticz controller.
Capture bindkeys are not imported automatically; `--import-bindkeys` permits
them only in a generated private configuration. Original files are not changed.
Generated devices expose temperature (child 0), humidity (child 1), battery level
(child 2) and flooding (child 3), so flood alarms appear in ordinary replay logs.
Existing device configurations retain their own `expose` mappings; include
`flooding` there to log flood alarms when replaying with `--config`.

Use `--expose-all` to add every gateway-supported measurement to each enabled
device's private `expose` list, preserving existing explicit and implicit child
IDs. The supported list comes from the binary, not a second Python decoder.
Stderr lists the missing exposures added and warns about captured devices without
an enabled configuration or archived keys absent from the configuration. It does
not enable disabled devices, add missing devices to an existing device list,
import keys without permission, or modify the source configuration. Not every
device transmits every supported measurement. The gateway's 200-exposure total
limit still applies; exceeding it rejects the simulation explicitly.

Gateway logging/trace options can follow `--`, or be passed as repeated
`--binary-arg` tokens:

```sh
python3 tools/replay_capture.py trace.pickle --binary ./target/debug/ble2uart-gateway --import-bindkeys --expose-all -- --trace-decode --log-level debug
python3 tools/replay_capture.py trace.pickle --binary ./target/debug/ble2uart-gateway --binary-arg=--log-color --binary-arg=always
```

`--trace-decode` also displays decoded fields that have no supported exposure.
Forwarding is limited to logging/trace options: configuration, serial-device and
alternate command overrides are rejected to preserve simulation isolation.
These options and `--expose-all` require supervisor mode, not `--no-launch`.
Rebuild the binary after updating the supported-attributes API used by
`--expose-all` (`--web-config attributes`).

## Freetz Integration And Publishing

The Freetz-EVO package, CGI, service script and settings are named
`ble2uart_gateway` and install this binary as `/usr/bin/ble2uart-gateway`.
Runtime identifiers are platform independent: MQTT client ID/base topic
`ble2uart-gateway`, Home Assistant unique IDs `ble2uart_<MAC>_...`, Matter
vendor `ble2uart` and mDNS host `ble2uart-gateway.local`.

For a separate repository, this directory is the Cargo project root: include
its Cargo files, `src`, `spec` and `tests`, plus the Python tools under `tools`.
Include the existing license text and attribution from the parent project;
the Cargo manifest retains EUPL-1.2. Publishing a repository is a separate step.