#!/usr/bin/env python3
"""Exercise the actual service-log setup without touching router paths."""

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "files/root/etc/init.d/rc.ble2uart_gateway"


class ServiceLogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = self.root / "storage with spaces"
        self.store.mkdir()
        self.log = self.root / "rc.ble2uart_gateway.log"
        source = INIT.read_text()
        match = re.search(r"(?ms)^setup_service_log\(\) \{\n.*?^\}", source)
        self.assertIsNotNone(match)
        self.function = match.group()
        match = re.search(r"(?ms)^store_is_persistent\(\) \{\n.*?^\}", source)
        self.assertIsNotNone(match)
        self.check_store = match.group()
        match = re.search(r"(?ms)^config\(\) \{\n.*?^\}", source)
        self.assertIsNotNone(match)
        self.config = match.group()
        match = re.search(r"(?ms)^start\(\) \{\n.*?^\}", source)
        self.assertIsNotNone(match)
        self.start = match.group()

    def setup_log(self, prefix=""):
        environment = dict(
            os.environ,
            LOG=str(self.log),
            BLE2UART_GATEWAY_STORE=str(self.store),
            DAEMON="ble2uart_gateway",
        )
        return subprocess.run(
            ["sh", "-c", self.function + "\n" + prefix + "\nsetup_service_log"],
            env=environment,
            text=True,
            capture_output=True,
        )

    def test_existing_log_is_preserved_and_link_is_reusable(self):
        self.log.write_text("old records\n")
        result = self.setup_log()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.log.is_symlink())
        self.assertEqual(os.readlink(self.log), str(self.store / self.log.name))
        backups = list(self.store.glob(self.log.name + ".previous.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "old records\n")
        (self.store / self.log.name).write_text("new records\n")
        self.assertEqual(self.log.read_text(), "new records\n")
        result = self.setup_log()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(list(self.store.glob(self.log.name + ".previous.*"))), 1)

    def test_backup_failure_keeps_original_log(self):
        self.log.write_text("keep this\n")
        result = self.setup_log("cp() { return 1; }")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cannot preserve", result.stderr)
        self.assertFalse(self.log.is_symlink())
        self.assertEqual(self.log.read_text(), "keep this\n")

    def test_existing_ancestor_must_be_on_persistent_filesystem(self):
        for fstype, expected in (("ext4", 0), ("nfs", 0), ("tmpfs", 1), ("overlay", 1), ("", 1)):
            with self.subTest(fstype=fstype):
                shell = (
                    self.check_store
                    + '\ndf() { printf "Filesystem Type\\n/dev/test %s\\n" "$FSTYPE"; }\n'
                    + 'store_is_persistent "$STORE"'
                )
                environment = dict(os.environ, STORE=str(self.store / "new" / "directory"), FSTYPE=fstype)
                result = subprocess.run(["sh", "-c", shell], env=environment, capture_output=True)
                self.assertEqual(result.returncode, expected)

    def test_start_passes_log_path_and_quoted_config_to_daemon(self):
        executable = self.root / "fake-gateway"
        executable.write_text(
            '#!/bin/sh\n'
            'if [ "$3" = "--get" ]; then printf "/dev/null\\n"; exit 0; fi\n'
            'printf "%s\\n" "$BLE2UART_GATEWAY_LOG" "$1" "$2"\n'
        )
        executable.chmod(0o755)
        (self.store / "ble2uart_gateway.yaml").write_text("config\n")
        shell = (
            self.check_store + "\n" + self.function + "\n" + self.config + "\n" + self.start
            + """
modlib_startdaemon() {
    config || return 1
    while [ "$1" != "-c" ]; do shift; done
    shift
    command=$1
    shift
    /bin/sh -c "$command" "$@"
}
start
"""
        )
        environment = dict(
            os.environ,
            LOG=str(self.log),
            BLE2UART_GATEWAY_STORE=str(self.store),
            DAEMON="ble2uart_gateway",
            GATEWAY_BIN=str(executable),
            PID_FILE=str(self.root / "gateway.pid"),
            BLE2UART_GATEWAY_VERBOSE="no",
            BLE2UART_GATEWAY_EXTRA_ARGS="",
        )
        result = subprocess.run(["sh", "-c", shell], env=environment, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.store / self.log.name
        self.assertEqual((self.store / (self.log.name + ".startup")).read_text().splitlines(),
                         [str(target), "--config", str(self.store / "ble2uart_gateway.yaml")])
        self.assertEqual(os.readlink(self.log), str(target))


if __name__ == "__main__":
    unittest.main()
