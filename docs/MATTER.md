# Matter in Domoticz without Node.js

Domoticz 2026.4 ships a **Matter hardware driver** (`hardware/Matter.cpp`), but the driver is a *client*: it opens a WebSocket connection to a **Matter controller** and exchanges JSON messages with it. The controller is a separate program, and `matterjs-server` (Node.js) is only **one** of the possible implementations — it is not part of Domoticz and not the only option.

This document describes how to run Matter with Domoticz **without Node.js**. For the local FRITZ!Box accessory, the native `matter-bridge` daemon embeds the controller and WebSocket API; no off-box server is needed. See [local setup](make/matter-bridge.md#local-setup).

## The chain has two hops, with two different protocols

```
Domoticz ──WebSocket + python-matter-server JSON API──> controller ──Matter──> device
          TCP 5580, this is *not* Matter                 UDP 5540: mDNS discovery,
                                                         PASE commissioning, CASE
                                                         sessions, TLV interaction model
```

Keep the two hops apart, because they are different protocols:

* the **first hop** exists only because that is how `python-matter-server` exposes a controller over a local WebSocket. It is the API described in section 1 below;
* the **second hop is Matter itself**: UDP on port 5540, mDNS-based operational discovery, PASE for commissioning, CASE for session establishment, and a TLV interaction model for reads, writes, commands and subscriptions.

In this tree, [`matter-bridge`](make/matter-bridge.md) implements both the WebSocket API and native Matter controller, while [`freetz-matter`](make/freetz-matter.md) is the Matter accessory. The local chain automatically commissions an uncommissioned freetz-matter at `[::1]:5540`, reads its attributes and subscribes to reports. The packages remain independent for other controllers/accessories.

## 1. How the driver talks to the server

The driver connects to `ws://<host>:<port>/ws` (default port **5580**) and speaks the **python-matter-server** JSON API:

**Handshake** (sent by the server on connect). Domoticz reads:

| Field | Use |
|---|---|
| `schema_version`, `min_schema_version` | protocol compatibility check |
| `sdk_version` | shown as server version |
| `wifi_credentials_set`, `thread_credentials_set` | whether commissioning data is already stored |
| `fabric_id`, `compressed_fabric_id` | fabric identification |

**Requests** (Domoticz → server):

```json
{"message_id": "1", "command": "start_listening", "args": null}
{"message_id": "2", "command": "device_command",  "args": {"node_id": 5, "endpoint_id": 1, "cluster_id": 6, "command_name": "Toggle", "payload": {}}}
{"message_id": "3", "command": "write_attribute","args": {"attribute_path": "1/8/0", "value": 128}}
{"message_id": "4", "command": "commission_with_code", "args": {"code": "..."}}
```

Commands used by the driver: `start_listening`, `device_command`, `write_attribute`, `commission_with_code`, `interview_node`, `remove_node`, `set_thread_dataset`, `set_wifi_credentials`, `set_default_fabric_label`.

**Responses** (server → Domoticz): `{"message_id": "N", "result": ...}`, where `result` is either an array of node objects or an object with a `nodes` array. Every node object contains `node_id` and an `attributes` map keyed `"<endpoint>/<cluster>/<attribute>"`. Errors use `{"message_id": "N", "error_code": <int>, "details": "..."}`.

**Events** (server → Domoticz): `{"event": "<type>", "data": ...}`. The most important one is `attribute_updated`, whose `data` is a **positional array**:

```json
{"event": "attribute_updated", "data": [5, "1/6/0", true]}
```

Because the driver speaks the python-matter-server API, **any** server implementing it works — the Node.js implementation is not required.

## 2. Local Setup And Full-Feature Alternative

For Domoticz and freetz-matter on the same box, enable both Matter services and add Domoticz Matter hardware at `127.0.0.1:5580`. Commissioning is automatic with the default local test accessory; preserve both fabric stores and run `modsave` after commissioning. The native daemon is a known-address controller, not a certified or full python-matter-server replacement. Multicast discovery, Wi-Fi/Thread provisioning and verified Device Attestation are not implemented. For those broader workflows, the off-box alternative remains:

| Component | Where | Why |
|---|---|---|
| **Matter controller** | `python-matter-server` on a glibc Linux host: NAS, Raspberry Pi, PC, or the official container `ghcr.io/home-assistant-libs/python-matter-server` | Pure Python, no Node.js. It embeds the CHIP SDK through the Python bindings and exposes exactly the API described above |
| **Thread border router** | On the FRITZ!Box, with the [OpenThread Border Router](make/ot-br-posix.md) (`ot-br-posix`) and [OpenThread](make/openthread.md) packages prepared in this tree, plus an 802.15.4 RCP dongle | Matter-over-Thread devices need a border router on the same IPv6 network as the controller |
| **Domoticz** | On the FRITZ!Box | Matter hardware type: host = controller IP, port = 5580 |

No Node.js is involved: the controller is Python (or the Home Assistant Matter integration, which uses the same library), and the Thread side runs on the box.

The Thread packages are the part that genuinely belongs on the FRITZ!Box: the controller needs an IPv6-reachable network, which `otbr-agent` provides, while the controller itself is a normal Linux server program and can stay on a host with more flash and RAM.

## 3. Why the controller has not run on the FRITZ!Box so far

Every ready Matter controller embeds the same C++ SDK (**connectedhomeip**):

- `python-matter-server` uses the `chip` Python bindings; `matterjs-server` uses the JavaScript bindings. Both bindings are compiled against connectedhomeip and published for glibc on x86_64/aarch64 only — they cannot link against uClibc/MIPS.
- Porting connectedhomeip is not realistic in the Freetz environment: the repository has **79 git submodules** (`pigweed`, `openthread`, `ot-br-posix`, `mbedtls`, `nanopb`, …), the build system is **GN + ninja** (GN is not part of Freetz and must be fetched as a host binary from pigweed/CIPD), and the Linux reference builds additionally expect glib, avahi/dbus and GObject introspection development packages.
- `rs-matter` (pure Rust, `no_std`) implements **both** sides, contrary to what this document assumed before the controller work started. Besides the accessory modules (`attest`, `cert`, `fabric`, `pairing`, `persist`, `respond`, `im`), it contains `onboard::Commissioner` (PASE commissioning: `ArmFailSafe` → `AddTrustedRootCertificate` → `AddNOC`, then operational discovery + CASE + `CommissioningComplete`), the controller's fabric PKI (`onboard::cac::{RcacGenerator, IcacGenerator}`, `onboard::noc::NocGenerator`), the PASE and CASE initiators (`sc/pase/initiator.rs`, `sc/case/`) and an interaction-model **client** with read/write/invoke/subscribe (`im/client.rs`). What was missing was never the protocol: it is the plumbing around it (an mDNS resolver usable on the box — rs-matter's own backends need D-Bus or desktop daemons —, the node store and a process that ties them together).
- `chip-tool` (the C++ CLI from connectedhomeip) is a ready controller, but it has the same cross-compilation blockers and needs the SDK build described above.

