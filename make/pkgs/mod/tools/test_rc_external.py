#!/usr/bin/env python3

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "files/root/etc/init.d/rc.external"


class DeferredServicesTests(unittest.TestCase):
    def test_status_contract_preserves_daemon_guard_and_loads_frontends(self):
        source = SCRIPT.read_text()
        start = source.index("start_deferred_services() {")
        end = source.index("\n}\n", start) + 3
        function = source[start:end]

        with tempfile.TemporaryDirectory(prefix="freetz-external-test-") as temporary:
            directory = Path(temporary)
            init = directory / "init"
            init.mkdir()
            calls = directory / "calls"
            deferred = directory / "deferred.pkg"
            statuses = {
                "running": ("running", 0),
                "inetd": ("inetd", 5),
                "stopped": ("stopped", 3),
                "unknown": ("unknown", 1),
                "mpd-mpc": ("Radio station\n[playing] #1/1\nvolume: 50%", 0),
                "empty": ("", 0),
                "compound-running": ("snapserver: running\nsnapclient: stopped", 0),
                "compound-inetd": ("server: stopped\nclient: inetd", 5),
                "compound-stopped": ("snapserver: stopped\nsnapclient: stopped", 3),
                "external": ("stopped", 3),
                "not-executable": ("stopped", 3),
            }
            deferred.write_text("\n".join(statuses) + "\nmissing\n")
            for name, (status, returncode) in statuses.items():
                script = init / f"rc.{name}"
                script.write_text(
                    "#!/bin/sh\ncase \"$1\" in\n"
                    f"status) printf '%s' {shlex.quote(status)}; exit {returncode} ;;\n"
                    f"load) printf '%s\\n' {shlex.quote(name)} >> {shlex.quote(str(calls))} ;;\n"
                    "esac\n"
                )
                script.chmod(0o644 if name == "not-executable" else 0o755)

            function = function.replace("/mod/etc/external.defer.pkg", str(deferred))
            function = function.replace("/mod/etc/init.d/rc.$pkg", str(init / "rc.$pkg"))
            result = subprocess.run(
                ["sh", "-s"],
                input="log() { printf '%s\\n' \"$*\"; }\n" + function + "\nstart_deferred_services\n",
                env=dict(os.environ, EXTERNAL_SERVICES=" external "),
                text=True,
                capture_output=True,
                check=True,
            )
            loaded = calls.read_text().splitlines() if calls.exists() else []
            self.assertIn("mpd-mpc", loaded)
            self.assertEqual(loaded, ["stopped", "unknown", "mpd-mpc", "empty", "compound-stopped"])
            self.assertIn("no executable init script", result.stdout)

            calls.unlink()
            external = directory / "external.pkg"
            external.write_text("external\n")
            start = source.index("exec_rcs() {")
            end = source.index("\n}\n", start) + 3
            routing = source[start:end]
            routing = routing.replace("/mod/etc/external.pkg", str(external))
            routing = routing.replace("/mod/etc/static.pkg", str(deferred))
            routing = routing.replace("/mod/etc/init.d/rc.$pkg", str(init / "rc.$pkg"))
            subprocess.run(
                ["sh", "-s"],
                input=("log() { printf '%s\\n' \"$*\"; }\nstatus() { return 0; }\neventadd() { :; }\n"
                       + routing + "\n" + function + "\nexec_rcs load\nstart_deferred_services\n"),
                env=dict(os.environ, MOD_EXTERNAL_FREETZ_SERVICES="yes", MOD_EXTERNAL_OWN_SERVICES="mpd-mpc",
                         EXTERNAL_CUSTOM_FILE=str(directory / "no-custom-hook")),
                text=True,
                capture_output=True,
                check=True,
            )
            loaded = calls.read_text().splitlines()
            self.assertEqual(loaded.count("mpd-mpc"), 1)
            self.assertEqual(loaded, ["mpd-mpc", "external", "stopped", "unknown", "empty", "compound-stopped"])


if __name__ == "__main__":
    unittest.main()