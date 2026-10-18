"""Restricted, dependency-free import of private ATC advertisement archives."""

import collections
import dataclasses
import datetime
import io
import math
import pickle
import re


UUID_BYTES = {"custom": "1a18", "custom_enc": "1a18", "atc1441": "1a18",
              "atc1441_enc": "1a18", "mi_like": "95fe", "bt_home": "1c18",
              "bt_home_enc": "1e18", "bt_home_v2": "d2fc"}


class RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        allowed = {("collections", "OrderedDict"): collections.OrderedDict,
                   ("datetime", "datetime"): datetime.datetime,
                   ("datetime", "timezone"): datetime.timezone,
                   ("datetime", "timedelta"): datetime.timedelta}
        if (module, name) not in allowed:
            raise pickle.UnpicklingError("unsupported pickle object type")
        return allowed[module, name]


def normalize_mac(value):
    digits = re.sub(r"[:-]", "", str(value)).upper()
    if not re.fullmatch(r"[0-9A-F]{12}", digits):
        raise ValueError("invalid capture MAC")
    return digits


def service_format(payload):
    for name, uuid in UUID_BYTES.items():
        if payload[:2].hex() != uuid:
            continue
        lengths = {"custom": 15, "custom_enc": 11, "atc1441": 13, "atc1441_enc": 8}
        if name not in lengths or len(payload) - 2 == lengths[name]:
            return name
    return None


def advertisement(raw):
    if len(raw) >= 2 and raw[:2].hex() in UUID_BYTES.values():
        if len(raw) > 254:
            raise ValueError("service data exceeds an AD structure")
        return bytes([len(raw) + 1, 0x16]) + raw, raw, "service_data"
    index = 0
    while index < len(raw):
        length = raw[index]
        if not length:
            break
        if index + length >= len(raw):
            return raw, b"", "truncated_advertisement"
        if raw[index + 1] == 0x16 and length >= 3:
            service = raw[index + 2:index + 1 + length]
            if service_format(service):
                return raw, service, "advertisement"
        index += length + 1
    return raw, b"", "unsupported_advertisement"


def recorded_time(entry):
    value = next((entry[key] for key in ("timestamp", "time", "datetime", "date") if key in entry), None)
    try:
        if isinstance(value, datetime.datetime):
            value = value.timestamp()
        elif isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                value = datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        return float(value) if not isinstance(value, bool) and isinstance(value, (float, int)) and math.isfinite(value) else None
    except (ValueError, OverflowError, OSError):
        return None


@dataclasses.dataclass(repr=False)
class Capture:
    archive: str
    index: int
    mac: str
    bindkey: str
    raw: bytes
    ad: bytes
    service: bytes
    framing: str
    format: str
    context: str = "archived"
    variant: str = "original"
    source_format: str = ""
    recorded_at: float | None = None
    radio: dict = dataclasses.field(default_factory=dict)

    @property
    def identifier(self):
        base = f"{self.archive}#{self.index}"
        return base if self.variant == "original" else base + "/" + self.variant

    def request(self):
        return {"case": self.identifier, "observation": {"mac": self.mac or "000000000000", "data": self.ad.hex()},
                "device": {"mac": self.mac or "000000000000", "bindkey": self.bindkey}}


def load_captures(path):
    if path.stat().st_size > 128 * 1024 * 1024:
        raise ValueError("archive exceeds 128 MiB")
    archive = RestrictedUnpickler(io.BytesIO(path.read_bytes())).load()
    if isinstance(archive, dict):
        gallery, metadata = archive, {}
    elif isinstance(archive, (list, tuple)) and len(archive) == 2:
        gallery, metadata = archive
    else:
        raise ValueError("unsupported archive layout")
    if not isinstance(gallery, dict) or not isinstance(metadata, dict):
        raise ValueError("invalid gallery/reference maps")
    references = {normalize_mac(mac): entry for mac, entry in metadata.items()}
    captures, errors = [], []
    for index, (label, entry) in enumerate(gallery.items(), 1):
        identifier = f"{path.name}#{index}"
        try:
            radio = {}
            observed = None
            if isinstance(entry, bytes):
                raw = entry
                match = re.search(r"(?i)(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}", str(label))
                mac = normalize_mac(match.group()) if match else ""
            else:
                raw = entry["binary"]
                mac = normalize_mac(entry["mac_address"]) if entry.get("mac_address") else ""
                observed = recorded_time(entry)
                radio = {key: entry[key] for key in ("rssi", "phy_raw", "event_type", "addr_type", "directed") if key in entry}
            if not isinstance(raw, bytes):
                raise ValueError("binary field is not bytes")
            key = references.get(mac, {}).get("bindkey", "") or ""
            if isinstance(key, bytes):
                key = key.hex()
            if not isinstance(key, str) or (key and not re.fullmatch(r"[0-9A-Fa-f]{32}", key)):
                raise ValueError("invalid capture bindkey")
            ad, service, framing = advertisement(raw)
            name = service_format(service) or "unsupported"
            captures.append(Capture(path.name, index, mac, key, raw, ad, service, framing, name,
                                    "archived" if mac else "missing_identity", recorded_at=observed, radio=radio))
        except (ValueError, KeyError, TypeError) as error:
            reason = str(error) if isinstance(error, ValueError) else "missing or invalid entry fields"
            errors.append({"case": identifier, "error": reason})
    return captures, errors