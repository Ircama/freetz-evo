#!/usr/bin/env python3
"""Real WS -> PASE/CASE/IM integration; requires a host rs-matter light_tests."""
import argparse
import asyncio
import json
import pathlib
import subprocess
import tempfile

import websockets

EVENTS = []

def verify_init_arguments(directory):
    packages = pathlib.Path(__file__).resolve().parents[2]
    harness = r'''
set -e
PID_FILE=/var/run/matter-test.pid
FREETZ_MATTER_PORT=5549
MATTER_BRIDGE_PORT=5599
MATTER_BRIDGE_BIND=127.0.0.1
MATTER_BRIDGE_PEER='[::1]:5549'
MATTER_BRIDGE_AUTO_LOCAL=yes
FREETZ_MATTER_STORE="$2"
MATTER_BRIDGE_STORE="$2"
expected="$3"
source <(sed -n '/^config() {/,/^stop() {/p' "$1" | sed '$d')
modlib_startdaemon() {
    config
    [[ "$*" == *"$expected"* ]]
    [[ "$*" == *"$MATTER_BRIDGE_STORE"* ]]
    [[ $(stat -c %a "$MATTER_BRIDGE_STORE") == 700 ]]
}
start
'''
    for package, expected in (
        ("freetz-matter", "freetz-matter -p 5549 -d "),
        ("matter-bridge", "--peer [::1]:5549 --auto-local"),
    ):
        script = packages / package / "files/root/etc/init.d" / f"rc.{package}"
        subprocess.run(["bash", "-s", "--", str(script), str(directory / package), expected],
            input=harness, text=True, check=True)

async def request(socket, command, args=None, expected_error=None):
    await socket.send(json.dumps({"message_id": command, "command": command, "args": args or {}}))
    while True:
        message = json.loads(await asyncio.wait_for(socket.recv(), 130))
        if "event" in message:
            EVENTS.append(message)
        if message.get("message_id") == command:
            if expected_error is not None:
                assert message.get("error_code") == expected_error, message
                return message
            assert "error_code" not in message, message
            return message["result"]


async def connect(port):
    for attempt in range(100):
        try:
            socket = await websockets.connect(f"ws://127.0.0.1:{port}/ws")
            info = json.loads(await socket.recv())
            assert info["schema_version"] == 11 and "event" not in info, info
            assert info["min_supported_schema_version"] == 9, info
            assert isinstance(info["compressed_fabric_id"], int) and info["compressed_fabric_id"] > 1, info
            return socket
        except OSError:
            await asyncio.sleep(0.1)
    raise AssertionError("server did not start")


async def verify(server, device, directory, port, freetz=False):
    device_log = open(directory / "device.log", "w")
    server_log = open(directory / "server.log", "a")
    device_args = [device, "--port", "5549"]
    device_args += ["--store-dir", str(directory / "device-store")] if freetz else ["--KVS", str(directory / "device.kvs")]
    endpoint = 2 if freetz else 1
    onoff_path = f"{endpoint}/6/0"
    level_path = f"{endpoint}/8/0"
    accessory = subprocess.Popen(device_args, stdout=device_log, stderr=device_log)
    bridge = None
    try:
        await asyncio.sleep(1)
        command = [server, "--port", str(port), "--store", str(directory / "controller"), "--peer", "[::1]:5549", "--auto-local"]
        bridge = subprocess.Popen(command, stdout=server_log, stderr=server_log)
        socket = await connect(port)
        EVENTS.clear()
        await request(socket, "start_listening")
        nodes = []
        for attempt in range(40):
            nodes = await request(socket, "get_nodes")
            if nodes and nodes[0]["available"] and nodes[0]["interview_version"]:
                break
            await asyncio.sleep(1)
        assert len(nodes) == 1 and nodes[0]["available"], nodes
        node_id = nodes[0]["node_id"]
        await request(socket, "get_node", {"node_id": node_id + 1000}, expected_error=5)
        await request(socket, "get_node", {}, expected_error=8)
        await request(socket, "unsupported_command", expected_error=9)
        assert onoff_path in nodes[0]["attributes"], nodes
        if freetz:
            assert "1/1026/0" in nodes[0]["attributes"] and "0/40/3" in nodes[0]["attributes"], nodes
        await request(socket, "device_command", {"node_id": node_id, "endpoint_id": endpoint, "cluster_id": 6, "command_name": "Off", "payload": {}})
        assert await request(socket, "read_attribute", {"node_id": node_id, "attribute_path": onoff_path}) is False
        await request(socket, "device_command", {"node_id": node_id, "endpoint_id": endpoint, "cluster_id": 6, "command_name": "On", "payload": {}})
        assert await request(socket, "read_attribute", {"node_id": node_id, "attribute_path": onoff_path}) is True
        await request(socket, "device_command", {"node_id": node_id, "endpoint_id": endpoint, "cluster_id": 8,
            "command_name": "MoveToLevelWithOnOff", "payload": {"level": 200, "transitionTime": 50}})
        EVENTS.clear()
        async def level_report():
            while True:
                message = json.loads(await socket.recv())
                if message.get("event") == "attribute_updated" and message["data"] == [node_id, level_path, 200]:
                    return
        await asyncio.wait_for(level_report(), 40)
        await request(socket, "write_attribute", {"node_id": node_id, "attribute_path": "0/40/5", "value": "Native bridge test"})
        assert await request(socket, "read_attribute", {"node_id": node_id, "attribute_path": "0/40/5"}) == "Native bridge test"
        await socket.close()
        fabric = (directory / "controller" / "fabric.json").read_bytes()
        bridge.terminate()
        bridge.wait(timeout=10)
        if freetz:
            accessory.terminate()
            accessory.wait(timeout=10)
            accessory = subprocess.Popen(device_args, stdout=device_log, stderr=device_log)
            await asyncio.sleep(1)
        bridge = subprocess.Popen(command, stdout=server_log, stderr=server_log)
        socket = await connect(port)
        EVENTS.clear()
        await request(socket, "start_listening")
        assert await request(socket, "read_attribute", {"node_id": node_id, "attribute_path": onoff_path}) is True
        assert (directory / "controller" / "fabric.json").read_bytes() == fabric
        assert len(await request(socket, "get_nodes")) == 1
        async def restored():
            while not any(event.get("event") == "node_updated" and event["data"]["available"] for event in EVENTS):
                EVENTS.append(json.loads(await socket.recv()))
        await asyncio.wait_for(restored(), 45)
        await socket.close()
        print("PASS: automatic local PASE/CASE, interview, On/Off/level, asynchronous report, read/write and fabric restart recovery")
    finally:
        for process in (bridge, accessory):
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
        device_log.close()
        server_log.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--port", type=int, default=5599)
    parser.add_argument("--freetz", action="store_true")
    options = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="matter-bridge-test-") as temporary:
        directory = pathlib.Path(temporary)
        try:
            verify_init_arguments(directory / "init")
            asyncio.run(verify(options.server, options.device, directory, options.port, options.freetz))
        except Exception:
            for log in directory.glob("*.log"):
                print(log.name, log.read_text()[-12000:])
            raise


if __name__ == "__main__":
    main()