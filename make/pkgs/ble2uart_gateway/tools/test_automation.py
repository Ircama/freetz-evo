#!/usr/bin/env python3
"""Run per-device availability rules, BLE PTY traffic and verified HTTPS webhooks."""

import argparse
import http.server
import json
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import time

from replay_capture import Firmware


def certificates(root):
    commands = [
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
         "-subj", "/CN=BLE automation test CA", "-addext", "basicConstraints=critical,CA:TRUE",
         "-keyout", str(root / "ca.key"), "-out", str(root / "ca.pem")],
        ["openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=localhost",
         "-keyout", str(root / "server.key"), "-out", str(root / "server.csr")],
    ]
    for command in commands:
        subprocess.run(command, check=True, capture_output=True)
    (root / "server.ext").write_text(
        "subjectAltName=IP:127.0.0.1,DNS:localhost\nextendedKeyUsage=serverAuth\nbasicConstraints=critical,CA:FALSE\n"
    )
    subprocess.run(["openssl", "x509", "-req", "-in", str(root / "server.csr"),
                    "-CA", str(root / "ca.pem"), "-CAkey", str(root / "ca.key"), "-CAcreateserial",
                    "-days", "2", "-extfile", str(root / "server.ext"), "-out", str(root / "server.pem")],
                   check=True, capture_output=True)


