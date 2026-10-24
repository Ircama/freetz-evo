# ble2uart_gateway: Freetz-EVO Integration

Native Rust gateway for an ESP32 BLE USB adapter running ADV_BLE2UART
`esp32-c3/ble50_scan`. It decodes advertisements and publishes values through
MySensors TCP, MQTT, a Matter bridge, InfluxDB 3 and SQLite.

The standalone daemon is named `ble2uart-gateway`; see [the portable daemon
guide](src/README.md) for ordinary Linux builds and a separate repository layout.
The Freetz package, its CGI, service script, settings and default store are all
named `ble2uart_gateway`; the installed binary is `ble2uart-gateway`.

For sensor configuration, see the Italian [ATC parameter and patch
reference](ATC_PARAMETERS.md): C/JavaScript comparison, versioned layouts,
all configuration families, examples and current codec limitations.
The separate [Construct schema review (Italian)](ATC_CONSTRUCT_REVIEW.md)
identifies firmware-driven format revisions, native Xiaomi distinctions,
missing command layouts and reproducible codec mismatches.
The local [ATC Python package](../../../atc_mi_interface/README.md) uses only
Bleak's public application API, with native OS, dedicated ADV2UART and shared
gateway backends. The gateway backend leaves this daemon running and restores
its radio state when the GATT session ends.

## Parallel Applications And Simulation

Domoticz does not reserve the gateway exclusively. MySensors accepts multiple
TCP clients; MQTT allows multiple broker subscribers with different client IDs;
the dedicated Matter controller accepts multiple WebSocket clients. Independent
Matter controllers need separate authorized commissioning/fabrics. Resource
limits still apply, and one slow MySensors client can delay fan-out until its
write timeout. Only one process should own the physical serial adapter.

The reusable Python PTY emulator replaces hardware during debugging:

```sh
python3 make/pkgs/ble2uart_gateway/tools/replay_capture.py /path/to/trace.pickle \
  --binary /path/to/ble2uart-gateway --config /path/to/config.yaml \
  --timing fixed --interval 1 --speed 2
```

It uses a private copy of the configuration and disables frontend publishing by
default. Use `--allow-frontends` only with isolated test ports/brokers. For a
separately started daemon, use `--no-launch --pty-link /tmp/ble-replay.tty` and
configure its serial port to that link. `--timing recorded` requires timestamps;
archives without them use `--interval`. `--repeat 0` loops until interrupted.
Pickles are read with a restricted class whitelist; original packets/files are
not edited, keys are not printed, and `--import-bindkeys` is an explicit opt-in
for a generated private configuration. The differential tests and PTY runner
share the same archive reader; frontend integration tests share the emulator.

## Initial Setup

1. Open `/cgi-bin/conf/ble2uart_gateway` in the authenticated freetz interface.
2. Under **Startup and storage**, choose the start type and configuration store.
   Prefer persistent external storage and keep its contents private.
   Apply these startup settings and start the service to initialize a new store.
3. In **Settings**, configure the serial device and MySensors listener. Typical
   values are `/dev/ttyACM0` and `127.0.0.1:5003` respectively.
4. Save and restart the service. In Domoticz, configure a MySensors TCP
   gateway using the same listener address and port.

Both baudrate controls offer the supported presets: 9600, 19200, 38400, 57600,
115200, 230400, 460800, 921600, 1000000 and 2000000. Previously stored non-preset
values remain visible rather than silently changing when the page opens.
**Initial baud rate** applies only when creating a new YAML configuration;
change an existing connection under **Settings → Serial → Baudrate**, then
**Save configuration → Status → restart**. The ESP32-C3 native USB Serial/JTAG
firmware ignores host baudrate; USB/UART adapters must match their firmware.
Startup validation uses the pending settings prepared by the framework, not
stale/unset shell variables. Apply-save reads the newly saved configuration.

**Startup and storage** is expanded and shows the selected YAML path. Its
dedicated save button applies only Freetz startup/storage options and explicitly
confirms the framework's restart of a running service. Save or reload any gateway
draft first. The unrelated framework **Default** button is hidden because it does
not reset the gateway YAML. Service restart is available once, under **Status**.
**Save configuration** writes the validated YAML without restarting; for stores
under `/tmp/flash` it also invokes `modsave flash`, reporting archive failures.
Freetz restores that archive at boot: `/tmp/flash` is not an ordinary disposable
temporary directory. Prefer external persistent storage for databases and Matter
state; select the configuration directory in **Startup and storage**.

## Live Firmware / BLE Commands

The **Commands** tab sends firmware diagnostics, host-managed GATT sessions and
TXADV requests through the **already running daemon**, without stopping or
restarting the service. **Read ATC configuration** and **Apply ATC configuration
patch** send their requests directly after confirmation: no second **Send command**
click is needed. Select the peer MAC/address type/PHY or an existing session first.
The generic **Send command** remains available for all other operations.

The confirmation and request/result/radio views use read-only Ace JSON editors.
The patch uses an **editable Ace JSON editor**: invalid or empty objects cannot
be sent. A prepared ATC patch initially enables `bt5phy` and `longrange`; edited
patch fields are retained when applying it. To edit before sending, choose the
`patch` operation or cancel the confirmation, edit the patch, then apply it again.
All command buttons are locked while a request is pending. If the service is
stopped or unavailable, an explicit error is shown; commands never start it
implicitly.

JSON views use syntax highlighting and folding; command errors use Ace's
plain-text mode. The YAML tab remains editable in Ace's YAML mode. If editor
assets cannot load, an explicit error is shown and radio data remains readable;
retry refreshing the radio status after restoring the assets.
Commands use the running configuration, not
unsaved edits; they do not save settings or implicitly restart the service.
The command controls and tooltips follow the browser language (English, German,
Italian, French or Spanish). Existing configuration/discovery views are unchanged.
The Freetz startup form declares German and English in `files/.language`;
other firmware languages use the framework's translation or fallback mechanism.

