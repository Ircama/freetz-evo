#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
# Copyright (c) 2026 Ircama
#
# atc2spec.py -- development-time converter.
#
# Turns the Python codec of the ATC_Mi interface (construct based: see
# atc_mi_construct.py, atc_mi_construct_adapters.py and atc_mi_adv_format.py of
# the freetz-ble-portal project) into the data specification the Rust daemon
# interprets (src/spec/codec.yaml).
#
# Python is NOT part of the daemon: this script runs once, by hand, whenever the
# Python codec changes. It imports the codec modules, walks the construct object
# tree and emits a small node vocabulary (struct, bitstruct, int, decimal,
# string, switch, enum, const, if, select, codec, ...).
#
# Construct predicates that carry real logic cannot be expressed as data: they
# are reported in the "named predicates" list and the Rust interpreter
# implements them by name (src/src/codec/predicates.rs). Nothing is ever
# silently dropped.
#
# Usage:
#   python3 tools/atc2spec.py --codec <dir>/atc_mi_interface --out src/spec/codec.yaml
#   python3 tools/atc2spec.py --codec <dir>/atc_mi_interface --list
#
# The specification is written atomically (temporary file + rename), so an
# interrupted run can never leave a truncated codec.yaml behind.

import argparse
import ast
import collections
import functools
import importlib
import inspect
import json
import math
import os
import sys

import construct as cs


class Unmapped(Exception):
    """A construct object with no counterpart in the Rust interpreter."""


@functools.lru_cache(maxsize=8)
def source_lambdas(filename):
    with open(filename, encoding="utf8") as handle:
        tree = ast.parse(handle.read())
    return {node.lineno: node.body for node in ast.walk(tree) if isinstance(node, ast.Lambda)}


def arithmetic(node):
    if isinstance(node, ast.Subscript):
        path = []
        while isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            path.insert(0, node.slice.value)
            node = node.value
        if isinstance(node, ast.Name) and node.id == "this":
            return {"op": "field", "path": path}
    if isinstance(node, ast.Name) and node.id in ("obj", "obj_"):
        return {"op": "input"}
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return {"op": "literal", "value": node.value}
    if isinstance(node, ast.BinOp):
        operation = {ast.Add: "add", ast.Sub: "subtract", ast.Mult: "multiply", ast.Div: "divide"}.get(type(node.op))
        if operation:
            return {"op": operation, "left": arithmetic(node.left), "right": arithmetic(node.right)}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return {"op": "subtract", "left": {"op": "literal", "value": 0}, "right": arithmetic(node.operand)}
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("int", "float") and len(node.args) == 1:
        return {"op": node.func.id, "argument": arithmetic(node.args[0])}
    raise Unmapped("unsupported arithmetic expression: " + ast.dump(node))


def adapter_arithmetic(func):
    if isinstance(func, (cs.BinExpr, cs.UniExpr, cs.Path)):
        return arithmetic(ast.parse(str(func), mode="eval").body)
    filename = inspect.getsourcefile(func)
    code = getattr(func, "__code__", None)
    if filename and code:
        body = source_lambdas(filename).get(code.co_firstlineno)
        if body is not None:
            return arithmetic(body)
    raise Unmapped("adapter arithmetic needs a Construct expression or source lambda")


def describe(obj):
    """Cheap description: repr() and sizeof() of a construct object both walk the
    whole subtree (megabytes for the big structures), so only the class name is
    used here."""
    return type(obj).__name__


def sizeof(obj):
    try:
        return obj.sizeof()
    except Exception:
        return None


def func_name(func):
    """Cheap, stable identification of a transform or of a predicate.

    inspect.getsource() is unusable here: hundreds of lambdas in a 68 KB module
    take minutes. The name is what the interpreter needs; the rare anonymous
    lambda is reported so it can be mapped by hand once.

    `getattr` is never applied blindly to a cs.Path: see path_of().
    """
    name = getattr(func, "__name__", None)
    if not isinstance(name, str) or not name:
        return type(func).__name__
    if name == "<lambda>":
        return type(func).__name__ + ".<lambda>"
    return name


