#!/usr/bin/env python3
"""Replay restricted pickle captures through an ADV_BLE2UART PTY, optionally supervising ble2uart-gateway."""

import argparse
import contextlib
import json
import math
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import tty

from capture_trace import load_captures, normalize_mac


def crc16(data):
    checksum = 0xFFFF
    for byte in data:
        checksum ^= byte
        for _ in range(8):
            checksum = (checksum >> 1) ^ (0xA001 if checksum & 1 else 0)
    return checksum.to_bytes(2, "little")


class Firmware:
    def __init__(self):
        self.master, self.slave = os.openpty()
        tty.setraw(self.slave)
        os.fchmod(self.slave, 0o600)
        os.set_blocking(self.master, False)
        self.path = os.ttyname(self.slave)
        self.scanning = threading.Event()
        self.stopped = threading.Event()
        self.writer = threading.Lock()
        self.whitelist, self.blacklist = set(), set()
        self.error = None
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def write(self, data):
        deadline = time.monotonic() + 5
        with self.writer:
            remaining = memoryview(data)
            while remaining and not self.stopped.is_set():
                if time.monotonic() >= deadline:
                    raise TimeoutError("PTY consumer stopped reading")
                if select.select([], [self.master], [], 0.1)[1]:
                    try:
                        remaining = remaining[os.write(self.master, remaining):]
                    except BlockingIOError:
                        pass

    def run(self):
        pending = bytearray()
        try:
            while not self.stopped.is_set():
                if not select.select([self.master], [], [], 0.1)[0]:
                    continue
                pending.extend(os.read(self.master, 4096))
                while pending:
                    command = pending[0]
                    length = 9 if command in (2, 3) else 4 if command in (5, 8) else 3
                    if command in (2, 3):
                        lengths = [size for size in range(4, min(9, len(pending)) + 1) if crc16(pending[:size - 2]) == pending[size - 2:size]]
                        if lengths:
                            length = max(lengths)
                        elif len(pending) < 9:
                            break
                        else:
                            raise ValueError("invalid MAC filter command CRC")
                    if command == 1:
                        if len(pending) < 2:
                            break
                        if len(pending) >= 8 and crc16(pending[:6]) == pending[6:8]:
                            length = 8
                        elif len(pending) >= 6 and crc16(pending[:4]) == pending[4:6]:
                            length = 6
                        elif len(pending) < 8:
                            break
                        else:
                            raise ValueError("invalid SCAN command CRC")
                    if len(pending) < length:
                        break
                    packet = bytes(pending[:length])
                    if crc16(packet[:-2]) != packet[-2:]:
                        if command == 1 and length == 8 and crc16(packet[:4]) == packet[4:6]:
                            length = 6
                            packet = bytes(pending[:length])
                        else:
                            raise ValueError("invalid host command CRC")
                    del pending[:length]
                    status = 64 if command == 4 else 2 if command == 0 else 0
                    if command == 4:
                        self.whitelist.clear()
                        self.blacklist.clear()
                    elif command in (2, 3):
                        entries = self.whitelist if command == 2 else self.blacklist
                        entries.add(packet[1:-2])
                        status = len(entries)
                    elif command == 1 and not packet[1]:
                        self.scanning.clear()
                    elif command not in (0, 1, 5, 8, 10):
                        status = 1
                    response = bytes([0, command, status, 0, 0xFF]) + bytes(6)
                    self.write(response + crc16(response))
                    if command == 1 and packet[1]:
                        self.scanning.set()
        except (OSError, ValueError, TimeoutError) as error:
            self.error = str(error)
            self.stopped.set()

    def observation(self, mac, data, rssi=-60, phy_raw=0x01, event_type=0, addr_type=0, directed=False):
        if len(data) > 229:
            raise ValueError("advertisement exceeds the firmware's 229-byte limit")
        if not -128 <= rssi <= 127 or not 0 <= phy_raw < 255 or not 0 <= event_type <= 255 or not 0 <= addr_type <= 15:
            raise ValueError("invalid radio metadata")
        address = bytes.fromhex(normalize_mac(mac))[::-1]
        if not self.scanning.is_set() or self.stopped.is_set() or any(address.endswith(prefix) for prefix in self.blacklist) or (self.whitelist and not any(address.endswith(prefix) for prefix in self.whitelist)):
            return False
        frame = bytes([len(data), rssi & 255, event_type, addr_type | (16 if directed else 0), phy_raw]) + address + data
        self.write(frame + crc16(frame))
        return True

    def advertise(self, service, sequence):
        return self.observation("AABBCCDDEEFF", bytes([len(service) + 1, 0x16]) + service,
                                rssi=-60, phy_raw=0x33, event_type=sequence)

    def close(self):
        self.stopped.set()
        self.thread.join(timeout=6)
        os.close(self.master)
        os.close(self.slave)


