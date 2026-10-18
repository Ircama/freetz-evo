#!/usr/bin/env python3
"""Private real-capture import and differential decoder regression testing."""

import argparse
import collections
import dataclasses
import datetime
import glob
import hashlib
import io
import importlib
import json
import math
import os
from pathlib import Path
import pickle
import re
import subprocess
import sys
import tempfile
import contextlib

from capture_trace import Capture, RestrictedUnpickler, UUID_BYTES, advertisement, load_captures, normalize_mac, service_format


def encrypted(capture):
    if capture.format in ("custom_enc", "atc1441_enc", "bt_home_enc"):
        return True
    if capture.format == "mi_like" and len(capture.service) >= 4:
        return bool(capture.service[2] & 8)
    if capture.format == "bt_home_v2" and len(capture.service) >= 3:
        return bool(capture.service[2] & 1)
    return False


class Oracle:
    def __init__(self, directory):
        directory = Path(directory).resolve()
        sys.path.insert(0, str(directory.parent))
        self.module = importlib.import_module(directory.name + ".atc_mi_construct")
        self.selector = importlib.import_module(directory.name + ".atc_mi_adv_format")
        for item in self.selector.service_data_dict.values():
            item.setdefault("uuid_str", "0000" + item["uuid"] + "-0000-1000-8000-00805f9b34fb")

    def decode(self, capture, general=False):
        from gen_vectors import plain
        if capture.format == "unsupported":
            return {"status": "unsupported"}
        params = {"mac_address": bytes.fromhex(capture.mac or "000000000000")}
        if capture.bindkey:
            params["bindkey"] = bytes.fromhex(capture.bindkey)
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                structure = self.module.general_format if general else getattr(self.module, capture.format + "_format")
                decoded = plain(structure.parse(capture.service, **params))
            return {"status": "ok", "decoded": decoded}
        except Exception as error:
            return {"status": "rejected", "error_type": type(error).__name__}

    def selected_format(self, capture):
        if not capture.service:
            return "unsupported"
        from types import SimpleNamespace
        uuid = "0000" + capture.service[:2][::-1].hex() + "-0000-1000-8000-00805f9b34fb"
        name, _ = self.selector.atc_mi_advertising_format(SimpleNamespace(service_data={uuid: capture.service[2:]}))
        return name if name in UUID_BYTES else "unsupported"


def resolve_context(captures, oracle):
    pairs = {(capture.mac, capture.bindkey) for capture in captures if capture.mac and capture.bindkey}
    for capture in captures:
        if capture.mac and (capture.bindkey or not encrypted(capture)):
            continue
        if capture.mac:
            keys = {key for mac, key in pairs if mac == capture.mac}
            if len(keys) == 1:
                capture.bindkey = next(iter(keys))
                capture.context = "shared_unique_key"
                continue
        if not encrypted(capture):
            parsed = oracle.decode(capture)
            embedded = parsed.get("decoded", {}).get("MAC")
            if isinstance(embedded, str):
                capture.mac = normalize_mac(embedded)
                capture.context = "embedded_mac"
            elif not capture.mac:
                capture.mac = "000000000000"
                capture.context = "unrecorded_unused_identity"
            continue
        matches = []
        original_mac, original_key = capture.mac, capture.bindkey
        for mac, key in sorted(pairs):
            if original_mac and mac != original_mac:
                continue
            capture.mac, capture.bindkey = mac, key
            if oracle.decode(capture)["status"] == "ok":
                matches.append((mac, key))
        if len(matches) == 1:
            capture.mac, capture.bindkey = matches[0]
            capture.context = "authenticated_context_recovery"
        else:
            capture.mac, capture.bindkey = original_mac or "000000000000", original_key
            capture.context = "ambiguous_context" if matches else "unresolved_encrypted_context"


def differences(expected, actual, path="", output=None):
    if output is None:
        output = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            current = path + "." + key
            if key == "Host Local Date":
                continue
            if key not in expected or key not in actual:
                output.append(current + ":missing_field")
            else:
                differences(expected[key], actual[key], current, output)
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            output.append(path + ":list_length")
        for index, (left, right) in enumerate(zip(expected, actual)):
            differences(left, right, f"{path}[{index}]", output)
    elif isinstance(expected, bool) or isinstance(actual, bool):
        if type(expected) is not type(actual) or expected != actual:
            output.append(path + ":boolean")
    elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if not math.isclose(expected, actual, rel_tol=1e-10, abs_tol=1e-10):
            output.append(path + ":numeric")
    elif expected != actual:
        output.append(path + ":value")
    return output


