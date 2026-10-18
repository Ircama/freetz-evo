#!/usr/bin/env python3
"""Differential test vectors for the Rust codec (development-time only).

The Python codec shipped with atc_mi_interface is the reference implementation:
every vector here is a raw advertisement payload *plus* the exact structure the
reference decodes it into. The Rust interpreter must produce the same structure,
or fail where the reference fails. This is what makes "100% of the devices in
atc_mi_interface" a verifiable claim instead of an aspiration.

Payloads are synthetic (the firmware is not needed): the only constraint is the
leading const bytes (the service UUID), which are taken from the spec itself.

Usage:
    python3 tools/gen_vectors.py --codec <dir of atc_mi_interface> --out src/tests/vectors.json
"""

import argparse
import json
import os
import random
import struct
import sys
from atc2spec import CONTROL


# The reference decodes the service data *including* the UUID, so the payload
# starts with the UUID in wire order (little-endian, as in the advertisement).
UUID_BYTES = {
    "custom": "1a18",
    "custom_enc": "1a18",
    "atc1441": "1a18",
    "atc1441_enc": "1a18",
    "mi_like": "95fe",
    "bt_home": "1c18",
    "bt_home_enc": "1e18",
    "bt_home_v2": "d2fc",
}

# Structures that only describe a *bound* device (bindkey required): a random
# payload cannot decrypt, and the vector records that failure on purpose.
ENCRYPTED = {"custom_enc", "atc1441_enc", "bt_home_enc"}


