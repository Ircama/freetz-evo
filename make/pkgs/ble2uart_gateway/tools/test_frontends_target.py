#!/usr/bin/env python3
"""Isolated frontend tests or read-only verification of existing native Domoticz integrations."""

import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import select
import shutil
import socket
import subprocess
import tempfile
import threading
import time

from replay_capture import Firmware, crc16


def equal(expected, actual):
    if isinstance(expected, dict) and isinstance(actual, dict):
        return expected.keys() == actual.keys() and all(equal(value, actual[key]) for key, value in expected.items() if key != "Host Local Date")
    if isinstance(expected, list) and isinstance(actual, list):
        return len(expected) == len(actual) and all(equal(left, right) for left, right in zip(expected, actual))
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(expected) is type(actual) and expected == actual
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return math.isclose(expected, actual, rel_tol=1e-10, abs_tol=1e-10)
    return expected == actual


def run(args):
    import paho.mqtt.client as mqtt

    started = time.monotonic()
    directory = Path(tempfile.mkdtemp(prefix="ble-frontends-isolated-"))
    os.chmod(directory, 0o700)
    firmware = Firmware()
    children, logs = [], []
    client = None
    second_client = None
    connection = None
    second_connection = None
    discovery_messages = queue.Queue()
    successful = False

    def spawn(arguments, name, environment=None):
        log = open(directory / (name + ".log"), "wb")
        logs.append(log)
        process = subprocess.Popen(arguments, stdout=log, stderr=log, env={**os.environ, **(environment or {})})
        children.append(process)
        return process

    try:
        broker_config = directory / "mosquitto.conf"
        broker_config.write_text(f"listener {args.mqtt_port} 127.0.0.1\nallow_anonymous true\npersistence false\n")
        broker_config.chmod(0o600)
        broker = spawn([args.broker, "-c", str(broker_config)], "broker")
        subscribed = threading.Event()
        messages = queue.Queue()
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"ble-regression-observer-{os.getpid()}")
        client.on_connect = lambda connection, *_: connection.subscribe([("ble-regression/AABBCCDDEEFF/state", 1), ("ble-regression-discovery/#", 1)])
        client.on_subscribe = lambda *_: subscribed.set()
        client.on_message = lambda _, __, message: (messages if message.topic.endswith("/state") else discovery_messages).put(json.loads(message.payload))
        client.connect_async("127.0.0.1", args.mqtt_port)
        client.loop_start()
        assert subscribed.wait(15), "isolated MQTT broker/subscriber did not start"
        second_messages = queue.Queue()
        second_subscribed = threading.Event()
        second_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"ble-regression-second-observer-{os.getpid()}")
        second_client.on_connect = lambda connection, *_: connection.subscribe("ble-regression/AABBCCDDEEFF/state", qos=1)
        second_client.on_subscribe = lambda *_: second_subscribed.set()
        second_client.on_message = lambda _, __, message: second_messages.put(json.loads(message.payload))
        second_client.connect_async("127.0.0.1", args.mqtt_port)
        second_client.loop_start()
        assert second_subscribed.wait(15), "second MQTT subscriber did not start"
        assert broker.poll() is None, "isolated broker exited"

        config = {
            "version": 1, "log_level": "warn",
            "serial": {"port": firmware.path, "command_timeout_ms": 2000, "reconnect_delay_ms": 200},
            "scanner": {"filter_known_devices": False, "dup_filter": False},
            "devices": [{"mac": "AABBCCDDEEFF", "label": "Isolated regression sensor",
                         "manufacturer": "TestCo", "model": "MetadataProbe", "firmware_version": "test-only",
                         "bindkey": "000102030405060708090A0B0C0D0E0F",
                         "expose": [{"attribute": name} for name in ("temperature", "humidity", "opened", "battery_level", "new_vendor_value")]}],
            "frontends": {
                "mysensors": {"enabled": True, "bind": "127.0.0.1", "port": args.mysensors_port},
                "mqtt": {"enabled": True, "host": "127.0.0.1", "port": args.mqtt_port,
                         "client_id": f"ble-regression-gateway-{os.getpid()}", "base_topic": "ble-regression", "retain": True,
                         "domoticz_discovery": True, "discovery_prefix": "ble-regression-discovery"},
                "matter": {"enabled": not args.mqtt_only, "bind": "::1", "port": args.matter_port,
                           "store": str(directory / "matter"), "advertise": False},
            },
        }
        config_path = directory / "gateway.yaml"
        config_path.write_text(json.dumps(config))
        config_path.chmod(0o600)
        gateway = spawn([str(args.binary), "--config", str(config_path)], "gateway",
                        {"BLE2UART_GATEWAY_CONTROL_SOCKET": str(directory / "control/control.sock"), "RUST_LOG": "warn"})
        assert firmware.scanning.wait(20), "gateway did not configure simulated firmware"
        assert gateway.poll() is None, "isolated gateway exited"
        presentations = {}
        with socket.create_connection(("127.0.0.1", args.mysensors_port), timeout=15) as mysensors_socket:
            with mysensors_socket.makefile("r", encoding="utf-8") as stream:
                while not all(key in presentations for key in ("model", "firmware", "temperature")):
                    line = stream.readline().rstrip("\n")
                    assert line, "isolated MySensors connection closed during presentation"
                    fields = line.split(";", 5)
                    if len(fields) != 6 or fields[0] != "10":
                        continue
                    if fields[1:5] == ["255", "3", "0", "11"]:
                        presentations["model"] = fields[5]
                    elif fields[1:5] == ["255", "3", "0", "12"]:
                        presentations["firmware"] = fields[5]
                    elif fields[1] == "0" and fields[2] == "0":
                        presentations["temperature"] = fields[5]
        assert presentations["model"] == "TestCo MetadataProbe"
        assert presentations["firmware"] == "test-only"
        assert presentations["temperature"].endswith(" temperature") and len(presentations["temperature"].encode()) <= 25

        document = json.loads(args.fixtures.read_text())
        names = {"custom", "custom_enc", "atc1441", "atc1441_enc", "mi_like", "bt_home", "bt_home_enc", "bt_home_v2"}
        selected = {}
        for vector in document["roundtrips"]:
            name = vector["format"].removesuffix("_format")
            if name not in names:
                continue
            encrypted = bool(vector.get("encrypted")) or name in {"custom_enc", "atc1441_enc", "bt_home_enc"}
            selected.setdefault((name, encrypted), vector)
        assert {name for name, _ in selected} == names
        latest = None
        verified = []
        for sequence, ((name, encrypted), vector) in enumerate(sorted(selected.items()), 1):
            firmware.advertise(bytes.fromhex(vector["encoded"]), sequence)
            deadline = time.monotonic() + 15
            while True:
                state = messages.get(timeout=max(0.1, deadline - time.monotonic()))
                if state["radio"]["event_type"] == sequence:
                    break
                assert time.monotonic() < deadline, "MQTT state did not reach expected sequence"
            assert state["wire_format"] == name, "MQTT format mismatch"
            assert equal(vector["decoded"], state["decoded"]), "MQTT lost decoded fields"
            assert "latest_values" in state
            assert state["device"] == {"name": "Isolated regression sensor", "manufacturer": "TestCo", "model": "MetadataProbe", "firmware_version": "test-only"}
            latest = state
            verified.append(name + (":encrypted" if encrypted else ":plain"))

        deadline = time.monotonic() + 15
        while True:
            discovery = discovery_messages.get(timeout=max(0.1, deadline - time.monotonic()))
            if discovery.get("unique_id") == "ble2uart_AABBCCDDEEFF_a_temperature":
                assert discovery["name"] == "temperature"
                assert discovery["device"] == {"identifiers": ["ble2uart_AABBCCDDEEFF"], "name": "Isolated regression sensor", "manufacturer": "TestCo", "model": "MetadataProbe", "sw_version": "test-only"}
                break

        matter = {"requested": not args.mqtt_only, "commissioned": False, "full_json_verified": False}
        expected_observer_state = latest
        if not args.mqtt_only:
            import websocket
            controller_store = directory / "controller"
            controller = spawn([args.controller, "--port", str(args.controller_port), "--bind", "127.0.0.1",
                                "--store", str(controller_store), "--peer", f"[::1]:{args.matter_port}"],
                               "controller", {"MATTER_MDNS_INTERFACE": "lo", "RUST_LOG": "warn"})
            deadline = time.monotonic() + 20
            connection = None
            while time.monotonic() < deadline:
                try:
                    connection = websocket.create_connection(f"ws://127.0.0.1:{args.controller_port}/ws", timeout=5)
                    break
                except (OSError, websocket.WebSocketException):
                    assert controller.poll() is None, "isolated controller exited before WebSocket startup"
                    threading.Event().wait(0.1)
            assert connection is not None, "isolated controller WebSocket did not start"
            connection.settimeout(args.matter_timeout)
            connection.send(json.dumps({"message_id":"ble-frontend-commission", "command":"commission_on_network", "args":{"setup_pin_code":20202021}}))
            while True:
                message = json.loads(connection.recv())
                if message.get("message_id") == "ble-frontend-commission":
                    assert "error_code" not in message, "Matter commissioning rejected: " + message.get("details", "unspecified error")
                    break
            nodes_path = controller_store / "controller-nodes.json"
            deadline = time.monotonic() + args.matter_timeout
            while time.monotonic() < deadline:
                assert gateway.poll() is None, "gateway exited during Matter commissioning"
                assert controller.poll() is None, "controller exited during commissioning"
                try:
                    nodes = json.loads(nodes_path.read_text())
                    node = next(iter(nodes.values()))
                    attributes = node["attributes"]
                    endpoint = json.loads((directory / "matter/endpoints.json").read_text())["AABBCCDDEEFF"]
                    blocks = attributes[f"{endpoint}/{0xFFF1FC00}/3"]
                    raw = b"".join(base64.b64decode(block, validate=True) for block in blocks)
                    state = json.loads(raw)
                    if node["interview_version"] > 0 and state["radio"]["event_type"] == len(selected):
                        assert equal(latest, state), "Matter vendor cluster differs from complete MQTT state"
                        assert attributes[f"{endpoint}/{0xFFF1FC00}/2"] == len(raw)
                        assert attributes[f"{endpoint}/57/1"] == "TestCo"
                        assert attributes[f"{endpoint}/57/3"] == "MetadataProbe"
                        assert attributes[f"{endpoint}/57/5"] == "Isolated regression sensor"
                        assert attributes[f"{endpoint}/57/10"] == "test-only"
                        matter.update(commissioned=True, full_json_verified=True, attributes=len(attributes), blocks=len(blocks))
                        break
                except (FileNotFoundError, KeyError, StopIteration, ValueError, TypeError):
                    pass
                threading.Event().wait(0.1)
            assert matter["full_json_verified"], "Matter commissioning/interview did not produce a complete matching vendor snapshot"
            connection.send(json.dumps({"message_id":"ble-frontend-listen", "command":"start_listening"}))
            while True:
                message = json.loads(connection.recv())
                if message.get("message_id") == "ble-frontend-listen":
                    assert "error_code" not in message, "Matter controller rejected event registration"
                    break
            second_connection = websocket.create_connection(f"ws://127.0.0.1:{args.controller_port}/ws", timeout=30)
            second_connection.send(json.dumps({"message_id":"ble-second-listen", "command":"start_listening"}))
            while True:
                message = json.loads(second_connection.recv())
                if message.get("message_id") == "ble-second-listen":
                    assert "error_code" not in message
                    break
            firmware.advertise(bytes.fromhex(sorted(selected.items())[-1][1]["encoded"]), len(selected) + 1)
            deadline = time.monotonic() + 20
            while True:
                updated = messages.get(timeout=max(0.1, deadline - time.monotonic()))
                if updated["radio"]["event_type"] == len(selected) + 1:
                    break
                assert time.monotonic() < deadline
            matter["subscription_update_verified"] = False
            connection.settimeout(30)
            while time.monotonic() < deadline:
                message = json.loads(connection.recv())
                if message.get("event") != "attribute_updated":
                    continue
                event = message.get("data", [])
                if len(event) != 3 or event[1] != f"{endpoint}/{0xFFF1FC00}/3":
                    continue
                try:
                    state = json.loads(b"".join(base64.b64decode(block, validate=True) for block in event[2]))
                except (ValueError, TypeError):
                    continue
                if state["radio"]["event_type"] == len(selected) + 1:
                    assert equal(updated, state), "Matter subscription lost complete state values"
                    matter["subscription_update_verified"] = True
                    break
            assert matter["subscription_update_verified"], "Matter subscription did not deliver the next complete state"
            matter["two_websocket_clients_verified"] = False
            while time.monotonic() < deadline:
                message = json.loads(second_connection.recv())
                event = message.get("data", [])
                if message.get("event") != "attribute_updated" or len(event) != 3 or event[1] != f"{endpoint}/{0xFFF1FC00}/3":
                    continue
                try:
                    state = json.loads(b"".join(base64.b64decode(block, validate=True) for block in event[2]))
                except (ValueError, TypeError):
                    continue
                if state["radio"]["event_type"] == len(selected) + 1:
                    assert equal(updated, state), "second Matter observer lost state"
                    matter["two_websocket_clients_verified"] = True
                    break
            assert matter["two_websocket_clients_verified"]
            expected_observer_state = updated

        deadline = time.monotonic() + 15
        while True:
            observed = second_messages.get(timeout=max(0.1, deadline - time.monotonic()))
            if observed["radio"]["event_type"] == expected_observer_state["radio"]["event_type"]:
                assert equal(expected_observer_state, observed), "concurrent MQTT observers differ"
                break

        report = {"success": True, "formats": verified, "mqtt_states_verified": len(verified), "matter": matter,
                  "binary_sha256": hashlib.sha256(args.binary.read_bytes()).hexdigest(),
                  "elapsed_seconds": round(time.monotonic() - started, 2), "live_serial_used": False,
                  "mysensors_enabled": True, "mysensors_metadata": presentations,
                  "mqtt_metadata_verified": True, "matter_metadata_verified": not args.mqtt_only,
                  "two_mqtt_subscribers_verified": True,
                  "live_config_modified": False}
        print(json.dumps(report, indent=2))
        successful = True
    finally:
        if second_connection is not None:
            second_connection.close()
        if connection is not None:
            connection.close()
        if client is not None:
            client.disconnect()
            client.loop_stop()
        if second_client is not None:
            second_client.disconnect()
            second_client.loop_stop()
        for process in reversed(children):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        firmware.close()
        for handle in logs:
            handle.close()
        if successful:
            shutil.rmtree(directory)
        else:
            print("Failed isolated-test logs retained privately at:", directory)