The native alternative now uses rs-matter inside the single [`matter-bridge`](make/matter-bridge.md) daemon. PASE/CASE, interviews, subscriptions and persistent fabric are implemented. `matter-bridge-ctl` is a separate diagnostic CLI, not the daemon's backend and not required by Domoticz.

## 4. Freetz building blocks already available

The **device** direction of rs-matter is no longer theoretical: [`freetz-matter`](make/freetz-matter.md) cross-compiles rs-matter 0.4.1 for `mips-unknown-linux-uclibc` and installs a working Matter accessory (temperature sensor, speaker, real box data in `BasicInformation`). That work also produced most of what a native *controller* would need, because the obstacles were in the toolchain rather than in the protocol:

* **Rust cross-compilation**: `make/host-tools/rust-host` plus `make/include/650-rust-cargo.mk` (custom target specs including `mips-unknown-linux-uclibc`, `build-std` for targets without a prebuilt `std`, in-registry patches for uClibc-hostile crates, MIPS `-no-pie` workaround). Two of those patches were written for this dependency graph: `RUSTIX_APPLY_UCLIBC_PATCHES_LIBC_NORAW__INT` (rustix on the libc backend without `linux_raw_dep`) and the shared `getrandom` syscall fallback. rs-matter's IDL codegen (~30 MB of Rust) also needs a memory-conscious Cargo profile. See [RUST.md](RUST.md) and [freetz-matter.md](make/freetz-matter.md).
- **WebSocket/JSON layer**: `libwebsockets`, `jsoncpp`, `cJSON` are all packaged in this tree, so the server side of the protocol (section 1) can be implemented in C++ or Rust without new dependencies.
- **Crypto**: `mbedtls` and `openssl` are packaged (Matter needs SPAKE2+, HKDF, AES-CCM, ECDSA/P-256, certificates).
- **Thread side**: [openthread](make/openthread.md) and [ot-br-posix](make/ot-br-posix.md), so a future in-box controller would not have to implement the 802.15.4/6LoWPAN layers.

The local in-box setup now needs only `domoticz`, `matter-bridge` and `freetz-matter`. The daemon directly connects its WebSocket commands to rs-matter's commissioner and interaction client, with no IPC or seed-node simulation. Real mDNS discovery and network provisioning remain outside the implemented scope. Host integration tests cover automatic PASE/CASE, reads/writes, OnOff/LevelControl, delayed subscription reports and controller restart recovery; box-specific temperature/audio and boot persistence require hardware testing.
