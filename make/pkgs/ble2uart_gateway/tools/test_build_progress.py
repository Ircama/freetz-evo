#!/usr/bin/env python3
"""Exercise the package's progress context without a firmware build."""

from pathlib import Path
import subprocess
import tempfile
import unittest


class BuildProgressTests(unittest.TestCase):
    def progress(self, context):
        package = Path(__file__).resolve().parents[1]
        repository = package.parents[2]
        declarations = "\n".join(
            line for line in (package / "ble2uart_gateway.mk").read_text().splitlines()
            if ": private pkg :=" in line or ": private PKG_TYPE :=" in line
        )
        self.assertTrue(declarations)
        with tempfile.TemporaryDirectory(prefix="ble-progress-") as directory:
            source = f"""
SHELL := /bin/bash
.DEFAULT_GOAL := check
SOURCE_DIR_ROOT := {directory}
RM := rm -f
FREETZ_VERBOSITY_LEVEL := 0
include {repository}/make/include/500-echo.mk
PKG := BLE2UART_GATEWAY
pkg := ble2uart_gateway
PKG_TYPE := BIN
BLE2UART_GATEWAY_DIR := build
BLE2UART_GATEWAY_CARGO_DL_STAMP := fetched
BLE2UART_GATEWAY_BINARY := binary
{declarations if context else ''}
PKG :=
pkg :=
PKG_TYPE :=
.PHONY: check binary
binary:
\t@$(call _ECHO,building)
check: binary
\t@$(call _ECHO_DONE)
"""
            result = subprocess.run(
                ["make", "--no-print-directory", "-f", "-"],
                input=source, capture_output=True, text=True, check=True,
            )
        return result.stdout

    def test_package_context_produces_header_and_done(self):
        output = self.progress(True)
        self.assertIn("package/ble2uart_gateway", output)
        self.assertRegex(output, r"\bdone\x1b")

    def test_cleared_context_reproduces_missing_done(self):
        output = self.progress(False)
        self.assertNotIn("package/ble2uart_gateway", output)
        self.assertNotIn("done", output)


if __name__ == "__main__":
    unittest.main()
