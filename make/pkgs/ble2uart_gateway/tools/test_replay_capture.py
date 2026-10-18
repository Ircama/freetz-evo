#!/usr/bin/env python3
"""Hardware-free regression checks for restricted captures and the PTY replay supervisor."""

import datetime
import hashlib
import http.server
import io
import json
import os
from pathlib import Path
import pickle
import select
import signal
import subprocess
import tempfile
import threading
import types
import unittest
from unittest import mock

from capture_trace import RestrictedUnpickler, load_captures
from replay_capture import Firmware, crc16, expose_all_attributes, offsets, validate_binary_args


class RejectedObject:
    def __reduce__(self):
        return eval, ("1+1",)


class ReplayTests(unittest.TestCase):
    def test_expose_all_preserves_explicit_and_implicit_children(self):
        devices = [{"mac": "AABBCCDDEEFF", "enabled": True, "expose": [
            {"attribute": "battery_level", "child": 2},
            {"attribute": "humidity", "child": None},
        ]}]
        with mock.patch("sys.stderr", new_callable=io.StringIO) as messages:
            expose_all_attributes(devices, ["humidity", "battery_level", "temperature", "flooding"])
        self.assertEqual(devices[0]["expose"], [
            {"attribute": "battery_level", "child": 2}, {"attribute": "humidity", "child": 0},
            {"attribute": "temperature", "child": 1}, {"attribute": "flooding", "child": 3},
        ])
        self.assertIn("missing exposures added privately", messages.getvalue())
        with mock.patch("sys.stderr", new_callable=io.StringIO) as messages:
            expose_all_attributes(devices, ["humidity", "battery_level", "temperature", "flooding"])
        self.assertEqual(messages.getvalue(), "")
        self.assertEqual(len(devices[0]["expose"]), 4)

    def test_gateway_forwarding_accepts_diagnostics_and_rejects_isolation_overrides(self):
        validate_binary_args(["--log-level", "debug", "--trace-decode", "--log-color", "always"])
        for arguments in (["--config", "/tmp/other.yaml"], ["--serial", "/dev/ttyUSB0"],
                          ["--decode-captures"], ["--log-level"], ["--log-level", "--trace-rx"]):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                validate_binary_args(arguments)

    def test_expose_all_leaves_disabled_devices_disabled_and_reports_child_exhaustion(self):
        disabled = {"mac": "AABBCCDDEEFF", "enabled": False, "expose": []}
        with mock.patch("sys.stderr", new_callable=io.StringIO) as messages:
            expose_all_attributes([disabled], ["flooding"])
        self.assertIn("device disabled", messages.getvalue())
        self.assertEqual(disabled["expose"], [])
        full = {"mac": "AABBCCDDEEFF", "enabled": True,
                "expose": [{"attribute": str(child), "child": child} for child in range(255)]}
        with self.assertRaisesRegex(ValueError, "no free measurement child IDs"):
            expose_all_attributes([full], ["flooding"])

    def test_cli_rejects_forwarding_overrides_and_supervision_options_in_pty_only_mode(self):
        replay = str(Path(__file__).with_name("replay_capture.py"))
        for options in (["--", "--serial", "/dev/ttyUSB0"],
                        ["--no-launch", "--expose-all"],
                        ["--no-launch", "--", "--trace-decode"]):
            with self.subTest(options=options):
                result = subprocess.run(["python3", replay, "unused.pickle", *options],
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("error:", result.stderr)
                self.assertNotIn("replay failed:", result.stderr)

    def test_pickle_cannot_import_arbitrary_classes(self):
        with self.assertRaises(pickle.UnpicklingError):
            RestrictedUnpickler(io.BytesIO(pickle.dumps(RejectedObject()))).load()

    def test_capture_reader_preserves_original_payload_and_recorded_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.pickle"
            raw = bytes.fromhex("D2FC400001")
            path.write_bytes(pickle.dumps(({"one": {"binary": raw, "mac_address": "AA:BB:CC:DD:EE:FF",
                "timestamp": datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc), "rssi": -75}}, {})))
            original = hashlib.sha256(path.read_bytes()).digest()
            captures, errors = load_captures(path)
            self.assertFalse(errors)
            self.assertEqual(captures[0].raw, raw)
            self.assertEqual(captures[0].ad, bytes.fromhex("0616D2FC400001"))
            self.assertEqual(captures[0].mac, "AABBCCDDEEFF")
            self.assertEqual(captures[0].recorded_at, 1767225600)
            self.assertEqual(captures[0].radio["rssi"], -75)
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(), original)

    def test_fixed_and_recorded_timing_are_scaled_and_missing_time_is_rejected(self):
        captures = [types.SimpleNamespace(recorded_at=10), types.SimpleNamespace(recorded_at=14)]
        self.assertEqual(offsets(captures, "fixed", 1, 2), [0, 0.5])
        self.assertEqual(offsets(captures, "recorded", 1, 2), [0, 2])
        with self.assertRaises(ValueError):
            offsets(list(reversed(captures)), "recorded", 1, 1)
        with self.assertRaises(ValueError):
            offsets([types.SimpleNamespace(recorded_at=None)], "recorded", 1, 1)
        for invalid in (0, -1, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                offsets(captures, "fixed", 1, invalid)

    def test_scanner_short_extended_stop_and_mac_filters(self):
        firmware = Firmware()

        def command(payload):
            os.write(firmware.slave, payload + crc16(payload))
            self.assertTrue(select.select([firmware.slave], [], [], 2)[0], firmware.error)
            response = os.read(firmware.slave, 256)
            self.assertEqual(crc16(response[:-2]), response[-2:])
            return response

        try:
            self.assertEqual(crc16(b"123456789"), bytes.fromhex("374b"))
            command(bytes([4]))
            self.assertEqual(command(bytes([2]) + bytes.fromhex("FFEEDDCCBBAA"))[2], 1)
            command(bytes([1, 1, 64, 1]))
            self.assertTrue(firmware.scanning.wait(2))
            self.assertFalse(firmware.observation("001122334455", b""))
            self.assertTrue(firmware.observation("AABBCCDDEEFF", b"\x02\x01\x06"))
            self.assertTrue(select.select([firmware.slave], [], [], 2)[0])
            frame = os.read(firmware.slave, 256)
            self.assertEqual(frame[5:11], bytes.fromhex("FFEEDDCCBBAA"))
            self.assertEqual(crc16(frame[:-2]), frame[-2:])
            command(bytes([1, 0, 0, 0]))
            self.assertFalse(firmware.scanning.is_set())
            command(bytes([1, 3, 64, 1, 64, 0]))
            self.assertTrue(firmware.scanning.wait(2))
            self.assertEqual(command(bytes([3]) + bytes.fromhex("FFEEDDCCBBAA"))[2], 1)
            self.assertFalse(firmware.observation("AABBCCDDEEFF", b""))
            with self.assertRaises(ValueError):
                firmware.observation("AABBCCDDEEFF", bytes(230))
        finally:
            firmware.close()
        self.assertFalse(firmware.thread.is_alive())

    def test_real_gateway_uses_private_pty_and_does_not_publish_by_default(self):
        binary = Path(os.environ.get("BLE2UART_TEST_BINARY", str(Path(__file__).resolve().parents[1] / "src/target/debug/ble2uart-gateway")))
        if not binary.is_file():
            self.skipTest("build the native ble2uart-gateway binary first")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture = root / "capture.pickle"
            vectors = json.loads((Path(__file__).resolve().parents[1] / "src/tests/vectors.json").read_text())
            vector = next(item for item in vectors["roundtrips"] if item["format"] in ("custom", "custom_format"))
            capture.write_bytes(pickle.dumps(({str(index): {"binary": bytes.fromhex(vector["encoded"]),
                "mac_address": "AABBCCDDEEFF", "timestamp": 100 + index / 20} for index in range(2)}, {})))
            source = root / "source.yaml"
            source.write_text(json.dumps({"version": 1, "frontends": {"mysensors": {"enabled": True, "port": 1},
                "influx": {"enabled": True, "endpoint": "http://127.0.0.1:1"}}}))
            original = source.read_bytes()
            link = root / "replay.tty"
            with subprocess.Popen(["python3", str(Path(__file__).with_name("replay_capture.py")), str(capture),
                "--binary", str(binary), "--config", str(source), "--timing", "recorded", "--settle", "0.3", "--start-timeout", "5", "--pty-link", str(link)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True) as process:
                try:
                    stdout, stderr = process.communicate(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    stdout, stderr = process.communicate()
                    self.fail("owned replay process timed out: " + stderr[-2000:])
                self.assertEqual(process.returncode, 0, stderr)
            reports = [json.loads(line) for line in stdout.splitlines()]
            self.assertEqual(reports[-1]["emitted_packets"], 2)
            self.assertFalse(reports[0]["frontends_allowed"])
            self.assertIn("serial link up: /dev/pts/", stderr)
            self.assertIn("frontends=mysensors:off mqtt:off matter:off influx:off", stderr)
            self.assertEqual(source.read_bytes(), original)
            self.assertFalse(link.is_symlink())
            self.assertFalse(Path(reports[0]["private_config"]).exists())

    def test_real_gateway_logs_flooding_and_preserves_configured_children(self):
        binary = Path(os.environ.get("BLE2UART_TEST_BINARY", str(Path(__file__).resolve().parents[1] / "src/target/debug/ble2uart-gateway")))
        if not binary.is_file():
            self.skipTest("build the native ble2uart-gateway binary first")
        vectors = json.loads((Path(__file__).resolve().parents[1] / "src/tests/vectors.json").read_text())
        vector = next(item for item in vectors["roundtrips"]
                      if item.get("branch") == "XIAOMI_DATA_ID_Flooding")
        flooded = bytes.fromhex(vector["encoded"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture = root / "capture.pickle"
            capture.write_bytes(pickle.dumps(({
                "wet": {"binary": flooded, "mac_address": "AABBCCDDEEFF"},
                "dry": {"binary": flooded[:-1] + b"\x00", "mac_address": "AABBCCDDEEFF"},
            }, {})))
            source = root / "source.yaml"
            source.write_text(json.dumps({"version": 1, "devices": [{
                "mac": "AABBCCDDEEFF", "enabled": True,
                "expose": [{"attribute": "flooding", "child": 7}],
            }]}))
            original = source.read_bytes()
            for configured, child in ((False, 3), (True, 7)):
                with self.subTest(configured=configured):
                    command = ["python3", str(Path(__file__).with_name("replay_capture.py")), str(capture),
                               "--binary", str(binary), "--interval", "0.02",
                               "--settle", "0.3", "--start-timeout", "5"]
                    if configured:
                        command.extend(["--config", str(source)])
                    result = subprocess.run(command, capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr.count(f"child {child}: flooding=1"), 1, result.stderr)
                    self.assertEqual(result.stderr.count(f"child {child}: flooding=0"), 1, result.stderr)
                    self.assertNotIn("authentication failed", result.stderr)
                    reports = [json.loads(line) for line in result.stdout.splitlines()]
                    self.assertEqual(reports[-1]["emitted_packets"], 2)
                    self.assertFalse(reports[0]["frontends_allowed"])
                    self.assertEqual(source.read_bytes(), original)

            source.write_text(json.dumps({"version": 1, "devices": [{
                "mac": "AABBCCDDEEFF", "enabled": True,
                "expose": [{"attribute": "battery_level", "child": 2}],
            }]}))
            original = source.read_bytes()
            for forwarded in (["--", "--log-level", "debug", "--trace-decode"],
                              ["--binary-arg=--log-level", "--binary-arg=debug",
                               "--binary-arg=--trace-decode"]):
                with self.subTest(forwarded=forwarded):
                    result = subprocess.run([
                        "python3", str(Path(__file__).with_name("replay_capture.py")), str(capture),
                        "--binary", str(binary), "--config", str(source), "--expose-all",
                        "--interval", "0.02", "--settle", "0.3", "--start-timeout", "5", *forwarded,
                    ], capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("missing exposures added privately", result.stderr)
                    self.assertIn("flooding=child ", result.stderr)
                    self.assertRegex(result.stderr, r"child \d+: flooding=1")
                    self.assertRegex(result.stderr, r"child \d+: flooding=0")
                    self.assertIn("ble.decode", result.stderr)
                    self.assertEqual(source.read_bytes(), original)

    def test_real_gateway_writes_decoded_measurements_to_isolated_influxdb3(self):
        binary = Path(os.environ.get("BLE2UART_TEST_BINARY", str(Path(__file__).resolve().parents[1] / "src/target/debug/ble2uart-gateway")))
        if not binary.is_file():
            self.skipTest("build the native ble2uart-gateway binary first")
        vectors = json.loads((Path(__file__).resolve().parents[1] / "src/tests/vectors.json").read_text())
        vector = next(item for item in vectors["roundtrips"] if item.get("branch") == "XIAOMI_DATA_ID_Flooding")
        requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"])).decode()
                requests.append((self.path, self.headers.get("Authorization"), body))
                self.send_response(204)
                self.end_headers()

            def log_message(self, *arguments):
                pass

        with http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server, tempfile.TemporaryDirectory() as directory:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            root = Path(directory)
            capture = root / "capture.pickle"
            capture.write_bytes(pickle.dumps(({"wet": {"binary": bytes.fromhex(vector["encoded"]),
                                                       "mac_address": "AABBCCDDEEFF"}}, {})))
            source = root / "source.yaml"
            source.write_text(json.dumps({"version": 1, "frontends": {"influx": {
                "enabled": True, "endpoint": f"http://127.0.0.1:{server.server_port}", "database": "ble test",
                "measurement": "ble", "token": "private-token", "batch_size": 1, "flush_interval_ms": 10}},
                "devices": [{"mac": "AABBCCDDEEFF", "label": "Wet room", "enabled": True}]}))
            result = subprocess.run([
                "python3", str(Path(__file__).with_name("replay_capture.py")), str(capture), "--binary", str(binary),
                "--config", str(source), "--allow-frontends", "--interval", "0.02", "--settle", "0.5", "--start-timeout", "5",
            ], capture_output=True, text=True, timeout=20)
            server.shutdown()
            thread.join()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("influx:on", result.stderr)
        self.assertNotIn("private-token", result.stderr + result.stdout)
        self.assertTrue(requests, result.stderr)
        self.assertEqual({path for path, _, _ in requests}, {"/api/v3/write_lp?db=ble%20test&precision=nanosecond"})
        self.assertEqual({authorization for _, authorization, _ in requests}, {"Bearer private-token"})
        body = "\n".join(body for _, _, body in requests)
        self.assertRegex(body, r'(?m)^ble,mac=AABBCCDDEEFF,attribute=flooding value_(?:int=1i|uint=1u|float=1|bool=true),'
                               r'unit="[^"]*",label="Wet room" \d+$')


if __name__ == "__main__":
    unittest.main()