def plain(value):
    """Convert whatever the codec returns into JSON-safe data.

    Bytes become upper-case hex, dates become ISO strings: the two sides must
    agree on the *textual* form, which is also what the front-ends publish.
    """
    if isinstance(value, (bytes, bytearray)):
        return value.hex().upper()
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items() if not str(k).startswith("_")}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float, str)):
        return value
    if hasattr(value, "isoformat"):
        return value.replace(microsecond=0).isoformat()
    return str(value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--codec", required=True, help="directory of the atc_mi_interface package")
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=20261016)
    args = parser.parse_args()

    directory = os.path.abspath(args.codec)
    parent, package = os.path.dirname(directory), os.path.basename(directory)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    codec = __import__("%s.atc_mi_construct" % package, fromlist=["*"])

    rng = random.Random(args.seed)
    vectors = []
    for name, uuid in sorted(UUID_BYTES.items()):
        structure = getattr(codec, "%s_format" % name, None)
        if structure is None:
            print("missing structure: %s_format" % name, file=sys.stderr)
            continue
        # Lengths 8..32 cover every format in the reference detector.
        for length in range(8, 33):
            for attempt in range(3):
                payload = bytes.fromhex(uuid) + bytes(rng.randrange(256) for _ in range(length - 2))
                entry = {"format": name, "payload": payload.hex().upper()}
                try:
                    entry["decoded"] = plain(dict(structure.parse(payload)))
                except Exception as error:
                    entry["error"] = type(error).__name__
                vectors.append(entry)
        print("%-14s structures=%d" % (name, sum(1 for v in vectors if v["format"] == name)),
              file=sys.stderr)

    ok = sum(1 for v in vectors if "decoded" in v)
    roundtrips = []
    for name in CONTROL + [name + "_format" for name in UUID_BYTES if name not in ENCRYPTED]:
        structure = getattr(codec, name)
        count = 0
        for attempt in range(1000):
            prefix = bytes.fromhex(UUID_BYTES.get(name.removesuffix("_format"), ""))
            raw = prefix + (bytes(128) if attempt == 0 else bytes(rng.randrange(128) for _ in range(128)))
            try:
                parsed = structure.parse(raw)
                encoded = structure.build(parsed)
                decoded = structure.parse(encoded)
            except Exception:
                continue
            roundtrips.append({"format": name, "encoded": encoded.hex().upper(), "decoded": plain(decoded)})
            count += 1
            if count == 8:
                break
        if count == 0:
            raise RuntimeError("no valid encoder vectors for " + name)
        print("%-25s encoder vectors=%d" % (name, count), file=sys.stderr)
    mac = bytes.fromhex("AABBCCDDEEFF")
    bindkey = bytes(range(16))
    branches = []
    unbuildable = []
    for item_name, format_name, header in (
        ("mi_like_data", "mi_like_format", "95fe50505b0501ffeeddccbbaa"),
        ("bt_home_data", "bt_home_format", "1c18"),
        ("bt_home_v2_data", "bt_home_v2_format", "d2fc40"),
    ):
        item = getattr(codec, item_name)
        selector, switch = item.subcons[0].subcon, item.subcons[1].subcon
        enums = selector.subcons if selector.__class__.__name__ == "Select" else [selector]
        for name, case in switch.cases.items():
            discriminator = next(enum.build(name) for enum in enums if name in enum.encmapping)
            constant = b""
            if hasattr(case, "subcons") and case.subcons:
                first = case.subcons[0].subcon
                if first.__class__.__name__ == "Const" and isinstance(first.value, bytes):
                    constant = first.value
            for fill in (1, 2, 0, 64):
                try:
                    value = item.parse(discriminator + constant + bytes([fill]) * 256)
                    encoded_item = item.build(value)
                    structure = getattr(codec, format_name)
                    decoded = structure.parse(bytes.fromhex(header) + encoded_item)
                    encoded = structure.build(decoded)
                    decoded = structure.parse(encoded)
                    objects = decoded.get("bt_home_data", decoded.get("data_point", []))
                    if len(objects) != 1:
                        raise ValueError("object branch was not consumed by the reference")
                    roundtrips.append(dict(format=format_name, branch=str(name), encoded=encoded.hex().upper(), decoded=plain(decoded)))
                    branches.append(item_name + "." + str(name))
                    break
                except Exception as error:
                    failure = "%s: %s" % (type(error).__name__, error)
                    continue
            else:
                unbuildable.append(dict(branch=item_name + "." + str(name), error=failure))
                print("unbuildable: %s.%s: %s" % (item_name, name, failure), file=sys.stderr)
        print("%-25s branches=%d" % (item_name, len(switch.cases)), file=sys.stderr)
    for index in range(8):
        temperature, humidity, battery = -20 + index * 5, 45 + index, 80 + index
        flags = dict(humidity_trigger=False, temp_trigger=False, out_gpio_trg_flag=False,
                     out_gpio_trg_value=False, input_gpio_value=True)
        legacy = [codec.bt_home_data.parse(raw) for raw in (
            b"\x23\x02" + struct.pack("<h", temperature * 100),
            b"\x03\x03" + struct.pack("<H", humidity * 100), bytes([2, 1, battery]))]
        modern = [codec.bt_home_v2_data.parse(raw) for raw in (
            b"\x02" + struct.pack("<h", temperature * 100),
            b"\x03" + struct.pack("<H", humidity * 100), bytes([1, battery]))]
        mi = codec.mi_like_format.parse(bytes.fromhex("95fe50505b0501ffeeddccbbaa0d1004")
                                        + struct.pack("<hH", temperature * 10, humidity * 10))
        mi.ctrl.isEncrypted = True
        mi.data_point = dict(count_id=index, payload=mi.data_point)
        v2 = codec.bt_home_v2_format.parse(bytes.fromhex("d2fc40"))
        v2.DevInfo.Encryption = True
        v2.data_point = dict(count_id=index, payload=modern)
        inputs = {
            "custom_enc_format": dict(codec=dict(temperature=temperature, humidity=humidity, battery_level=battery, flags=flags)),
            "atc1441_enc_format": dict(codec=dict(temperature=temperature, humidity=humidity, batt_trg=dict(out_gpio_trg_flag=False, battery_level=battery))),
            "bt_home_enc_format": dict(codec=dict(count_id=index, payload=legacy)),
            "mi_like_format": mi,
            "bt_home_v2_format": v2,
        }
        for name, value in inputs.items():
            structure = getattr(codec, name)
            encoded = structure.build(value, mac_address=mac, bindkey=bindkey)
            decoded = structure.parse(encoded, mac_address=mac, bindkey=bindkey)
            roundtrips.append(dict(format=name, encoded=encoded.hex().upper(), decoded=plain(decoded), encrypted=True))
    document = {
        "generated_by": "tools/gen_vectors.py",
        "seed": args.seed,
        "count": len(vectors),
        "decoded": ok,
        "failed": len(vectors) - ok,
        "vectors": vectors,
        "roundtrips": roundtrips,
        "branches": branches,
        "unbuildable_branches": unbuildable,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as handle:
        json.dump(document, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print("vectors=%d decoded=%d failed=%d -> %s" % (len(vectors), ok, len(vectors) - ok, args.out))


if __name__ == "__main__":
    main()