An active scan is paused for diagnostics/GATT, then restored even after a
command error. GATT also temporarily stops daemon-configured TXADV and restores
its original PHY, interval and payload after disconnect/cancel. Open / operation
in open session / Close allow discovery, arbitrary characteristic subscriptions,
ATT writes and application-notification responses without reconnecting.
Sessions have ownership tokens and an idle timeout; other radio commands cannot
interfere. Discovery filters and remaining time are preserved throughout.
Starting **TXADV instead leaves scanning OFF**, cancels Discovery and
keeps scanning suppressed across serial reconnects. Stopping TXADV does not
restart scanning: use **Start configured scan** explicitly. This starts the
saved scanner with its filters and stops daemon-tracked TXADV. Runtime overrides
are reset by an explicit service restart; stop TXADV before that restart.

The CLI has the same interface:

```sh
ble2uart-gateway --command '{"command":"diagnostic","name":"info"}'
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"read","handle":42}'
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"exchange","uuid":"1F1F","value":"55","prefix":"55","codec":"cfg","offset":1}'
ble2uart-gateway --command '{"command":"txadv-start","phy":0,"interval_units":160,"data":"020106"}'
ble2uart-gateway --command '{"command":"txadv-stop"}'
ble2uart-gateway --command '{"command":"scan-start"}'
```

