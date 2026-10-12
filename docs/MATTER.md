# Matter in Domoticz without Node.js

Domoticz 2026.4 has a Matter driver (`hardware/Matter.cpp`) that is a *client*: it opens a WebSocket connection to a **Matter controller** and exchanges JSON messages with it. The controller is a separate program, and `matterjs-server` (Node.js) is only one possible implementation of it.

In this tree the controller is native: [`matter-bridge`](make/matter-bridge.md) provides both the WebSocket API and the Matter controller, so Domoticz runs without Node.js and without any off-box server. [`freetz-matter`](make/freetz-matter.md) is the Matter accessory on the same box.

```
Domoticz ──WebSocket + python-matter-server JSON API──> controller ──Matter──> device
          TCP 5580, this is *not* Matter                 UDP 5540: mDNS discovery,
                                                         PASE commissioning, CASE
                                                         sessions, TLV interaction model
```

* **first hop** — WebSocket on TCP 5580 with the `python-matter-server` JSON API described in section 1. It exists because that is how the reference server exposes its controller; it is not Matter.
* **second hop** — Matter itself: UDP 5540, mDNS-based operational discovery, PASE for commissioning, CASE for session establishment and a TLV interaction model for reads, writes, commands and subscriptions.

`matter-bridge` implements the first hop as a server and the second one as a controller: it commissions an uncommissioned `freetz-matter` on `[::1]:5540` by itself, reads its attributes and subscribes to its reports. Both packages also work with other controllers and accessories.

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

## Setup

**Local, without off-box software.** Enable the `matter-bridge` and
`freetz-matter` services, then add a Matter hardware entry in Domoticz pointing
at `127.0.0.1:5580`; the local accessory is commissioned automatically. Keep
both fabric stores (default `/tmp/flash/matter-bridge`) in the `modsave`
archive, otherwise the fabric is lost on reboot.

**Off-box controller.** `python-matter-server` on a glibc Linux host (NAS,
Raspberry Pi, PC or the official container
`ghcr.io/home-assistant-libs/python-matter-server`) is a drop-in replacement:
Domoticz speaks exactly the API of section 1, so only the WebSocket address
changes. Matter-over-Thread devices additionally need a border router on the
same IPv6 network — the box provides it with
[`ot-br-posix`](make/ot-br-posix.md) and [`openthread`](make/openthread.md)
plus an 802.15.4 RCP dongle.

**Scope.** `matter-bridge` is a known-address controller: PASE/CASE, attribute
reads and writes, commands and subscriptions are implemented, while multicast
discovery, Wi-Fi/Thread credential provisioning and verified Device Attestation
are not; it is not a certified replacement for the reference servers, see
[matter-bridge.md](make/matter-bridge.md). Porting `connectedhomeip` — the SDK
behind both reference servers, uClibc/MIPS excluded by its bindings — is not an
option here: it builds with GN/ninja and has 79 submodules.