def path_of(selector):
    """Field path of a construct selector/predicate.

    In construct a selector is frequently a `cs.Path` instance (`this.x.y`)
    rather than a function, and a Path must be recognised *first*:
    `Path.__getattr__` invents a new Path for **any** attribute name and
    `Path.__getitem__` invents a new Path for **any** index.  Reading
    `path.__closure__` therefore yields a Path, and iterating it never ends
    (`__getitem__` never raises IndexError), which turns the walk into an
    endless loop.  Only real functions are inspected through their closure.
    """
    if callable(selector) and not isinstance(selector, cs.Path):
        code = getattr(selector, "__code__", None)
        if code and "timestamp" in code.co_names:
            return "positive_timestamp:" + next(name for name in code.co_names if name != "timestamp")
        if code and "type_length" in code.co_names and 6 in code.co_consts:
            return "equals:type_length:6"
    path = None
    if isinstance(selector, cs.Path):
        path = str(selector)
    else:
        for cell in (getattr(selector, "__closure__", None) or ()):
            try:
                value = cell.cell_contents
            except ValueError:
                continue
            if isinstance(value, cs.Path):
                path = str(value)
                break
        if path is None:
            for default in (getattr(selector, "__defaults__", None) or ()):
                if isinstance(default, cs.Path):
                    path = str(default)
                    break
    if path and "__closure__" not in path and "slice" not in path:
        return path
    raise Unmapped("named predicate needed: %s" % (path or func_name(selector)))


def field_names(subcons):
    """(name, subcon) pairs of a Struct/BitStruct; unnamed entries keep no name."""
    out = []
    for entry in subcons:
        if isinstance(entry, cs.Renamed):
            out.append((entry.name, entry.subcon))
        else:
            out.append((None, entry))
    return out


# The decrypting codecs (construct Tunnel subclasses): they need the bind key, so
# they are implemented natively in Rust with AES-128-CCM.
CODE_CODECS = {
    "BtHomeCodec": "bt_home",
    "BtHomeV2Codec": "bt_home_v2",
    "AtcMiCodec": "atc_mi",
    "MiLikeCodec": "mi_like",
}

# construct builds Padded -> StringEncoded -> NullStripped around a
# FixedSized(Bytes): one "string" node is enough.
STRING_CLASSES = {"Padded", "StringEncoded", "NullStripped"}

# Format detection: name -> (structure, codec). uuid and the expected
# service-data length come from service_data_dict in atc_mi_adv_format.py;
# atc1441 (the legacy unencrypted format) is not advertised by the detector but
# the structure is kept, because the specification describes every format.
FORMAT_MAP = [
    ("custom", "custom_format", None),
    ("custom_enc", "custom_enc_format", "atc_mi"),
    ("atc1441", "atc1441_format", None),
    ("atc1441_enc", "atc1441_enc_format", "atc_mi"),
    ("mi_like", "mi_like_format", "mi_like"),
    ("bt_home", "bt_home_format", "bt_home"),
    ("bt_home_enc", "bt_home_enc_format", "bt_home"),
    ("bt_home_v2", "bt_home_v2_format", "bt_home_v2"),
]

# Entry points of a format.
TOP_LEVEL = [
    "custom_format",
    "custom_enc_format",
    "atc1441_format",
    "atc1441_enc_format",
    "mi_like_format",
    "bt_home_format",
    "bt_home_enc_format",
    "bt_home_v2_format",
    "general_format",
]

# Control structures of the ATC firmware: read and written through the GATT
# central role of the ESP32 firmware (advertising *and* control).
CONTROL = [
    "cfg",
    "trigger",
    "comfort_values",
    "native_temp_hum_v_values",
    "native_comfort_values",
    "device_name",
    "device_type",
    "i2c_devices",
    "mac_address",
    "token_bind_mi_keys",
    "current_last_date",
    "time_tick_step",
]


