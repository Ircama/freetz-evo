#!/usr/bin/env python3
"""Exercise the read-only sensor dashboard CGI against a temporary database.

The test never touches the radio, the network or a production database: it
creates a schema-2 SQLite file, feeds it to `ble2uart-gateway --portal` through
`BLE2UART_PORTAL_DB` and checks the JSON/HTML the CGI returns for the same
environment variables the freetz wrapper provides.
"""

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
import subprocess
import tempfile
import time

SECOND = 1_000_000_000

SCHEMA = """
CREATE TABLE frames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at_ns INTEGER NOT NULL,
    mac TEXT NOT NULL,
    sensor_name TEXT NOT NULL,
    wire_format TEXT NOT NULL,
    state_json TEXT NOT NULL
);
CREATE INDEX frames_mac_time ON frames(mac, received_at_ns);
CREATE INDEX frames_time ON frames(received_at_ns);
CREATE TABLE measurements (
    frame_id INTEGER NOT NULL REFERENCES frames(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    attribute TEXT NOT NULL,
    unit TEXT NOT NULL,
    type TEXT NOT NULL,
    value_real REAL,
    value_int INTEGER,
    value_text TEXT,
    PRIMARY KEY (frame_id, ordinal)
);
CREATE INDEX measurements_attribute_frame ON measurements(attribute, frame_id);
CREATE TABLE history_devices (
    mac TEXT PRIMARY KEY,
    sensor_name TEXT NOT NULL,
    device_json TEXT NOT NULL
);
CREATE TABLE history_series (
    id INTEGER PRIMARY KEY,
    mac TEXT NOT NULL REFERENCES history_devices(mac),
    attribute TEXT NOT NULL,
    unit TEXT NOT NULL,
    UNIQUE(mac, attribute, unit)
);
CREATE TABLE history_samples (
    id INTEGER PRIMARY KEY,
    series_id INTEGER NOT NULL REFERENCES history_series(id),
    received_at_ns INTEGER NOT NULL,
    type TEXT NOT NULL,
    value_json TEXT NOT NULL
);
CREATE INDEX history_series_time ON history_samples(series_id, received_at_ns, id);
CREATE INDEX history_series_order ON history_samples(series_id, id);
CREATE VIEW history AS
    SELECT series.mac, device.sensor_name, series.attribute, series.unit,
           sample.received_at_ns, sample.type, sample.value_json
    FROM history_samples sample
    JOIN history_series series ON series.id = sample.series_id
    JOIN history_devices device ON device.mac = series.mac
    UNION ALL
    SELECT frame.mac, frame.sensor_name, measure.attribute, measure.unit,
           frame.received_at_ns, measure.type,
           CASE measure.type
             WHEN 'real' THEN printf('%!.17g', measure.value_real)
             WHEN 'integer' THEN CAST(measure.value_int AS TEXT)
             WHEN 'boolean' THEN CASE measure.value_int WHEN 0 THEN 'false' ELSE 'true' END
             WHEN 'text' THEN json_quote(measure.value_text)
             WHEN 'null' THEN 'null'
             ELSE measure.value_text
           END
    FROM measurements measure JOIN frames frame ON frame.id = measure.frame_id;
PRAGMA user_version = 2;
"""


def build(directory):
    database = directory / "portal.db"
    # Keep the synthetic samples inside the "last 24 hours" window.
    now = int(time.time()) * SECOND
    connection = sqlite3.connect(database)
    connection.executescript(SCHEMA)

    def frame(identifier, mac, name, offset):
        connection.execute(
            "INSERT INTO frames (id, received_at_ns, mac, sensor_name, wire_format, state_json)"
            " VALUES (?,?,?,?,'bthome','{}')",
            (identifier, now - offset, mac, name))

    def measure(frame_id, ordinal, attribute, unit, kind, real=None, integer=None, text=None):
        connection.execute(
            "INSERT INTO measurements (frame_id, ordinal, attribute, unit, type,"
            " value_real, value_int, value_text) VALUES (?,?,?,?,?,?,?,?)",
            (frame_id, ordinal, attribute, unit, kind, real, integer, text))

    # device A: archived temperature + raw humidity/contact/text
    connection.execute(
        "INSERT INTO history_devices (mac, sensor_name, device_json) VALUES (?,?,'{}')",
        ("AABBCCDDEEFF", "Sonda cucina"))
    connection.execute(
        "INSERT INTO history_series (id, mac, attribute, unit) VALUES (1,'AABBCCDDEEFF','temperature','°C')")
    for offset, value in ((90, "20.0"), (60, "21.0"), (30, "22.0")):
        connection.execute(
            "INSERT INTO history_samples (series_id, received_at_ns, type, value_json)"
            " VALUES (1, ?, 'real', ?)", (now - offset * SECOND, value))
    frame(1, "AABBCCDDEEFF", "Sonda cucina", 10 * SECOND)
    measure(1, 0, "humidity", "%", "real", real=55.5)
    measure(1, 1, "contact", "", "boolean", integer=1)
    measure(1, 2, "firmware", "", "text", text="v1.2")
    measure(1, 3, "counter", "", "unsigned", text="42")

    # device B: raw-only values, no consolidated history at all
    frame(2, "112233445566", "Sonda garage", 5 * SECOND)
    measure(2, 0, "temperature", "°C", "real", real=10.5)
    measure(2, 1, "battery_v", "V", "real", real=2.9)
    connection.commit()
    connection.close()
    return database, now


