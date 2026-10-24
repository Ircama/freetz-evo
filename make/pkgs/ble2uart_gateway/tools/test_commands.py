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
        self.txadv_parameters = (0, 160, b"\x02\x01\x06")
        self.subscriptions = {}
        self.configuration = bytes.fromhex("43 85 10 00 00 28 04 a9 31 31 04 b4")
        self.fail_operation = None
        self.drop_application_response = False
        self.disconnect_on_write = False
        self.ignore_disconnect_once = False
        self.duplicate_uuid = False
        super().__init__()

    def reply(self, command, status=0, data=b""):
        frame = bytes([max(0, len(data) - 6), command, status, len(data), 0xFF])
        frame += data[:6].ljust(6, b"\0") + data[6:]
        self.write(frame + crc16(frame))

    def connection_reply(self):
        self.reply(12, data=bytes([self.connection, 0, 0, 0, 40, 0]))

    def completion(self, operation, handle=0, status=0, data=b""):
        self.reply(12, 0x84, bytes([operation]) + handle.to_bytes(2, "little") + bytes([status]) + data)

    def notify(self, handle, data, indication=False):
        self.reply(14, 0x1D if indication else 0x1B,
                   handle.to_bytes(2, "little") + bytes([len(data)]) + data)

    def run(self):
        pending = bytearray()
        try:
            while not self.stopped.is_set():
                if not select.select([self.master], [], [], 0.1)[0]:
                    continue
                pending.extend(os.read(self.master, 4096))
                while len(pending) >= 3:
                    command = pending[0]
                    size = 3
                    if command == 1:
                        if len(pending) >= 8 and crc16(pending[:6]) == pending[6:8]:
                            size = 8
                        elif len(pending) >= 6 and crc16(pending[:4]) == pending[4:6]:
                            size = 6
                        elif len(pending) < 8:
                            break
                        else:
                            raise AssertionError("invalid SCAN frame")
                    elif command in (2, 3):
                        sizes = [size for size in range(4, min(9, len(pending)) + 1)
                                 if crc16(pending[:size - 2]) == pending[size - 2:size]]
                        if not sizes:
                            break
                        size = max(sizes)
                    elif command in (5, 8, 9, 16):
                        size = 4
                    elif command == 6:
                        size = 5
                    elif command == 11:
                        if pending[1] == 1:
                            if len(pending) < 6:
                                break
                            size = 8 + pending[5]
                        else:
                            size = 4
                    elif command == 12:
                        operation = pending[1]
                        if operation in (1, 2):
                            size = 12
                        elif operation in (6, 8):
                            size = 7
                        elif operation in (7, 9):
                            if len(pending) < 6:
                                break
                            size = 8 + pending[5]
                        elif operation == 13:
                            size = 8
                        else:
                            size = 4
                    elif command == 13:
                        if len(pending) < 4:
                            break
                        size = 6 + pending[3]
                    if len(pending) < size:
                        break
                    # A prefix of a valid command can also have a valid CRC.
                    if crc16(pending[:size - 2]) != pending[size - 2:size]:
                        raise AssertionError("invalid command CRC")
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
                            self.txadv_parameters = (packet[2], int.from_bytes(packet[3:5], "little"), packet[6:])
                        elif packet[1] == 0:
                            self.txadv = False
                        phy, interval, data = self.txadv_parameters
                        self.reply(11, data=bytes([phy + 1 if self.txadv else 0]) +
                                   interval.to_bytes(2, "little") + bytes([len(data), 0, 0]))
                    elif command == 12:
                        if self.scanning.is_set():
                            raise AssertionError("GATT command sent while scanning")
                        operation = packet[1]
                        if operation in (1, 2):
                            if len(packet) != 10 or packet[-1] != 1:
                                raise AssertionError("connection must use the host-managed flag")
                            if self.txadv:
                                raise AssertionError("GATT opened without stopping TXADV")
                            self.connection = 1
                            self.connection_reply()
                            self.connection = 2
                        elif operation in (3, 4):
                            if self.ignore_disconnect_once:
                                self.ignore_disconnect_once = False
                            else:
                                self.connection = 0
                                self.subscriptions.clear()
                        self.connection_reply()
                        if operation in (1, 2, 10):
                            self.reply(12, data=b"\xC8\0")
                            self.completion(10, data=b"\xC8\0")
                        elif operation in (6, 8):
                            if packet[2] != 0 or len(packet) != 5:
                                raise AssertionError("read requires the reserved zero byte")
                            self.completion(operation, int.from_bytes(packet[3:5], "little"),
                                            5 if operation == self.fail_operation else 0, b"\xAB\xCD")
                        elif operation == 5:
                            self.reply(12, 0x80, b"\x01\x01\x00\x64\x00\x10\x1F")
                            self.reply(12, 0x81, b"\x2A\x00\x18\x1F\x1F")
                            self.reply(12, 0x82, b"\x3D\x00\x02\x29")
                            if self.duplicate_uuid:
                                self.reply(12, 0x81, b"\x2B\x00\x18\x1F\x1F")
                            self.reply(12, 0x83, b"\0")
                        elif operation == 13:
                            if packet[2] != 0 or len(packet) != 6:
                                raise AssertionError("subscribe requires the reserved zero byte and mode")
                            handle = int.from_bytes(packet[3:5], "little")
                            status = 5 if operation == self.fail_operation else 0
                            if not status:
                                if packet[5]:
                                    self.subscriptions[handle] = packet[5]
                                else:
                                    self.subscriptions.pop(handle, None)
                            self.completion(operation, handle, status, packet[5:6])
                        elif operation in (7, 9):
                            if packet[2] != 0 or len(packet) != 6 + packet[5]:
                                raise AssertionError("write requires the reserved zero byte and exact length")
                            handle = int.from_bytes(packet[3:5], "little")
                            value = packet[6:]
                            if self.disconnect_on_write:
                                self.disconnect_on_write = False
                                self.connection = 0
                                self.subscriptions.clear()
                                self.connection_reply()
                                continue
                            if operation == self.fail_operation:
                                self.completion(operation, handle, 5)
                                continue
                            if handle == 42 and value[:1] == b"\x55":
                                if handle not in self.subscriptions:
                                    raise AssertionError("ATC request without completed notification subscription")
                                if len(value) > 1:
                                    if len(value) != 12:
                                        raise AssertionError("0x55 writes must omit the response firmware-version byte")
                                    self.configuration = self.configuration[:1] + value[1:]
                                if not self.drop_application_response:
                                    # Application data can arrive before ATT write completion.
                                    self.notify(handle, b"\x55" + self.configuration,
                                                self.subscriptions[handle] == 2)
                            self.completion(operation, handle)
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
    def test_firmware_uses_lengths_not_crc_valid_prefixes(self):
        firmware = CommandFirmware()
        packets = [
            bytes.fromhex("01000000"),
            bytes.fromhex("010030003000"),
            bytes.fromhex("0C0100FFEEDDCCBBAA01"),
            bytes.fromhex("0C0D002A0001"),
            bytes.fromhex("0C07002A000155"),
            bytes.fromhex("0C0700360038") + bytes(range(56)),
        ]
        try:
            for packet in packets:
                os.write(firmware.slave, packet + crc16(packet))
            deadline = time.monotonic() + 3
            while len(firmware.requests) < len(packets) and firmware.error is None:
                self.assertLess(time.monotonic(), deadline, firmware.requests)
                time.sleep(0.01)
            self.assertIsNone(firmware.error)
            self.assertEqual(firmware.requests, packets)
        finally:
            firmware.close()

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
                        self.assertEqual(result.returncode == 0, success or args[0] == "--control",
                                         result.stdout + result.stderr + f"\nfirmware error: {firmware.error}")
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

                    def cgi_command(payload):
                        body = json.dumps(payload)
                        api = subprocess.run(
                            ["sh", "-c", script], input=body, text=True,
                            env={**cgi_env, "REQUEST_METHOD": "POST", "CONTENT_LENGTH": str(len(body.encode()))},
                            capture_output=True, timeout=15,
                        )
                        self.assertEqual(api.returncode, 0, api.stderr)
                        self.assertTrue(api.stdout.rstrip().endswith("</pre></div></div>"))
                        wrapped = re.search(r"<pre>Content-Type: application/json\s+(.*?)</pre>", api.stdout, re.S)
                        self.assertIsNotNone(wrapped, api.stdout)
                        response = json.loads(html.unescape(wrapped.group(1)))
                        self.assertTrue(response["success"], response)
                        return response

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
                    self.assertEqual(len(discovered["result"]["entries"]), 3)
                    self.assertEqual(discovered["result"]["entries"][1]["uuid"], "00001F1F-0000-1000-8000-00805F9B34FB")
                    self.assertEqual(discovered["result"]["entries"][2]["characteristic_handle"], 42)
                    self.assertEqual(discovered["result"]["entries"][2]["handle"], 61)
                    written = command({"command": "gatt", "mac": "AABBCCDDEEFF",
                                       "operation": "write-without-response", "handle": 4660, "value": "0102"})
                    self.assertFalse(written["result"]["att_confirmed"])

                    def open_session(**kwargs):
                        opened = command({"command": "gatt-open", "mac": "AABBCCDDEEFF", **kwargs})
                        self.assertFalse(opened["radio"]["scanning"])
                        self.assertEqual(opened["result"]["connection"]["mtu"], 200)
                        self.assertTrue(opened["result"]["host_managed"])
                        return opened["result"]["session"]

                    def session_command(token, operation, success=True, **kwargs):
                        return command({"command": "gatt", "session": token, "operation": operation, **kwargs}, success)

                    def atc(token, operation="exchange", success=True, **kwargs):
                        return session_command(token, operation, success, uuid="1F1F", value="55", prefix="55",
                                               codec="cfg", offset=1, **kwargs)

                    control("--control", "discover-start", "3")
                    remaining = control("--control", "status")["remaining_s"]
                    opens = sum(packet[:2] == b"\x0C\x01" for packet in firmware.requests)
                    token = open_session()
                    self.assertEqual(len(token), 32)
                    status = control("--control", "status")
                    self.assertTrue(status["active"])
                    self.assertTrue(status["paused"])
                    paused_remaining = status["remaining_s"]
                    self.assertNotIn("session", status["radio"]["gatt"], "status must not leak ownership tokens")
                    for payload in [{"command": "diagnostic", "name": "info"}, {"command": "scan-start"},
                                    {"command": "scan-stop"}, {"command": "txadv-stop"},
                                    {"command": "gatt-open", "mac": "AABBCCDDEEFF"},
                                    {"command": "gatt-close", "session": "0" * 32}]:
                        count = len(firmware.requests)
                        command(payload, success=False)
                        self.assertEqual(len(firmware.requests), count, payload)
                    control("--control", "discover-start", "10", success=False)
                    control("--control", "discover-stop", success=False)
                    session_command(token, "discover")
                    session_command(token, "subscribe", uuid="1F1F")
                    requested = atc(token)
                    self.assertEqual(requested["result"]["notifications"][0]["value"], "55" + firmware.configuration.hex().upper())
                    self.assertFalse(requested["result"]["notifications"][0]["decoded"]["flg2"]["bt5phy"])
                    initial_config = firmware.configuration
                    patched = atc(token, "patch", patch={"flg2": {"bt5phy": True, "longrange": True}}, write_offset=1)
                    self.assertTrue(patched["result"]["patch_verified"])
                    self.assertTrue(patched["result"]["notifications"][0]["decoded"]["flg2"]["longrange"])
                    self.assertEqual(firmware.configuration[:2], initial_config[:2])
                    self.assertEqual(firmware.configuration[2], initial_config[2] | 0x60)
                    self.assertEqual(firmware.configuration[3:], initial_config[3:], "unmodified configuration bytes must be preserved")
                    self.assertEqual(patched["result"]["written"], "55" + firmware.configuration[1:].hex().upper())
                    session_command(token, "subscribe", handle=42, mode=2)
                    firmware.notify(42, bytes(range(197)), indication=True)
                    notifications = session_command(token, "notifications", handle=42)
                    self.assertEqual(notifications["result"]["notifications"][0]["value"], bytes(range(197)).hex().upper())
                    self.assertEqual(notifications["result"]["notifications"][0]["opcode"], 0x1D)
                    session_command(token, "subscribe", handle=42, mode=0)
                    self.assertNotIn(42, firmware.subscriptions)
                    self.assertEqual(sum(packet[:2] == b"\x0C\x01" for packet in firmware.requests), opens + 1,
                                     "multiple exchanges must use a single connection")
                    time.sleep(3.1)
                    paused = control("--control", "status")
                    self.assertTrue(paused["active"], "discovery must not expire during an open GATT session")
                    self.assertEqual(paused["remaining_s"], paused_remaining)
                    closed = command({"command": "gatt-close", "session": token})
                    self.assertTrue(closed["radio"]["scanning"])
                    status = control("--control", "status")
                    self.assertFalse(status["paused"])
                    self.assertTrue(status["active"])
                    self.assertGreaterEqual(status["remaining_s"], remaining - 2)
                    control("--control", "discover-stop")

                    cgi_session = cgi_command({"command": "gatt-open", "mac": "AABBCCDDEEFF"})["result"]["session"]
                    cgi_read = cgi_command({"command": "gatt", "session": cgi_session, "operation": "exchange",
                                            "uuid": "1F1F", "value": "55", "prefix": "55", "codec": "cfg", "offset": 1})
                    self.assertTrue(cgi_read["result"]["notifications"][0]["decoded"]["flg2"]["bt5phy"])
                    cgi_patch = cgi_command({"command": "gatt", "session": cgi_session, "operation": "patch",
                                             "uuid": "1F1F", "value": "55", "prefix": "55", "codec": "cfg",
                                             "offset": 1, "write_offset": 1, "patch": {"flg2": {"bt5phy": False}}})
                    self.assertTrue(cgi_patch["result"]["patch_verified"])
                    self.assertTrue(cgi_command({"command": "gatt-close", "session": cgi_session})["radio"]["scanning"])

                    for failure in ("att-read", "att-write", "subscribe", "application-timeout",
                                    "unexpected-disconnect", "lossy-codec", "codec-tail", "unknown-patch",
                                    "ambiguous-uuid"):
                        with self.subTest(gatt_failure=failure):
                            token = open_session()
                            firmware.fail_operation = {"att-read": 6, "att-write": 7, "subscribe": 13}.get(failure)
                            firmware.drop_application_response = failure == "application-timeout"
                            firmware.disconnect_on_write = failure == "unexpected-disconnect"
                            firmware.duplicate_uuid = failure == "ambiguous-uuid"
                            saved = firmware.configuration
                            if failure == "lossy-codec":
                                firmware.configuration = saved[:8] + b"\x1C" + saved[9:]
                            if failure == "codec-tail":
                                firmware.configuration += b"\x01"
                            before_writes = sum(packet[:2] == b"\x0C\x07" for packet in firmware.requests)
                            if failure == "att-read":
                                response = session_command(token, "read", False, handle=42)
                            elif failure in ("lossy-codec", "codec-tail", "unknown-patch"):
                                response = atc(token, "patch", False, write_offset=1,
                                               patch={"missing": True} if failure == "unknown-patch" else {"flg2": {"bt5phy": False}})
                            else:
                                response = atc(token, success=False, timeout_ms=100)
                            self.assertTrue(response["radio"]["scanning"], response)
                            self.assertIsNone(response["radio"]["gatt"])
                            self.assertEqual(firmware.connection, 0)
                            if failure in ("lossy-codec", "codec-tail", "unknown-patch"):
                                self.assertEqual(sum(packet[:2] == b"\x0C\x07" for packet in firmware.requests),
                                                 before_writes + 1, "failed patch validation may query, never commit")
                            if failure == "application-timeout":
                                self.assertIn("timed out", response["error"])
                                self.assertEqual(sum(packet[:2] == b"\x0C\x07" for packet in firmware.requests),
                                                 before_writes + 1, "application writes must not be automatically retried")
                            firmware.configuration = saved
                            firmware.fail_operation = None
                            firmware.drop_application_response = False
                            firmware.duplicate_uuid = False

                    token = open_session(idle_timeout_ms=1000)
                    deadline = time.monotonic() + 5
                    while control("--control", "status")["radio"]["gatt"] is not None:
                        self.assertLess(time.monotonic(), deadline, "abandoned session was not closed")
                        time.sleep(0.02)
                    self.assertTrue(firmware.scanning.is_set())
                    session_command(token, "discover", False)

                    token = open_session()
                    firmware.ignore_disconnect_once = True
                    failed_close = command({"command": "gatt-close", "session": token}, success=False)
                    self.assertTrue(failed_close["radio"]["recovery_required"])
                    self.assertFalse(failed_close["radio"]["scanning"])
                    deadline = time.monotonic() + 5
                    while not control("--control", "status")["radio"]["scanning"]:
                        self.assertLess(time.monotonic(), deadline, "connection recovery did not restore scan")
                        time.sleep(0.02)
                    self.assertEqual(firmware.connection, 0)

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
                    firmware.txadv = True
                    firmware.txadv_parameters = (2, 320, b"\x02\x01\x06\x05")
                    count = len(firmware.requests)
                    external = command({"command": "gatt", "mac": "AABBCCDDEEFF", "operation": "discover"}, success=False)
                    self.assertIn("payload cannot be recovered", external["error"])
                    self.assertEqual(firmware.requests[count:], [b"\x0B\x02"])
                    self.assertTrue(firmware.txadv, "untracked TXADV must not be stopped without a recoverable payload")
                    firmware.txadv = False
                    tx = command({"command": "txadv-start", "phy": 0, "interval_units": 160, "data": "020106"})
                    self.assertFalse(tx["radio"]["scanning"])
                    self.assertTrue(tx["radio"]["scan_suppressed"])
                    self.assertTrue(firmware.txadv)
                    parameters = firmware.txadv_parameters
                    token = open_session()
                    self.assertFalse(firmware.txadv)
                    atc(token)
                    restored = command({"command": "gatt-close", "session": token})
                    self.assertFalse(restored["radio"]["scanning"])
                    self.assertTrue(restored["radio"]["scan_suppressed"])
                    self.assertTrue(restored["radio"]["txadv_active"])
                    self.assertTrue(firmware.txadv)
                    self.assertEqual(firmware.txadv_parameters, parameters)
                    firmware.fail_operation = 13
                    failed = command({"command": "gatt", "mac": "AABBCCDDEEFF", "operation": "exchange",
                                      "uuid": "1F1F", "value": "55"}, success=False)
                    self.assertTrue(failed["radio"]["txadv_active"], "TXADV must be restored after ATT failure")
                    self.assertFalse(firmware.scanning.is_set())
                    self.assertTrue(firmware.txadv)
                    firmware.fail_operation = None
                    token = open_session()
                    self.assertFalse(firmware.txadv)
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
                    self.assertIsNone(radio["gatt"])
                    self.assertTrue(firmware.txadv, "serial recovery must restore TXADV suspended by the lost session")
                    self.assertEqual(firmware.txadv_parameters, parameters)
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
