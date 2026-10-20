#!/usr/bin/env python3
"""Exercise package build/install rules without a firmware build."""

from pathlib import Path
import re
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


class BuildInstallTests(unittest.TestCase):
    def install(self, separate, fail_patch=False):
        package = Path(__file__).resolve().parents[1]
        repository = package.parents[2]
        rules = (package / "ble2uart_gateway.mk").read_text()
        start = rules.index("$($(PKG)_TARGET_BINARY):")
        install_rule = rules[start:rules.index("\n\n", start)]
        dependency = next(line for line in rules.splitlines() if "_DEPENDS_ON +=" in line)
        helpers = []
        for filename, name in [
            ("make/include/300-helper.mk", "INSTALL_FILE"),
            ("make/pkgs/Makefile.in", "INSTALL_BINARY_STRIP"),
        ]:
            match = re.search(
                rf"^define {name}\n.*?^endef$",
                (repository / filename).read_text(), re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(match)
            helpers.append(match.group())
        with tempfile.TemporaryDirectory(prefix="ble-install-") as temporary:
            directory = Path(temporary)
            (directory / "binary").write_text("test executable\n")
            for name, body in {
                "readelf": "printf 'INTERP\\n'",
                "strip": "echo strip >> events",
                "patch": f'echo "patch $*" >> events\nexit {42 if fail_patch else 0}',
            }.items():
                script = directory / name
                script.write_text("#!/bin/sh\n" + body + "\n")
                script.chmod(0o755)
            makefile = f"""
SHELL := /bin/bash
.DEFAULT_GOAL := all
PKG := BLE2UART_GATEWAY
BLE2UART_GATEWAY_BINARY := binary
BLE2UART_GATEWAY_TARGET_BINARY := stage/gateway
FREETZ_SEPARATE_AVM_UCLIBC := {'y' if separate else ''}
FREETZ_LIBRARY_DIR := /usr/lib/freetz
TOOLS_DIR := tools
PATCHELF_TARGET := $(CURDIR)/tools/patchelf-target
TARGET_READELF := $(CURDIR)/readelf
TARGET_STRIP := $(CURDIR)/strip
{dependency}
{chr(10).join(helpers)}
{install_rule}
tools/patchelf-target: patch
\t@mkdir -p tools
\t@echo tool >> events
\t@cp $< $@
.PHONY: all
all: stage/gateway
\t@echo dependencies=$(BLE2UART_GATEWAY_DEPENDS_ON)
"""
            result = subprocess.run(
                ["make", "--no-print-directory", "-j8", "-f", "-"],
                cwd=directory, input=makefile, capture_output=True, text=True,
            )
            events = (directory / "events").read_text().splitlines()
        return result, events

    def test_separate_libc_builds_patchelf_before_install_and_patches_once(self):
        result, events = self.install(True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dependencies=patchelf-target-host", result.stdout)
        self.assertEqual(events, [
            "tool", "patch --set-interpreter /usr/lib/freetz/ld-uClibc.so.1 stage/gateway", "strip",
        ])

    def test_shared_libc_needs_no_patchelf(self):
        result, events = self.install(False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dependencies=\n", result.stdout)
        self.assertEqual(events, ["strip"])

    def test_patchelf_failure_is_not_hidden_by_strip(self):
        result, events = self.install(True, fail_patch=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error 42", result.stderr)
        self.assertEqual(events, [
            "tool", "patch --set-interpreter /usr/lib/freetz/ld-uClibc.so.1 stage/gateway",
        ])


if __name__ == "__main__":
    unittest.main()
