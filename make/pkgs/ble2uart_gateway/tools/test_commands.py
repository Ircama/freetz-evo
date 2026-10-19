#!/usr/bin/env python3
"""CLI/daemon command regressions against a private PTY, never real hardware."""

import json
import html
import os
from pathlib import Path
import select
import re
import sqlite3
import subprocess
import tempfile
import time
import unittest

from replay_capture import Firmware, crc16


ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "src/target/debug/ble2uart-gateway"


class CommandFirmware(Firmware):
    def __init__(self):
        self.requests = []
        self.connection = 0
        self.txadv = False
        super().__init__()

    def reply(self, command, status=0, data=b""):
        frame = bytes([max(0, len(data) - 6), command, status, len(data), 0xFF])
        frame += data[:6].ljust(6, b"\0") + data[6:]
        self.write(frame + crc16(frame))

    def connection_reply(self):
        self.reply(12, data=bytes([self.connection, 0, 0, 0, 40, 0]))

    def run(self):
        pending = bytearray()
        try:
            while not self.stopped.is_set():
                if not select.select([self.master], [], [], 0.1)[0]:
                    continue
                pending.extend(os.read(self.master, 4096))
                while len(pending) >= 3:
                    size = next((size for size in range(3, min(64, len(pending)) + 1)
                                 if crc16(pending[:size - 2]) == pending[size - 2:size]), None)
                    if size is None:
                        break
                    packet = bytes(pending[:size - 2])
                    del pending[:size]
                    self.requests.append(packet)
                    command = packet[0]
                    if command == 1:
                        self.scanning.set() if packet[1] & 3 else self.scanning.clear()
                        self.reply(1)
                    elif command == 4:
                        self.reply(4, 64)
                    elif command == 0:
                        self.reply(0, 2, bytes(6))
                    elif command == 11:
                        if packet[1] == 1:
                            if self.scanning.is_set():
                                raise AssertionError("TXADV started without stopping scan")
                            self.txadv = True
                        elif packet[1] == 0:
                            self.txadv = False
                        self.reply(11, data=bytes([self.txadv, 0, 160, 0, 3, 0]))
                    elif command == 12:
                        if self.scanning.is_set():
                            raise AssertionError("GATT command sent while scanning")
                        operation = packet[1]
                        if operation in (1, 2):
                            self.connection = 1
                            self.connection_reply()
                            self.connection = 2
                        elif operation in (3, 4):
                            self.connection = 0
                        self.connection_reply()
                        if operation == 6:
                            self.reply(12, data=packet[2:4] + b"\x02\xAB\xCD")
                        elif operation == 5:
                            self.reply(12, 0x80, b"\x01\x01\x00\x05\x00\x0F\x18")
                            self.reply(12, 0x83)
                    elif command == 13:
                        if self.scanning.is_set():
                            raise AssertionError("TXDATA sent while scanning")
                        self.reply(13, data=packet[1:4] + bytes(3))
                    else:
                        if self.scanning.is_set():
                            raise AssertionError("diagnostic sent while scanning")
                        self.reply(command, 3 if command == 15 else 0, b"\x01\x02")
        except (OSError, ValueError, TimeoutError, AssertionError) as error:
            self.error = str(error)
            self.stopped.set()