def check_controller_idle(args):
    with tempfile.TemporaryDirectory(prefix="ble-controller-idle-") as directory:
        process = subprocess.Popen([args.controller, "--bind", "127.0.0.1", "--port", str(args.controller_port),
                                    "--peer", "[::1]:5599", "--store", directory],
                                   env={**os.environ, "MATTER_MDNS_INTERFACE": "lo", "RUST_LOG": "matter_bridge=debug,rs_matter=warn"},
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            try:
                output, _ = process.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    output, _ = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    output, _ = process.communicate()
            ticks = output.count("watchdog tick")
            assert process.returncode in (0, -15), "isolated controller exited unexpectedly"
            assert ticks >= 2, f"controller watchdog dormant without a WebSocket client: {ticks} ticks"
            print(json.dumps({"success": True, "mode": "controller-idle", "watchdog_ticks_without_client": ticks}))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


def check_mdns(args):
    import struct
    from dnslib import DNSRecord, DNSQuestion, QTYPE

    index = socket.if_nametoindex(args.mdns_interface)
    family = socket.AF_INET6 if args.mdns_ipv6 else socket.AF_INET
    query = DNSRecord()
    query.add_question(DNSQuestion(args.mdns_service, QTYPE.PTR, qclass=0x8001))
    with socket.socket(family, socket.SOCK_DGRAM) as client:
        if args.mdns_ipv6:
            client.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, index)
            client.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 255)
            client.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_RECVHOPLIMIT, 1)
            client.bind(("::", 0))
            destination = ("ff02::fb", 5353, 0, index)
            expected_level, expected_kind = socket.IPPROTO_IPV6, socket.IPV6_HOPLIMIT
        else:
            if not args.mdns_ipv4_address:
                raise ValueError("IPv4 discovery requires --mdns-ipv4-address for the selected interface")
            client.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(args.mdns_ipv4_address))
            client.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
            client.setsockopt(socket.IPPROTO_IP, socket.IP_RECVTTL, 1)
            client.bind((args.mdns_ipv4_address, 0))
            destination = ("224.0.0.251", 5353)
            expected_level, expected_kind = socket.IPPROTO_IP, socket.IP_TTL
        client.sendto(query.pack(), destination)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if not select.select([client], [], [], max(0, deadline - time.monotonic()))[0]:
                break
            data, ancillary, _, peer = client.recvmsg(9000, 256)
            response = DNSRecord.parse(data)
            records = list(response.rr) + list(response.auth) + list(response.ar)
            services = [record for record in records if record.rtype == QTYPE.SRV and record.rdata.port == args.matter_port]
            if not services:
                continue
            hops = [struct.unpack("i", value[:4])[0] for level, kind, value in ancillary
                    if level == expected_level and kind == expected_kind]
            assert hops == [255], f"mDNS IP hop limit must be 255, received {hops}"
            assert peer[1] == 5353, "mDNS response used an unexpected source port"
            assert all(str(record.rname).endswith(args.mdns_service.rstrip(".") + ".") for record in services)
            for service in services:
                assert any(record.rtype == QTYPE.PTR and record.rdata.label == service.rname for record in records), "DNS-SD browse pointer missing"
                assert any(record.rtype == QTYPE.TXT and record.rname == service.rname for record in records), "Matter DNS-SD TXT metadata missing"
                assert any(record.rtype == QTYPE.AAAA and record.rname == service.rdata.target for record in records), "Matter service target has no IPv6 address"
            report = {"success": True, "mode": "mdns-readonly", "service": args.mdns_service,
                      "interface": args.mdns_interface, "ipv6_transport": args.mdns_ipv6, "ip_hop_limit": hops[0],
                      "ptr_txt_and_target_ipv6_verified": True,
                      "instances": [{"name": str(record.rname), "target": str(record.rdata.target),
                                     "port": record.rdata.port, "dns_ttl_seconds": record.ttl} for record in services]}
            if args.report:
                args.report.write_text(json.dumps(report, indent=2) + "\n")
                args.report.chmod(0o600)
            print(json.dumps(report, indent=2))
            return
    raise AssertionError("no matching Matter DNS-SD service responded on the selected interface")


