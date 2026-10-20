#!/usr/bin/env python3
"""Convert an atc2spec JSON/YAML codec specification to Python/Construct."""

import argparse
import ast
import builtins
import codecs
import json
import keyword
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import textwrap


class ConversionError(ValueError):
    pass


def fail(path, message):
    raise ConversionError("%s: %s" % (path, message))


def mapping(value, path):
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        fail(path, "expected an object with string keys")
    return value


def number(value, path, nonzero=False):
    if (type(value) not in (int, float)
            or (type(value) is float and not math.isfinite(value))
            or abs(value) > sys.float_info.max
            or (nonzero and value == 0)):
        fail(path, "expected a finite%s number" % (" nonzero" if nonzero else ""))
    return ascii(value)


def integer(value, path, maximum=1048576, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        fail(path, "expected an integer between %d and %d" % (minimum, maximum))
    return str(value)


def boolean(value, path):
    if type(value) is not bool:
        fail(path, "expected a boolean")
    return str(value)


def literal(value, path):
    if value is None or type(value) in (str, bool, int):
        return ascii(value)
    if type(value) is float:
        return number(value, path)
    fail(path, "expected a scalar literal")


def expression(value, path, allow_input=False, depth=0):
    if depth >= 64:
        fail(path, "expression exceeds maximum depth")
    value = mapping(value, path)
    op = value.get("op")
    keys = {"input": set(), "field": {"path"}, "literal": {"value"},
            "int": {"argument"}, "float": {"argument"},
            "add": {"left", "right"}, "subtract": {"left", "right"},
            "multiply": {"left", "right"}, "divide": {"left", "right"}}
    if not isinstance(op, str) or op not in keys or set(value) != keys[op] | {"op"}:
        fail(path, "unknown or malformed arithmetic operation")
    if op == "input":
        if not allow_input:
            fail(path, "input is only available in an encoder")
        return "obj"
    if op == "field":
        steps = value["path"]
        if not isinstance(steps, list) or not steps or any(not isinstance(x, str) for x in steps):
            fail(path, "field path must be a nonempty list of strings")
        return "ctx" + "".join("[%s]" % ascii(step) for step in steps)
    if op == "literal":
        return number(value["value"], path + ".value")
    child = lambda key: expression(value[key], path + "." + key, allow_input, depth + 1)
    if op in ("int", "float"):
        return "%s(%s)" % (op, child("argument"))
    operator = {"add": "+", "subtract": "-", "multiply": "*", "divide": "/"}[op]
    return "(%s %s %s)" % (child("left"), operator, child("right"))


def selector(value, path):
    if not isinstance(value, str):
        fail(path, "expected a selector string")
    if value.startswith("positive_timestamp:"):
        field = value.split(":", 1)[1]
        if not field:
            fail(path, "missing timestamp field")
        return "ctx[%s].timestamp() > 0" % ascii(field)
    if value.startswith("equals:"):
        parts = value.split(":")
        if len(parts) != 3 or not parts[1] or not re.fullmatch(r"-?\d+", parts[2]):
            fail(path, "invalid equality predicate")
        return "ctx[%s] == %d" % (ascii(parts[1]), int(parts[2]))
    value = value.removeprefix("named predicate needed: ")
    try:
        tree = ast.parse(value, mode="eval").body
    except (SyntaxError, RecursionError) as error:
        fail(path, "invalid selector: %s" % error)

    def walk(node, depth=0):
        if depth >= 64:
            fail(path, "selector exceeds maximum depth")
        if isinstance(node, ast.Name) and node.id == "this":
            return "ctx"
        if isinstance(node, ast.Attribute):
            return "%s[%s]" % (walk(node.value, depth + 1), ascii(node.attr))
        if isinstance(node, ast.Subscript):
            base = walk(node.value, depth + 1)
            item = node.slice
            if isinstance(item, ast.Constant) and type(item.value) in (str, int):
                return "%s[%s]" % (base, ascii(item.value))
            if (isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
                    and item.func.id == "slice" and not item.keywords and len(item.args) == 3
                    and all(isinstance(x, ast.Constant) and
                            (x.value is None or type(x.value) is int) for x in item.args)):
                return "%s[slice(%s)]" % (base, ", ".join(ascii(x.value) for x in item.args))
        fail(path, "unsupported selector (only this.field paths and literal slices are allowed)")

    return walk(tree)


def call(name, *args):
    if all("\n" not in arg for arg in args) and sum(map(len, args)) < 85:
        return "%s(%s)" % (name, ", ".join(args))
    return "%s(\n%s\n)" % (name, textwrap.indent(",\n".join(args), "    "))


NODE_KEYS = {
    "struct": {"fields"}, "bitstruct": {"fields"}, "int": {"fmt"},
    "decimal": {"factor", "sub"}, "mac": {"swapped"}, "bytes": {"length"},
    "string": {"length", "prefix", "greedy", "encoding", "pad"},
    "varint": set(), "const": {"value", "sub"}, "boolean": set(),
    "bits": {"length", "signed", "swapped"}, "bytesint": {"length", "signed", "swapped"},
    "enum": {"sub", "mapping"}, "literal": {"value"},
    "switch": {"selector", "cases", "default"}, "if": {"predicate", "then", "else"},
    "select": {"alternatives"}, "greedy": {"sub"}, "array": {"count", "sub"},
    "fixed": {"length", "sub"}, "padding": {"length"}, "pass": set(),
    "timestamp": {"sub"}, "transform": {"func", "factor", "offset", "decoder", "encoder", "sub"},
    "computed": {"func", "calculation"}, "codec": {"codec", "sub"},
}
CODECS = {"atc_mi", "mi_like", "bt_home", "bt_home_v2"}


def node(value, path, depth=0):
    if depth >= 64:
        fail(path, "structure exceeds maximum depth")
    value = mapping(value, path)
    kind = value.get("kind")
    if not isinstance(kind, str) or kind not in NODE_KEYS:
        fail(path, "unsupported node kind %r" % kind)
    unknown = set(value) - NODE_KEYS[kind] - {"kind", "name"}
    if unknown:
        fail(path, "unknown properties: %s" % ", ".join(sorted(unknown)))

    def required(key):
        if key not in value:
            fail(path, "missing " + key)
        return value[key]

    def child(key="sub"):
        return node(required(key), path + "." + key, depth + 1)

    def children(key):
        items = required(key)
        if not isinstance(items, list):
            fail(path + "." + key, "expected a list")
        return [node(item, "%s.%s[%d]" % (path, key, index), depth + 1)
                for index, item in enumerate(items)]

    if kind in ("struct", "bitstruct"):
        fields = required("fields")
        if isinstance(fields, list):
            names = [field.get("name") for field in fields if isinstance(field, dict) and "name" in field]
            if any(not isinstance(name, str) for name in names) or len(set(names)) != len(names):
                fail(path, "field names must be unique strings")
        result = call("cs.BitStruct" if kind == "bitstruct" else "cs.Struct", *children("fields"))
    elif kind == "int":
        fmt = required("fmt")
        if not isinstance(fmt, str) or not re.fullmatch(r"[<>=][bBhHiIlLqQfd?]", fmt):
            fail(path, "expected a scalar struct format such as '<h'")
        result = call("cs.FormatField", ascii(fmt[0]), ascii(fmt[1]))
    elif kind == "decimal":
        result = call("DecimalNumber", child(), number(required("factor"), path + ".factor", True))
    elif kind == "mac":
        result = "ByteAdapter(swapped=%s)" % boolean(value.get("swapped", True), path + ".swapped")
    elif kind in ("bytes", "padding"):
        result = "cs.%s(%s)" % ("Bytes" if kind == "bytes" else "Padding",
                               integer(required("length"), path + ".length"))
    elif kind == "string":
        modes = int("length" in value) + int("prefix" in value) + int(value.get("greedy") is True)
        if modes != 1:
            fail(path, "string needs exactly one of length, prefix or greedy=true")
        if "greedy" in value:
            boolean(value["greedy"], path + ".greedy")
        encoding = value.get("encoding")
        if encoding is not None:
            if not isinstance(encoding, str):
                fail(path, "encoding must be a string")
            try:
                codecs.lookup(encoding)
            except LookupError:
                fail(path, "unknown string encoding")
        if "pad" in value:
            if (encoding is not None or "length" not in value or value["pad"] != "b'\\x00'"
                    or "name" in value):
                fail(path, "only anonymous, unencoded, fixed zero padding can be reconstructed")
            result = "cs.Padding(%s)" % integer(value["length"], path + ".length")
        elif "prefix" in value:
            result = call("cs.Prefixed", child("prefix"), "cs.GreedyBytes")
            if encoding is not None:
                result = call("cs.StringEncoded", result, ascii(encoding))
        elif value.get("greedy"):
            result = "cs.GreedyBytes" if encoding is None else "cs.GreedyString(%s)" % ascii(encoding)
        elif encoding is None:
            result = "cs.Bytes(%s)" % integer(value["length"], path + ".length")
        else:
            result = "cs.PaddedString(%s, %s)" % (integer(value["length"], path + ".length"), ascii(encoding))
    elif kind in ("varint", "boolean", "pass"):
        result = {"varint": "cs.VarInt", "boolean": "cs.Flag", "pass": "cs.Pass"}[kind]
    elif kind in ("bits", "bytesint"):
        maximum = 64 if kind == "bits" else 8
        result = "cs.%s(%s, signed=%s, swapped=%s)" % (
            "BitsInteger" if kind == "bits" else "BytesInteger",
            integer(required("length"), path + ".length", maximum, 1),
            boolean(value.get("signed", False), path + ".signed"),
            boolean(value.get("swapped", False), path + ".swapped"))
    elif kind == "const":
        subcon = mapping(required("sub"), path + ".sub")
        constant = required("value")
        if subcon.get("kind") == "bytes" and isinstance(constant, str):
            try:
                constant = bytes.fromhex(constant)
            except ValueError:
                fail(path, "byte constant must be hexadecimal")
            if len(constant) != subcon.get("length"):
                fail(path, "byte constant length differs from its subcon")
            constant = ascii(constant)
        else:
            constant = literal(constant, path + ".value")
        result = call("cs.Const", constant, child())
    elif kind == "enum":
        entries = mapping(required("mapping"), path + ".mapping")
        if any(not re.fullmatch(r"-?\d+", key) or not isinstance(symbol, str)
               for key, symbol in entries.items()):
            fail(path, "enum mapping must contain integer keys and string symbols")
        if len({int(key) for key in entries}) != len(entries):
            fail(path, "enum keys collide after integer conversion")
        symbols = {symbol: int(key) for key, symbol in entries.items()}
        if len(symbols) != len(entries):
            fail(path, "enum symbols must be unique")
        result = call("cs.Enum", child(), "**" + ascii(symbols))
    elif kind == "literal":
        result = call("cs.Computed", literal(required("value"), path + ".value"))
    elif kind == "switch":
        cases = mapping(required("cases"), path + ".cases")
        entries = [ascii(key) + ": " + node(case, path + ".cases[" + ascii(key) + "]", depth + 1)
                   for key, case in cases.items()]
        case_source = "{\n" + textwrap.indent(",\n".join(entries), "    ") + "\n}"
        result = call("cs.Switch", "lambda ctx: str(%s)" % selector(required("selector"), path + ".selector"),
                      case_source, "default=" + (child("default") if "default" in value else "cs.Pass"))
    elif kind == "if":
        result = call("cs.IfThenElse", "lambda ctx: " + selector(required("predicate"), path + ".predicate"),
                      child("then"), child("else") if "else" in value else "cs.Pass")
    elif kind == "select":
        if not required("alternatives"):
            fail(path, "select needs at least one alternative")
        result = call("cs.Select", *children("alternatives"))
    elif kind == "greedy":
        result = call("cs.GreedyRange", child())
    elif kind in ("array", "fixed"):
        key = "count" if kind == "array" else "length"
        result = call("cs.Array" if kind == "array" else "cs.FixedSized",
                      integer(required(key), path + "." + key, 65536 if kind == "array" else 1048576), child())
    elif kind == "timestamp":
        result = call("cs.Timestamp", child(), "1", "1970")
    elif kind == "computed":
        if ("func" in value) == ("calculation" in value):
            fail(path, "computed needs exactly one of func or calculation")
        if "calculation" in value:
            calculation = expression(value["calculation"], path + ".calculation")
        else:
            functions = {"absolute_humidity": "_absolute_humidity(ctx)", "dew_point": "_dew_point(ctx)",
                         "host_local_date": "_datetime.datetime.now().replace(microsecond=0).isoformat()"}
            if not isinstance(value["func"], str) or value["func"] not in functions:
                fail(path, "unsupported computed callback")
            calculation = functions[value["func"]]
        result = call("cs.Computed", "lambda ctx: " + calculation)
    elif kind == "transform":
        func = required("func")
        if func == "affine":
            factor = number(required("factor"), path + ".factor", True)
            offset = number(value.get("offset", 0), path + ".offset")
            if "encoder" not in value:
                fail(path, "affine transform needs the exported encoder (rounding cannot be inferred)")
            encoder = expression(value["encoder"], path + ".encoder", allow_input=True)
            decoder = (expression(value["decoder"], path + ".decoder", allow_input=True)
                       if "decoder" in value else "obj * %s + %s" % (factor, offset))
            result = call("cs.ExprAdapter", child(), "lambda obj, ctx: " + decoder,
                          "lambda obj, ctx: " + encoder)
        elif func in ("bytes2bits", "swapbytes"):
            if set(value) & {"factor", "offset", "decoder", "encoder"}:
                fail(path, "arithmetic properties require an affine transform")
            result = call("cs.Bitwise" if func == "bytes2bits" else "cs.ByteSwapped", child())
        else:
            fail(path, "unsupported transform %r (missing inverse or transform parameters)" % func)
    elif kind == "codec":
        codec = required("codec")
        if not isinstance(codec, str) or codec not in CODECS:
            fail(path, "unsupported encryption codec")
        result = call("_Codec", ascii(codec), child())
    if "name" in value:
        if not isinstance(value["name"], str):
            fail(path, "name must be a string")
        result = ascii(value["name"]) + " / " + result
    return result


def generate(spec):
    spec = mapping(spec, "spec")
    if type(spec.get("version")) is not int or spec["version"] != 1 or "structures" not in spec:
        fail("spec", "expected codec specification version 1 with structures, not a Discovery observation")
    structures = mapping(spec["structures"], "spec.structures")
    if not structures:
        fail("spec.structures", "at least one structure is required")
    formats = mapping(spec.get("formats", {}), "spec.formats")
    for name, entry in formats.items():
        entry = mapping(entry, "spec.formats." + name)
        if set(entry) - {"structure", "uuid", "detect", "length", "codec"}:
            fail("spec.formats." + name, "unknown format properties")
        if not isinstance(entry.get("structure"), str) or entry["structure"] not in structures:
            fail("spec.formats." + name, "unknown structure")
        if not isinstance(entry.get("uuid", ""), str) or not re.fullmatch(r"(?:[0-9a-fA-F]{4})?", entry.get("uuid", "")):
            fail("spec.formats." + name, "UUID must be empty or four hexadecimal digits")
        if "detect" in entry:
            boolean(entry["detect"], "spec.formats." + name + ".detect")
        if "length" in entry:
            integer(entry["length"], "spec.formats." + name + ".length")
        if "codec" in entry and (not isinstance(entry["codec"], str) or entry["codec"] not in CODECS):
            fail("spec.formats." + name, "unknown encryption codec")
    runtime = Path(__file__).with_name("spec2atc_runtime.py").read_text(encoding="utf-8")
    reserved = set(vars(builtins)) | {"cs", "DecimalNumber", "ByteAdapter",
                                     "STRUCTURES", "FORMATS", "SPEC_VERSION"}
    used = set(structures) | reserved
    definitions, exports = [], {}
    for index, (name, value) in enumerate(structures.items()):
        variable = name
        if (not name.isascii() or not name.isidentifier() or keyword.iskeyword(name)
                or name.startswith("_") or name in reserved):
            variable = "_structure_%d" % index
            while variable in used:
                variable += "_"
        used.add(variable)
        definitions.append("%s = %s\n" % (variable, node(value, "spec.structures." + name)))
        exports[name] = variable
    source = "# Generated by tools/spec2atc.py; requires Construct 2.10.70.\n" + runtime + "\n\n"
    source += "\n\n".join(definitions)
    source += "\nSPEC_VERSION = 1\nFORMATS = " + ascii(formats) + "\n"
    source += "STRUCTURES = {\n" + "".join("    %s: %s,\n" % (ascii(name), variable)
                                          for name, variable in exports.items()) + "}\n"
    try:
        compile(source, "<generated codec>", "exec")
    except (SyntaxError, ValueError, RecursionError) as error:
        fail("spec", "generated module cannot be compiled: %s" % error)
    return source


def load_spec(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as error:
            raise ConversionError("YAML input requires PyYAML; JSON input uses only the standard library") from error
        try:
            class UniqueLoader(yaml.SafeLoader):
                def construct_mapping(self, node, deep=False):
                    self.flatten_mapping(node)
                    result = {}
                    for key_node, value_node in node.value:
                        key = self.construct_object(key_node, deep=deep)
                        if not isinstance(key, (str, int, float, bool)) and key is not None:
                            raise ConversionError("YAML mapping keys must be scalar")
                        if key in result:
                            raise ConversionError("duplicate YAML key: %s" % key)
                        result[key] = self.construct_object(value_node, deep=deep)
                    return result
            return yaml.load(text, Loader=UniqueLoader)
        except yaml.YAMLError as error:
            raise ConversionError("invalid YAML: %s" % error) from error
    try:
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ConversionError("duplicate JSON key: " + key)
                result[key] = value
            return result
        return json.loads(text, object_pairs_hook=unique_pairs)
    except ValueError as error:
        raise ConversionError("invalid JSON: %s" % error) from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path, help="codec specification (.json, .yaml or .yml)")
    parser.add_argument("--out", required=True, type=Path, help="standalone generated Python module")
    args = parser.parse_args(argv)
    temporary = None
    try:
        if args.spec.resolve() == args.out.resolve():
            raise ConversionError("input and output must be different files")
        source = generate(load_spec(args.spec))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.out.parent,
                                         prefix=args.out.name + ".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(source)
        os.replace(temporary, args.out)
        temporary = None
    except (ConversionError, OSError, UnicodeError, RecursionError) as error:
        print("spec2atc: %s" % error, file=sys.stderr)
        return 1
    finally:
        if temporary is not None:
            temporary.unlink()
    print("written %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
