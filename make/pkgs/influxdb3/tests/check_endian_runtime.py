#!/usr/bin/env python3
"""Check sparse values, bitmap filtering and duplicate writes on a running server."""

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request


def request(endpoint, path, data, content_type):
    req = urllib.request.Request(
        endpoint.rstrip("/") + path,
        data=data.encode(),
        headers={"Content-Type": content_type},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.read().decode()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"HTTP {error.code}: {error.read().decode()}") from error


def query(endpoint, database, sql):
    return json.loads(request(
        endpoint, "/api/v3/query_sql",
        json.dumps({"db": database, "q": sql, "format": "json"}),
        "application/json",
    ))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8181")
    parser.add_argument("--database", default="endian_regression")
    parser.add_argument("--table", default="probe_" + str(time.time_ns()))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if not args.table.isascii() or not args.table.replace("_", "").isalnum():
        parser.error("table must contain only ASCII letters, digits and underscores")
    table = args.table
    if not args.verify_only:
        timestamp = time.time_ns()
        lines = []
        for index in range(193):
            stamp = timestamp + index
            lines.extend((
                f'{table},attribute=temperature,mac=A value_float={index + 0.25},label="Thermometer",unit="°C" {stamp}',
                f'{table},attribute=battery,mac=B value_uint={4294967296 + index}u,signed={-1099511627776 + index}i,label="Battery" {stamp}',
                f'{table},attribute=opened,mac=C value_bool={"true" if index % 2 else "false"},label="Door" {stamp}',
            ))
        path = "/api/v3/write_lp?" + urllib.parse.urlencode({
            "db": args.database, "precision": "nanosecond",
        })
        request(args.endpoint, path, "\n".join(lines), "text/plain")
        # Replacing the same points must preserve omitted fields and the row count.
        duplicates = [
            f'{table},attribute=temperature,mac=A label="Updated" {timestamp + index}'
            for index in range(1, 193, 3)
        ]
        request(args.endpoint, path, "\n".join(duplicates), "text/plain")

    rows = query(args.endpoint, args.database, f"SELECT * FROM {table} ORDER BY time, attribute")
    assert len(rows) == 579, f"duplicate handling lost or added rows: {len(rows)} != 579"
    groups = {}
    for row in rows:
        assert row.get("time") is not None, row
        groups.setdefault(row["attribute"], []).append(row)
    for attribute in ("temperature", "battery", "opened"):
        subset = groups.get(attribute, [])
        assert len(subset) == 193, (attribute, len(subset))
        filtered = query(args.endpoint, args.database, (
            f"SELECT * FROM {table} WHERE attribute = '{attribute}' ORDER BY time"
        ))
        assert filtered == subset, f"bitmap filtering disagrees for {attribute}"
        for index, row in enumerate(subset):
            if attribute == "temperature":
                assert row.get("value_float") == index + 0.25, row
                assert row.get("label") == ("Updated" if index % 3 == 1 else "Thermometer"), row
                assert row.get("unit") == "°C", row
            elif attribute == "battery":
                assert row.get("value_uint") == 4294967296 + index, row
                assert row.get("signed") == -1099511627776 + index, row
                assert row.get("label") == "Battery", row
            else:
                assert row.get("value_bool") is bool(index % 2), row
                assert row.get("label") == "Door", row
    print(json.dumps({"status": "passed", "database": args.database, "table": table,
                      "rows": len(rows), "verify_only": args.verify_only}))


if __name__ == "__main__":
    main()
