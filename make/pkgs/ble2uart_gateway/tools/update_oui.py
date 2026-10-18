#!/usr/bin/env python3
"""Refresh the offline IEEE MA-L vendor table used by discovery."""

import csv
import io
from pathlib import Path
import urllib.request

SOURCE = "https://standards-oui.ieee.org/oui/oui.csv"


def main():
    request = urllib.request.Request(SOURCE, headers={"User-Agent": "ble2uart-gateway/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        rows = csv.DictReader(io.StringIO(response.read().decode("utf-8-sig")))
        vendors = {
            row["Assignment"].upper(): " ".join(row["Organization Name"].split())
            for row in rows
            if row["Registry"] == "MA-L" and len(row["Assignment"]) == 6
        }
    assert len(vendors) > 30000, "incomplete IEEE registry"
    assert "Telink" in vendors["A4C138"], "unexpected vendor assignment"
    target = Path(__file__).resolve().parents[1] / "src/spec/oui.tsv"
    target.write_text("".join(f"{prefix}\t{name}\n" for prefix, name in sorted(vendors.items())), encoding="utf-8")
    print(f"{len(vendors)} OUI assignments -> {target}")


if __name__ == "__main__":
    main()