def call(binary, database, query, method="GET"):
    environment = dict(os.environ)
    environment.update({
        "BLE2UART_PORTAL_DB": str(database),
        "QUERY_STRING": query,
        "REQUEST_METHOD": method,
        "GATEWAY_INTERFACE": "CGI/1.1",
        "SERVER_PROTOCOL": "HTTP/1.1",
    })
    result = subprocess.run([binary, "--portal"], env=environment,
                            capture_output=True, timeout=120)
    # Do not use text=True: universal newlines would rewrite the CRLF
    # separators the CGI protocol requires.
    output = result.stdout.decode("utf-8", "replace")
    head, _, body = output.partition("\r\n\r\n")
    return head, body, result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(binary):
    with tempfile.TemporaryDirectory(prefix="ble-portal-smoke-") as temporary:
        directory = Path(temporary)
        database, now = build(directory)
        before = digest(database)

        head, body, _ = call(binary, database, "action=page")
        assert "200 OK" in head, head
        assert "text/html" in head, head
        assert "/ble2uart_gateway/portal.js" in body, body[:200]

        head, body, _ = call(binary, database, "action=page", method="HEAD")
        assert "200 OK" in head and body == "", (head, body[:80])

        info = json.loads(call(binary, database, "action=info")[1])
        assert info["ok"] and info["schema"] == 2, info
        assert info["devices"] == 1 and info["series"] == 1, info
        assert info["samples"] == 3 and info["process"]["peak_kb"] > 0, info

        catalog = json.loads(call(binary, database, "action=catalog")[1])
        devices = {device["mac"]: device for device in catalog["devices"]}
        assert set(devices) == {"AABBCCDDEEFF", "112233445566"}, devices.keys()
        assert devices["AABBCCDDEEFF"]["name"] == "Sonda cucina"
        found = {(series["attribute"], series["unit"]): series
                 for series in devices["AABBCCDDEEFF"]["series"]}
        assert found[("temperature", "°C")]["kind"] == "numeric"
        assert found[("temperature", "°C")]["value"] == 22.0
        assert found[("temperature", "°C")]["series_id"] == 1
        assert found[("humidity", "%")]["value"] == 55.5
        assert found[("contact", "")]["kind"] == "boolean"
        assert found[("contact", "")]["value"] is True
        assert found[("firmware", "")]["kind"] == "text"
        assert found[("firmware", "")]["value"] == "v1.2"
        raw_only = {series["attribute"]: series
                    for series in devices["112233445566"]["series"]}
        assert raw_only["temperature"]["series_id"] is None
        assert raw_only["battery_v"]["value"] == 2.9

        # 1 hour with 300 buckets keeps the three archived samples apart.
        series = json.loads(call(
            binary, database,
            "action=series&mac=AABBCCDDEEFF&attribute=temperature"
            "&unit=%C2%B0C&kind=numeric&range=3600")[1])
        assert series["ok"] and series["kind"] == "numeric", series
        assert [point[1] for point in series["points"]] == [20.0, 21.0, 22.0], series["points"]

        # A coarse resolution averages them instead of dropping samples.
        coarse = json.loads(call(
            binary, database,
            "action=series&mac=AABBCCDDEEFF&attribute=temperature"
            "&unit=%C2%B0C&kind=numeric&range=86400")[1])
        assert [point[1] for point in coarse["points"]] == [21.0], coarse["points"]
        assert coarse["points"][0][2] == 3, coarse["points"]

        # An explicit window (used by the browser zoom) wins over `range`.
        zoomed = json.loads(call(
            binary, database,
            f"action=series&mac=AABBCCDDEEFF&attribute=temperature&unit=%C2%B0C"
            f"&kind=numeric&range=86400&from={now - 70 * SECOND}&to={now}")[1])
        assert [point[1] for point in zoomed["points"]] == [21.0, 22.0], zoomed["points"]

        whole = json.loads(call(
            binary, database,
            "action=series&mac=AABBCCDDEEFF&attribute=temperature"
            "&unit=%C2%B0C&kind=numeric&range=0")[1])
        assert whole["from_ns"] <= now - 90 * SECOND, whole

        boolean = json.loads(call(
            binary, database,
            "action=series&mac=AABBCCDDEEFF&attribute=contact&unit="
            "&kind=boolean&range=86400")[1])
        assert boolean["ok"] and boolean["points"][-1][1] == 1.0, boolean

        missing = json.loads(call(
            binary, database,
            "action=series&mac=NOPE&attribute=temperature&kind=numeric")[1])
        assert missing["ok"] and missing["points"] == [], missing

        failure = json.loads(call(
            binary, directory / "missing.db", "action=catalog")[1])
        assert failure["ok"] is False and "does not exist" in failure["error"], failure

        head, body, _ = call(binary, database, "action=nope")
        assert "404" in head and "unknown action" in body, (head, body)

        assert digest(database) == before, "the dashboard modified the database"
        return {
            "devices": len(devices),
            "series": len(found) + len(raw_only),
            "temperature_points": len(series["points"]),
            "boolean_last": boolean["points"][-1][1],
            "text_value": found[("firmware", "")]["value"],
            "read_only": True,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", help="path to the ble2uart-gateway binary")
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.binary), sort_keys=True))


if __name__ == "__main__":
    main()
