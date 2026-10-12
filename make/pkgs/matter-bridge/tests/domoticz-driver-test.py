#!/usr/bin/env python3
"""Drive matter-bridge exactly like the Domoticz Matter driver does.

Reference: domoticz/hardware/Matter.cpp
  - connects to ws://<host>:<port>/ws
  - requires server_info with schema_version + min_supported_schema_version
  - sends start_listening, then device_command / write_attribute
  - expects attribute_updated events as [node_id, "ep/cluster/attr", value]
"""
import json
import sys
from websockets.sync.client import connect

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5599
URI = f"ws://127.0.0.1:{PORT}/ws"  # same path Domoticz uses

events = []
failures = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  -> ' + detail}")
    if not ok:
        failures.append(name)


def collect(ws, message_id, timeout=3.0):
    """Read until the reply for message_id arrives, collecting events."""
    got = None
    while True:
        msg = json.loads(ws.recv(timeout=timeout))
        if "event" in msg:
            events.append(msg)
            continue
        if str(msg.get("message_id")) == str(message_id):
            got = msg
            break
    return got


with connect(URI, open_timeout=5) as ws:
    print(f"connected to {URI}")

    # --- 1. server_info (pushed immediately by the bridge) -------------------
    info = json.loads(ws.recv(timeout=5))
    while info.get("event") != "server_info":
        info = json.loads(ws.recv(timeout=5))
    data = info["data"]
    check("server_info event", info.get("event") == "server_info", json.dumps(info)[:120])
    check("schema_version present", "schema_version" in data, json.dumps(data)[:160])
    check("min_supported_schema_version present (Domoticz requirement)",
          "min_supported_schema_version" in data, json.dumps(data)[:160])
    check("schema_version >= 3 (Domoticz MIN_SCHEMA)", data.get("schema_version", 0) >= 3,
          str(data.get("schema_version")))
    check("min_supported_schema_version <= 11 (Domoticz OUR_SCHEMA)",
          data.get("min_supported_schema_version", 99) <= 11,
          str(data.get("min_supported_schema_version")))
    check("sdk_version present", bool(data.get("sdk_version")), json.dumps(data)[:160])
    check("fabric_id + compressed_fabric_id present",
          "fabric_id" in data and "compressed_fabric_id" in data, json.dumps(data)[:160])

    # --- 2. start_listening -------------------------------------------------
    ws.send(json.dumps({"message_id": "1", "command": "start_listening", "args": {}}))
    reply = collect(ws, "1")
    nodes = reply.get("result")
    check("start_listening returns a result", nodes is not None, json.dumps(reply)[:160])
    check("result is a node array", isinstance(nodes, list), type(nodes).__name__)
    if isinstance(nodes, list):
        ok = True
        for node in nodes:
            if "node_id" not in node or "attributes" not in node:
                ok = False
            elif not (1 <= node["node_id"] <= 255):  # Domoticz ignores out-of-range ids
                ok = False
            else:
                for path in node["attributes"]:
                    parts = path.split("/")
                    if len(parts) != 3 or not all(p.isdigit() for p in parts):
                        ok = False
        check("each node has node_id 1..255 + attributes keyed as 'ep/cluster/attr'", ok,
              json.dumps(nodes)[:200])
        print(f"      nodes reported: {[(n['node_id'], len(n['attributes'])) for n in nodes]}")

    # --- 3. device_command: OnOff cluster 6 (Domoticz sendOnOff) ------------
    before = len(events)
    ws.send(json.dumps({"message_id": "2", "command": "device_command", "args": {
        "node_id": 1, "endpoint_id": 1, "cluster_id": 6,
        "command_name": "On", "payload": {}}}))
    reply = collect(ws, "2")
    check("OnOff 'On' acknowledged (result null)", reply.get("result", "x") is None,
          json.dumps(reply)[:160])
    new = events[before:]
    check("attribute_updated emitted for 1/6/0",
          any(e["data"][:2] == [1, "1/6/0"] and e["data"][2] is True for e in new),
          json.dumps(new)[:200])
    check("attribute_updated format [node_id, path, value]",
          all(isinstance(e["data"], list) and len(e["data"]) == 3 for e in new),
          json.dumps(new)[:200])

    # --- 4. device_command: LevelControl cluster 8 (Domoticz sendLevel) -----
    before = len(events)
    ws.send(json.dumps({"message_id": "3", "command": "device_command", "args": {
        "node_id": 1, "endpoint_id": 1, "cluster_id": 8,
        "command_name": "MoveToLevelWithOnOff",
        "payload": {"level": 128, "optionsMask": 1, "optionsOverride": 1,
                    "transitionTime": 0}}}))
    reply = collect(ws, "3")
    check("MoveToLevelWithOnOff acknowledged", reply.get("result", "x") is None,
          json.dumps(reply)[:160])
    new = events[before:]
    check("attribute_updated emitted for 1/8/0 with level 128",
          any(e["data"][:2] == [1, "1/8/0"] and e["data"][2] == 128 for e in new),
          json.dumps(new)[:200])

    # --- 5. write_attribute (Domoticz color/climate path) -------------------
    ws.send(json.dumps({"message_id": "4", "command": "write_attribute", "args": {
        "node_id": 1, "attribute_path": "1/6/0", "value": False}}))
    reply = collect(ws, "4")
    check("write_attribute acknowledged", reply.get("result", "x") is None,
          json.dumps(reply)[:160])

    # --- 6. unknown command -> error_code 9 ---------------------------------
    ws.send(json.dumps({"message_id": "5", "command": "no_such_command", "args": {}}))
    reply = collect(ws, "5")
    check("unknown command answered with error_code", "error_code" in reply,
          json.dumps(reply)[:160])
    check("unknown command error_code == 9", reply.get("error_code") == 9,
          json.dumps(reply)[:160])

    # --- 7. commissioning commands are refused without crashing -------------
    ws.send(json.dumps({"message_id": "6", "command": "commission_with_code",
                        "args": {"code": "1234"}}))
    reply = collect(ws, "6")
    check("controller-only command refused with error_code 9",
          reply.get("error_code") == 9, json.dumps(reply)[:160])

print()
if failures:
    print(f"RESULT: {len(failures)} CHECK(S) FAILED: {', '.join(failures)}")
    sys.exit(1)
print("RESULT: ALL CHECKS PASSED")
