#!/usr/bin/env python3
"""Check Freetz service integration without rebuilding or touching router services."""

import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time
import unittest


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE / "files/root"
DEFAULTS = ROOT / "etc/default.influxdb3/influxdb3.cfg"
HOOK = ROOT / "etc/default.influxdb3/influxdb3.save"
RC = ROOT / "etc/init.d/rc.influxdb3"


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="influx-service-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.data = self.directory / "data with spaces"
        self.data.mkdir()
        self.saved = self.directory / "saved.cfg"
        self.args = self.directory / "args"
        self.events = self.directory / "events"
        self.pid = self.directory / "influxdb3.pid"
        self.wait_pid = self.directory / "influxdb3.wait.pid"
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        (self.bin / "influxdb3").write_text("#!/bin/sh\nexit 0\n")
        (self.bin / "wget").write_text('#!/bin/sh\n[ "$HEALTH_GOOD" = 1 ]\n')
        for file in self.bin.iterdir():
            file.chmod(0o755)
        self.environment = {
            **os.environ, "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
            "TEST_ARGS": str(self.args), "TEST_EVENTS": str(self.events), "HEALTH_GOOD": "0",
        }
        self.modlib = self.directory / "modlibrc"
        self.modlib.write_text("""
modlib_start() { start; }
modlib_startdaemon() { printf '%s\\0' "$@" > "$TEST_ARGS"; }
modlib_stop() { echo stop >> "$TEST_EVENTS"; }
modlib_restart() { echo restart >> "$TEST_EVENTS"; }
modlib_status() { :; }
modreg() { printf '%s\\n' "$*" >> "$TEST_EVENTS"; }
modunreg() { printf '%s\\n' "$*" >> "$TEST_EVENTS"; }
""")
        source = RC.read_text()
        for original, replacement in {
            "/etc/init.d/modlibrc": str(self.modlib),
            "/mod/etc/default.influxdb3/influxdb3.cfg": str(DEFAULTS),
            "/mod/etc/default.influxdb3/influxdb3.save": str(HOOK),
            "/mod/etc/conf/influxdb3.cfg": str(self.saved),
            "/usr/bin/influxdb3": str(self.bin / "influxdb3"),
            "/var/run/influxdb3.pid": str(self.pid),
            "/var/run/influxdb3.wait.pid": str(self.wait_pid),
            "/tmp/rc.influxdb3.log": str(self.directory / "service.log"),
        }.items():
            source = source.replace(original, replacement)
        self.script = self.directory / "rc.influxdb3"
        self.script.write_text(source)
        self.script.chmod(0o755)
        self.save(INFLUXDB3_DATA_DIR=str(self.data))

    def save(self, **values):
        self.saved.write_text("\n".join(
            f"export {key}={shlex.quote(str(value))}" for key, value in values.items()
        ))

    def run_rc(self, action, **environment):
        return subprocess.run(
            ["sh", str(self.script), action], capture_output=True, text=True, timeout=5,
            env={**self.environment, **environment},
        )

    def validate(self, **values):
        self.save(**values)
        return subprocess.run(
            ["sh", "-c", '. "$1"; . "$2"; . "$3"; pkg_pre_save',
             "sh", str(DEFAULTS), str(self.saved), str(HOOK)],
            capture_output=True, text=True, timeout=5,
        )

    def test_all_cgi_fields_have_exported_defaults(self):
        names = re.findall(r"^export INFLUXDB3_([A-Z_]+)=", DEFAULTS.read_text(), re.M)
        fields = re.findall(r'cgi_print_\w+\s+"([a-z_]+)"', (ROOT / "usr/lib/cgi-bin/influxdb3.cgi").read_text())
        self.assertEqual(set(fields), {name.lower() for name in names})
        self.assertIn("INFLUXDB3_ENABLED='no'", DEFAULTS.read_text())
        self.assertIn("INFLUXDB3_WITHOUT_AUTH='no'", DEFAULTS.read_text())
        self.assertEqual(self.validate().returncode, 0)
        for key, value in (
            ("INFLUXDB3_PORT", "0"), ("INFLUXDB3_PORT", "65536"),
            ("INFLUXDB3_PORT", "12345678901234567890"),
            ("INFLUXDB3_NODE_ID", "../other"), ("INFLUXDB3_NODE_ID", ""),
            ("INFLUXDB3_DATA_DIR", "relative"), ("INFLUXDB3_DATA_DIR", "/tmp/bad\npath"),
            ("INFLUXDB3_CONFIG_WAIT", "-1"), ("INFLUXDB3_CONFIG_WAIT", "601"),
            ("INFLUXDB3_STARTUP_WAIT", "0"), ("INFLUXDB3_WITHOUT_AUTH", "maybe"),
        ):
            with self.subTest(key=key, value=value):
                result = self.validate(**{key: value})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Error:", result.stderr)
        self.assertNotEqual(self.validate(INFLUXDB3_ENABLED="yes").returncode, 0)
        result = self.validate(INFLUXDB3_ENABLED="yes", INFLUXDB3_DATA_DIR=str(self.data))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_start_quotes_paths_and_auth_is_not_disabled_implicitly(self):
        result = self.run_rc("start")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.args.read_bytes().decode().split("\0")[:-1]
        self.assertEqual(args[args.index("--data-dir") + 1], str(self.data))
        self.assertEqual(args[args.index("--http-bind") + 1], "127.0.0.1:8181")
        self.assertIn("--wal-replay-fail-on-error", args)
        self.assertNotIn("--without-auth", args)
        self.save(INFLUXDB3_DATA_DIR=str(self.data), INFLUXDB3_BIND="::1", INFLUXDB3_WITHOUT_AUTH="yes")
        result = self.run_rc("start")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.args.read_bytes().decode().split("\0")[:-1]
        self.assertEqual(args[args.index("--http-bind") + 1], "[::1]:8181")
        self.assertIn("--without-auth", args)

    def test_start_fails_fast_for_missing_storage_or_unmanaged_listener(self):
        self.save(INFLUXDB3_DATA_DIR=str(self.directory / "missing"))
        result = self.run_rc("start")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("data directory missing", result.stderr)
        self.assertFalse((self.directory / "missing").exists())
        self.save(INFLUXDB3_DATA_DIR=str(self.data))
        result = self.run_rc("start", HEALTH_GOOD="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unmanaged", result.stderr)
        self.assertFalse(self.args.exists())

    def test_disabled_load_registers_without_starting_and_save_does_not_restart(self):
        result = self.run_rc("load")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cgi influxdb3 InfluxDB 3", self.events.read_text())
        self.assertIn("daemon influxdb3", self.events.read_text())
        self.assertFalse(self.args.exists())
        result = subprocess.run(
            ["sh", "-c", '. "$1"; pkg_apply_save', "sh", str(HOOK)],
            capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.args.exists())

    def test_boot_wait_is_async_and_can_be_cancelled(self):
        self.save(INFLUXDB3_ENABLED="yes", INFLUXDB3_DATA_DIR=str(self.directory / "absent"), INFLUXDB3_CONFIG_WAIT="120")
        began = time.monotonic()
        try:
            result = self.run_rc("load")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertLess(time.monotonic() - began, 2)
            self.assertTrue(self.wait_pid.exists())
        finally:
            stopped = self.run_rc("stop")
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        self.assertFalse(self.wait_pid.exists())
        self.assertFalse(self.args.exists())
        self.save(INFLUXDB3_ENABLED="yes", INFLUXDB3_DATA_DIR=str(self.data), INFLUXDB3_CONFIG_WAIT="0")
        self.assertEqual(self.run_rc("load").returncode, 0)
        self.assertTrue(self.args.exists())

    def test_startup_health_failure_terminates_only_the_started_process(self):
        self.save(INFLUXDB3_DATA_DIR=str(self.data), INFLUXDB3_STARTUP_WAIT="1")
        child = subprocess.Popen(["sleep", "60"])
        try:
            self.pid.write_text(str(child.pid))
            command = f"set -- status; . {shlex.quote(str(self.script))}; startdaemon_post"
            result = subprocess.run(
                ["sh", "-c", command], env=self.environment, capture_output=True, text=True, timeout=5,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("did not become healthy", result.stderr)
            child.wait(timeout=3)
        finally:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=3)

    def test_boot_wait_starts_when_storage_is_ready_and_removes_waiter_pid(self):
        self.save(INFLUXDB3_ENABLED="yes", INFLUXDB3_DATA_DIR=str(self.data), INFLUXDB3_CONFIG_WAIT="120")
        try:
            result = self.run_rc("load")
            self.assertEqual(result.returncode, 0, result.stderr)
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if self.args.exists() and not self.wait_pid.exists():
                    break
                time.sleep(0.01)
            self.assertTrue(self.args.exists(), (self.directory / "service.log").read_text())
            self.assertFalse(self.wait_pid.exists())
        finally:
            self.run_rc("stop")

    def test_cgi_native_language_substitution(self):
        for language in ("de", "en"):
            with self.subTest(language=language):
                cgi = self.directory / f"influxdb3-{language}.cgi"
                cgi.write_text((ROOT / "usr/lib/cgi-bin/influxdb3.cgi").read_text())
                subprocess.run(
                    ["bash", "-c", '. "$1"; modlangsubst "$2" "$3"', "bash",
                     str(PACKAGE.parents[2] / "tools/freetz_functions"), language, str(cgi)],
                    env={**os.environ, "FREETZ_LANG_NEEDS_TRANSLATION": "n"},
                    capture_output=True, text=True, check=True, timeout=5,
                )
                self.assertNotIn("$(lang ", cgi.read_text())
                self.assertNotIn("*** error:", cgi.read_text())
                subprocess.run(["sh", "-n", str(cgi)], check=True, capture_output=True, timeout=5)

    def test_make_progress_uses_package_context_and_standard_recompile(self):
        makefile = (PACKAGE / "influxdb3.mk").read_text()
        self.assertNotIn("$(pkg)-recompile:", makefile)
        self.assertNotIn("$(INSTALL_BINARY_STRIP)", makefile)
        declarations = "\n".join(
            line for line in makefile.splitlines()
            if ": private pkg :=" in line or ": private PKG_TYPE :=" in line
        )
        self.assertTrue(declarations)
        source = f"""
SHELL := /bin/bash
.DEFAULT_GOAL := check
SOURCE_DIR_ROOT := {self.directory}
RM := rm -f
FREETZ_VERBOSITY_LEVEL := 0
include {PACKAGE.parents[2]}/make/include/500-echo.mk
PKG := INFLUXDB3
pkg := influxdb3
PKG_TYPE := BIN
INFLUXDB3_BINARY := binary
{declarations}
PKG :=
pkg :=
PKG_TYPE :=
.PHONY: check binary
binary:
\t@$(call _ECHO,building)
check: binary
\t@$(call _ECHO_DONE)
"""
        result = subprocess.run(["make", "--no-print-directory", "-f", "-"], input=source, capture_output=True, text=True, check=True)
        self.assertIn("package/influxdb3", result.stdout)
        self.assertRegex(result.stdout, r"\bdone\x1b")


if __name__ == "__main__":
    unittest.main()
