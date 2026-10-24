#!/usr/bin/env python3
"""Exercise startup save hooks with framework-prepared settings."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


def assignments(values):
    return "".join(
        f"{key}='" + str(value).replace("'", "'\"'\"'") + "'\n"
        for key, value in values.items()
    )


class SaveHookTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ble-save-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        package = Path(__file__).resolve().parents[1]
        repository = package.parents[2]
        defaults_directory = package / "files/root/etc/default.ble2uart_gateway"
        self.defaults = self.directory / "defaults.cfg"
        self.defaults.write_text((defaults_directory / "ble2uart_gateway.cfg").read_text())
        self.saved = self.directory / "saved.cfg"
        self.old_store = self.directory / "old"
        self.new_store = self.directory / "new"
        self.old_store.mkdir()
        (self.old_store / "ble2uart_gateway.yaml").write_text("devices: []\n")
        self.values = {
            "BLE2UART_GATEWAY_ENABLED": "no",
            "BLE2UART_GATEWAY_BAUDRATE": "115200",
            "BLE2UART_GATEWAY_SERIAL": "/dev/ttyACM0",
            "BLE2UART_GATEWAY_STORE": str(self.old_store),
            "BLE2UART_GATEWAY_EXTRA_ARGS": "",
        }
        self.saved.write_text(assignments(self.values))
        source = (defaults_directory / "ble2uart_gateway.save").read_text()
        source = source.replace(
            "/mod/etc/default.ble2uart_gateway/ble2uart_gateway.cfg", str(self.defaults)
        ).replace(
            "/mod/etc/conf/ble2uart_gateway.cfg", str(self.saved)
        ).replace("/tmp/ble2uart_gateway-save.", str(self.directory / "pending."))
        self.hook = self.directory / "hook.sh"
        self.hook.write_text(source)
        modconf = (repository / "make/pkgs/mod/files/root/usr/bin/modconf").read_text()
        modconf = modconf.replace("TMP=/var/tmp", f"TMP={self.directory}")
        # The script entry point uses BusyBox syntax; its merge subprocess is POSIX.
        self.modconf = self.directory / "modconf"
        self.modconf.write_text("#!/bin/bash\n" + modconf)
        self.modconf.chmod(0o755)

    def run_hook(self, pending, script="pkg_pre_save", stale_baudrate=""):
        settings = self.directory / "settings"
        settings.write_text(assignments(pending))
        environment = os.environ.copy()
        environment.update(
            PATH=f"{self.directory}:{environment['PATH']}",
            BLE2UART_GATEWAY_BAUDRATE=stale_baudrate,
        )
        result = subprocess.run(
            ["sh", "-c", 'settings=$(cat "$1"); . "$2"; ' + script,
             "save-test", str(settings), str(self.hook)],
            env=environment, capture_output=True, text=True,
        )
        self.assertEqual(list(self.directory.glob("pending.*")), [])
        return result

    def test_two_million_uses_pending_value_not_empty_or_stale_environment(self):
        pending = dict(self.values, BLE2UART_GATEWAY_BAUDRATE="2000000")
        for stale in ["", "old-invalid-value"]:
            with self.subTest(stale=stale):
                result = self.run_hook(pending, stale_baudrate=stale)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Error:", result.stderr)
        self.assertIn("115200", self.saved.read_text())

    def test_invalid_pending_baudrate_is_not_hidden_by_valid_saved_value(self):
        for value in ["", "2M", "2000000x", "2000000\n"]:
            with self.subTest(value=value):
                result = self.run_hook(
                    dict(self.values, BLE2UART_GATEWAY_BAUDRATE=value),
                    stale_baudrate="115200",
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("the baud rate must be numeric", result.stderr)

    def test_pending_settings_also_work_before_the_first_saved_configuration(self):
        self.saved.unlink()
        result = self.run_hook(dict(self.values, BLE2UART_GATEWAY_BAUDRATE="2000000"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.saved.exists())

    def test_pending_values_use_framework_quoting_without_reinterpretation(self):
        store = self.directory / "sensor's-$device"
        pending = dict(self.values, BLE2UART_GATEWAY_STORE=str(store))
        result = self.run_hook(
            pending, 'pkg_pre_save && printf "%s\\n" "$BLE2UART_GATEWAY_STORE"'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(store))

    def test_apply_reads_saved_values_and_retains_old_store_across_pipeline(self):
        pending = dict(
            self.values,
            BLE2UART_GATEWAY_BAUDRATE="2000000",
            BLE2UART_GATEWAY_STORE=str(self.new_store),
        )
        updated = self.directory / "updated.cfg"
        updated.write_text(assignments(pending))
        result = self.run_hook(
            pending,
            'pkg_pre_save | cat; '
            f'cp "{updated}" "{self.saved}"; '
            'pkg_apply_save && printf "%s\\n" "$BLE2UART_GATEWAY_BAUDRATE"',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "2000000")
        self.assertEqual(
            (self.new_store / "ble2uart_gateway.yaml").read_text(), "devices: []\n"
        )
        self.assertTrue((self.old_store / "ble2uart_gateway.yaml").exists())
        self.assertIn("store moved", result.stderr)

    def test_modconf_failure_is_reported_and_temporary_file_removed(self):
        self.modconf.write_text("#!/bin/sh\nexit 1\n")
        result = self.run_hook(self.values)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not load pending gateway settings", result.stderr)


class CgiPersistenceTests(unittest.TestCase):
    def check_persistence(self, store, *, method="POST", failure=False, origin=""):
        package = Path(__file__).resolve().parents[1]
        source = (package / "files/root/usr/lib/cgi-bin/ble2uart_gateway.cgi").read_text()
        function = source[source.index("\tapi_reply() {"):source.index("\n\tapi_reply |")]
        with tempfile.TemporaryDirectory(prefix="ble-persist-test-") as directory:
            calls = Path(directory) / "calls"
            modsave = Path(directory) / "modsave"
            modsave.write_text(
                '#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALLS"\n'
                + ("exit 1\n" if failure else "exit 0\n")
            )
            modsave.chmod(0o755)
            function = function.replace("/usr/bin/modsave", str(modsave))
            environment = dict(
                os.environ, ACTION="persist", REQUEST_METHOD=method,
                BLE2UART_GATEWAY_STORE=store, HTTP_ORIGIN=origin,
                HTTP_HOST="fritz.box:81", CALLS=str(calls),
            )
            result = subprocess.run(
                ["sh", "-c", function + "\napi_reply"],
                env=environment, capture_output=True, text=True, check=True,
            )
            return json.loads(result.stdout), calls.read_text() if calls.exists() else ""

    def test_ram_store_is_archived_without_restarting(self):
        response, calls = self.check_persistence("/tmp/flash/ble2uart_gateway")
        self.assertTrue(response["success"])
        self.assertEqual(calls, "flash\n")

    def test_disk_store_does_not_write_router_flash(self):
        response, calls = self.check_persistence("/var/media/ftp/USB/ble2uart_gateway")
        self.assertTrue(response["success"])
        self.assertEqual(calls, "")

    def test_flash_failure_is_not_reported_as_persistent(self):
        response, calls = self.check_persistence("/tmp/flash/ble2uart_gateway", failure=True)
        self.assertFalse(response["success"])
        self.assertIn("not confirmed persistent", response["error"])
        self.assertEqual(calls, "flash\n")

    def test_get_and_cross_origin_requests_cannot_archive(self):
        for options in [{"method": "GET"}, {"origin": "https://other.example"}]:
            with self.subTest(options=options):
                response, calls = self.check_persistence("/tmp/flash/gateway", **options)
                self.assertFalse(response["success"])
                self.assertEqual(calls, "")


if __name__ == "__main__":
    unittest.main()