def offsets(captures, timing, interval, speed):
    if not math.isfinite(speed) or speed <= 0 or not math.isfinite(interval) or interval <= 0:
        raise ValueError("speed and interval must be positive finite numbers")
    if timing == "fixed":
        return [index * interval / speed for index in range(len(captures))]
    stamps = [capture.recorded_at for capture in captures]
    if any(stamp is None for stamp in stamps):
        raise ValueError("recorded timing requires timestamps on every packet; use --timing fixed")
    if stamps != sorted(stamps):
        raise ValueError("recorded timestamps are not monotonic; use --timing fixed")
    return [(stamp - stamps[0]) / speed for stamp in stamps]


def expose_all_attributes(devices, attributes):
    for device in devices:
        mac = normalize_mac(device["mac"])
        if not device["enabled"]:
            print(f"replay warning: {mac}: device disabled; exposure does not enable it", file=sys.stderr)
            continue
        exposed = device.setdefault("expose", [])
        used, next_child = set(), 0
        for entry in exposed:
            child = entry.get("child")
            if child is None:
                child = next_child
                next_child = min(255, next_child + 1)
                entry["child"] = child
            used.add(child)
        names = {entry["attribute"] for entry in exposed}
        added = []
        for name in attributes:
            if name in names:
                continue
            child = next((child for child in range(255) if child not in used), None)
            if child is None:
                raise ValueError(f"{mac}: no free measurement child IDs")
            exposed.append({"attribute": name, "child": child})
            used.add(child)
            names.add(name)
            added.append(f"{name}=child {child}")
        if added:
            print(f"replay config: {mac}: missing exposures added privately: {', '.join(added)}", file=sys.stderr)


def validate_binary_args(arguments):
    flags = {"--foreground", "--log-stdout", "--verbose", "-v",
             "--trace-tx", "--no-trace-tx", "--trace-rx", "--no-trace-rx",
             "--trace-decode", "--no-trace-decode", "--trace-phy", "--no-trace-phy"}
    values = {"--log-level", "--log-color"}
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in values:
            index += 1
            if index == len(arguments) or arguments[index].startswith("-"):
                raise ValueError(f"{argument} requires a value")
        elif argument not in flags:
            raise ValueError(f"gateway option not allowed in replay: {argument}; only logging/trace options can be forwarded")
        index += 1


def prepare_config(binary, source, path, firmware, captures, allow_frontends=False, import_bindkeys=False, expose_all=False):
    if source is None:
        subprocess.run([binary, "--write-default-config", str(path)], check=True, stdout=subprocess.DEVNULL)
        source = path
    result = subprocess.run([binary, "--config", str(source), "--web-config", "read"],
                            input="", capture_output=True, text=True, check=True)
    config = json.loads(result.stdout)["config"]
    if not config["devices"]:
        devices = {}
        for capture in captures:
            device = devices.setdefault(capture.mac, {"mac": capture.mac, "label": capture.mac, "enabled": True,
                "expose": [{"attribute": name, "child": child} for child, name in enumerate(("temperature", "humidity", "battery_level", "flooding"))]})
            if import_bindkeys and capture.bindkey:
                if device.get("bindkey") and device["bindkey"] != capture.bindkey:
                    raise ValueError("conflicting capture bindkeys; provide a device configuration")
                device["bindkey"] = capture.bindkey
        config["devices"] = list(devices.values())
    if expose_all:
        result = subprocess.run([binary, "--web-config", "attributes"], input="",
                                capture_output=True, text=True, check=True)
        expose_all_attributes(config["devices"], json.loads(result.stdout)["attributes"])
        enabled = {normalize_mac(device["mac"]) for device in config["devices"] if device["enabled"]}
        for mac in sorted({capture.mac for capture in captures} - enabled):
            print(f"replay warning: {mac}: no enabled device configuration; packets will not be decoded", file=sys.stderr)
        archived_keys = {capture.mac for capture in captures if capture.bindkey}
        for device in config["devices"]:
            mac = normalize_mac(device["mac"])
            if device["enabled"] and mac in archived_keys and not device.get("bindkey"):
                print(f"replay warning: {mac}: archive has a bindkey but configuration does not; encrypted packets cannot be decoded", file=sys.stderr)
    config["serial"]["port"] = firmware.path
    config["serial"]["reset_on_open"] = False
    if not allow_frontends:
        for frontend in config["frontends"].values():
            frontend["enabled"] = False
    config["frontends"]["matter"].update(store=str(path.parent / "matter"), advertise=False, bind="::1", domoticz_port=0)
    path.write_text(json.dumps(config, indent=2))
    path.chmod(0o600)
    subprocess.run([binary, "--check-config", str(path)], check=True, stdout=subprocess.DEVNULL)


def stop_child(child):
    if child and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