Use firmware under `source/esp32ble/ble50_scan` implementing host-managed open
flag `1`, subscription op `13` and typed ATT completion events (`0x84`), not the
old `master` scanner. See
[the command reference](src/README.md#firmware-commands-while-the-daemon-is-running)
for all operations, limits, failure semantics and firmware limitations.
Writes with response now wait for confirmed ATT completion, but that is **not**
the sensor's application response. `exchange` additionally awaits a matching
notification. The ATC read/patch actions send `0x55` requests; generic raw and
codec-backed requests work for other commands too. A configuration patch preserves
unmodified fields and refuses codec mismatches before committing. See the
[ATC/Coded PHY example](src/README.md#persistent-sessions-and-atc-configuration)
for version-byte handling and verification from actual advertisements.

The active file is `<store>/ble2uart_gateway.yaml`. Runtime serial settings
come from YAML; the startup serial fields only initialize a new store.

## Generate The Device-Format Database With Python

The decoder database is `codec.yaml`: it describes supported packet formats
and fields. Generate it on a development PC from the Python model in
`atc_mi_interface`. This is separate from the
list of installed devices: MACs, bindkeys and exposed attributes belong in
`ble2uart_gateway.yaml` and are not generated by this converter.

From the freetz repository root, create a Python environment and set `ATC` to
the **package directory**, not to `atc_mi_advertising.py`:

```sh
python3 -m venv ~/.venvs/ble2uart-codec
. ~/.venvs/ble2uart-codec/bin/activate
python3 -m pip install construct==2.10.70 PyYAML pycryptodome arrow
ATC="atc_mi_interface"
python3 make/pkgs/ble2uart_gateway/tools/atc2spec.py --codec "$ATC" --out /tmp/ble-codec/codec.yaml
```

Check the conversion report before using the result. Unmapped constructs must
be resolved; named predicates must have matching Rust implementations. Python
conversion does not implement new algorithms in the daemon.

For a running router, back up any existing `<store>/codec.yaml` first, then
transfer the generated file next to the active configuration:

```sh
scp /tmp/ble-codec/codec.yaml root@fritz.box:/path/to/store/codec.yaml
```

On the router, validate the configuration and adjacent codec, then restart:

```sh
CFG=/path/to/store/ble2uart_gateway.yaml
/mod/external/usr/bin/ble2uart-gateway --check-config "$CFG"
if [ $? -eq 0 ]; then
  /mod/external/etc/init.d/rc.ble2uart_gateway restart
fi
```

Use the actual store path in these commands. The runtime file merges with and
overrides the embedded definitions, so deploying it does not require rebuilding
the binary.

To update the database embedded in a firmware build instead, use
`--out make/pkgs/ble2uart_gateway/src/spec/codec.yaml` in the generator command,
then run `make ble2uart_gateway-precompiled`. A runtime `codec.yaml` still
overrides those embedded definitions. Python is only needed for generation,
not for decoding on the router. No SQLite device database is generated.

### Select An External Codec

The gateway always starts from its embedded codec. Choose one external overlay:

| Selection | Behavior |
|---|---|
| No option, no `<store>/codec.yaml` | Embedded codec only |
| No option, `<store>/codec.yaml` exists | Automatically merge that file |
| `--codec /path/to/mycodec.yaml` | Merge this file instead; do not load `<store>/codec.yaml` |

Merge adds new structures/formats and replaces matching names; unrelated embedded
definitions remain available. An explicit path is mandatory after `--codec`.
Missing, unreadable or invalid selected files are errors, not a fallback to the
embedded codec. A relative codec path is relative to the working directory,
whereas automatic lookup is relative to the `--config` file.

```sh
# Named overlay for a direct daemon invocation:
ble2uart-gateway --config /path/to/store/ble2uart_gateway.yaml \
  --codec /path/to/mycodec.yaml --foreground

# Validate without opening the serial device:
ble2uart-gateway --config /path/to/store/ble2uart_gateway.yaml \
  --check-config --codec /path/to/mycodec.yaml
```

`--codec` is supported by daemon startup, `--check-config`, `--encode`,
`--decode`, `--benchmark-codec`, `--decode-captures` and `--web-config inspect`.
It is process-local and is not saved in the gateway YAML. To use it on service
startup, put `--codec /absolute/path/mycodec.yaml` in **Additional command line
options**, then restart the service. Use a path without spaces in that field:
the init script splits additional arguments on whitespace.

**CGI consistency:** the CGI starts separate helper processes and does not
forward the daemon's additional arguments. Its Inspect and validation helpers
continue to use the automatic adjacent `codec.yaml`; setting `--codec` only for
the daemon does not change them. To share one custom codec between the service,
CGI and CLI, prefer automatic lookup: copy the file to `<store>/codec.yaml`,
or retain its name with a symlink (only when `codec.yaml` does not already exist):

```sh
ln -s /absolute/path/mycodec.yaml /path/to/store/codec.yaml
```

Back up an existing overlay before replacing it. The daemon needs a restart
after file changes; standalone helper commands load it on each invocation.
Recompilation is only required to change the embedded copy or implement new
codec operations.

### Reconstruct Python/Construct From The Codec Specification

`tools/spec2atc.py` implements the reverse direction: **codec specification
JSON/YAML -> executable Python/Construct definitions**. It does not infer
binary layouts from Discovery/Inspect observations or create device entries.

Use the same development environment described above:

```sh
python3 make/pkgs/ble2uart_gateway/tools/spec2atc.py \
  --spec make/pkgs/ble2uart_gateway/src/spec/codec.yaml \
  --out /tmp/ble-codec/atc_mi_construct_generated.py
```

For JSON, use `--spec /path/to/codec.json`. The input must contain
`"version": 1` and `"structures"`; optional `"formats"` associations are
preserved. JSON conversion itself needs only the Python standard library;
YAML input additionally needs PyYAML.

The generated module includes its helpers and does not import the original
`atc_mi_interface` package or the converter. Executing it requires Construct
2.10.70, Arrow for timestamp structures, and PyCryptodome when encrypted
formats are used. Its original top-level names are available as Python
variables when they are valid, nonreserved identifiers; `STRUCTURES` always
provides lookup by the exact original name, and `FORMATS` retains format
metadata.

For example, from the generated module's directory:

```python
from atc_mi_construct_generated import bt_home_v2_format

# Service data: UUID + DevInfo + objects, without AD length/type, flags or name.
raw = bytes.fromhex("D2FC40008A0C0E0B10001101")
decoded = bt_home_v2_format.parse(raw)
assert decoded.data_point[1].data.battery_v == 2.83
assert bt_home_v2_format.build(decoded) == raw
```

Encrypted structures accept `mac_address=bytes.fromhex(...)` (6 bytes, display
order) and `bindkey=bytes.fromhex(...)` (16 bytes) in both `parse` and `build`.
Missing parameters or failed CCM authentication raise explicit Construct
validation errors; there are no default keys.

This reconstructs equivalent supported declarations, not the original source:
comments, shared helper names and arbitrary Python callbacks cannot be recovered
from the exported schema. Known callbacks/predicates and the four BLE encryption
codecs are implemented explicitly. Unsupported nodes and ambiguous/incomplete
transforms are rejected with their schema location, without replacing an
existing output file. See [CODEC.md](CODEC.md) for the detailed limits.

Run the inverse converter's tests on the development PC:

```sh
python3 -m unittest discover -s make/pkgs/ble2uart_gateway/tools -p test_spec2atc.py -v
```

For an independent comparison with the **original Construct model**, rather than
only stored vectors, also set:

```sh
ATC_CODEC_REFERENCE="$ATC" \
ATC_GENERATED_MODULE=/tmp/ble-codec/atc_mi_construct_generated.py \
python3 -m unittest discover -s make/pkgs/ble2uart_gateway/tools -p test_spec2atc.py -v
```

Use the same original package revision that generated the specification.
Without `ATC_CODEC_REFERENCE`, the four original-source comparison tests are
explicitly skipped. With it, the suite re-exports the original schema, directly
compares 1,000 stored and 4,200 independent packets, and exhaustively checks
all 256 byte values of each of the seven distinct affine adapters.

Affine nodes now preserve the original `decoder` expression as well as the
`encoder`: reducing `(obj + 1) * 0.02` to `obj * 0.02 + 0.02` changes floating
point rounding and can change the re-encoded byte. Older specifications without
`decoder` remain readable, but cannot recover evaluation order that was lost.
Regenerate them from the original model to obtain the exact expressions.
The updated schema requires an updated gateway binary: older binaries reject
the new `decoder` property. Do not deploy it alone to an older router build.

The generated encryption helpers also use the current input/output stream when
building edited parsed objects, rather than a stale stream retained in a
Construct Container. A separate test records a known reference discrepancy:
the original BTHome v2 encoder hardcodes DevInfo `0x41` in its nonce. With
`Trigger=true`, it emits header `0x45` but cannot decrypt its own output.
The reconstructed helper deliberately uses the actual header and produces a
valid authenticated packet; this case is not claimed to be byte-equivalent
to the defective original encoder.

## Add Devices Through The GUI

### From Discovery

1. With the gateway running, open **Discovery**, choose a duration of 1-300
   seconds and select **Start discovery**.
2. Find the device by MAC or advertised name. Vendor filters and sorting affect
   only the table. OUI identifies the address assignee, not necessarily the
   product brand; random addresses may have no identifiable vendor.
3. Select **Configure** and enter a label. For encrypted advertisements, enter
   the device's **Bindkey**: exactly 32 hexadecimal digits. Leave it empty for
   unencrypted devices. **Show/Hide** changes only the key's visibility.
4. Leave **Forced wire format** empty for automatic detection. Configure decodes
  the selected packet and prefills supported **Exposed attributes**, not protocol
  metadata. For encrypted packets, enter the bindkey and select **Detect
  attributes**. Later packets can contain additional measurements; review and
  supplement the list, keeping existing child IDs stable.
5. Select **Add to configuration draft** (or **Update configuration draft** for
  an existing device). The dialog closes and returns to **Devices**, focusing
  the configuration save action. Use **Inspect** to check decoded data.
6. Select **Save configuration**, then **Status → restart** to activate changes.

Discovery temporarily removes ESP32 filters, then restores the configured
scanner on Stop or timeout, even if the page is closed. It never enrolls a
device automatically. Inspect reports unsupported formats and decoding errors;
a discovered MAC alone does not imply a supported device.
The selected advertisement is shown as formatted, read-only JSON in ACE, with
syntax highlighting, collapsible objects/arrays and selectable text. If editor
assets cannot load, an explicit error is shown and the JSON remains readable
as plain text. Inspect does not modify the configuration or restart the service.
Hover a JSON **field name** for contextual help without changing the displayed
data. The collapsible **Advertisement field guide** provides the same root-field
explanations for keyboard/touch users and remains available without ACE. Nested
codec fields have protocol-specific or generic guidance. Help covers address
types, OUI/vendor lookup, configured state, PHY versus payload format, reception
counters/timestamps, and decoded values. Failed inspection also displays a
notice: an unexpected API response or expired web session does not establish
that the received BLE packet is invalid.

The device dialog explains the draft action and **Cancel** through tooltips.
Adding/updating validates the device and updates only the page draft; Cancel
discards only edits in that dialog, preserving other page changes.
Neither action writes the saved configuration or restarts the daemon.

**Availability monitoring** in each device dialog manages missing-reading
notifications. Add a rule, select its attribute and timeout, configure its own
HTTPS webhook and enable it when ready. Each rule has an independent test button.
See [device availability monitoring](src/README.md#device-availability-monitoring).

### Configure Advertisement Filters

Open **Settings → Scanner → Advertisement MAC filters**, or use
**Configure advertisement filters** in Discovery:

1. Choose whether **Filter registered devices in ESP32** is enabled. When on,
   only enabled configured devices are eligible; an include list further
   restricts them and an exclude list removes matches. With no eligible devices
   the scanner stays stopped.
2. Fill **one** list: **Include MACs/prefixes (whitelist)** to admit matches, or
   **Exclude MACs/prefixes (blacklist)** to reject matches. Both populated is an
   error, shown immediately and rejected by validation/save; neither list is
   automatically cleared.
3. Enter full MACs or 1-6-byte prefixes, for example `A4:C1:38` or
   `A4C1383406CE`, separated by newlines, spaces or commas. Prefixes start at
   the first displayed MAC byte; no wildcard is needed. The effective firmware
   list may contain at most 64 entries.
4. To receive unregistered addresses in normal scanning, turn registered-device
   filtering off. With it off and both lists empty, all addresses are admitted
   by the MAC filter; other scanner settings still apply. Reception alone does
   not configure devices or publish their measurements.
5. Select **Save configuration**, then **Status → restart**. **Start configured
   scan** resumes the configuration already loaded by the daemon; it does not
   reload newly saved edits.

Discovery's search, vendor and unconfigured-only controls filter the displayed
table, not the radio. Active Discovery temporarily bypasses configured MAC,
random/private-address and duplicate filters and enables both PHYs. Stop or
timeout restores the scanner configuration loaded by the daemon.

### From A Known MAC

Open **Devices → Add manually**, enter its MAC, label, optional bindkey and exposed
attributes, then follow the same draft, Save and Restart sequence. **Discover
devices** opens the assisted path; the separate labeled search filters only the
configured-device list below it.
Accepted MAC spellings include `AABBCCDDEE01` and `AA:BB:CC:DD:EE:01`.

**Edit** and **Remove** change the configuration draft; removing an entry does
not remove its Discovery observation. **Reload** can discard unsaved changes.
Save validates the configuration and creates a backup, but does not restart
the service itself. These settings configure the gateway, not sensor firmware.

## Add Devices In YAML

The **YAML** tab provides an ACE editor, validation, import/export and backup
loading. A loaded backup is a draft: save and restart to apply it.

Replace the example MACs below and expose only attributes returned by Inspect.
For an existing configuration, append entries to its existing `devices` list;
do not create a second `devices` key or overwrite unrelated settings.

```yaml
version: 1
log_level: info
serial:
  port: /dev/ttyACM0
frontends:
  mysensors:
    enabled: true
    bind: 127.0.0.1
    port: 5003
    node_id_base: 10
devices:
  - mac: "AA:BB:CC:DD:EE:01"
    label: "Living room thermometer"
    manufacturer: "Xiaomi"
    model: "LYWSD03MMC"
    firmware_version: ""
    enabled: true
    bindkey: ""
    format: ""
    expose:
      - attribute: temperature
        child: 0
      - attribute: humidity
        child: 1
      - attribute: battery_level
        child: 2
  - mac: "AA:BB:CC:DD:EE:02"
    label: "Window contact"
    enabled: true
    bindkey: ""
    expose:
      - attribute: opened
        child: 0
      - attribute: battery_level
        child: 1
```

| Field | Meaning |
| --- | --- |
| `mac` | Required, unique device address. Quote it in YAML. |
| `label` | Friendly device name; falls back to `model`, then MAC. |
| `manufacturer` | Optional physical-device manufacturer, such as `Xiaomi`. |
| `model` | Optional physical model, such as `LYWSD03MMC`; not a BLE format. |
| `firmware_version` | Optional known device firmware version; never inferred from the packet format or gateway version. |
| `enabled` | Monitor this entry; defaults to `true`. |
| `bindkey` | Empty or the device's 32-digit hexadecimal AES key. |
| `format` | Empty for automatic detection, or a supported format name. |
| `expose` | MySensors children and standard Matter endpoints to create; MQTT and proprietary Matter state remain complete. |
| `expose[].child` | MySensors child ID, 0-255. Use explicit IDs unique within the device. |

Supported formats: `custom`, `custom_enc`, `atc1441`, `atc1441_enc`, `mi_like`,
`bt_home`, `bt_home_enc`, `bt_home_v2`. PVVX firmware can advertise BTHome v2;
do not force `custom` based on firmware brand alone.

Common attributes include `temperature`, `humidity`, `battery_level`,
`battery_v`, `pressure`, `illuminance`, `contact`, `water_leak` and `motion`.
BTHome may also provide `switch`, `boolean` and `opened`; custom PVVX packets
may provide `humidity_trigger`, `temp_trigger`, `out_gpio_trg_flag`,
`out_gpio_trg_value` and `input_gpio_value`. Availability depends on the packet:
use Inspect. Attributes without a MySensors mapping remain available through
MQTT and the proprietary Matter cluster.

**Preserve MySensors IDs:** node IDs currently depend on device-list order.
Reordering or deleting entries can renumber later devices; disable entries
instead when existing IDs must remain unchanged. Keep child IDs stable too.
At most 200 exposed attributes are supported in total.

YAML files, exports and backups contain bindkeys. Keep them private.

### Shared Device Metadata

Set metadata in the device editor or YAML. Empty manufacturer/model/firmware
fields remain unknown, rather than being reported as Freetz hardware. The full
MQTT state and proprietary Matter state include a `device` metadata object.

MQTT discovery uses `device.name`, `manufacturer`, `model` and `sw_version`;
entity names contain only the measurement name, without repeating the device.
Matter uses standard Bridged Device Basic Information attributes `NodeLabel`
(`5`), `VendorName` (`1`), `ProductName` (`3`) and `SoftwareVersionString` (`10`).
Optional attributes are advertised only when configured; string limits are
applied without splitting UTF-8 characters.

MySensors uses manufacturer/model for the node sketch name, a known firmware
version for the sketch version, and the device name plus measurement for child
presentations. Text is escaped and limited to the protocol's 25-byte payload;
the advertised MySensors protocol version remains separate from device firmware.

Metadata edits do not change MQTT unique IDs/topics, Matter endpoint IDs or
UniqueIDs, or MySensors node/child IDs. Keep device order and child IDs unchanged.
Controllers may retain existing names or user aliases; metadata does not rewrite
Domoticz history, user names or its legacy subtype labels. Save and restart the
gateway after metadata changes.

## SQLite

The optional SQLite frontend is available in **Settings → Frontends → SQLite**.
Settings exposes all five frontends: MySensors, MQTT, Matter, InfluxDB 3 and
SQLite. It uses the same validated YAML store and Save/Restart workflow as the
other frontends; saving does not restart the service implicitly.
Each frontend has a distinct bordered group, an enabled/disabled status and its
**Enabled** checkbox first. Parameter tooltips and keyboard/touch-accessible **?**
buttons explain units, limits and consequences such as queue overflow.

The CGI renders the typed configuration returned by the daemon binary, not just
sections already present in the saved YAML. The current daemon supplies default,
disabled SQLite settings even for older YAML without `frontends.sqlite`; reading
does not rewrite that file. If a frontend is missing from the API response, the
CGI explicitly warns that the backend is incomplete/outdated. Update the daemon
binary together with the CGI and reload the page; updating only the CGI or
restarting an old binary cannot add SQLite support.

```yaml
frontends:
  sqlite:
    enabled: true
    path: /var/media/ftp/USB/ble2uart_gateway/readings.sqlite3
    batch_size: 100
    queue_capacity: 1024
    flush_interval_ms: 1000
    busy_timeout_ms: 1000
```

Replace `USB` with an actual local mount, preferably ext4, and create the parent
directory there first. The default database path is empty and must be set
explicitly. Do not place continuously written history in `/tmp/flash` or on
internal flash. SQLite is bundled into the binary; no SQLite daemon, shell
command, or additional shared library is required.

One `frames` row stores each decoded reception and its complete JSON metadata;
linked `measurements` rows store each attribute, unit and exact typed value,
including fields not listed in `expose`. Frame and measurement rows commit
atomically. A bounded worker queue keeps disk writes off the serial reader.
WAL permits concurrent local rendering readers. Database errors, queue overflow
and shutdown losses are reported in the service log.

`batch_size` limits frames per transaction, not a mandatory minimum. A full batch
commits immediately; otherwise `flush_interval_ms` triggers the write (default
1000 ms), subject to locks, backlog, storage errors and retries. Sensor/radio
arrival frequency, including duplicate filtering, is independent of this timer.
Normal SQLite readers of the original database see committed WAL rows without
waiting for a checkpoint of the main `.db` file. Its modification time alone can
therefore look minutes old. A long-lived read transaction retains its snapshot:
end it before querying for fresh data. Do not copy only `.db` while recording;
use SQLite's backup API rather than an incomplete file copy or `immutable=1`.

See [SQLite configuration, schema, queries and operational limits](src/README.md#sqlite-history).
Optional **History maintenance** runs in a dedicated gateway thread, not cron.
It is disabled by default. The CGI provides enable/cadence/work-budget controls
and per-attribute policies with optional MAC overrides. Edit age bands with
duration/unit fields, add/remove bands and restore temperature/battery presets.
The temperature defaults preserve every sample for ten minutes, then use
1 minute / 150 seconds / 1 hour / 4 hours / 6 hours until respectively one hour /
one day / one week / eight weeks / 24 months, then expire older numeric samples.
Battery percentage and voltage use much sparser intervals. Recognized counters
are excluded from consolidated history by default, configurable through
**Default counter history** or explicit per-attribute/MAC policies. Other unknown
attributes and boolean/discrete states preserve every sample indefinitely.

Each series is related to its device by MAC and identified by attribute/unit.
Old complete frames are atomically split into `history_samples` through
`history_series` and `history_devices`; one typed JSON value avoids sparse
sensor columns. Consolidation keeps real samples, not min/max or averages.
**Back up before enabling:** schema 2 is not readable by older binaries, and
discarded samples/full packet JSON cannot be reconstructed. Query the `history`
view to combine recent raw measurements and consolidated series. Disabling
maintenance stops future reductions without removing existing archives.
See [maintenance settings and schema](src/README.md#progressive-history-maintenance)
for presets, transaction limits and migration/downgrade precautions.

## Sensor Dashboard

`/cgi-bin/extra/ble2uart_gateway/portal` is a read-only dashboard for the SQLite
database: it shows the latest value of every sensor and draws their charts. It
uses the standard freetz login, the same authentication as
`/cgi-bin/conf/ble2uart_gateway`, elfinder and rutorrent; there is no separate
password. Open **Settings** with the gear button in the top bar to go back to the
configuration editor.

Nothing is hard-coded. Devices, sensor names, attributes, units and value types
are discovered from the database on every request:

* consolidated series come from `history_devices` / `history_series`, so the
  dashboard also lists attributes that are no longer present in recent frames;
* raw-only attributes come from the most recent frames, so it works with history
  maintenance disabled as well;
* `real`/`integer`/`unsigned` values are charted as lines, `boolean` values as
  step lines (`0`/`1`), and `text`/`json` values are shown as a value only.

Tap a sensor card to add it to the chart (up to six series, shared time axis) and
tap it again, or a legend chip, to remove it. The range buttons cover 1 hour to
the whole history; the chart is downsampled server-side with weighted per-bucket
averages, merging archived samples and the recent raw frames. Values are never
interpolated. The page refreshes the values every 30 seconds.

Resource use (measured on the FRITZ!Box 7590 AX with the production database,
one CGI request): peak RSS about 7 MB for this implementation against about
19 MB for an equivalent PHP `php-cgi` script (PHP 8.5 with `pdo_sqlite`) that runs
the same queries, and about 14 MB for PHP alone. A PHP request also starts an
interpreter per call, while this CGI execs the gateway binary that is already
installed. The wrapper is `/usr/lib/cgi-bin/ble2uart_gateway/portal.cgi` (POSIX
shell: login guard, then `exec ble2uart-gateway --portal`); the HTML shell, CSS
and JavaScript are in `/usr/mww/ble2uart_gateway/portal.*` and need no Internet
access, no CDN and no charting library.

The CGI never writes: the connection is opened with `PRAGMA query_only=ON`, so
the dashboard cannot modify or lock the history. It uses short read transactions
and reads the WAL, so it always sees the committed data even while the gateway is
writing. If the database does not exist yet the page reports it instead of
failing.

## Availability Monitoring

Open **Devices → Edit → Availability monitoring**. Each device owns its rules;
Settings contains no global ITTT, availability-rule or webhook section.
Each rule can be added, edited, removed, enabled and disabled independently.
Set the attribute and **Notify if no reading received for more than (seconds)**,
then open its **Webhook configuration** for ntfy/Gotify, HTTPS URL, private token,
priority/tags, IPv4 selection, timeouts/retries and optional trusted PEM CA.

New rules start disabled with temperature/600-second defaults. Each rule has a
confirmed **Test webhook** button using its draft without saving or restarting.
The rule's optional notification message overrides automatic alert/recovery/test
text only when filled. Its optional **tgs** field overrides `webhook.tags` for
that rule; blank fields retain the existing defaults. Missing webhook URLs open
the configuration panel automatically. Device status is read-only Ace JSON.
Save the device draft, Save configuration and explicitly restart to apply.
Identical temperatures refresh freshness; battery-only packets do not. One stale
episode and one recovery are retained across restarts; no periodic reminders run.
There is no external rule engine or editable workflow language. Earlier global
configurations migrate to their devices without placing private URLs in sources.
See [monitoring settings and delivery semantics](src/README.md#device-availability-monitoring).

## MQTT And Matter

Both frontends receive every successfully decoded field for enabled configured
devices, independently of MySensors type mappings and `expose`. The complete
`decoded` object preserves nested fields, arrays, nulls and numeric precision;
typed `measurements` include units. `latest_values` retains measurements from
alternating packets. Unsupported formats and authentication failures are not
published as decoded values. Bindkeys and broker passwords are never included.

Enable either frontend in Settings or merge the relevant section into YAML:

```yaml
frontends:
  mqtt:
    enabled: true
    host: 127.0.0.1
    port: 1883
    client_id: ble2uart-gateway
    base_topic: ble2uart-gateway
    username: ""
    password: ""
    retain: true
  matter:
    enabled: true
    bind: "::"
    port: 5541
    store: /var/media/ftp/USB/ble2uart_gateway-matter
    advertise: true
    mdns_backend: auto
    mdns_hostname: ""
    mdns_interface: ""
```

MQTT publishes JSON to `<base_topic>/<MAC>/state`, with normalized MACs such as
`AABBCCDDEE01`. It uses QoS 1, optional retain and reconnect replay of the latest
state per device. Broker outages do not block BLE reception; intermediate
transitions are not a persistent event history. Use a unique client ID for each
gateway. This configuration uses plain MQTT TCP: do not send credentials over
an untrusted network without a secure external tunnel or proxy.

Matter needs a dedicated persistent store for its fabric and endpoint map.
Endpoint IDs remain stable across device-list reordering and are not reused
after removal. Pair the BLE gateway separately using its startup pairing code;
the build uses development attestation credentials, not certified credentials.
Set `mdns_interface` when interface autodetection is unsuitable; direct-IP
commissioning remains possible if mDNS is unavailable.

The SDK is pinned to `c69916a5a78957d46500145486df375acf4ab490`, the latest
upstream `main` checked on 2026-10-17 (package version `0.4.1`, newer than the
`v0.4.1` release tag). The pin and lockfile keep builds reproducible rather
than following a moving branch.

The Freetz-EVO package builds the daemon with the Cargo feature `freetz`, so
`mdns_backend: auto` uses the builtin responder, `mdns_hostname: ""` announces
`ble2uart-gateway.local` (a DNS label cannot contain `_`) and interface
autodetection prefers `lan`, then `br*`. The same feature adds the
`/mod/external/usr/bin` helper lookup. MQTT defaults, Home Assistant unique IDs
(`ble2uart_<MAC>_...`) and the Matter basic information are the same as in the
standalone build.
`mdns_backend: disabled` (or the legacy `advertise: false`) turns DNS-SD off.

When `advertise` is enabled, built-in DNS-SD advertises commissionable services
while the commissioning window is open and operational `_matter._tcp` services
for commissioned fabrics. It shares UDP 5353 with the router responder, selects
the LAN multicast interface and uses IP TTL/hop limit 255. The DNS record TTL is
separate and managed by the SDK. A failed initial network setup is retried every
10 seconds without stopping direct-IP Matter or the other frontends.

## InfluxDB 3

InfluxDB 3 receives every typed decoded measurement for enabled configured
devices, independently of `expose`. Enable it in Settings or in YAML:

```yaml
frontends:
  influx:
    enabled: true
    endpoint: http://127.0.0.1:8181
    database: ble
    measurement: ble
    token: ""
    batch_size: 100
    queue_capacity: 1024
    flush_interval_ms: 5000
    timeout_ms: 3000
```

The gateway posts line protocol to `<endpoint>/api/v3/write_lp` with
nanosecond receive timestamps. Each point uses tags `mac` and `attribute`;
fields are `unit`, `label` and one typed value field (`value_float`,
`value_int`, `value_uint`, `value_bool` or `value_text`). Example query:

```sql
SELECT time, label, value_float, unit FROM ble
WHERE mac = 'AABBCCDDEE01' AND attribute = 'temperature' ORDER BY time DESC
```

`measurement` is the Influx table name, not the sensor attribute: if configured
as `ble_live`, query `ble_live` instead of `ble`. `label` is the configured
sensor name, `mac` is its stable identity and `attribute` identifies the reading.
There is no generic `value` column. Fields are created when first written, so
querying a typed value column that has never been used can fail schema validation.
To inspect all available fields, including their values:

```sql
SELECT * FROM ble_live ORDER BY time DESC LIMIT 100;
```

For InfluxQL clients, select the correct typed field, for example
`SELECT value_float FROM ble_live WHERE attribute = 'temperature' AND time > now() - 6h`.
Do not combine different sensors into a single graph series: group by `mac` and
`attribute`, or filter the desired MAC and attribute explicitly. The timestamp
is stored in UTC; clients may display local time.

The token is sent as a bearer token and is not logged or published. Tokens
over plain HTTP are accepted only for loopback endpoints; use HTTPS remotely.
URL credentials, query strings and redirects are rejected. Writes run in a
separate worker and never block BLE reception. Server errors and timeouts retry
the current batch; HTTP 4xx rejections discard it. The queue is bounded and
in memory: overflow, shutdown and power loss can drop samples. Changes require
Save and Restart service.

The optional Domoticz controller stays loopback-only and intentionally does not
advertise on the LAN; the BLE accessory itself provides LAN discovery as
`ble2uart-gateway.local`.

Read-only on-device discovery verification requires the Python `dnslib` package:

```sh
python3 tools/test_frontends_target.py --check-mdns --mdns-interface lan \
  --mdns-ipv6 --matter-port 5541
```

For an uncommissioned accessory use `--mdns-service _matterc._udp.local.`.

Standard read-only endpoints cover configured temperature, humidity, pressure,
illuminance, occupancy, boolean/contact, battery percentage and voltage values.
Conversions check units and range; values that cannot be represented retain
their original form in the proprietary payload, without silent clamping.

Every device also exposes vendor cluster `0xFFF1FC00`:

| Attribute | Type / Meaning |
| --- | --- |
| `0` | Schema version. |
| `1` | State version; verify it before and after a multi-read snapshot. |
| `2` | Complete JSON byte length. |
| `3` | List of octet-string blocks, at most 256 bytes each. Concatenate before decoding UTF-8 JSON. |
| `4` | Device MAC. |

A controller must understand this vendor cluster to use arbitrary fields;
complete value preservation is not universal standard-sensor compatibility.
Matter and MQTT changes require Save and Restart service.

### Native Domoticz

For MQTT, enable native discovery in the gateway YAML:

```yaml
frontends:
  mqtt:
    enabled: true
    host: 127.0.0.1
    port: 1883
    domoticz_discovery: true
    discovery_prefix: homeassistant
    local_broker: true
```

`local_broker` requires Mosquitto and an unused port. It starts a private,
gateway-owned broker bound only to `127.0.0.1`, without changing the global
Mosquitto service. Set it to `false` when using an existing broker.

In Domoticz add **MQTT Auto Discovery Client Gateway with LAN interface**
(hardware type `125`), address `127.0.0.1`, port `1883`, discovery prefix
`homeassistant`. Discovery configs are retained, identities include the MAC,
and each measurement uses a scalar state topic. Complete JSON remains on the
original state topic. This is the native Auto Discovery protocol, not the
separate legacy `domoticz/in` protocol used by hardware type `43`.
Domoticz may create combined or separate temperature/humidity sensors when
additional temperature measurements such as dew point are present. Its native
display types round values; the full MQTT state retains the original precision.

For Matter, add `domoticz_port: 5581` under the enabled `frontends.matter`
section. This requires `matter-bridge` and starts a dedicated loopback
controller with its own persistent store below `<matter.store>/domoticz-controller`.
Add native **Matter** hardware in Domoticz, address `127.0.0.1`, port `5581`.
An existing controller on `5580` is left untouched. The packaged Domoticz patch
groups environmental readings by physical bridged device rather than mixing
the first temperature and humidity of the entire bridge. Standard sensors are
available natively; arbitrary vendor-cluster fields still need controller support.

## Scanner Filtering

By default, the ESP32 forwards only enabled configured MACs to USB:

```yaml
scanner:
  filter_known_devices: true
```

The effective filter supports at most 64 MACs. With no matching enabled devices,
scanning stays stopped. Explicit `scanner.whitelist` prefixes further restrict
the registered set; `scanner.blacklist` prefixes exclude entries. The explicit
lists are mutually exclusive.

Set `filter_known_devices: false` to disable the automatic filter. Explicit
lists still apply; with both empty, all MACs reach USB, but the daemon still
processes only configured enabled devices. Save and restart after scanner
changes. Discovery manages temporary unrestricted scans itself.

This is a daemon behavior, not an RC-only option: the firmware filter is
programmed after **every serial connection/reconnection**, including automatic
Freetz boot startup, manual RC start/restart and ordinary CLI gateway startup.
The sequence is stop scan, clear the old list, add the effective WMAC/BMAC
entries while checking firmware acknowledgements, then start scanning. Failure
keeps scanning stopped. The firmware cannot hold an active whitelist and
blacklist simultaneously:

| Configuration | Effective firmware list |
|---------------|-------------------------|
| `filter_known_devices: true` (default) | Whitelist of enabled configured devices, restricted by explicit whitelist prefixes and excluding blacklist prefixes |
| `filter_known_devices: false`, explicit whitelist | Explicit whitelist |
| `filter_known_devices: false`, explicit blacklist | Explicit blacklist |
| `filter_known_devices: false`, both lists empty | Empty list: no MAC restriction in firmware |

With registered-only filtering enabled and an empty effective list, the scanner
stays stopped instead of admitting every MAC. Discovery temporarily clears MAC
filters (and random/RPA/duplicate restrictions), then restores configured filters
on Stop or timeout. Summary logs are at INFO; individual effective entries are
at DEBUG. Saving settings alone does not reprogram a running scanner; restart
the service to apply them.

## Diagnostics

The service log is `/tmp/rc.ble2uart_gateway.log`. In Settings, choose a log
level (`off`, `error`, `warn`, `info`, `debug`, `trace`) and independently enable
TX, RX, decode or PHY traces. Dumps require at least `info` and may contain
private data. The startup Debug logging option overrides the YAML log level.

After saving logging changes, **Reload logging** applies them without restarting
the scanner. Device, scanner and codec changes require **Restart service**.
For decoding failures, check the MAC, bindkey and detected format. `stage=rx`
precedes format detection, so format/family are `pending`; `stage=decode status=ok`
confirms decoding, not controller delivery.

For CLI checks, set `CFG` to the active configuration file:

```sh
CFG=/path/to/store/ble2uart_gateway.yaml
/mod/external/usr/bin/ble2uart-gateway --check-config "$CFG"
/mod/external/etc/init.d/rc.ble2uart_gateway restart
```

Stop the service before CLI `--info` or `--scan`: the serial port has one owner.
Offline `--decode`, `--encode` and `--decode-captures` do not open serial.

## Development And Limits

An optional `<store>/codec.yaml` extends the embedded declarative codec. Changes
using existing operations need a restart, not recompilation; new algorithms
require Rust changes.

Build and test from the repository root:

```sh
cargo test --manifest-path make/pkgs/ble2uart_gateway/src/Cargo.toml
make ble2uart_gateway-precompiled
./evo-eng-tools/deploy-ble2uart_gateway.sh
```

The deployment helper preserves existing YAML and publishes the English CGI.
For targets with separate AVM/Freetz uClibc, the package depends on
`patchelf-target-host` and waits for `tools/patchelf-target` before installing the
binary. The shared install helper sets the ELF interpreter once, only when
required. A missing `patchelf-target` after Cargo reports success is an
installation dependency error, not a Rust compilation error.

Browser regression tests require Playwright/Chromium and a freshly built native
daemon, so they exercise the current frontend schema rather than a stale binary:

```sh
cargo build --manifest-path make/pkgs/ble2uart_gateway/src/Cargo.toml --offline --no-default-features
node make/pkgs/ble2uart_gateway/tools/test_web_ui.cjs
python3 -m unittest discover -s make/pkgs/ble2uart_gateway/tools -p test_build_progress.py -v
python3 -m unittest discover -s make/pkgs/ble2uart_gateway/tools -p test_save_hooks.py -v
python3 -m unittest discover -s make/pkgs/ble2uart_gateway/tools -p test_codec_cli.py -v
```

`tools/test_captures.py --help` documents private pickle regression testing;
keep converted captures and keys outside the repository.
`tools/test_frontends_target.py --help` covers isolated frontend tests and
`--live-domoticz-db` checks of existing native MQTT/Matter hardware. Live mode
only observes real updates and opens the database read-only; it never publishes
synthetic measurements or opens the serial port.

SQLite-backed MySensors stable IDs/persistence are not yet implemented.
MQTT last-state replay is in memory;
Matter persists its fabric and endpoint identities, not historical BLE samples.