def domoticz_environment(rows, mac, matter_id=None):
    identifier = str(matter_id) if matter_id is not None else f"ble2uart_{mac}"
    combined = next((row for row in rows if row["DeviceID"] == identifier and row["Type"] == 82), None)
    if combined is not None:
        temperature, humidity, *_ = combined["sValue"].split(";")
        selected = [combined]
    else:
        temperature_id = identifier if matter_id is not None else identifier + "_a_temperature"
        humidity_id = identifier if matter_id is not None else identifier + "_a_humidity"
        temperature_row = next(row for row in rows if row["DeviceID"] == temperature_id and row["Type"] == 80)
        humidity_row = next(row for row in rows if row["DeviceID"] == humidity_id and row["Type"] == 81)
        temperature, humidity = temperature_row["sValue"], humidity_row["nValue"]
        selected = [temperature_row, humidity_row]
    return {"temperature": float(temperature), "humidity": int(humidity),
            "batteries": [row["BatteryLevel"] for row in selected],
            "device_ids": [row["ID"] for row in selected],
            "timestamps": [row["LastUpdate"] for row in selected]}


def run_live(args):
    import sqlite3
    import paho.mqtt.client as mqtt
    import websocket

    started = time.monotonic()
    database = sqlite3.connect(args.live_domoticz_db.resolve().as_uri() + "?mode=ro", uri=True)
    database.row_factory = sqlite3.Row
    controller = None
    client = None
    try:
        controller = websocket.create_connection(f"ws://127.0.0.1:{args.controller_port}/ws", timeout=30)

        def nodes(command):
            identifier = "ble-readonly-" + command
            controller.send(json.dumps({"message_id": identifier, "command": command, "args": {}}))
            while True:
                message = json.loads(controller.recv())
                if message.get("message_id") == identifier:
                    assert "error_code" not in message, message.get("details", "controller rejected request")
                    result = message["result"]
                    return result.get("nodes", []) if isinstance(result, dict) else result

        commissioned = nodes("start_listening")
        identities = {}
        for mac in args.mac:
            matches = [(node["node_id"], int(path.split("/")[0])) for node in commissioned
                       for path, value in node["attributes"].items()
                       if path.endswith(f"/{0xFFF1FC00}/4") and value == mac]
            assert len(matches) == 1, f"Matter identity missing or duplicated: {mac}"
            identities[mac] = matches[0]
        assert len(set(identities.values())) == len(args.mac), "physical Matter identities overlap"

        def snapshot():
            result = {}
            for protocol, hardware in (("mqtt", args.mqtt_hardware), ("matter", args.matter_hardware)):
                rows = database.execute("SELECT ID,DeviceID,Type,nValue,sValue,BatteryLevel,LastUpdate FROM DeviceStatus WHERE HardwareID=?", (hardware,)).fetchall()
                result[protocol] = {}
                for mac in args.mac:
                    node, parent = identities[mac]
                    result[protocol][mac] = domoticz_environment(rows, mac, node * 256 + parent if protocol == "matter" else None)
            return result

        messages = queue.Queue()
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"ble-readonly-verifier-{os.getpid()}")
        topics = [(f"ble2uart-gateway/{mac}/state", 1) for mac in args.mac]
        topics.extend((f"homeassistant/sensor/ble2uart_{mac}_a_battery_level/config", 1) for mac in args.mac)
        client.on_connect = lambda connection, *_: connection.subscribe(topics)
        client.on_message = lambda _, __, message: messages.put((message.topic, message.retain, json.loads(message.payload)))
        client.connect("127.0.0.1", args.mqtt_port)
        client.loop_start()
        latest = {}
        diagnostics = set()
        updates = {mac: set() for mac in args.mac}
        device_updates = {(protocol, mac): set() for protocol in ("mqtt", "matter") for mac in args.mac}
        deadline = time.monotonic() + args.matter_timeout
        while time.monotonic() < deadline:
            topic, retained, state = messages.get(timeout=max(0.1, deadline - time.monotonic()))
            if topic.startswith("homeassistant/"):
                assert retained and state["device_class"] == "battery" and state["entity_category"] == "diagnostic"
                diagnostics.add(state["device"]["identifiers"][0])
                continue
            mac = topic.split("/")[1]
            latest[mac] = state
            if not retained:
                updates[mac].add(state["received_at"])
            try:
                current = snapshot()
            except StopIteration:
                continue
            for protocol in current:
                for address, reading in current[protocol].items():
                    device_updates[protocol, address].add(tuple(reading["timestamps"]))
            if all(len(samples) >= 2 for samples in updates.values()) and all(len(samples) >= 2 for samples in device_updates.values()) and len(diagnostics) == len(args.mac):
                break
        else:
            raise AssertionError("not enough fresh updates from each native Domoticz thermometer")
        assert all(len(samples) >= 2 for samples in updates.values())
        assert all(len(samples) >= 2 for samples in device_updates.values())

        actual_nodes = nodes("get_nodes")
        final = snapshot()
        report = {"success": True, "mode": "live-readonly", "devices": {}, "synthetic_values_published": False,
                  "live_config_modified": False, "database_opened_readonly": True}
        for mac in args.mac:
            node_id, parent = identities[mac]
            attributes = next(node["attributes"] for node in actual_nodes if node["node_id"] == node_id)
            parts = attributes[f"{parent}/29/3"]
            temperature = next(value / 100 for path, value in attributes.items() if int(path.split("/")[0]) in parts and path.endswith("/1026/0") and value is not None)
            humidity = next(value / 100 for path, value in attributes.items() if int(path.split("/")[0]) in parts and path.endswith("/1029/0") and value is not None)
            battery = next(value / 2 for path, value in attributes.items() if int(path.split("/")[0]) in parts and path.endswith("/47/12") and value is not None)
            values = latest[mac]["latest_values"]
            for protocol in final:
                reading = final[protocol][mac]
                assert abs(reading["temperature"] - values["temperature"]["value"]) <= 0.15, f"{protocol} mixed/stale temperature: {mac}"
                assert abs(reading["humidity"] - values["humidity"]["value"]) <= 1.05, f"{protocol} mixed/stale humidity: {mac}"
                assert all(level == values["battery_level"]["value"] for level in reading["batteries"]), f"{protocol} battery mismatch: {mac}"
            assert abs(temperature - values["temperature"]["value"]) <= 0.15
            assert abs(humidity - values["humidity"]["value"]) <= 1.05
            assert battery == values["battery_level"]["value"]
            report["devices"][mac] = {"mqtt_fresh_updates": len(updates[mac]), "matter_node": node_id, "matter_parent": parent,
                                      "native_fresh_updates": {protocol: len(device_updates[protocol, mac]) for protocol in final},
                                      "mqtt": final["mqtt"][mac], "matter": final["matter"][mac]}
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        if args.report:
            args.report.write_text(json.dumps(report, indent=2) + "\n")
            args.report.chmod(0o600)
        print(json.dumps(report, indent=2))
    finally:
        if client is not None:
            client.disconnect()
            client.loop_stop()
        if controller is not None:
            controller.close()
        database.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--live-domoticz-db", type=Path)
    parser.add_argument("--mqtt-hardware", type=int)
    parser.add_argument("--matter-hardware", type=int)
    parser.add_argument("--mac", action="append", default=[])
    parser.add_argument("--report", type=Path)
    parser.add_argument("--broker", default="mosquitto")
    parser.add_argument("--controller", default="matter-bridge")
    parser.add_argument("--check-controller-idle", action="store_true")
    parser.add_argument("--check-mdns", action="store_true")
    parser.add_argument("--mdns-interface", default="lan")
    parser.add_argument("--mdns-ipv6", action="store_true")
    parser.add_argument("--mdns-ipv4-address")
    parser.add_argument("--mdns-service", default="_matter._tcp.local.")
    parser.add_argument("--mqtt-port", type=int, default=18891)
    parser.add_argument("--mysensors-port", type=int, default=50039)
    parser.add_argument("--matter-port", type=int, default=5569)
    parser.add_argument("--controller-port", type=int, default=5589)
    parser.add_argument("--matter-timeout", type=int, default=120)
    parser.add_argument("--mqtt-only", action="store_true")
    args = parser.parse_args()
    if args.check_mdns:
        check_mdns(args)
    elif args.check_controller_idle:
        check_controller_idle(args)
    elif args.live_domoticz_db:
        import re
        args.mac = [mac.replace(":", "").upper() for mac in args.mac]
        if not args.mqtt_hardware or not args.matter_hardware or len(set(args.mac)) < 2 or any(not re.fullmatch(r"[0-9A-F]{12}", mac) for mac in args.mac):
            parser.error("live mode needs both native hardware IDs and at least two distinct --mac addresses")
        run_live(args)
    else:
        if not args.binary or not args.fixtures:
            parser.error("isolated mode requires --binary and --fixtures")
        run(args)


if __name__ == "__main__":
    main()