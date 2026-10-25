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

Create target/release/ble2uart-gateway:

```sh
cd make/pkgs/ble2uart_gateway/src
cargo build --release
```

Initialize config.yaml:

```sh
target/release/ble2uart-gateway --write-default-config ./config.yaml
```

Run target/release/ble2uart-gateway in foreground:

```sh
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

## Codec Selection

The binary embeds `spec/codec.yaml`, so no external codec file is required.
An external file is an **overlay**, not a complete replacement: structures and
formats with matching names replace the embedded definitions, new names are
added, and other embedded definitions remain available.

| Invocation | External codec selection |
|---|---|
| No `--codec`, no adjacent `codec.yaml` | Embedded definitions only |
| No `--codec`, adjacent `codec.yaml` exists | Embedded definitions plus that file |
| `--codec /path/to/mycodec.yaml` | Embedded definitions plus this file; adjacent `codec.yaml` is ignored |

"Adjacent" means the directory containing the gateway configuration selected by
`--config`, not the current directory or the executable directory. With the
default configuration path it is `/etc/ble2uart-gateway/codec.yaml`.
Explicit relative paths such as `--codec ./mycodec.yaml` are resolved from the
process working directory. A missing, unreadable or invalid explicitly selected
file is an error; there is no silent fallback to another file. Invalid automatic
overlays also fail rather than being silently ignored.

```sh
# Automatic lookup of ./codec.yaml next to ./config.yaml:
ble2uart-gateway --config ./config.yaml --foreground

# Keep the custom filename, without copying/renaming it:
ble2uart-gateway --config ./config.yaml --codec ./mycodec.yaml --foreground

# Validate both the gateway configuration and the selected codec:
ble2uart-gateway --config ./config.yaml --codec ./mycodec.yaml --check-config

# Use the same selection for offline decoding:
printf '%s\n' D2FC40008A0C0E0B10001101 |
  ble2uart-gateway --codec ./mycodec.yaml --decode bt_home_v2
