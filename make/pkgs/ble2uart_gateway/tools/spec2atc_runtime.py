"""Construct helpers embedded by spec2atc.py in the generated Python module."""

import datetime as _datetime
import math as _math
import re as _re

import construct as cs


class DecimalNumber(cs.Adapter):
    def __init__(self, subcon, decimal):
        super().__init__(subcon)
        self.decimal = decimal

    def _decode(self, obj, context, path):
        return obj / self.decimal

    def _encode(self, obj, context, path):
        return int(float(obj) * self.decimal)


class ByteAdapter(cs.Adapter):
    def __init__(self, swapped=False):
        super().__init__(cs.Bytes(6))
        self.swapped = swapped

    def _decode(self, obj, context, path):
        raw = obj[::-1] if self.swapped else obj
        return ":".join("%02X" % byte for byte in raw)

    def _encode(self, obj, context, path):
        raw = bytes.fromhex(_re.sub(r"[.:\- ]", "", obj))
        return raw[::-1] if self.swapped else raw


def _absolute_humidity(context):
    temperature, humidity = context["temperature"], context["humidity"]
    return (2.1674 * 6.112 * _math.exp(17.67 * temperature / (temperature + 243.5))
            * humidity / (temperature + 273.15))


def _dew_point(context):
    temperature, humidity = context["temperature"], context["humidity"]
    alpha = _math.log(humidity / 100) + 17.67 * temperature / (temperature + 243.5)
    return 243.5 * alpha / (17.67 - alpha)


class _Codec(cs.Tunnel):
    """The service-data nonce layouts used by src/src/crypto.rs."""

    def __init__(self, codec, subcon):
        super().__init__(subcon)
        self.codec = codec

    def _parse(self, stream, context, path):
        context = cs.Container(context)
        context._io = stream
        return super()._parse(stream, context, path)

    def _build(self, obj, stream, context, path):
        # Parsed Containers can retain the old stream when their fields are edited.
        context = cs.Container(context)
        context._io = stream
        return super()._build(obj, stream, context, path)

    def _prefix(self, context, consumed, path):
        stream = context._io
        position = cs.stream_tell(stream, path)
        cs.stream_seek(stream, 0, 0, path)
        try:
            return cs.stream_read(stream, position - consumed, path)
        finally:
            cs.stream_seek(stream, position, 0, path)

    def _cipher(self, context, prefix, counter, atc_length, marker, path):
        try:
            from Crypto.Cipher import AES
        except ImportError as error:
            raise ImportError("encrypted formats require pycryptodome") from error
        params = context._params
        if "mac_address" not in params or "bindkey" not in params:
            raise cs.ValidationError(
                "encryption requires mac_address (6 bytes) and bindkey (16 bytes)", path=path)
        mac, key = params["mac_address"], params["bindkey"]
        if not isinstance(mac, bytes) or len(mac) != 6:
            raise cs.ValidationError("mac_address must contain exactly 6 bytes", path=path)
        if not isinstance(key, bytes) or len(key) != 16:
            raise cs.ValidationError("bindkey must contain exactly 16 bytes", path=path)
        if len(prefix) < 2:
            raise cs.ValidationError("missing service UUID before encrypted payload", path=path)
        uuid = prefix[:2]
        if self.codec == "atc_mi":
            if not 0 <= atc_length <= 255:
                raise cs.ValidationError("ATC frame exceeds one-byte length", path=path)
            nonce = mac[::-1] + bytes([atc_length, 0x16]) + uuid + bytes([marker])
        elif self.codec == "mi_like":
            if len(prefix) < 7:
                raise cs.ValidationError("missing MiLike device ID/counter", path=path)
            nonce = mac[::-1] + prefix[4:7] + counter
        elif self.codec == "bt_home":
            nonce = mac + uuid + counter
        else:
            if len(prefix) < 3:
                raise cs.ValidationError("missing BTHome v2 DevInfo", path=path)
            nonce = mac + uuid + prefix[2:3] + counter
        cipher = AES.new(key, AES.MODE_CCM, nonce=nonce, mac_len=4)
        if self.codec != "bt_home_v2":
            cipher.update(b"\x11")
        return cipher

    def _decode(self, data, context, path):
        prefix = self._prefix(context, len(data), path)
        count = 0 if self.codec == "atc_mi" else 3 if self.codec == "mi_like" else 4
        minimum = 5 if self.codec == "atc_mi" else count + 4
        if len(data) < minimum:
            raise cs.ValidationError("encrypted frame is too short", path=path)
        counter = data[-count - 4:-4] if count else b""
        cipher = self._cipher(context, prefix, counter, len(data) + 3, data[0], path)
        ciphertext = data[1:-4] if self.codec == "atc_mi" else data[:-count - 4]
        try:
            plain = cipher.decrypt_and_verify(ciphertext, data[-4:])
        except ValueError as error:
            raise cs.ValidationError("CCM authentication failed (wrong bindkey or damaged frame)",
                                     path=path) from error
        return counter + plain

    def _encode(self, data, context, path):
        prefix = self._prefix(context, 0, path)
        count = 0 if self.codec == "atc_mi" else 3 if self.codec == "mi_like" else 4
        if len(data) < count:
            raise cs.ValidationError("missing encrypted packet counter", path=path)
        counter = data[:count]
        cipher = self._cipher(context, prefix, counter, len(data) + 8, 0xBD, path)
        ciphertext, mic = cipher.encrypt_and_digest(data[count:])
        return (b"\xBD" if self.codec == "atc_mi" else b"") + ciphertext + counter + mic
