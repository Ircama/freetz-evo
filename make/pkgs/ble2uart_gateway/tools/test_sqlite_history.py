#!/usr/bin/env python3
"""Exercise the real SQLite maintenance worker without radio/network access."""

import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time


def run(binary):
    with tempfile.TemporaryDirectory(prefix="ble-history-smoke-") as temporary:
        directory = Path(temporary)
        config_path = directory / "gateway.yaml"
        database = directory / "history.sqlite3"
        log_path = directory / "gateway.log"
        subprocess.run([binary, "--write-default-config", str(config_path)],
                       check=True, capture_output=True)
        config = json.loads(subprocess.run(
            [binary, "--config", str(config_path), "--web-config", "read"],
            check=True, capture_output=True, text=True,
        ).stdout)["config"]
        config["serial"].update(port="/dev/ble-history-smoke-missing", reconnect_delay_ms=20)
        for frontend in config["frontends"].values():
            frontend["enabled"] = False
        sqlite = config["frontends"]["sqlite"]
        sqlite.update(enabled=True, path=str(database), flush_interval_ms=10)
        environment = dict(os.environ, BLE2UART_GATEWAY_CONTROL_SOCKET=str(directory / "private/control.sock"))

        def start():
            config_path.write_text(json.dumps(config))
            subprocess.run([binary, "--check-config", str(config_path)],
                           check=True, capture_output=True)
            log = log_path.open("ab")
            try:
                process = subprocess.Popen([binary, "--config", str(config_path)],
                                           stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                           env=environment)
            finally:
                log.close()
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise AssertionError(log_path.read_text())
                if (directory / "private/control.sock").exists():
                    return process
                time.sleep(0.02)
            stop(process)
            raise AssertionError("private test control socket did not become ready")

        def stop(process):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise AssertionError("gateway did not stop its maintenance worker")
            if process.returncode != 0:
                raise AssertionError(log_path.read_text())

        def wait_query(process, query, expected):
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise AssertionError(log_path.read_text())
                if database.exists():
                    try:
                        with sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=1) as reader:
                            result = reader.execute(query).fetchall()
                        if result == expected:
                            return result
                    except sqlite3.OperationalError:
                        pass
                time.sleep(0.02)
            raise AssertionError(f"query did not converge: {query}\n{log_path.read_text()}")

        process = start()
        try:
            wait_query(process, "PRAGMA user_version", [(1,)])
            wait_query(process, "SELECT count(*) FROM frames", [(0,)])
        finally:
            stop(process)

        noon = int(time.time()) // 86400 * 86400 - 86400 + 43200
        timestamps = [noon + 10, noon + 20, noon + 70, noon + 80, noon - 5 * 86400]
        with sqlite3.connect(database) as writer:
            for index, timestamp in enumerate(timestamps):
                measures = [
                    ("temperature", "C", "real", 20.0 + index, None),
                    ("battery_level", "%", "integer", None, 90 - index),
                    ("opened", "", "integer", None, index % 2),
                    ("counter", "", "integer", None, index),
                ]
                frame = writer.execute(
                    "INSERT INTO frames(received_at_ns,mac,sensor_name,wire_format,state_json) VALUES (?,?,?,?,?)",
                    (timestamp * 1_000_000_000, "AABBCCDDEEFF", "Synthetic", "test", "{}"),
                ).lastrowid
                for ordinal, (attribute, unit, kind, real, integer) in enumerate(measures):
                    writer.execute(
                        "INSERT INTO measurements(frame_id,ordinal,attribute,unit,type,value_real,value_int) VALUES (?,?,?,?,?,?,?)",
                        (frame, ordinal, attribute, unit, kind, real, integer),
                    )

        maintenance = sqlite["maintenance"]
        maintenance.update(enabled=True, interval_s=1, raw_retention_s=1, batch_size=2)
        maintenance["policies"] = [
            {"mac": "", "attribute": attribute, "mode": "progressive",
             "tiers": [{"max_age_s": 2 * 86400, "sample_interval_s": interval}]}
            for attribute, interval in [("temperature", 60), ("battery_level", 86400)]
        ]
        process = start()
        expected = [("battery_level", 1), ("opened", 5), ("temperature", 2)]
        try:
            wait_query(process, "PRAGMA user_version", [(2,)])
            wait_query(process, "SELECT count(*) FROM frames", [(0,)])
            wait_query(process, "SELECT attribute,count(*) FROM history GROUP BY attribute ORDER BY attribute", expected)
            wait_query(process, "SELECT value_json FROM history WHERE attribute='temperature' ORDER BY received_at_ns", [("21.0",), ("23.0",)])
            wait_query(process, "PRAGMA foreign_key_check", [])
            with sqlite3.connect(database, timeout=2) as external_writer:
                external_writer.execute("BEGIN IMMEDIATE")
                frame = external_writer.execute(
                    "INSERT INTO frames(received_at_ns,mac,sensor_name,wire_format,state_json) VALUES (?,?,?,?,?)",
                    ((noon + 100) * 1_000_000_000, "AABBCCDDEEFF", "Synthetic", "test", "{}"),
                ).lastrowid
                external_writer.execute(
                    "INSERT INTO measurements(frame_id,ordinal,attribute,unit,type,value_real) VALUES (?,?,?,?,?,?)",
                    (frame, 0, "humidity", "%", "real", 50.0),
                )
                time.sleep(2.2)
            expected = [("battery_level", 1), ("humidity", 1), ("opened", 5), ("temperature", 2)]
            wait_query(process, "SELECT count(*) FROM frames", [(0,)])
            wait_query(process, "SELECT attribute,count(*) FROM history GROUP BY attribute ORDER BY attribute", expected)
            assert "SQLite maintenance deferred: database is locked" not in log_path.read_text(), log_path.read_text()
        finally:
            stop(process)

        maintenance["enabled"] = False
        process = start()
        try:
            wait_query(process, "SELECT attribute,count(*) FROM history GROUP BY attribute ORDER BY attribute", expected)
        finally:
            stop(process)
        return {"schema": 2, "temperature_samples": 2, "battery_samples": 1,
            "contact_samples": 5, "counter_samples": 0, "reopen_without_maintenance": True,
            "external_writer_lock_recovered": True, "transient_lock_warning_spam": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    arguments = parser.parse_args()
    print(json.dumps(run(str(Path(arguments.binary).resolve()))))