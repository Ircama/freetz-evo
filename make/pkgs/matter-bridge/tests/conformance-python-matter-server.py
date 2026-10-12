#!/usr/bin/env python3
"""Conformance test: validate matter-bridge against the reference server.

Every message the bridge sends is parsed with python-matter-server 8.1.2's own
dataclasses (matter_server.common.models) and compared against the reference
constants (SCHEMA_VERSION / MIN_SCHEMA_VERSION / EventType / error codes).
"""
import json
import sys
import importlib.util

PMS = "/tmp/pms/python_matter_server-8.1.2"


def load_models():
    sys.path.insert(0, PMS)
    from matter_server.common import models  # noqa
    from matter_server.common.const import SCHEMA_VERSION  # noqa
    from matter_server.common.errors import InvalidCommand, InvalidArguments, NodeNotExists  # noqa

    # matter_server.server.const pulls in the aiohttp/SDK stack, so read the
    # authoritative MIN_SCHEMA_VERSION straight from the reference source.
    import re
    with open(f"{PMS}/matter_server/server/const.py", encoding="utf-8") as fh:
        MIN_SCHEMA_VERSION = int(re.search(r"MIN_SCHEMA_VERSION\s*=\s*(\d+)", fh.read()).group(1))
    return models, SCHEMA_VERSION, MIN_SCHEMA_VERSION, (InvalidCommand, InvalidArguments, NodeNotExists)


models, SCHEMA_VERSION, MIN_SCHEMA_VERSION, ERRS = load_models()
EventType = models.EventType
from websockets.sync.client import connect  # noqa: E402

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5599
failures = []
events = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  -> ' + detail}")
    if not ok:
        failures.append(name)


def validate_event(msg):
    """Parse an event with the upstream EventMessage dataclass."""
    ev = models.EventMessage(**msg)
    ev.event = EventType(msg["event"])  # raises if the name is not a known EventType
    return ev


def validate_success(msg):
    return models.SuccessResultMessage(**msg)


def validate_error(msg):
    return models.ErrorResultMessage(**msg)


def collect(ws, message_id, timeout=3.0):
    while True:
        msg = json.loads(ws.recv(timeout=timeout))
        if "event" in msg:
            validate_event(msg)
            events.append(msg)
            continue
        if str(msg.get("message_id")) == str(message_id):
            return msg