class CommandTests(unittest.TestCase):
    def test_cli_commands_discovery_txadv_and_advertisement_pipeline(self):
        self.assertTrue(BINARY.is_file(), "build the host gateway first")
        firmware = CommandFirmware()
        child = None
        directory_fd = None
        try:
            with tempfile.TemporaryDirectory(prefix="ble-command-test-") as directory:
                directory = Path(directory)
                config = directory / "gateway.yaml"
                env = {**os.environ, "BLE2UART_GATEWAY_CONTROL_SOCKET": str(directory / "control/control.sock")}
                subprocess.run([BINARY, "--write-default-config", config], check=True, capture_output=True)
                original = subprocess.run([BINARY, "--config", config, "--web-config", "read"],
                                          check=True, capture_output=True, text=True)
                settings = json.loads(original.stdout)["config"]
                serial_link = directory / "adapter.tty"
                serial_link.symlink_to(firmware.path)
                # Keep a stable /dev path without creating files in shared /dev.
                directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                settings["serial"].update(port=f"/dev/fd/{directory_fd}/adapter.tty", command_timeout_ms=200, reconnect_delay_ms=50)
                settings["scanner"]["filter_known_devices"] = False
                settings["devices"] = [{"mac": "AABBCCDDEEFF", "label": "Command regression sensor"}]
                for frontend in settings["frontends"].values():
                    frontend["enabled"] = False
                database = directory / "history.sqlite3"
                settings["frontends"]["sqlite"].update(enabled=True, path=str(database), flush_interval_ms=10)
                config.write_text(json.dumps(settings))
                with (directory / "daemon.log").open("w+") as output:
                    child = subprocess.Popen([BINARY, "--config", config], env=env, stdout=output, stderr=output,
                                             pass_fds=(directory_fd,))

                    def control(*args, payload=None, success=True):
                        result = subprocess.run([BINARY, *args], input=payload, env=env,
                                                text=True, capture_output=True, timeout=15)
                        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
                        response = json.loads(result.stdout)
                        self.assertEqual(response["success"], success, response)
                        return response

                    def command(payload, success=True):
                        return control("--command", "-", payload=json.dumps(payload), success=success)

                    self.assertTrue(firmware.scanning.wait(10), firmware.error or (directory / "daemon.log").read_text())
                    self.assertTrue(control("--control", "status")["radio"]["scanning"])
                    before = config.read_bytes()
                    reply = command({"command": "diagnostic", "name": "version"})
                    self.assertTrue(reply["radio"]["scanning"])
                    self.assertEqual(reply["result"]["data"], "0102")
                    cgi = (ROOT / "files/root/usr/lib/cgi-bin/ble2uart_gateway.cgi").read_text()
                    ajax = cgi[cgi.index('if [ "$(cgi_param ajax)"'):cgi.index("# Page")]
                    script = 'cgi_param() { case "$1" in ajax) printf 1;; action) printf command;; esac; }\n'
                    script += f"DAEMON_BIN='{BINARY}'\n" + ajax
                    body = json.dumps({"command": "diagnostic", "name": "version"})
                    cgi_env = {**env, "CONTENT_LENGTH": str(len(body)), "CONTENT_TYPE": "application/json",
                               "HTTP_HOST": "localhost", "HTTP_ORIGIN": "http://localhost"}
                    for method, origin, success in [("POST", "http://localhost", True),
                                                     ("GET", "http://localhost", False),
                                                     ("POST", "https://other.invalid", False)]:
                        api = subprocess.run(["sh", "-c", script], input=body, text=True,
                                             env={**cgi_env, "REQUEST_METHOD": method, "HTTP_ORIGIN": origin},
                                             capture_output=True, timeout=15)
                        self.assertEqual(api.returncode, 0, api.stderr)
                        self.assertTrue(api.stdout.rstrip().endswith("</pre></div></div>"))
                        encoded = re.search(r"<pre>Content-Type: application/json\s+(.*?)</pre>", api.stdout, re.S)
                        self.assertIsNotNone(encoded, api.stdout)
                        response = json.loads(html.unescape(encoded.group(1)))
                        self.assertEqual(response["success"], success, response)
                    denied = command({"command": "diagnostic", "name": "vbat"}, success=False)
                    self.assertTrue(denied["radio"]["scanning"])
                    count = len(firmware.requests)
                    command({"command": "txadv-start", "phy": 5, "interval_units": 160, "data": ""}, success=False)
                    self.assertEqual(len(firmware.requests), count)
                    control("--control", "discover-start", "30")
                    discovery = control("--control", "status")
                    self.assertTrue(discovery["active"])
                    read = command({"command": "gatt", "mac": "AABBCCDDEEFF", "operation": "read", "handle": 4660})
                    self.assertEqual(read["result"]["value"], "ABCD")
                    self.assertTrue(read["radio"]["scanning"])
                    self.assertTrue(control("--control", "status")["active"])
                    control("--control", "discover-stop")
                    discovered = command({"command": "gatt", "mac": "AABBCCDDEEFF", "operation": "discover"})
                    self.assertEqual(len(discovered["result"]["entries"]), 1)
                    written = command({"command": "gatt", "mac": "AABBCCDDEEFF",
                                       "operation": "write-without-response", "handle": 4660, "value": "0102"})
                    self.assertFalse(written["result"]["att_confirmed"])
                    vector = next(vector for vector in json.loads((ROOT / "src/tests/vectors.json").read_text())["roundtrips"]
                                  if vector["format"] == "atc1441_format")
                    firmware.advertise(bytes.fromhex(vector["encoded"]), 1)
                    deadline = time.monotonic() + 5
                    while True:
                        with sqlite3.connect(database) as connection:
                            rows = connection.execute("SELECT count(*) FROM frames").fetchone()[0]
                        if rows:
                            break
                        self.assertLess(time.monotonic(), deadline, output.read())
                        time.sleep(0.02)
                    tx = command({"command": "txadv-start", "phy": 0, "interval_units": 160, "data": "020106"})
                    self.assertFalse(tx["radio"]["scanning"])
                    self.assertTrue(tx["radio"]["scan_suppressed"])
                    self.assertTrue(firmware.txadv)
                    count = len(firmware.requests)
                    blocked = command({"command": "gatt", "mac": "AABBCCDDEEFF", "operation": "discover"}, success=False)
                    self.assertFalse(blocked["radio"]["scanning"])
                    self.assertEqual(len(firmware.requests), count, "GATT must not interfere with active TXADV")
                    firmware.close()
                    firmware = CommandFirmware()
                    serial_link.unlink()
                    serial_link.symlink_to(firmware.path)
                    deadline = time.monotonic() + 5
                    while not any(packet[0] == 4 for packet in firmware.requests):
                        self.assertLess(time.monotonic(), deadline, "gateway did not reopen the replacement adapter")
                        time.sleep(0.02)
                    radio = control("--control", "status")["radio"]
                    self.assertFalse(radio["scanning"], "serial reconnect must not undo TXADV scan suppression")
                    self.assertTrue(radio["scan_suppressed"])
                    self.assertFalse(firmware.scanning.is_set())
                    diagnostic = command({"command": "diagnostic", "name": "version"})
                    self.assertFalse(diagnostic["radio"]["scanning"])
                    stopped = command({"command": "txadv-stop"})
                    self.assertFalse(stopped["radio"]["scanning"])
                    self.assertTrue(stopped["radio"]["scan_suppressed"])
                    self.assertFalse(firmware.txadv)
                    resumed = command({"command": "scan-start"})
                    self.assertTrue(resumed["radio"]["scanning"])
                    self.assertFalse(resumed["radio"]["scan_suppressed"])
                    self.assertEqual(config.read_bytes(), before, "commands must not rewrite saved configuration")
                    self.assertIsNone(firmware.error)
                    self.assertIsNone(child.poll())
        finally:
            if child is not None and child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
            if directory_fd is not None:
                os.close(directory_fd)
            firmware.close()


if __name__ == "__main__":
    unittest.main()