def private_json(path, value):
    with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as handle:
        json.dump(value, handle, ensure_ascii=True)
        handle.write("\n")


def mutations(capture, reference):
    if reference["status"] != "ok":
        return []
    result = []
    source = capture.format
    if encrypted(capture) and capture.bindkey:
        result.append(dataclasses.replace(capture, bindkey="", variant="missing_key", source_format=source))
        wrong = bytes([int(capture.bindkey[:2], 16) ^ 1]) + bytes.fromhex(capture.bindkey[2:])
        result.append(dataclasses.replace(capture, bindkey=wrong.hex(), variant="wrong_key", source_format=source))
        changed = capture.service[:-1] + bytes([capture.service[-1] ^ 1])
        result.append(dataclasses.replace(capture, service=changed, ad=bytes([len(changed) + 1, 0x16]) + changed,
                                          variant="tampered_mic", source_format=source))
    shortened = capture.service[:-1]
    result.append(dataclasses.replace(capture, service=shortened, ad=bytes([len(shortened) + 1, 0x16]) + shortened,
                                      variant="truncated_payload", source_format=source))
    raw, service, framing = advertisement(capture.ad[:-1])
    result.append(dataclasses.replace(capture, ad=raw, service=service, framing=framing,
                                      format=service_format(service) or "unsupported",
                                      variant="truncated_ad", source_format=source))
    return result