```

The option also applies to `--encode`, `--benchmark-codec`, `--decode-captures`
and `--web-config inspect`. It does not change `--config`, write a codec path
into the saved configuration, or change another running process. Supply it for
each invocation that needs the custom codec. Restart the daemon to apply codec
changes; no recompilation is needed for layouts using existing codec operations.
New Rust operations or changes to the embedded copy require rebuilding.

To keep automatic lookup while retaining the original filename, create a
`codec.yaml` symlink next to the gateway configuration, pointing to the custom
file. Back up an existing automatic overlay before replacing it. For Freetz
service/CGI deployment and process-local option behavior, see the
[Freetz integration guide](../README.md#select-an-external-codec).

## Firmware Commands While The Daemon Is Running

`--command '<JSON>'` sends a validated request to the running daemon through its
private Unix socket. Use `--command -` to read JSON from stdin. This never opens
the serial device in a second process and does not change saved configuration.
Failures return JSON with `success: false` and a nonzero CLI exit status.
The same operations are available in the authenticated Freetz **Commands** tab.

The target firmware is the host-managed GATT revision of the
[`esp32-c3` branch of ADV_BLE2UART](https://github.com/pvvx/ADV_BLE2UART/tree/esp32-c3/source/esp32ble/ble50_scan),
under `source/esp32ble/ble50_scan`, not the older scanner under
`master/source/esp32-c3`. GATT requires open flag `1`, subscription op `13`,
and typed operation-completion events (`CONN` status `0x84`); a branch name or
version number alone does not establish these capabilities. The gateway waits
for the initial typed MTU completion before allowing application commands.
Older firmware fails explicitly; it is not silently treated as compatible.
Requests follow the C parser, including the reserved zero before attribute handles.

```sh
ble2uart-gateway --command '{"command":"diagnostic","name":"version"}'
ble2uart-gateway --command '{"command":"diagnostic","name":"gpio-read","pin":9}'
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","addr_type":0,"operation":"discover"}'
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"read","handle":42}'
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"write","handle":42,"value":"0102"}'
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"exchange","uuid":"1F1F","value":"55","prefix":"55","codec":"cfg","offset":1}'
ble2uart-gateway --command '{"command":"txadv-start","phy":0,"interval_units":160,"data":"020106"}'
ble2uart-gateway --command '{"command":"txadv-stop"}'
ble2uart-gateway --command '{"command":"scan-start"}'
```

### Scan Lifecycle

- Diagnostics pause an active scan, then restore its
  previous PHY/window settings without clearing MAC filters, on success **or
  error**. GATT suspends scanning and daemon-configured TXADV until the connection
  is closed. An inactive scan stays inactive. Discovery's filters and remaining
  duration are preserved, including throughout an interactive GATT session.
- A one-shot `gatt` command connects, performs the operation, then disconnects
  or cancels an unsuccessful open. `gatt-open` instead holds one host-managed
  connection for multiple `gatt` requests carrying its ownership token;
  `gatt-close` releases it. A pre-existing connection is never taken over.
- GATT cleanup runs after ATT errors, application timeouts, unexpected disconnects,
  notification overflow, idle expiry, serial failure and daemon shutdown.
  Scan/TXADV restoration follows confirmed disconnection/cancellation, never an
  uncertain close. Failed cleanup prevents further commands and is retried after
  reopening the link; application writes are **never automatically retried**.
- TXADV is restored with its original PHY, interval and payload, even on error.
  Firmware status does not expose the payload: an active TXADV not configured
  by this daemon is rejected before opening GATT. Explicitly stop that external
  transmission first rather than guessing the data to restore.
- **Starting TXADV stops scanning indefinitely for this daemon session.**
  It also cancels Discovery. Stopping TXADV, running diagnostics, or reconnecting
  the serial link does **not** restart scanning. If a TXADV start result is
  uncertain, scanning remains suppressed and TXADV is conservatively considered
  active until explicitly stopped.
- `scan-start` explicitly stops any daemon-tracked TXADV and reapplies the
  configured filters/scanner. `scan-stop` explicitly disables scanning without
  stopping TXADV. `txadv-stop` only stops transmission. Discovery cannot start
  while TXADV is active; stop TXADV first.
- These overrides are runtime state, not persisted YAML: an explicit service
  restart returns to the saved scanner configuration. Stop TXADV before
  restarting the service; the adapter may retain advertising across host restarts.
- Restoration/cleanup failures are reported, not disguised as command success.
  The daemon retries connection recovery after reopening the link. Commands
  themselves are never automatically retried.

`--control status` includes a `radio` object with `scanning`, `scan_suppressed`,
`txadv_active`, `recovery_required`, `gatt` and `gatt_error`. An active `gatt`
includes peer, MTU, subscriptions, queued notification count and remaining idle
time, but **not its ownership token**. These represent daemon-tracked/requested
state, not a guarantee that every radio packet was received. Scan suspension
necessarily loses advertisements transmitted during that interval. Requests
are serialized; other control requests wait while an operation is running.
Between operations, status and frontend workers remain available, while other
radio commands and Discovery start/stop are rejected until the session closes.
The serial reader continues collecting events.

### Command Parameters And Confirmation

Diagnostics are read-only queries: `info`, `version`, `uart`, `rfsdk`, `vbat`,
`gpio-events`, `gpio-status`, `gpio-read`, `analog-read`, `connection-status`,
`txadv-status`. GPIO queries accept `pin`. Results include raw response hex and,
where applicable, firmware metadata.

One-shot GATT accepts `mac`, `addr_type` (0 public, 1 random), `coded` (default
false), `operation`, and `timeout_ms` (100-30000, default 10000).
For an open session, replace all peer parameters with `session`.
`gatt-open` accepts the same peer/timeout fields and `idle_timeout_ms`
(1000-300000, default 60000). Successful operations renew the idle timeout;
incoming notifications alone do not keep an abandoned client connected.
Cleanup and radio restoration have separate bounded timeouts.

For attribute operations, select exactly one nonzero decimal `handle` **or**
`uuid` (16-, 32- or 128-bit UUID). UUID selection discovers services,
characteristics and descriptors on demand; ambiguous UUIDs require a handle.
No fixed ATC handle or adjacent-CCCD assumption is made.

| Operation | Additional fields | Reported confirmation |
|-----------|-------------------|-----------------------|
| `discover` | None | Complete event; up to 512 entries with full UUIDs, handles, properties, service/characteristic parents and raw `data` |
| `read`, `read-descriptor` | `handle` or `uuid`; optional `codec`, `offset` | Typed ATT completion, hex `value`, optional `decoded` |
| `write`, `write-descriptor` | Target, hex `value` | Typed ATT completion; `att_confirmed: true`, **not** application confirmation |
| `write-without-response` | Target, hex `value` | Stack acceptance only; `att_confirmed: false` |
| `mtu` | None | Negotiated MTU result |
| `unpair` | None | Disconnect observed; bond removal remains `security_confirmed: false` |
| `subscribe` | Target, `mode`: 0 disable, 1 notify (default), 2 indicate | Typed registration/actual-CCCD completion |
| `notifications` | Target, optional hex `prefix`, `count` (1-64), `codec`, `offset` | Matching queued/new RXDATA events, each with handle, opcode, sequence and hex value |
| `poll-notifications` | Same fields as `notifications` | Immediately returns available matching events, including an empty list; no notification-wait timeout |
| `exchange` | Target, request hex `value`, notification options, optional `mode` | Subscribe if needed, write with ATT completion, await **fresh** matching application notifications |
| `patch` | Exchange fields plus `codec`, JSON `patch`, optional `write_offset`, `write_prefix` | Query, decode, validate/merge, encode, write, await and verify the application response in the **same connection** |

Writes carry at most `min(MTU - 3, 56)` bytes, or 58 for writes without
response. Before MTU negotiation the ATT limit is 20. Values are never silently
truncated or padded. Empty raw writes are allowed if the peripheral accepts them.
Unknown fields, invalid addresses, odd/nonhex values and oversized requests fail
before scanning is changed.

An ATT Write Response is distinct from an ATC command response. `exchange`
waits for RXDATA on the selected characteristic, including when it arrives
**before** the ATT completion. Its optional `prefix` filters command IDs without
mistaking older queued responses or another characteristic's data for the reply.
Use `notifications` to drain previously queued events. Complete notification/
indication values up to 197 bytes are retained; the queue is bounded to 128
events and overflow closes the session explicitly, without silently dropping
data. This protocol has no transaction IDs: serialize requests and close after
timeouts. Multiple notifications are returned separately, not blindly concatenated
or fragmented. Interactive pairing and firmware flashing are not implemented.

Bleak clients use `poll-notifications` to keep an idle subscription open without
triggering the ordinary notification-wait timeout that closes a session.
The private control socket also accepts
`{"action":"advertisement-events","after":0}`: it returns `events`, `cursor`
and `dropped` from a bounded 256-report ring. Each event includes its sequence,
MAC, address type, RSSI and raw advertisement data. Subsequent requests pass the
returned cursor as `after`; readers have independent cursors, and a nonzero
`dropped` explicitly reports lost history. This API does not start discovery,
change filters or consume another frontend's reports.
See the [local ATC Python package](../../../../atc_mi_interface/README.md)
for the native, dedicated UART and shared gateway Bleak backends.

TXADV accepts `phy` (0 legacy 1M, 1 extended 1M, 2 coded),
`interval_units` (32-65535, in 0.625 ms units), and hex `data` (at most 31 bytes).
It periodically broadcasts until explicitly stopped; it is not an addressed
GATT write, and only devices implementing that advertisement protocol will act
on it. GATT temporarily suspends/restores daemon-configured TXADV.

### Persistent Sessions And ATC Configuration

The separate [Construct schema review (Italian)](../ATC_CONSTRUCT_REVIEW.md)
documents required Python codec revisions and the distinction between
native Xiaomi payloads and ATC command responses.

See the Italian [ATC parameter and patch reference](../ATC_PARAMETERS.md)
before choosing a sensor schema. Recent firmware repurposes legacy `cfg`
fields, and the upstream source examined there has a configuration-notification
length discrepancy that strict patch decoding intentionally rejects.

The **Commands** tab offers Open / operation in open session / Close, generic
attribute controls, notification filters and an editable **Ace JSON patch editor**.
Opening fills the session token automatically. **Read ATC configuration** and
**Apply ATC configuration patch** send the selected request directly after
confirmation, using the selected peer or session. The confirmation and request/
response views show JSON in read-only Ace editors. No additional **Send command**
click is required for these ATC actions; that button handles other operations.
An initial ATC patch enables `bt5phy` and `longrange`. To customize it before
submission, select the `patch` operation or cancel the confirmation, edit the
JSON in Ace, then apply it. Existing edits are preserved. Invalid/empty JSON and
duplicate clicks while a request is running do not send another command.

The daemon must already be running and **stays active** throughout command
execution. These controls never start/stop/restart it or save gateway settings;
an unavailable service produces an explicit error. Leaving the page attempts a
best-effort close; the daemon's idle timeout is the independent cleanup guarantee
if the browser closes, crashes or loses its response. A token can also be pasted
into another CLI/CGI client explicitly; do not run concurrent application exchanges.

For example, open once and copy `result.session` into `TOKEN`:

```sh
ble2uart-gateway --command '{"command":"gatt-open","mac":"AA:BB:CC:DD:EE:FF","idle_timeout_ms":60000}'
TOKEN='paste-the-returned-32-digit-token'
ble2uart-gateway --command "{\"command\":\"gatt\",\"session\":\"$TOKEN\",\"operation\":\"discover\"}"
ble2uart-gateway --command "{\"command\":\"gatt\",\"session\":\"$TOKEN\",\"operation\":\"subscribe\",\"uuid\":\"1F1F\"}"
ble2uart-gateway --command "{\"command\":\"gatt\",\"session\":\"$TOKEN\",\"operation\":\"exchange\",\"uuid\":\"1F1F\",\"value\":\"55\",\"prefix\":\"55\",\"codec\":\"cfg\",\"offset\":1}"
ble2uart-gateway --command "{\"command\":\"gatt-close\",\"session\":\"$TOKEN\"}"
```

To enable Coded advertising on a compatible **LYWSD03MMC with ATC 4.2+**, the
following one-shot example reads and updates within one connection:

```sh
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"patch","uuid":"1F1F","value":"55","prefix":"55","codec":"cfg","offset":1,"write_offset":1,"patch":{"flg2":{"bt5phy":true,"longrange":true}}}'
```

For an already open connection, replace `mac` with `session`. The ATC `0x55`
notification starts with command ID and firmware version. `offset: 1` removes
the command ID before decoding `cfg`; `write_offset: 1` omits the **response-only
firmware version** when writing `55 + parameters`, matching the Python interface
and Telink flasher. Other protocols can specify another `write_prefix` (default:
request `value`) and offsets; no command-ID table or fixed config byte offsets
are embedded in the GATT engine.

`patch` accepts only existing, type-compatible fields. Before committing it
requires full-byte consumption and an **exact decode/encode roundtrip** of the
original response; unknown tails, lossy conversions, changed layouts and edits
to omitted/computed fields are refused without a configuration write. This is
intentional: use a firmware-matched external codec rather than overwriting
unmodeled fields. Raw writes remain available for protocols not described by the
codec, with explicit caller responsibility. A verified patch confirms the
requested fields in the application response, not persistence across power loss.

The embedded `codec.yaml` contains `cfg`, `trigger`, `comfort_values`, time and
other structures from `atc_mi_construct.py`. The Python command-ID catalogue
lives separately in `atc_mi_config.py` and is **not** generated into this codec.
Generic writes/exchanges support those and newer commands without a gateway
update; select the appropriate schema/offsets or inspect raw notifications.
Command support, field meaning, persistence and reboot requirements depend on
the installed sensor firmware. If it requires an ATC reboot-on-disconnect, send
an explicit raw `write` of `72` before closing; no reboot is inserted implicitly.

After changing PHY, close and use Discovery (1M + Coded) or a configured Coded
scan to check the **received device advertisements**. Firmware PHY values
`primary=3` and/or `secondary=3` indicate Coded. Neither a successful `0x55`
reply nor connecting with `coded: true` proves that Coded advertisements are
actually received. An ESP32-C3 plus real sensor test is still required.

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
filesystem requirements. Without optional history maintenance the DB grows.

### Progressive History Maintenance

An optional thread inside the gateway archives and consolidates history; no
cron, external process or database server is required. It is disabled by default.
Freetz users can configure every setting and age band graphically under
**Settings → Frontends → SQLite → Retention policies**. Save and explicitly
restart to apply changes. The standalone YAML/CLI uses the same schema and
validation as reception and the CGI:

```yaml
frontends:
  sqlite:
    enabled: true
    path: /absolute/path/on/local-storage/readings.sqlite3
    maintenance:
      enabled: true
      counter_mode: discard
      interval_s: 300
      batch_size: 100
      max_work_ms: 100
      raw_retention_s: 600
