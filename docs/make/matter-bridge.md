# matter-bridge 0.1 (native Matter controller for Domoticz)
  - Package: [master/make/pkgs/matter-bridge/](https://github.com/Freetz-NG/freetz-ng/tree/master/make/pkgs/matter-bridge/)
  - Steward: Ircama

`matter-bridge` combines the Rust/rs-matter controller and Domoticz-compatible
WebSocket API in one daemon. No Node.js, Python server or IPC backend is needed:

```text
Domoticz -> ws://127.0.0.1:5580/ws -> matter-bridge -> Matter/CASE -> freetz-matter
```

## Local Setup

1. Include `domoticz`, `matter-bridge` and `freetz-matter` in the firmware.
2. Run `matter-bridge-setup` on the box. It enables both Matter services through
   `modconf`, preserves stores/settings and starts only stopped services.
3. In Domoticz, add **Matter (python-matterjs-server)** hardware with address
   `127.0.0.1` and port `5580`. No pairing code is needed for the local accessory.
4. After the node appears, run `modsave` again to persist both fabric stores
   to flash. Preserve them when upgrading firmware.

Automatic commissioning retries until the device becomes available. An
accessory commissioned elsewhere must have an open commissioning window.
Existing fabrics are never deleted. Restarts reuse the controller keys/node ID.

Manual startup is also possible:

```sh
/etc/init.d/rc.freetz-matter start
/etc/init.d/rc.matter-bridge start
```

Logs are `/tmp/rc.matter-bridge.log` and `/tmp/rc.freetz-matter.log`.
Temperature is attribute `1/1026/0`; speaker mute and volume are `2/6/0`
and `2/8/0`. These are device attributes, not a seed-node simulation.

## Implemented Scope

- Known-address IPv6 PASE commissioning, CASE and CommissioningComplete.
- Atomic private files for persistent certificates, ICAC/operational keys,
  IPK and nodes; malformed stores are rejected, not reset.
- Wildcard interviews, chunked reads, subscription priming and asynchronous
  ReportData, status replies and reconnect watchdog.
- Flat server-info, `start_listening`, `get_nodes`, `get_node`,
  `get_node_ip_addresses`, `interview_node`, `read_attribute`, `write_attribute`.
- Real OnOff `On`, `Off`, `Toggle`; LevelControl `MoveToLevel`,
  `MoveToLevelWithOnOff`; Identify commands.
- Positional `attribute_updated`: `[node_id, "ep/cluster/attr", value]`.

This is not a certified Matter controller or full python-matter-server
replacement. The daemon advertises itself and answers mDNS resolve queries with
rs-matter's built-in responder (`_matter._tcp`, plus the A/AAAA records of
`matter-bridge.local`), sharing UDP 5353 with the closed mDNS responder of
FRITZ!OS: both sockets set `SO_REUSEADDR` and each one answers only for its own
records. Browsing for other commissionable devices, Bluetooth and Wi-Fi/Thread
provisioning, fabric removal and opening commissioning windows are not
implemented.
Unsupported commands fail rather than simulating success.
rs-matter lacks production Device Attestation verification. Loopback test
commissioning is accepted locally; remote use needs explicit
`--allow-test-attestation` and is not covered by the local integration test.
Subscription routing by subscription ID is intended for the single local
accessory, not authenticated multi-device remote operation.

## Configuration

Defaults: `/mod/etc/default.matter-bridge/matter-bridge.cfg`.
Overrides: `/mod/etc/conf/matter-bridge.cfg`.

| Variable | Default | Purpose |
|---|---|---|
| `MATTER_BRIDGE_ENABLED` | `no` | Boot autostart |
| `MATTER_BRIDGE_PORT` | `5580` | WebSocket port |
| `MATTER_BRIDGE_BIND` | `127.0.0.1` | WebSocket bind address |
| `MATTER_BRIDGE_STORE` | `/tmp/flash/matter-bridge` | Fabric/node directory archived by modsave |
| `MATTER_BRIDGE_PEER` | `[::1]:5540` | Accessory address |
| `MATTER_BRIDGE_AUTO_LOCAL` | `yes` | Automatic local commissioning |
| `MATTER_BRIDGE_VERBOSE` | `no` | Debug logs |
| `MATTER_BRIDGE_CONFIG_WAIT` | `120` | Seconds to wait for `/usr/bin/matter-bridge` when the binary lives on external storage; the wait runs in a background subshell, `0` disables it |
| `MATTER_BRIDGE_EXTRA_ARGS` | empty | Additional native options |

Settings are applied after an explicit restart, not implicitly on Save. The
unauthenticated WebSocket API must not be exposed to untrusted networks. Local
Matter UDP also binds to loopback.

Freetz archives `/tmp/flash`, not arbitrary `/mod/etc` directories. The device
store defaults to `/tmp/flash/freetz-matter`. Existing store overrides are not
moved automatically; use external persistent storage or migrate both stores
while the services are stopped, then save the corresponding configuration.
On devices with a 32 KiB flash archive limit, check the result of `modsave`;
use persistent external storage for larger stores. There is no automatic
flash write for every attribute report.

`matter-bridge-ctl` is a separate diagnostic commissioner that generates a
fresh fabric per invocation. It is not used by the service; do not point it
at the production daemon store or use it for the automatic local setup.

## Build And Tests

```sh
make matter-bridge-precompiled
python3 make/pkgs/matter-bridge/tests/native-controller-test.py \
  --server /path/to/host/matter-bridge --device /path/to/host/light_tests
python3 make/pkgs/matter-bridge/tests/native-controller-test.py \
   --server /path/to/host/matter-bridge --device /path/to/host/freetz-matter --freetz
```

The native host test checks automatic PASE/CASE, interview, OnOff/level,
read/write, delayed asynchronous subscription report and restart recovery.
It also intercepts init launch arguments to verify configured stores/ports
and automatic commissioning. The freetz variant restarts both daemons.
The recipe uses Rust nightly, pinned rs-matter, Cargo.lock and isolated
uClibc patches. Both Rust binaries are externalizable; init/config/fabric stay
on the box. Router temperature/audio, actual Domoticz UI and boot persistence
require target-device testing. Host-level testing does not establish
native-server certification or full API equivalence.