def run(args):
    captures = []
    rejected = 0
    for path in args.captures:
        imported, errors = load_captures(path)
        if errors and not args.skip_invalid:
            raise ValueError(f"{path.name}: {len(errors)} invalid records; use --skip-invalid explicitly to omit them")
        rejected += len(errors)
        captures.extend(imported)
    if not captures:
        raise ValueError("no packets in the capture archives")
    for capture in captures:
        capture.mac = capture.mac or args.mac or ""
        if not capture.mac:
            raise ValueError("a capture has no MAC; provide --mac instead of inventing an identity")
        if len(capture.ad) > 229:
            raise ValueError("a packet exceeds the firmware limit; it will not be truncated")
    schedule = offsets(captures, args.timing, args.interval, args.speed)
    stopped = threading.Event()
    previous_handlers = {number: signal.signal(number, lambda *_: stopped.set()) for number in (signal.SIGINT, signal.SIGTERM)}
    firmware = Firmware()
    child = None
    link_owned = False
    try:
        if args.pty_link:
            args.pty_link.symlink_to(firmware.path)
            link_owned = True
        with contextlib.ExitStack() as owned:
            directory = owned.enter_context(tempfile.TemporaryDirectory(prefix="ble2uart-replay-"))
            config_path = Path(directory) / "config.yaml"
            if not args.no_launch:
                binary = shutil.which(args.binary)
                if binary is None:
                    raise ValueError("gateway executable not found; set --binary")
                prepare_config(binary, args.config, config_path, firmware, captures, args.allow_frontends, args.import_bindkeys, args.expose_all)
                environment = {**os.environ, "BLE2UART_GATEWAY_CONTROL_SOCKET": str(Path(directory) / "control/control.sock")}
                child = subprocess.Popen([binary, "--config", str(config_path), "--foreground", *args.binary_arg],
                                         env=environment, stdout=sys.stderr)
                owned.callback(stop_child, child)
            print(json.dumps({"event": "ready", "pty": firmware.path, "packets": len(captures),
                              "timing": args.timing, "speed": args.speed, "rejected_records": rejected,
                              "private_config": str(config_path) if child else None,
                              "frontends_allowed": args.allow_frontends if child else None}), flush=True)
            deadline = time.monotonic() + args.start_timeout
            while not firmware.scanning.wait(0.05):
                if stopped.is_set():
                    return
                if firmware.error or (child and child.poll() is not None) or time.monotonic() >= deadline:
                    raise RuntimeError(firmware.error or "gateway did not start scanning; see its stderr")
            emitted = 0
            cycle = 0
            started = time.monotonic()
            while not stopped.is_set() and (args.repeat == 0 or cycle < args.repeat):
                for capture, offset in zip(captures, schedule):
                    if stopped.wait(max(0, started + offset - time.monotonic())):
                        break
                    if child and child.poll() is not None:
                        raise RuntimeError("gateway exited during replay")
                    radio = {"rssi": args.rssi, "phy_raw": args.phy, **capture.radio}
                    emitted += firmware.observation(capture.mac, capture.ad, **radio)
                    if firmware.error:
                        raise RuntimeError(firmware.error)
                cycle += 1
                started += schedule[-1] + args.interval / args.speed
            stopped.wait(args.settle)
            print(json.dumps({"event": "finished", "cycles": cycle, "emitted_packets": emitted,
                              "source_packets": len(captures), "source_files_modified": False}), flush=True)
            if child and child.poll() is not None:
                raise RuntimeError("gateway exited before replay completion")
    finally:
        stop_child(child)
        firmware.close()
        if link_owned and args.pty_link.is_symlink() and os.readlink(args.pty_link) == firmware.path:
            args.pty_link.unlink()
        for number, handler in previous_handlers.items():
            signal.signal(number, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path, nargs="+")
    parser.add_argument("--binary", default="ble2uart-gateway")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument("--pty-link", type=Path)
    parser.add_argument("--timing", choices=("fixed", "recorded"), default="fixed")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--repeat", type=int, default=1, help="0 repeats until interrupted")
    parser.add_argument("--mac", type=normalize_mac)
    parser.add_argument("--rssi", type=int, default=-60)
    parser.add_argument("--phy", type=lambda value: int(value, 0), default=0x01)
    parser.add_argument("--start-timeout", type=float, default=30)
    parser.add_argument("--settle", type=float, default=1)
    parser.add_argument("--allow-frontends", action="store_true", help="explicitly allow publishing simulated data to configured frontends")
    parser.add_argument("--import-bindkeys", action="store_true", help="copy capture keys only into the private generated device config")
    parser.add_argument("--skip-invalid", action="store_true")
    parser.add_argument("--expose-all", action="store_true", help="add every supported measurement to private device exposures, preserving existing child IDs")
    parser.add_argument("--binary-arg", action="append", default=[], help="forward a logging/trace argument; use --binary-arg=--trace-decode or put gateway options after --")
    arguments = sys.argv[1:]
    forwarded = []
    if "--" in arguments:
        separator = arguments.index("--")
        arguments, forwarded = arguments[:separator], arguments[separator + 1:]
    args = parser.parse_args(arguments)
    args.binary_arg.extend(forwarded)
    try:
        validate_binary_args(args.binary_arg)
    except ValueError as error:
        parser.error(str(error))
    if args.repeat < 0 or not math.isfinite(args.start_timeout) or args.start_timeout <= 0 or not math.isfinite(args.settle) or args.settle < 0:
        parser.error("invalid repetition count, timeout or settling interval")
    if args.no_launch and (args.config or args.import_bindkeys or args.allow_frontends or args.expose_all or args.binary_arg):
        parser.error("PTY-only mode does not modify an external gateway's config/frontends")
    try:
        run(args)
    except Exception as error:
        print(f"replay failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())