def run(binary, tls_directory=None):
    with tempfile.TemporaryDirectory(prefix="ble-automation-test-") as temporary:
        root = Path(temporary)
        tls = Path(tls_directory) if tls_directory else root
        if tls_directory is None:
            certificates(tls)
        received = []
        lock = threading.Lock()

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                with lock:
                    received.append({"path": self.path, "headers": {name.lower(): value for name,value in self.headers.items()}, "body": body.decode()})
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *arguments):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(tls / "server.pem"), str(tls / "server.key"))
        server.socket = context.wrap_socket(server.socket, server_side=True)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        firmware = Firmware()
        config_path, state_path, log_path = root / "config.yaml", root / "state.json", root / "gateway.log"
        subprocess.run([binary, "--write-default-config", str(config_path)], check=True, capture_output=True)
        config = json.loads(subprocess.run([binary, "--config", str(config_path), "--web-config", "read"],
                                          check=True, capture_output=True, text=True).stdout)["config"]
        for frontend in config["frontends"].values():
            frontend["enabled"] = False
        preset = json.loads(subprocess.run([binary, "--web-config", "availability-presets"],
                          check=True, capture_output=True, text=True).stdout)["rule"]
        assert preset["stale_after_s"] == 600
        assert "automation" not in config
        config["serial"].update(port=firmware.path, reconnect_delay_ms=20)
        config["availability_state_file"] = str(state_path)
        rule = preset
        rule.update(enabled=True, stale_after_s=2, startup_grace_s=0)
        config["devices"] = [{"mac": "AABBCCDDEEFF", "label": "Synthetic thermometer", "enabled": True, "rules": [rule]}]
        endpoint = f"https://127.0.0.1:{server.server_port}"
        rule["webhook"].update(provider="ntfy", url=endpoint + "/thermometers",
                                      token="synthetic-private-token", ca_file=str(tls / "ca.pem"), timeout_ms=2000, ipv4_only=True)
        config_path.write_text(json.dumps(config))
        environment = dict(os.environ, BLE2UART_GATEWAY_CONTROL_SOCKET=str(root / "private/control.sock"))
        process = None

        def start():
            nonlocal process
            firmware.scanning.clear()
            with log_path.open("ab") as log:
                process = subprocess.Popen([binary, "--config", str(config_path)], env=environment,
                                           stdin=subprocess.DEVNULL, stdout=log, stderr=log)
            deadline = time.monotonic() + 20
            while not firmware.scanning.wait(0.05):
                if process.poll() is not None or time.monotonic() > deadline:
                    raise AssertionError(log_path.read_text())

        def stop():
            nonlocal process
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise AssertionError("automation worker did not stop")
                assert process.returncode == 0, log_path.read_text()
            process = None

        def traffic(seconds, temperature):
            deadline = time.monotonic() + seconds
            advertisement = bytes.fromhex("0716D2FC4002C409" if temperature else "0616D2FC400164")
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise AssertionError(log_path.read_text())
                assert firmware.observation("AABBCCDDEEFF", advertisement), firmware.error
                time.sleep(0.2)

        def events():
            with lock:
                return list(received)

        def webhook_test(settings):
            response = subprocess.run([binary, "--config", str(config_path), "--web-config", "availability-test"],
                                      input=json.dumps({"rule": settings}), capture_output=True, text=True, timeout=10)
            return json.loads(response.stdout)

        try:
            start()
            traffic(3, True)
            assert len(events()) == 0, "equal fresh temperatures must not alert"
            traffic(6, False)
            assert len(events()) == 1, (events(), log_path.read_text())
            alert = events()[0]
            assert alert["path"] == "/thermometers"
            assert alert["headers"]["authorization"] == "Bearer synthetic-private-token"
            assert alert["headers"]["priority"] == "4"
            assert alert["headers"]["tags"] == "thermometer"
            assert "no temperature reading" in alert["body"]
            stop()
            start()
            traffic(3, False)
            assert len(events()) == 1, "active episode must not be re-sent after restart"
            traffic(3, True)
            assert len(events()) == 2, (events(), log_path.read_text())
            assert "readings resumed" in events()[1]["body"]
            assert len({event["headers"]["idempotency-key"] for event in events()}) == 2
            status = subprocess.run([binary, "--config", str(config_path), "--web-config", "availability-status"],
                                    check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=10)
            assert "synthetic-private-token" not in status.stdout
            assert json.loads(status.stdout)["engine"] == "availability"
            stop()
            custom = json.loads(json.dumps(rule))
            custom.update(message="Synthetic custom message\nSecond line", tgs="warning,test")
            custom["webhook"]["tags"] = "base-tags"
            assert webhook_test(custom)["success"]
            assert events()[-1]["body"] == custom["message"]
            assert events()[-1]["headers"]["tags"] == "warning,test"
            fallback = json.loads(json.dumps(custom))
            fallback.update(message=" \n", tgs="  ")
            assert webhook_test(fallback)["success"]
            assert "explicit webhook configuration test" in events()[-1]["body"]
            assert events()[-1]["headers"]["tags"] == "base-tags"
            gotify = json.loads(json.dumps(custom))
            gotify["webhook"].update(provider="gotify", url=endpoint + "/message")
            assert webhook_test(gotify)["success"]
            message = events()[-1]
            assert message["path"] == "/message"
            assert message["headers"]["x-gotify-key"] == "synthetic-private-token"
            assert json.loads(message["body"])["title"]
            assert json.loads(message["body"])["message"] == custom["message"]
            untrusted = json.loads(json.dumps(gotify))
            untrusted["webhook"]["ca_file"] = ""
            before = len(events())
            assert not webhook_test(untrusted)["success"], "untrusted HTTPS certificate must fail"
            assert len(events()) == before, "no HTTP request may pass an untrusted TLS connection"
            rule.update(message="Synthetic automatic custom message", tgs="automatic,custom")
            rule["webhook"]["tags"] = "base-tags"
            config["availability_state_file"] = str(root / "custom-state.json")
            config_path.write_text(json.dumps(config))
            before = len(events())
            start()
            traffic(3, True)
            assert len(events()) == before
            traffic(5, False)
            assert len(events()) == before + 1
            assert events()[-1]["body"] == rule["message"]
            assert events()[-1]["headers"]["tags"] == rule["tgs"]
            traffic(3, True)
            assert len(events()) == before + 2
            assert events()[-1]["body"] == rule["message"]
            stop()
            return {"engine": "availability", "preset_seconds": 600, "stale_notifications": 2,
                    "recovery_notifications": 2, "restart_duplicates": 0, "ntfy_https": True,
                    "gotify_https": True, "untrusted_certificate_rejected": True,
                    "custom_message_and_tgs": True, "empty_override_defaults": True}
        finally:
            stop()
            firmware.close()
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--tls-directory")
    options = parser.parse_args()
    print(json.dumps(run(str(Path(options.binary).resolve()), options.tls_directory)))