```

Omitting `policies` loads all built-in presets. Setting it explicitly replaces
that list. Each policy has `mac` (empty = all devices), `attribute`, `mode`
(`keep_all`, `discard` or `progressive`) and `tiers`, an ordered list of
`{max_age_s, sample_interval_s}`. A specific MAC/attribute overrides the global
attribute policy. Attribute and unit identify separate measurement series.

The temperature preset is:

| Sample age | Sample interval |
|------------|-----------------|
| 0–10 minutes | Every sample |
| 10 minutes–1 hour | 60 seconds |
| 1 hour–1 day | 150 seconds (two intervals per five minutes) |
| 1 day–1 week | 1 hour |
| 1–8 weeks | 4 hours |
| 8 weeks–24 months | 6 hours |
| Older | Delete |

Battery percentage (`battery_level`, `battery`) and voltage (`battery_v`,
`voltage`) use much coarser presets: 15 minutes until one hour old, one hour
until one day, four hours until one week, one day until eight weeks, then
48 hours until 24 months, followed by deletion. A month here is 365/12 days;
24 months are 730 days, not calendar-month boundaries.

Intervals retain the latest **remaining real sample** in each UTC-aligned
bucket: no averages, interpolation, min/max columns or synthetic readings.
Progressive thinning is irreversible; changing bands cannot reconstruct samples
removed by an earlier policy. Age limits must strictly increase, intervals must
not decrease, and `sample_interval_s: 0` keeps every sample in that band.
Complete raw frames remain for at least `raw_retention_s`, so that horizon is
also a lower bound on full-resolution retention.

**Recognized counters are excluded from consolidated history by default.**
`counter_mode: discard` covers `counter`, `packet_id`, `count_id`,
`count_i/count_s/count_m/count_l` and `counter8/16/32`, including unsigned values.
It also applies to existing policy lists that omit those attributes. Choose
`keep_all` to retain counters globally, or override an individual attribute/MAC
with `keep_all`, `discard` or a progressive policy. Recent complete raw frames
still contain these fields until `raw_retention_s` expires.

Other unconfigured attributes and discrete states keep every sample forever.
Known contact/GPIO/discrete attributes reject both progressive and discard
policies. Boolean, text, JSON and null values are never pruned; unsigned values
can be discarded but are not progressively thinned. Custom numeric discrete
attributes should use `keep_all`.

**Back up the database before enabling.** First activation extends schema 1 to
schema 2 transactionally, without rewriting existing samples. The thread moves
older frames in atomic chunks into these normalized tables before deleting the
source frame and its measurements:

- `history_devices(mac, sensor_name, device_json)` stores shared device metadata.
- `history_series(id, mac, attribute, unit)` identifies each independent series.
- `history_samples(id, series_id, received_at_ns, type, value_json)` stores one
  typed JSON value per sample, without sparse sensor columns. Integer precision,
  booleans, repeated attributes and original timestamps are preserved.

The `history` view combines these samples with measurements in recent full
frames, without double counting across a transfer. Use it for complete history:

```sql
SELECT received_at_ns, mac, sensor_name, attribute, unit, type, value_json
FROM history
WHERE mac = 'AABBCCDDEEFF' AND attribute = 'temperature'
ORDER BY received_at_ns DESC;
```

`frames`/`measurements` contain only the recent complete-frame horizon after
maintenance catches up. The archive intentionally does not retain old full
packet/radio JSON. Disable maintenance to stop further transfers/deletions;
existing archives remain accessible through `history`, but are not expanded
back into full frames. Older schema-1-only binaries cannot reopen schema 2:
restore the pre-migration backup if downgrading.

The thread uses a separate connection, small transactions and SQLite progress
cancellation. Receiver and maintenance share a write gate that prioritizes
waiting receiver batches; maintenance yields rather than competing with the
receiver's SQLite transaction. External writer contention is also a normal
short retry, not a warning on every collision. If write access remains unavailable
for 30 seconds, a warning is emitted at most once per minute. Other maintenance
errors are likewise time-throttled, even if successful chunks occur between them.
`batch_size` is 1–1000
frames transferred or samples examined per series/chunk, including samples that
are retained. An indexed cursor resumes the next chunk rather than rescanning
the start of a long series. `max_work_ms` is a
10–1000 ms execution budget. Incomplete transactions are rolled back before
write access is released. SQL cancellation cannot bound a stalled
filesystem/fsync. An unsynchronized clock before 2020 postpones maintenance.
Shutdown wakes the thread rather than waiting for `interval_s` (1–86400 seconds).

Background deletion makes pages reusable; it does not promise a smaller `.db`
file. No disruptive automatic full `VACUUM` is run. Retention is eventual, not
a hard deletion deadline: a backlog, storage error or insufficient work budget
can postpone it. Rendering and rollup charts remain the external reader's job.

### Sensor dashboard CGI

The configuration CGI also exposes `--web-config log` (`{"lines":N}` on stdin,
at most 2000, 64 KiB read from the end of the file multiplied by nothing: only
the tail is read), which the **Log** tab uses to show
`/tmp/rc.ble2uart_gateway.log`.

`ble2uart-gateway --portal` is a CGI program (`portal.rs`) that serves both the
HTML shell and the JSON API; it is reached through the shell wrapper
`usr/lib/cgi-bin/ble2uart_gateway/portal.cgi`, which sources
`/usr/lib/libmodcgi.sh` for the standard freetz authentication and then execs the
binary. The mode never writes: it opens the database read/write (so a WAL file
can be recovered) and immediately sets `PRAGMA query_only=ON`.

| Request | Meaning |
| --- | --- |
| `?action=page` (default) | HTML shell, CSS/JS loaded from `/ble2uart_gateway/portal.*` |
| `?action=info` | schema version, table counts, file/WAL sizes, own RSS |
| `?action=catalog` | devices, series (attribute/unit/kind), latest value and timestamps |
| `?action=series&mac=..&attribute=..&unit=..&kind=numeric\|boolean&range=<s>` | bucketed points `[unix_ms, average, samples]`; `range=0` means the whole series |
| `?action=series&...+&from=<ns>&to=<ns>` | explicit window (used by the browser zoom); it wins over `range` |

The catalog merges two independent sources, so nothing is hard-coded and the
dashboard also works before history maintenance has ever run:

* `history_devices` / `history_series` for consolidated series, including
  attributes that disappeared from recent frames;
* the newest frames of each device (`frames_mac_time`, at most
  `RAW_CATALOG_ROWS` measurement rows) for raw-only attributes.

The newest value of a series is the newer of the last `history_samples` row and
a raw lookup that walks `frames_mac_time` backwards with
`INDEXED BY frames_mac_time` and stops at the first hit; it therefore does not
scan the whole `measurements` table when maintenance is disabled. Charts are
bucketed in SQL per series and merged with sample-count weighting, so archived
and raw data can be combined without interpolation.

Static assets stay plain files (`portal.css`, `portal.js`, referenced with a
version query so a caching httpd serves new copies) and draw the chart on a
canvas without any library: the page works on a router without Internet access.
Hovering draws a crosshair plus one marker per series; dragging selects a time
window, `+`/`−`/reset change it and `⛶` uses the Fullscreen API. Measured on the FRITZ!Box 7590 AX against the production database, one
request peaks at about 7 MB RSS; the equivalent PHP 8.5 `php-cgi` script with
`pdo_sqlite` peaks at about 19 MB (about 14 MB for PHP alone before doing any
query), which is why the portal is part of the Rust binary rather than a PHP page.

## Device Availability Monitoring

Availability monitoring is configured only through each device's `rules` list,
where a rule can also carry a `recovery_message` (sent instead of the automatic
recovery text) and a `webhook.provider` of `ntfy`, `gotify` or `rest`; the REST
provider adds `method`, `content_type`, `body` and `header` with `{event}`,
`{message}`, `{title}`, `{device}`, `{attribute}`, `{value}`, `{unit}` and `{id}`
placeholders.
or **Devices → Edit → Availability monitoring** in the CGI. There is no global
rule engine, workflow library or Settings-tab webhook configuration.

Add, remove, edit, enable or disable rules independently. Each rule selects an
`attribute`, a positive `stale_after_s` timeout and its own complete `webhook`
configuration. New rules default to temperature/600 seconds and start disabled
until configured. The device's own Enabled switch also controls its monitors.
Changes enter the device draft first; Save configuration and explicitly restart
the service to activate them.

```yaml
devices:
  - mac: AABBCCDDEEFF
    label: Thermometer
    rules:
      - id: temperature_missing
        enabled: true
        attribute: temperature
        stale_after_s: 600
        startup_grace_s: 600
        notify_recovery: true
        webhook:
          provider: ntfy
          url: https://ntfy.example.org/thermometers
          priority: 4
          tags: thermometer
          max_attempts: 1