with connect(f"ws://127.0.0.1:{PORT}/ws", open_timeout=5) as ws:
    # ---------- 1. first frame: flat ServerInfoMessage ---------------------
    info = json.loads(ws.recv(timeout=5))
    check("first frame is the unsolicited server info (upstream contract)",
          "event" not in info and "message_id" not in info, json.dumps(info)[:160])
    check("server info detected by top-level sdk_version (Domoticz dispatch)",
          "sdk_version" in info, json.dumps(info)[:160])
    srv = models.ServerInfoMessage(**info)
    check("frame validates as upstream ServerInfoMessage (flat, no envelope)", srv is not None)
    unknown = set(info) - set(models.ServerInfoMessage.__dataclass_fields__)
    check("contains no field unknown to the reference model", not unknown, str(unknown))
    check(f"schema_version == upstream SCHEMA_VERSION ({SCHEMA_VERSION})",
          srv.schema_version == SCHEMA_VERSION, str(srv.schema_version))
    check(f"min_supported_schema_version == upstream MIN_SCHEMA_VERSION ({MIN_SCHEMA_VERSION})",
          srv.min_supported_schema_version == MIN_SCHEMA_VERSION,
          str(srv.min_supported_schema_version))
    check("sdk_version is a non-empty string", bool(srv.sdk_version), repr(srv.sdk_version))
    check("fabric_id / compressed_fabric_id are ints",
          isinstance(srv.fabric_id, int) and isinstance(srv.compressed_fabric_id, int))
    check("wifi/thread credentials + bluetooth flags are bools",
          all(isinstance(v, bool) for v in
              (srv.wifi_credentials_set, srv.thread_credentials_set, srv.bluetooth_enabled)))

    # ---------- 2. start_listening ----------------------------------------
    ws.send(json.dumps({"message_id": "1", "command": "start_listening", "args": {}}))
    reply = collect(ws, "1")
    validate_success(reply)
    nodes = reply["result"]
    check("start_listening returns a node array (upstream returns the node list)",
          isinstance(nodes, list) and len(nodes) > 0, json.dumps(reply)[:160])
    ok = all("node_id" in n and "attributes" in n for n in nodes)
    check("nodes carry node_id + attributes (shape used by HandleNode)", ok,
          json.dumps(nodes)[:200])
    attr_paths = [p for n in nodes for p in n["attributes"]]
    ok = all(len(p.split("/")) == 3 and all(x.isdigit() for x in p.split("/"))
             for p in attr_paths)
    check("attribute keys are 'endpoint/cluster/attribute'", ok, str(attr_paths[:5]))

    # ---------- 3. get_nodes ----------------------------------------------
    ws.send(json.dumps({"message_id": "2", "command": "get_nodes", "args": {}}))
    reply = collect(ws, "2")
    validate_success(reply)
    check("get_nodes returns the same node set",
          isinstance(reply["result"], list) and len(reply["result"]) == len(nodes))

    # ---------- 4. read_attribute -----------------------------------------
    ws.send(json.dumps({"message_id": "3", "command": "read_attribute",
                        "args": {"node_id": 1, "attribute_path": "1/8/0"}}))
    reply = collect(ws, "3")
    validate_success(reply)
    check("read_attribute returns the stored value (128)", reply["result"] == 128,
          json.dumps(reply)[:120])

    # missing attribute -> NodeNotExists (error code 5)
    ws.send(json.dumps({"message_id": "4", "command": "read_attribute",
                        "args": {"node_id": 1, "attribute_path": "1/99/0"}}))
    reply = collect(ws, "4")
    err = validate_error(reply)
    check("unknown attribute -> NodeNotExists (5)", err.error_code == 5, str(err.error_code))
    check("error payload has no result key (matches upstream ErrorResultMessage; "
          "JsonCpp still reports null so Domoticz's check passes)",
          "result" not in reply, json.dumps(reply)[:120])
    check("error payload carries details", isinstance(err.details, str), str(err.details))

    # bad args -> InvalidArguments (error code 8)
    ws.send(json.dumps({"message_id": "5", "command": "read_attribute", "args": {}}))
    err = validate_error(collect(ws, "5"))
    check("missing args -> InvalidArguments (8)", err.error_code == 8, str(err.error_code))

    # ---------- 5. device_command (Domoticz sendOnOff / sendLevel) ---------
    before = len(events)
    ws.send(json.dumps({"message_id": "6", "command": "device_command", "args": {
        "node_id": 1, "endpoint_id": 1, "cluster_id": 6,
        "command_name": "On", "payload": {}}}))
    reply = collect(ws, "6")
    validate_success(reply)
    check("device_command OnOff -> result null", reply["result"] is None,
          json.dumps(reply)[:120])
    new = events[before:]
    check("attribute_updated emitted for 1/6/0 (positional tuple like upstream)",
          any(e["data"][:2] == [1, "1/6/0"] and e["data"][2] is True for e in new),
          json.dumps(new)[:200])

    before = len(events)
    ws.send(json.dumps({"message_id": "7", "command": "device_command", "args": {
        "node_id": 1, "endpoint_id": 1, "cluster_id": 8,
        "command_name": "MoveToLevelWithOnOff",
        "payload": {"level": 200, "optionsMask": 1, "optionsOverride": 1,
                    "transitionTime": 0}}}))
    reply = collect(ws, "7")
    validate_success(reply)
    new = events[before:]
    check("LevelControl MoveToLevelWithOnOff -> 1/8/0 == 200",
          any(e["data"][:2] == [1, "1/8/0"] and e["data"][2] == 200 for e in new),
          json.dumps(new)[:200])

    # ---------- 6. write_attribute ----------------------------------------
    ws.send(json.dumps({"message_id": "8", "command": "write_attribute",
                        "args": {"node_id": 1, "attribute_path": "1/6/0", "value": False}}))
    validate_success(collect(ws, "8"))
    check("write_attribute accepted", True)

    # ---------- 7. unknown command == InvalidCommand (9) -------------------
    ws.send(json.dumps({"message_id": "9", "command": "bogus_command", "args": {}}))
    err = validate_error(collect(ws, "9"))
    check("unknown command -> InvalidCommand (9)", err.error_code == 9, str(err.error_code))

    # ---------- 8. controller commands refused, not silently accepted ------
    ws.send(json.dumps({"message_id": "10", "command": "commission_with_code",
                        "args": {"code": "1234"}}))
    reply = collect(ws, "10")
    err = validate_error(reply)
    check("commission_with_code refused with a valid error code", err.error_code == 9,
          str(err.error_code))

    # ---------- 9. many messages in one connection stay frame-separated ----
    ok = True
    for i in range(11, 21):
        ws.send(json.dumps({"message_id": str(i), "command": "get_nodes", "args": {}}))
    for i in range(11, 21):
        try:
            validate_success(collect(ws, str(i)))
        except Exception as exc:  # noqa: BLE001
            ok = False
            print(f"      message {i}: {exc}")
    check("20+ exchanges keep one JSON document per frame", ok)

print()
print(f"reference constants used: SCHEMA_VERSION={SCHEMA_VERSION}, "
      f"MIN_SCHEMA_VERSION={MIN_SCHEMA_VERSION}")
if failures:
    print(f"RESULT: {len(failures)} CHECK(S) FAILED: {', '.join(failures)}")
    sys.exit(1)
print("RESULT: ALL CONFORMANCE CHECKS PASSED")
