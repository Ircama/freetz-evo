"""Compatibility shim for environments without native orjson.

This module provides a small subset of the orjson API used by mashumaro and
webrtc_models. It is intentionally minimal and prioritizes compatibility.
"""

import json as _json


class JSONEncodeError(TypeError):
    pass


class JSONDecodeError(ValueError):
    pass


# orjson option flags (accepted but ignored by this shim)
OPT_APPEND_NEWLINE = 0
OPT_INDENT_2 = 0
OPT_NAIVE_UTC = 0
OPT_NON_STR_KEYS = 0
OPT_OMIT_MICROSECONDS = 0
OPT_PASSTHROUGH_DATACLASS = 0
OPT_PASSTHROUGH_DATETIME = 0
OPT_PASSTHROUGH_SUBCLASS = 0
OPT_SERIALIZE_DATACLASS = 0
OPT_SERIALIZE_NUMPY = 0
OPT_SERIALIZE_UUID = 0
OPT_SORT_KEYS = 0
OPT_STRICT_INTEGER = 0
OPT_UTC_Z = 0


def dumps(obj, default=None, option=0):
    try:
        return _json.dumps(obj, default=default, separators=(",", ":")).encode("utf-8")
    except TypeError as err:
        raise JSONEncodeError(str(err))


def loads(data):
    try:
        if isinstance(data, (bytes, bytearray)):
            data = bytes(data).decode("utf-8")
        return _json.loads(data)
    except ValueError as err:
        raise JSONDecodeError(str(err))
