#!/usr/bin/env python3
"""Development-only inverse codec tests; run with python3 -m unittest."""

import contextlib
import io
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import types
import unittest

import construct as cs
import yaml

import atc2spec
import spec2atc


PACKAGE = Path(__file__).resolve().parents[1]
SPEC = PACKAGE / "src/spec/codec.yaml"
PARAMS = {"mac_address": bytes.fromhex("AABBCCDDEEFF"), "bindkey": bytes(range(16))}


def module(spec):
    generated = types.ModuleType("generated_codec")
    exec(spec2atc.generate(spec), generated.__dict__)
    return generated


def single(node, name="packet"):
    return {"version": 1, "structures": {name: node}, "formats": {}}


def plain(obj):
    if isinstance(obj, bytes):
        return obj.hex().upper()
    if isinstance(obj, dict):
        return {str(key): plain(value) for key, value in obj.items()
                if not str(key).startswith("_") and key != "Host Local Date"}
    if isinstance(obj, (list, tuple)):
        return list(map(plain, obj))
    if hasattr(obj, "isoformat"):
        return obj.replace(microsecond=0).isoformat()
    return obj


class Spec2AtcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = yaml.safe_load(SPEC.read_text())
        cls.generated = module(cls.spec)

    def assert_values(self, actual, expected):
        if isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected))
            for key in expected:
                self.assert_values(actual[key], expected[key])
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for left, right in zip(actual, expected):
                self.assert_values(left, right)
        elif type(expected) is float:
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12),
                            (actual, expected))
        else:
            self.assertEqual(actual, expected)

    def test_all_structures_and_metadata(self):
        self.assertEqual(len(self.generated.STRUCTURES), 21)
        self.assertEqual(set(self.generated.STRUCTURES), set(self.spec["structures"]))
        self.assertEqual(self.generated.FORMATS, self.spec["formats"])
        self.assertEqual(self.generated.SPEC_VERSION, 1)

    def test_golden_roundtrips(self):
        vectors = json.loads((PACKAGE / "src/tests/vectors.json").read_text())["roundtrips"]
        self.assertEqual(len(vectors), 400)
        for vector in vectors:
            with self.subTest(format=vector["format"], branch=vector.get("branch")):
                structure = self.generated.STRUCTURES[vector["format"]]
                parsed = structure.parse(bytes.fromhex(vector["encoded"]), **PARAMS)
                self.assert_values(plain(parsed), plain(vector["decoded"]))
                self.assertEqual(structure.build(parsed, **PARAMS).hex().upper(), vector["encoded"])

    def test_golden_parse_and_errors(self):
        vectors = json.loads((PACKAGE / "src/tests/vectors.json").read_text())["vectors"]
        self.assertEqual(len(vectors), 600)
        for index, vector in enumerate(vectors):
            with self.subTest(index=index, format=vector["format"]):
                name = self.generated.FORMATS.get(vector["format"], {}).get("structure", vector["format"])
                structure = self.generated.STRUCTURES[name]
                if "error" in vector:
                    error = {"ValueError": cs.ValidationError, "StreamError": cs.StreamError,
                             "OverflowError": OverflowError}[vector["error"]]
                    with self.assertRaises(error):
                        structure.parse(bytes.fromhex(vector["payload"]), **PARAMS)
                else:
                    parsed = structure.parse(bytes.fromhex(vector["payload"]), **PARAMS)
                    self.assert_values(plain(parsed), plain(vector["decoded"]))

    def test_all_crypto_vectors_and_authentication(self):
        vectors = json.loads((PACKAGE / "src/tests/crypto_vectors.json").read_text())["vectors"]
        self.assertEqual(len(vectors), 40)
        for index, vector in enumerate(vectors):
            with self.subTest(index=index, codec=vector["codec"]):
                blob = bytes.fromhex(vector["blob"])
                if vector["codec"] == "mi_like":
                    blob = bytes.fromhex("95FE5050") + blob
                    header_length = 7
                else:
                    header_length = 3 if vector["codec"] == "bt_home_v2" else 2
                spec = single({"kind": "struct", "fields": [
                    {"kind": "const", "name": "header", "value": blob[:header_length].hex(),
                     "sub": {"kind": "bytes", "length": header_length}},
                    {"kind": "codec", "codec": vector["codec"], "name": "payload",
                     "sub": {"kind": "bytes", "length": len(bytes.fromhex(vector["payload"]))}},
                ]})
                structure = module(spec).packet
                params = {"mac_address": bytes.fromhex(vector["mac"]),
                          "bindkey": bytes.fromhex(vector["bindkey"])}
                parsed = structure.parse(blob, **params)
                self.assertEqual(parsed.payload.hex().upper(), vector["payload"])
                self.assertEqual(structure.build(parsed, **params), blob)
                with self.assertRaisesRegex(cs.ValidationError, "authentication"):
                    structure.parse(blob[:-1] + bytes([blob[-1] ^ 1]), **params)
                with self.assertRaisesRegex(cs.ValidationError, "authentication"):
                    structure.parse(blob, **dict(params, bindkey=b"\xFF" * 16))
                with self.assertRaisesRegex(cs.ValidationError, "requires"):
                    structure.parse(blob)

    def test_user_bthome_advertisement(self):
        # Service data only: exclude AD flags/length/type and the following name.
        raw = bytes.fromhex("D2FC40008A0C0E0B10001101")
        parsed = self.generated.bt_home_v2_format.parse(raw)
        self.assertEqual(parsed.DevInfo.Version, 2)
        self.assertFalse(parsed.DevInfo.Encryption)
        self.assertEqual([plain(item.data) for item in parsed.data_point],
                         [{"packet_id": 138}, {"battery_v": 2.83, "battery_v_unit": "V"},
                          {"switch": False}, {"opened": True}])
        self.assertEqual(self.generated.bt_home_v2_format.build(parsed), raw)

    def test_encrypt_modified_parsed_packet_uses_new_header(self):
        structure = self.generated.bt_home_v2_format
        for trigger in (False, True):
            with self.subTest(trigger=trigger):
                parsed = structure.parse(bytes.fromhex("D2FC40008A"))
                parsed.DevInfo.Encryption = True
                parsed.DevInfo.Trigger = trigger
                parsed.data_point = {"count_id": 123, "payload": parsed.data_point}
                encrypted = structure.build(parsed, **PARAMS)
                decoded = structure.parse(encrypted, **PARAMS)
                self.assertEqual(encrypted[2], 0x45 if trigger else 0x41)
                self.assertEqual(decoded.data_point.count_id, 123)
                self.assertEqual(decoded.data_point.payload[0].data.packet_id, 138)
                self.assertEqual(structure.build(decoded, **PARAMS), encrypted)
    def test_additional_node_compositions(self):
        spec = single({"kind": "struct", "fields": [
            {"kind": "padding", "length": 1},
            {"kind": "fixed", "length": 3, "name": "fixed",
             "sub": {"kind": "array", "count": 3, "sub": {"kind": "int", "fmt": "<B"}}},
            {"kind": "bitstruct", "name": "bits", "fields": [
                {"kind": "bits", "length": 7, "name": "value"},
                {"kind": "boolean", "name": "flag"}]},
            {"kind": "literal", "name": "odd 'name\n", "value": "quoted 'text\n"},
            {"kind": "pass", "name": "pass"},
            {"kind": "string", "name": "name", "length": 5, "encoding": "utf8"},
        ]})
        structure = module(spec).packet
        raw = b"\x00\x01\x02\x03\x81abc\x00\x00"
        parsed = structure.parse(raw)
        self.assertEqual(parsed.bits.value, 64)
        self.assertTrue(parsed.bits.flag)
        self.assertEqual(parsed.name, "abc")
        self.assertEqual(structure.build(parsed), raw)

    def test_string_variants(self):
        for node, raw, expected in [
            ({"kind": "string", "length": 3}, b"abc", b"abc"),
            ({"kind": "string", "prefix": {"kind": "varint"}, "encoding": "utf8"}, b"\x03abc", "abc"),
            ({"kind": "string", "greedy": True}, b"ab\x00", b"ab\x00"),
            ({"kind": "string", "greedy": True, "encoding": "utf8"}, b"abc", "abc"),
        ]:
            with self.subTest(node=node):
                structure = module(single(node)).packet
                self.assertEqual(structure.parse(raw), expected)
                self.assertEqual(structure.build(expected), raw)

    def test_case_keys_keep_exported_string_identity(self):
        for selector_node, selector_bytes, key in [
            ({"kind": "boolean"}, b"\x01", "True"),
            ({"kind": "int", "fmt": "<B"}, b"\x01", "1"),
            ({"kind": "enum", "mapping": {"1": "on"}, "sub": {"kind": "int", "fmt": "<B"}}, b"\x01", "on"),
        ]:
            selector_node = dict(selector_node, name="type")
            structure = module(single({"kind": "struct", "fields": [
                selector_node, {"kind": "switch", "selector": "this['type']", "name": "value",
                                "cases": {key: {"kind": "const", "value": "AA",
                                               "sub": {"kind": "bytes", "length": 1}}}},
            ]})).packet
            self.assertEqual(structure.parse(selector_bytes + b"\xAA").value, b"\xAA")

    def test_export_preserves_affine_decoder_operation_order(self):
        original = cs.ExprAdapter(cs.Byte, (cs.obj_ + 1) * 0.02,
                                  lambda obj, ctx: int(float(obj) / 0.02) - 1)
        with contextlib.redirect_stderr(io.StringIO()):
            exported = atc2spec.Converter().node(original)
        self.assertEqual(exported["decoder"], {
            "op": "multiply", "left": {"op": "add", "left": {"op": "input"},
                                      "right": {"op": "literal", "value": 1}},
            "right": {"op": "literal", "value": 0.02}})
        reconstructed = module(single(exported)).packet
        for raw in range(256):
            data = bytes([raw])
            with self.subTest(raw=raw):
                expected = original.parse(data)
                self.assertEqual(reconstructed.parse(data), expected)
                self.assertEqual(reconstructed.build(reconstructed.parse(data)), original.build(expected))
        legacy = dict(exported)
        del legacy["decoder"]
        self.assertEqual(module(single(legacy)).packet.parse(b"\x01"), 0.04)

    def test_names_cannot_replace_helpers_or_inject_code(self):
        names = ["cs", "class", "_math", "a b", "x\nraise Exception()", "packet",
                 "str", "bytes", "len", "super", "int"]
        spec = {"version": 1, "structures": {name: {"kind": "literal", "value": name} for name in names}}
        generated = module(spec)
        for name in names:
            self.assertEqual(generated.STRUCTURES[name].parse(b""), name)

    def test_reject_unsupported_and_malformed_nodes(self):
        invalid = [
            {"kind": "unmapped", "class": "CustomAdapter"},
            {"kind": "computed", "func": "__import__"},
            {"kind": "computed", "func": []},
            {"kind": "codec", "codec": []},
            {"kind": "computed", "calculation": {"op": []}},
            {"kind": "transform", "func": "affine", "factor": 1, "decoder": {"op": []},
             "encoder": {"op": "input"}, "sub": {"kind": "int", "fmt": "<B"}},
            {"kind": "computed", "calculation": {"op": "input"}},
            {"kind": "transform", "func": "affine", "factor": 1, "sub": {"kind": "int", "fmt": "<B"}},
            {"kind": "transform", "func": "unknown", "sub": {"kind": "pass"}},
            {"kind": "decimal", "factor": 0, "sub": {"kind": "pass"}},
            {"kind": "decimal", "factor": float("nan"), "sub": {"kind": "pass"}},
            {"kind": "bytes", "length": -1},
            {"kind": "array", "count": 65537, "sub": {"kind": "pass"}},
            {"kind": "bits", "length": 65},
            {"kind": "string", "length": 3, "greedy": True},
            {"kind": "string", "length": 3, "pad": "b'\\x00'", "name": "ambiguous"},
            {"kind": "string", "length": 3, "encoding": "not-an-encoding"},
            {"kind": "const", "value": "GG", "sub": {"kind": "bytes", "length": 1}},
            {"kind": "const", "value": "AAAA", "sub": {"kind": "bytes", "length": 1}},
            {"kind": "struct", "fields": [{"kind": "pass", "name": "x"}, {"kind": "pass", "name": "x"}]},
            {"kind": "enum", "mapping": {"1": "x", "01": "y"}, "sub": {"kind": "int", "fmt": "<B"}},
            {"kind": "bytes", "length": 1, "lenght": 2},
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaisesRegex(spec2atc.ConversionError, "spec.structures.packet"):
                spec2atc.generate(single(value))
        for source in ("__import__('os').system('false')", "this['x'].__class__()",
                       "this[open('x')]", "this['x'][slice(None, 9, __import__('os'))]"):
            with self.subTest(source=source), self.assertRaises(spec2atc.ConversionError):
                spec2atc.generate(single({"kind": "switch", "selector": source, "cases": {}}))

    def test_depth_and_observation_rejected(self):
        nested = {"kind": "pass"}
        for _ in range(65):
            nested = {"kind": "greedy", "sub": nested}
        with self.assertRaisesRegex(spec2atc.ConversionError, "maximum depth"):
            spec2atc.generate(single(nested))
        for value in ([], {"mac": "7A6AA429374D", "format": "", "addr_type": 1}):
            with self.assertRaises(spec2atc.ConversionError):
                spec2atc.generate(value)

    def test_cli_json_yaml_standalone_and_atomic_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            output = directory / "generated.py"
            json_input = directory / "codec.json"
            json_input.write_text(json.dumps(self.spec))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(spec2atc.main(["--spec", str(json_input), "--out", str(output)]), 0)
            json_result = output.read_text()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(spec2atc.main(["--spec", str(SPEC), "--out", str(output)]), 0)
            self.assertEqual(output.read_text(), json_result)
            result = subprocess.run([sys.executable, str(output)], cwd=directory,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            json_input.write_text('{"version":1,"structures":{},"version":2}')
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(spec2atc.main(["--spec", str(json_input), "--out", str(output)]), 1)
            self.assertIn("duplicate JSON key", errors.getvalue())
            self.assertEqual(output.read_text(), json_result)
            self.assertEqual(list(directory.glob("*.tmp")), [])
            yaml_input = directory / "duplicate.yaml"
            yaml_input.write_text("version: 1\nversion: 2\nstructures: {}\n")
            with self.assertRaisesRegex(spec2atc.ConversionError, "duplicate YAML key"):
                spec2atc.load_spec(yaml_input)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(spec2atc.main(["--spec", str(json_input), "--out", str(json_input)]), 1)


@unittest.skipUnless(os.environ.get("ATC_CODEC_REFERENCE"), "set ATC_CODEC_REFERENCE for independent source comparison")
class OriginalReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = yaml.safe_load(SPEC.read_text())
        cls.original, _, cls.advanced = atc2spec.load_codec(os.environ["ATC_CODEC_REFERENCE"])
        generated_path = os.environ.get("ATC_GENERATED_MODULE")
        if generated_path:
            definition = importlib.util.spec_from_file_location("verified_generated_codec", generated_path)
            cls.generated = importlib.util.module_from_spec(definition)
            definition.loader.exec_module(cls.generated)
        else:
            cls.generated = module(cls.spec)

    def test_original_export_matches_embedded_specification(self):
        converter = atc2spec.Converter()
        with contextlib.redirect_stderr(io.StringIO()):
            fresh = {
                "version": 1, "generated_by": "tools/atc2spec.py",
                "structures": {name: converter.node(getattr(self.original, name))
                               for name in atc2spec.TOP_LEVEL + atc2spec.CONTROL},
                "formats": atc2spec.build_formats(self.advanced),
            }
        self.assertEqual(atc2spec.sanitize(fresh), self.spec)
        self.assertEqual(self.generated.FORMATS, fresh["formats"])
        self.assertEqual(set(self.generated.STRUCTURES), set(fresh["structures"]))

    def compare_packet(self, name, raw):
        structures = [getattr(self.original, name), self.generated.STRUCTURES[name]]
        outcomes = []
        for structure in structures:
            try:
                outcomes.append((True, structure.parse(raw, **PARAMS)))
            except (cs.ConstructError, ValueError, OverflowError, ZeroDivisionError):
                outcomes.append((False, None))
            except IndexError:
                # The reference indexes the marker of empty encrypted ATC frames.
                self.assertIs(structure, structures[0])
                self.assertIn(name, ("custom_enc_format", "atc1441_enc_format"))
                self.assertEqual(len(raw), 2)
                outcomes.append((False, None))
        self.assertEqual(outcomes[0][0], outcomes[1][0], "parse acceptance differs")
        if not outcomes[0][0]:
            return
        self.assertEqual(plain(outcomes[0][1]), plain(outcomes[1][1]))
        encoded = []
        for structure, (_, parsed) in zip(structures, outcomes):
            try:
                encoded.append((True, structure.build(parsed, **PARAMS)))
            except (cs.ConstructError, ValueError, OverflowError, ZeroDivisionError):
                encoded.append((False, None))
        self.assertEqual(encoded[0], encoded[1], "encoded bytes differ")

    def test_direct_original_comparison(self):
        document = json.loads((PACKAGE / "src/tests/vectors.json").read_text())
        for index, vector in enumerate(document["roundtrips"]):
            with self.subTest(kind="roundtrip", index=index, name=vector["format"]):
                self.compare_packet(vector["format"], bytes.fromhex(vector["encoded"]))
        for index, vector in enumerate(document["vectors"]):
            name = self.generated.FORMATS[vector["format"]]["structure"]
            with self.subTest(kind="golden", index=index, name=name):
                self.compare_packet(name, bytes.fromhex(vector["payload"]))
        rng = random.Random(20261020)
        for name in self.generated.STRUCTURES:
            prefixes = [bytes.fromhex(entry["uuid"])[::-1] for entry in self.generated.FORMATS.values()
                        if entry["structure"] == name and entry.get("uuid")]
            prefix = prefixes[0] if prefixes else b""
            for index in range(200):
                size = rng.choice([0, 1, 2, 3, 4, 6, 8, 12, 16, 20, 24, 31, 64, 128])
                raw = prefix + bytes(rng.randrange(256) for _ in range(size))
                with self.subTest(kind="independent", name=name, index=index, raw=raw.hex()):
                    self.compare_packet(name, raw)

    def test_every_affine_byte_value_against_original(self):
        checked = 0
        for name in ("cfg", "atc1441_enc_format"):
            left = getattr(self.original, name)
            right = self.generated.STRUCTURES[name]
            if name != "cfg":
                left = next(field.subcon.subcon for field in left.subcons if field.name == "codec")
                right = next(field.subcon.subcon for field in right.subcons if field.name == "codec")
            fields = {field.name: field.subcon for field in right.subcons}
            for field in left.subcons:
                if not isinstance(field.subcon, cs.ExprAdapter):
                    continue
                for raw in range(256):
                    with self.subTest(structure=name, field=field.name, raw=raw):
                        expected = field.subcon.parse(bytes([raw]))
                        actual = fields[field.name].parse(bytes([raw]))
                        self.assertEqual(actual, expected)
                        self.assertEqual(fields[field.name].build(actual), field.subcon.build(expected))
                        checked += 1
        self.assertEqual(checked, 7 * 256)

    def test_reference_bthome_v2_encoder_hardcodes_devinfo(self):
        for trigger in (False, True):
            with self.subTest(trigger=trigger):
                parsed = self.original.bt_home_v2_format.parse(bytes.fromhex("D2FC40008A"))
                parsed.DevInfo.Encryption = True
                parsed.DevInfo.Trigger = trigger
                parsed.data_point = {"count_id": 123, "payload": parsed.data_point}
                original = self.original.bt_home_v2_format.build(parsed, **PARAMS)
                generated = self.generated.bt_home_v2_format.build(parsed, **PARAMS)
                if not trigger:
                    self.assertEqual(original, generated)
                    self.original.bt_home_v2_format.parse(original, **PARAMS)
                else:
                    self.assertNotEqual(original, generated)
                    with self.assertRaisesRegex(ValueError, "decrypt"):
                        self.original.bt_home_v2_format.parse(original, **PARAMS)
                decoded = self.generated.bt_home_v2_format.parse(generated, **PARAMS)
                self.assertEqual(decoded.DevInfo.Trigger, trigger)


if __name__ == "__main__":
    unittest.main()