```

Rule IDs are stable and unique within one device; the CGI generates them.
Rules may share an ID across different devices. The lightweight internal worker
checks once per second and applies only the timeout/recovery transition.

Each rule can set `message` and `tgs`. A nonempty `message` is transmitted
verbatim for alerts, recoveries and that rule's explicit webhook test. Blank or
whitespace-only text uses the corresponding automatic message. Multiline UTF-8
text is supported up to 4096 bytes. A nonempty `tgs` replaces `webhook.tags`
for ntfy; leaving it blank uses the webhook's tags. The override is limited to
256 ASCII bytes and is not used by Gotify.

The device availability status uses a read-only Ace JSON editor. Webhook
configuration is automatically expanded when its URL is missing, including for
a newly added disabled rule; configured destinations start collapsed.

Freshness is recorded from valid decoded measurements before `expose` filtering,
independently of SQLite batching, retention and merged last-value snapshots.
An unchanged temperature received again is fresh; a battery-only packet,
unknown device, unsupported packet or decoding failure does not refresh it.
Devices that have never produced a reading can also expire after startup grace.
Ensure the scanner/duplicate-filter settings allow the expected reporting rate.

An active episode produces one stale event, not a notification on every check.
An undelivered stale event is cancelled when readings resume; a recovery is sent
once only when the corresponding stale event was delivered and
`notify_recovery` is true. Stable device/rule/attribute identities preserve
episode state across restart and migration. There are no periodic reminders.

The internal `availability_state_file` defaults beside the configuration as
`automation-state.json`; it is not an additional Settings control.
It records last readings, episodes, pending deliveries and status in bounded,
atomic 0600 JSON writes with an exclusive process lock. The directory must
already exist. Prefer a persistent USB directory: `/tmp/flash` is only archived
by Freetz saves/clean stop, so a power failure can lose newer episode state.
Invalid/corrupt state is rejected, not silently reset into duplicate alarms.
Freshness is monotonic while running; saved reception timestamps restore age
after restart. Status is available inside the device's availability editor.

Older global automation settings are read once and distributed to the matching
devices, preserving their HTTPS destination and enable state. The global block
and workflows are not written back. Old unused per-device derived-state
definitions are converted to disabled availability rules, never activated
implicitly. Private destinations stay only in the router's configuration.

### HTTPS Notifications

Select the provider and configure the complete destination:

- **ntfy:** `https://ntfy.example.org/thermometers`, optional bearer token.
- **Gotify:** `https://gotify.example.org/message`, application token required.

