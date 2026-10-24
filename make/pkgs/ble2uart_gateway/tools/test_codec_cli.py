#!/usr/bin/env python3
"""Test explicit and automatic codec selection through the native CLI."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


class CodecCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = Path(__file__).resolve().parents[1] / "src/target/debug/ble2uart-gateway"
        if not cls.binary.is_file():
            raise RuntimeError("Build the native daemon before running codec CLI tests")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ble-codec-cli-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.config = self.directory / "gateway.yaml"
        self.run_cli("--write-default-config", self.config)
        self.selected = self.directory / "mycodec.yaml"
        self.selected.write_text(
            "version: 1\n"
            "structures:\n  selected_value: {kind: int, fmt: '<H'}\n"
            "formats:\n  selected: {structure: selected_value, uuid: ABCD, detect: true, length: 0}\n"
        )
        self.automatic = self.directory / "codec.yaml"
        self.automatic.write_text(
            "version: 1\nstructures:\n  automatic_value: {kind: int, fmt: '<B'}\n"
        )

    def run_cli(self, *arguments, data="", success=True):
        result = subprocess.run(
            [str(self.binary), *(str(value) for value in arguments)],
            input=data, capture_output=True, text=True, cwd=self.directory,
        )
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def test_automatic_adjacent_codec_remains_optional(self):
        result = self.run_cli("--config", self.config, "--decode", "automatic_value", data="2A")
        self.assertEqual(json.loads(result.stdout), 42)
        self.automatic.unlink()
        self.run_cli("--check-config", self.config)

    def test_selected_file_replaces_automatic_overlay_and_keeps_embedded_formats(self):
        result = self.run_cli(
            "--config", self.config, "--codec", "mycodec.yaml",
            "--decode", "selected_value", data="3412",
        )
        self.assertEqual(json.loads(result.stdout), 0x1234)
        self.run_cli(
            "--config", self.config, "--codec", self.selected,
            "--decode", "automatic_value", data="2A", success=False,
        )
        self.assertEqual(self.run_cli(
            "--codec", self.selected, "--encode", "selected_value", data="4660",
        ).stdout.strip(), "3412")
        self.assertEqual(json.loads(self.run_cli(
            "--codec", self.selected, "--benchmark-codec", "selected_value", data="3412",
        ).stdout), 0x1234)
        # This structure belongs to the embedded codec, not either overlay.
        self.run_cli("--codec", self.selected, "--decode", "bt_home_v2",
                     data="D2FC40008A0C0E0B10001101")

    def test_check_config_accepts_codec_after_an_action_without_positional_path(self):
        self.automatic.write_text("invalid codec")
        self.run_cli("--config", self.config, "--check-config", "--codec", self.selected)
        self.run_cli("--check-config", self.config, "--codec", self.selected)
        self.run_cli("--check-config", self.config, success=False)

    def test_selected_missing_or_invalid_file_fails_instead_of_falling_back(self):
        missing = self.directory / "absent.yaml"
        result = self.run_cli("--check-config", self.config, "--codec", missing, success=False)
        self.assertIn(str(missing), result.stderr)
        result = self.run_cli("--config", self.config, "--codec", missing, success=False)
        self.assertIn(str(missing), result.stderr)
        self.selected.write_text("not: [valid yaml")
        result = self.run_cli("--check-config", self.config, "--codec", self.selected, success=False)
        self.assertIn(str(self.selected), result.stderr)
        result = self.run_cli("--check-config", self.config, "--codec", self.directory, success=False)
        self.assertIn(str(self.directory), result.stderr)

    def test_codec_requires_a_filename(self):
        for arguments in [("--codec",), ("--codec", ""), ("--codec", "--version")]:
            with self.subTest(arguments=arguments):
                result = self.run_cli(*arguments, success=False)
                self.assertEqual(result.returncode, 2)
                self.assertIn("--codec <file>", result.stderr)

    def test_web_inspection_and_capture_decoding_use_the_same_selection(self):
        request = {"observation": {"mac": "AABBCCDDEEFF", "data": "0316CDAB"}}
        result = self.run_cli(
            "--config", self.config, "--codec", self.selected,
            "--web-config", "inspect", data=json.dumps(request),
        )
        decoded = json.loads(result.stdout)
        self.assertTrue(decoded["success"], decoded)
        self.assertEqual(decoded["wire_format"], "selected")
        self.assertEqual(decoded["decoded"], 0xABCD)
        result = self.run_cli(
            "--config", self.config, "--codec", self.selected,
            "--decode-captures", data=json.dumps(request) + "\n",
        )
        decoded = json.loads(result.stdout)["result"]
        self.assertEqual(decoded["wire_format"], "selected")
        self.assertEqual(decoded["decoded"], 0xABCD)


if __name__ == "__main__":
    unittest.main()