class Converter(object):
    """Walk the construct tree and emit spec nodes.

    Dispatch is by *class name*: in construct 2.10 most builders (Struct, Array,
    Const, Padding, Flag, Enum, Switch, IfThenElse, Select, Bytes, GreedyRange,
    Timestamp, PaddedString, ...) are functions returning instances of a small
    set of classes, so isinstance() against those names does not work.
    """

    def __init__(self):
        self.memo = {}
        self.in_progress = set()
        self.cycles = 0
        self.hits = 0
        self.count = 0
        self.unmapped = collections.Counter()
        self.transforms = collections.Counter()
        self.computed = collections.Counter()
        self.named = collections.Counter()

    def note_unmapped(self, obj):
        text = type(obj).__name__
        self.unmapped[text] += 1
        return {"kind": "unmapped", "class": text, "note": describe(obj), "length": sizeof(obj)}

    def note_named(self, reason):
        self.named[reason] += 1
        return reason

    def node(self, obj):
        """Memoised conversion. construct structures are a DAG: the same
        substructure (a shared BitStruct, a repeated TLV case, ...) appears in
        many places, and walking it again for each occurrence is exponential.
        """
        key = id(obj)
        cached = self.memo.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        if key in self.in_progress:
            self.cycles += 1
            return {"kind": "recursive", "class": type(obj).__name__}
        self.in_progress.add(key)
        try:
            node = self._node(obj)
        finally:
            self.in_progress.discard(key)
        self.memo[key] = node
        return node

    def fields(self, subcons):
        out = []
        for name, sub in field_names(subcons):
            node = self.node(sub)
            if name == "Host Local Date":
                node = {"kind": "computed", "func": "host_local_date"}
            if name:
                node = dict(node)
                node["name"] = name
            out.append(node)
        return out

    def _node(self, obj):
        self.count += 1
        if self.count <= 260:
            print("node %d: %s id=%d" % (self.count, type(obj).__name__, id(obj)),
                  file=sys.stderr, flush=True)
        if self.count > 200000:
            raise Unmapped("too many nodes: the construct tree has a cycle")

        if isinstance(obj, cs.Renamed):
            node = self.node(obj.subcon)
            node = dict(node)
            node["name"] = obj.name
            return node

        cls = type(obj).__name__

        if cls == "Struct":
            return {"kind": "struct", "fields": self.fields(obj.subcons)}
        if cls == "Bitwise":
            # BitStruct(...) is Bitwise(bytes2bits(Struct(...))) or
            # Bitwise(swapbytes(bytes2bits(...))): the plumbing transforms are
            # not data, they only mark the container as bit oriented.
            sub = obj.subcon
            for _ in range(3):
                if type(sub).__name__ in ("Transformed", "ExprAdapter") and \
                        func_name(getattr(sub, "decodefunc", None) or sub) in ("bytes2bits", "swapbytes"):
                    sub = sub.subcon
                    continue
                break
            inner = self.node(sub)
            if inner.get("kind") == "struct":
                inner["kind"] = "bitstruct"
                return inner
            return {"kind": "bitstruct", "fields": [inner]}
        if cls == "FormatField":
            return {"kind": "int", "fmt": obj.fmtstr}
        if cls == "Flag":
            return {"kind": "boolean"}
        if cls == "BitsInteger":
            return {"kind": "bits", "length": obj.length, "signed": bool(obj.signed), "swapped": bool(obj.swapped)}
        if cls == "BytesInteger":
            return {"kind": "bytesint", "length": obj.length, "signed": bool(obj.signed), "swapped": bool(obj.swapped)}
        if cls == "Const":
            return {"kind": "const", "value": self.const_value(obj.value), "sub": self.node(obj.subcon)}
        if cls == "Enum":
            return {
                "kind": "enum",
                "mapping": {str(k): str(v) for k, v in obj.ksymapping.items()},
                "sub": self.node(obj.subcon),
            }
        if cls == "Switch":
            try:
                selector = path_of(obj.keyfunc)
            except Unmapped as error:
                selector = self.note_named(str(error))
            cases = {str(key): self.node(sub) for key, sub in obj.cases.items()}
            node = {"kind": "switch", "selector": selector, "cases": cases}
            if obj.default is not None:
                node["default"] = self.node(obj.default)
            return node
        if cls == "IfThenElse":
            try:
                predicate = path_of(obj.condfunc)
            except Unmapped as error:
                predicate = self.note_named(str(error))
            node = {"kind": "if", "predicate": predicate, "then": self.node(obj.thensubcon)}
            if obj.elsesubcon is not None:
                node["else"] = self.node(obj.elsesubcon)
            return node
        if cls == "Select":
            return {"kind": "select", "alternatives": [self.node(sub) for sub in obj.subcons]}
        if cls == "Array":
            return {"kind": "array", "count": obj.count, "sub": self.node(obj.subcon)}
        if cls == "GreedyRange":
            return {"kind": "greedy", "sub": self.node(obj.subcon)}
        if cls == "Bytes":
            return {"kind": "bytes", "length": obj.length}
        if cls == "VarInt":
            return {"kind": "varint"}
        if cls == "FixedSized":
            return {"kind": "fixed", "length": obj.length, "sub": self.node(obj.subcon)}
        if cls == "Padding":
            return {"kind": "padding", "length": obj.length}
        if cls == "Pass":
            return {"kind": "pass"}
        if cls in STRING_CLASSES:
            if cls == "StringEncoded" and type(obj.subcon).__name__ == "Prefixed":
                return {"kind": "string", "encoding": obj.encoding,
                        "prefix": self.node(obj.subcon.lengthfield)}
            if cls == "StringEncoded" and type(obj.subcon).__name__ == "GreedyBytes":
                return {"kind": "string", "encoding": obj.encoding, "greedy": True}
            node = {"kind": "string"}
            self.walk_string_chain(obj, node)
            return node
        if cls == "DecimalNumber":
            return {"kind": "decimal", "factor": obj.decimal, "sub": self.node(obj.subcon)}
        if cls == "ByteAdapter":
            sample = obj._decode(list(range(6)), None, None)
            return {"kind": "mac", "swapped": sample.startswith("05")}
        if cls == "EpochTimestampAdapter":
            return {"kind": "timestamp", "sub": self.node(obj.subcon)}
        if cls in CODE_CODECS:
            return {"kind": "codec", "codec": CODE_CODECS[cls], "sub": self.node(obj.subcon)}
        if cls in ("Transformed", "ExprAdapter"):
            if cls == "ExprAdapter":
                zero = obj._decode(0, {}, "")
                one = obj._decode(1, {}, "")
                two = obj._decode(2, {}, "")
                if isinstance(zero, (int, float)) and math.isclose(two - one, one - zero, rel_tol=1e-10, abs_tol=1e-12):
                    decoder = inspect.getclosurevars(obj._decode).nonlocals["decoder"]
                    encoder = inspect.getclosurevars(obj._encode).nonlocals["encoder"]
                    return {"kind": "transform", "func": "affine", "factor": one - zero,
                        "offset": zero, "decoder": adapter_arithmetic(decoder),
                        "encoder": adapter_arithmetic(encoder), "sub": self.node(obj.subcon)}
            func = getattr(obj, "decodefunc", None) or getattr(obj, "encodefunc", None) or obj
            name = func_name(func)
            if name.endswith(".<lambda>"):
                self.named["transform lambda: %s" % describe(obj)] += 1
            self.transforms[name] += 1
            return {"kind": "transform", "func": name, "sub": self.node(obj.subcon) if getattr(obj, "subcon", None) is not None else None}
        if cls == "Computed":
            if isinstance(obj.func, (cs.BinExpr, cs.UniExpr, cs.Path)):
                return {"kind": "computed", "calculation": arithmetic(ast.parse(str(obj.func), mode="eval").body)}
            # A Computed holding a literal is a constant of the format, not
            # logic: `Computed(2)`, `Computed("Unknown vendor")`,
            # `Computed("\u00b0C")`. Keeping the literal in the specification
            # means the interpreter does not need a hand written table for the
            # versions, the units and the vendor names.
            if not callable(obj.func):
                return {"kind": "literal", "value": sanitize(obj.func)}
            text = func_name(obj.func)
            if text.endswith(".<lambda>"):
                names = obj.func.__code__.co_names
                text = next((name for name in ("absolute_humidity", "dew_point") if name in names), describe(obj.func))
            self.computed[text] += 1
            return {"kind": "computed", "func": text}
        if cls == "Hex":
            # A display wrapper: transparent for the data.
            return self.node(obj.subcon)
        return self.note_unmapped(obj)

    def walk_string_chain(self, obj, node):
        """Collect length/encoding/pad of a Padded/StringEncoded/NullStripped chain."""
        current = obj
        for _ in range(8):
            cls = type(current).__name__
            if cls == "Padded" and "length" not in node:
                node["length"] = current.length
                pad = current.pattern
                node["pad"] = hex(pad) if isinstance(pad, int) else str(pad)
            elif cls == "StringEncoded" and "encoding" not in node:
                node["encoding"] = current.encoding
            elif cls == "FixedSized" and "length" not in node:
                node["length"] = current.length
            nxt = getattr(current, "subcon", None)
            if nxt is None:
                return
            if "length" not in node and getattr(nxt, "length", None) is not None:
                node["length"] = nxt.length
            nxt_cls = type(nxt).__name__
            if nxt_cls in STRING_CLASSES:
                current = nxt
                continue
            if nxt_cls == "FixedSized":
                inner = getattr(nxt, "subcon", None)
                if inner is not None and getattr(inner, "length", None) is not None:
                    node["length"] = inner.length
            return

    def const_value(self, value):
        if isinstance(value, (bytes, bytearray)):
            return value.hex().upper()
        if isinstance(value, (int, str)):
            return value
        return str(value)