Tokens are masked in the CGI and sent in headers (`Authorization` or
`X-Gotify-Key`), never in URL queries or persisted episode state. HTTPS is
mandatory. Certificates/hostnames are verified using bundled public roots,
or the optional absolute `ca_file` PEM path for a private CA. Redirects and
proxy use are disabled. No insecure certificate-verification option exists.
Enable `ipv4_only` for destinations whose IPv6 address is unreachable from the
router; it restricts address resolution without changing TLS verification.
Each rule's **Test webhook** confirms and sends one test using that rule's draft;
it neither saves configuration nor starts/restarts a service.

Defaults are `timeout_ms: 5000`, `max_attempts: 1`, `retry_s: 60` and a bounded
internal queue of 256 events. Attempts are durably reserved **before** network I/O.
Priority is configurable (1-5, default 4); optional ntfy tags default to
`thermometer`. These settings contain no destination-specific personal data.
The default therefore avoids replaying an ambiguous request after a crash,
but deliberately does not guarantee delivery if the network/server fails.
Raising `max_attempts` explicitly enables bounded retries: a lost response can
then cause duplicate messages because ntfy/Gotify do not promise to honor the
stable `Idempotency-Key` sent by the gateway. No retries run in the serial reader.
Pending and last-error status exclude tokens; raw YAML exports remain private.

Save configuration and explicitly restart to apply rules or destination changes.
The worker cannot report its own process death or router power loss; that still
requires independent supervision. Missing-adapter failures can expire multiple
per-device watches; this first implementation does not group them into one
gateway-level event.

The hardware-free integration test uses the existing PTY emulator and a local
HTTPS server with a temporary CA, never the live radio or third-party services:

```sh
python3 tools/test_automation.py --binary target/debug/ble2uart-gateway
```

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