def verify(captures, oracle, binary, directory):
    config = directory / "config.yaml"
    created = subprocess.run([str(binary), "--write-default-config", str(config)], capture_output=True)
    if created.returncode:
        raise RuntimeError("cannot create isolated test configuration")
    requests = directory / "requests.jsonl"
    expected = []
    with open(os.open(requests, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as handle:
        for capture in captures:
            reference = oracle.decode(capture)
            for case in [capture] + mutations(capture, reference):
                result = reference if case is capture else oracle.decode(case)
                selected = oracle.selected_format(case)
                general = oracle.decode(case, general=True) if case.variant == "original" else {}
                general_names = [key.removesuffix("_format") for key, value in general.get("decoded", {}).items() if key.endswith("_format") and value]
                expected.append({"case": case.identifier, "format": case.format, "source_format":case.source_format or case.format,
                                 "variant":case.variant, "encrypted": encrypted(case), "context": case.context,
                                 "reference": result, "selector": selected, "general_formats": general_names,
                                 "firmware_transportable":len(case.ad) <= 229})
                handle.write(json.dumps(case.request()) + "\n")
    private_json(directory / "expected.json", expected)
    results = directory / "host-results.jsonl"
    with open(requests) as source, open(os.open(results, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as target:
        completed = subprocess.run([str(binary), "--config", str(config), "--decode-captures"], stdin=source, stdout=target, stderr=subprocess.PIPE)
    if completed.returncode:
        raise RuntimeError("native offline batch decoder failed; input and output retained privately")
    return compare_results(expected, results)


def compare_results(expected, results):
    coverage, negatives, archives, issues = {}, {}, {}, []
    with open(results) as handle:
        rows = [json.loads(line) for line in handle]
    if len(rows) != len(expected):
        issues.append({"case": "batch", "differences": ["result_count"]})
    for entry, row in zip(expected, rows):
        variant = entry.get("variant", "original")
        bucket = entry["format"] + (":encrypted" if entry["encrypted"] else ":plain")
        stats = coverage.setdefault(bucket, collections.Counter()) if variant == "original" else negatives.setdefault(variant, collections.Counter())
        stats["records"] += 1
        reference, native = entry["reference"], row["result"]
        archive = archives.setdefault(entry["case"].split("#")[0], collections.Counter()) if variant == "original" else None
        if archive is not None:
            archive["records"] += 1
            archive["reference_decoded" if reference["status"] == "ok" else "reference_rejected"] += 1
        fields = []
        if row.get("case") != entry["case"]:
            fields.append("case_order")
        if reference["status"] == "ok":
            stats["reference_decoded"] += 1
            if native.get("decode_status") != "ok":
                fields.append("native_rejected_reference_success")
            else:
                fields.extend(differences(reference["decoded"], native["decoded"]))
                if native.get("wire_format") != entry["selector"]:
                    fields.append("format_selection")
            if variant == "original" and entry["general_formats"] != [entry["format"]]:
                fields.append("python_general_format_disagreement")
        elif native.get("decode_status") == "ok":
            fields.append("native_accepted_reference_rejection")
        else:
            stats["both_rejected"] += 1
        if variant in ("missing_key", "wrong_key", "tampered_mic") and reference["status"] == "ok":
            fields.append("reference_accepted_authentication_mutation")
        if fields:
            stats["mismatches"] += 1
            if archive is not None:
                archive["mismatches"] += 1
            issues.append({"case": entry["case"], "differences": fields[:50]})
        else:
            stats["matched"] += 1
    return {"records":sum(entry.get("variant", "original") == "original" for entry in expected),
            "cases":len(expected), "results":len(rows), "coverage":coverage, "negative_coverage":negatives, "per_archive":archives, "mismatches":issues,
            "oversized_original_samples":sum(entry.get("variant", "original") == "original" and not entry.get("firmware_transportable",True) for entry in expected),
            "excluded_volatile_fields":["Host Local Date"], "numeric_tolerance":{"relative":1e-10,"absolute":1e-10}}


def self_test():
    minimal = bytes.fromhex("0516D2FC4000")
    ad, service, framing = advertisement(minimal)
    assert ad == minimal and service == minimal[2:] and framing == "advertisement"
    assert advertisement(minimal[:-1])[2] == "truncated_advertisement"
    assert differences({"value":None},{"value":[]})
    assert differences({"value":True},{"value":1})
    assert not differences({"value":0.1 + 0.2},{"value":0.3})
    try:
        RestrictedUnpickler(io.BytesIO(pickle.dumps(Path("blocked")))).load()
    except pickle.UnpicklingError:
        pass
    else:
        raise AssertionError("non-data pickle object was not rejected")
    print("capture harness self-test passed")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="*", help="pickle files or glob patterns")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--codec", type=Path)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare-results", type=Path)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    paths = sorted({Path(path) for pattern in args.archives for path in glob.glob(pattern)})
    if not paths:
        parser.error("no archives matched")
    reports, all_captures = [], []
    for path in paths:
        try:
            captures, errors = load_captures(path)
            all_captures.extend(captures)
            reports.append({"archive": path.name, "frames": len(captures),
                            "formats": dict(collections.Counter(capture.format for capture in captures)),
                            "framing": dict(collections.Counter(capture.framing for capture in captures)),
                            "with_key": sum(bool(capture.bindkey) for capture in captures),
                            "conversion_errors": errors})
        except Exception:
            reports.append({"archive": path.name, "archive_error": "unsupported or invalid restricted archive"})
    if args.inventory:
        print(json.dumps({"archives": reports}, indent=2))
        return int(any(report.get("archive_error") for report in reports))
    if not args.codec or not args.output:
        parser.error("verification requires --codec and --output")
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    if args.output.resolve().is_relative_to(Path(__file__).resolve().parents[4]):
        parser.error("private capture output must be outside the package repository")
    if args.compare_results:
        expected = json.loads((args.output / "expected.json").read_text())
        result = compare_results(expected, args.compare_results)
    else:
        if not args.binary:
            parser.error("verification requires --binary")
        oracle = Oracle(args.codec)
        resolve_context(all_captures, oracle)
        result = verify(all_captures, oracle, args.binary, args.output)
        result["archives"] = reports
        result["contexts"] = dict(collections.Counter(capture.context for capture in all_captures))
        result["framing"] = dict(collections.Counter(capture.framing for capture in all_captures))
        result["provenance"] = {"host_binary_sha256":hashlib.sha256(args.binary.read_bytes()).hexdigest(),
                    "archives":{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
                    "reference_sources":{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in args.codec.glob("atc_mi_*.py")}}
    report = args.output / ("target-report.json" if args.compare_results else "host-report.json")
    original_requests, decoded_requests = set(), set()
    expected = json.loads((args.output / "expected.json").read_text())
    with open(args.output / "requests.jsonl") as handle:
        for entry, line in zip(expected, handle):
            if entry["variant"] != "original":
                continue
            request = json.loads(line)
            request.pop("case", None)
            fingerprint = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).digest()
            original_requests.add(fingerprint)
            if entry["reference"]["status"] == "ok":
                decoded_requests.add(fingerprint)
    result["unique_original_requests"] = len(original_requests)
    result["unique_decodable_requests"] = len(decoded_requests)
    private_json(report, result)
    print(json.dumps(result, indent=2))
    return int(bool(result["mismatches"]) or any(report.get("archive_error") or report.get("conversion_errors") for report in reports))


if __name__ == "__main__":
    sys.exit(main())