def load_codec(directory):
    """Import the codec package whose directory is given (relative imports)."""
    directory = os.path.abspath(directory)
    parent, package = os.path.dirname(directory), os.path.basename(directory)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return (
        importlib.import_module("%s.atc_mi_construct" % package),
        importlib.import_module("%s.atc_mi_construct_adapters" % package),
        importlib.import_module("%s.atc_mi_adv_format" % package),
    )


def build_formats(advanced):
    detector = getattr(advanced, "service_data_dict", {})
    formats = {}
    for name, structure, codec_name in FORMAT_MAP:
        entry = detector.get(name, {})
        uuid = entry.get("uuid")
        node = {"structure": structure, "uuid": (uuid or "").upper(), "detect": bool(uuid)}
        if entry.get("length"):
            node["length"] = entry["length"]
        if codec_name:
            node["codec"] = codec_name
        formats[name] = node
    return formats


def sanitize(value):
    """Make every node value plain YAML data (no Path, bytes, tuples)."""
    if isinstance(value, dict):
        return {str(k): sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize(v) for v in value]
    if isinstance(value, (bytes, bytearray)):
        return value.hex().upper()
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--codec", required=True, help="directory of the atc_mi_interface package")
    parser.add_argument("--out", help="write the specification here")
    parser.add_argument("--list", action="store_true", help="print the inventory only")
    args = parser.parse_args()

    codec, _adapters, advanced = load_codec(args.codec)
    converter = Converter()

    spec = {
        "version": 1,
        "generated_by": "tools/atc2spec.py",
        "structures": {},
        "formats": build_formats(advanced),
    }
    for name in TOP_LEVEL + CONTROL:
        obj = getattr(codec, name, None)
        print("converting %s" % name, file=sys.stderr)
        if obj is None:
            print("missing structure: %s" % name, file=sys.stderr)
            continue
        try:
            spec["structures"][name] = converter.node(obj)
        except Unmapped as error:
            print("cannot convert %s: %s" % (name, error), file=sys.stderr)
            spec["structures"][name] = {"kind": "unmapped", "class": "structure", "note": str(error)}

    spec = sanitize(spec)
    report = {
        "nodes": converter.count,
        "memo_hits": converter.hits,
        "recursive_nodes": converter.cycles,
        "unmapped_constructs": dict(converter.unmapped),
        "transforms": dict(converter.transforms),
        "computed_fields": dict(converter.computed),
        "named_predicates_to_implement": dict(converter.named),
    }
    print(json.dumps(report, indent=2, sort_keys=True))

    if args.list:
        return 0
    if not args.out:
        print("--out is required unless --list is used", file=sys.stderr)
        return 2

    import yaml

    directory = os.path.dirname(os.path.abspath(args.out))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    temporary = "%s.tmp" % args.out
    with open(temporary, "w") as handle:
        handle.write("# SPDX-License-Identifier: EUPL-1.2\n")
        handle.write("# Codec specification, generated by tools/atc2spec.py.\n")
        handle.write("# Edit only together with the converter.\n")
        yaml.safe_dump(spec, handle, sort_keys=False, width=1000, default_flow_style=False)
    os.replace(temporary, args.out)
    print("written %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
