#!/usr/bin/env python3
"""Generate the home-screen icons of the sensor portal.

The portal is installable as a web app, so it needs real PNG icons in the web
root (`/usr/mww/ble2uart_gateway/`, served at `/ble2uart_gateway/`).  The image
is built here with integer arithmetic only, so the result is reproducible and
the repository does not need an image editor or a binary blobs pipeline:

    python3 tools/gen_portal_icons.py            # rewrite the icons
    python3 tools/gen_portal_icons.py --check    # non-zero if they are stale

Files written (all sRGB, 8-bit, alpha):
    icon-192.png            192x192  "any"      rounded square + sparkline
    icon-512.png            512x512  "any"
    icon-180.png            180x180  apple-touch-icon (no transparency)
    icon-maskable-512.png   512x512  "maskable" full bleed, 80% safe zone
"""

from __future__ import annotations

import argparse
import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "files" / "root" / "usr" / "mww" / "ble2uart_gateway"

# Palette of the dashboard header: the accent of the light theme and the teal
# of the field-help buttons, which is what the portal shows on a phone.
GRADIENT_FROM = (0x0B, 0x6B, 0xCB)
GRADIENT_TO = (0x08, 0x7E, 0x83)
INK = (0xFF, 0xFF, 0xFF)


def _mix(a, b, t: float):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _rounded_alpha(x: float, y: float, size: int, radius: float) -> float:
    """Coverage of a rounded square centred on the canvas, 0..1."""
    cx = cy = size / 2.0
    dx = abs(x - cx)
    dy = abs(y - cy)
    half = size / 2.0
    if dx <= half - radius or dy <= half - radius:
        inside = dx <= half and dy <= half
        return 1.0 if inside else 0.0
    # Corner: distance from the corner circle centre.
    ox = dx - (half - radius)
    oy = dy - (half - radius)
    distance = math.hypot(ox, oy)
    if distance <= radius - 0.5:
        return 1.0
    if distance >= radius + 0.5:
        return 0.0
    return max(0.0, min(1.0, radius + 0.5 - distance))


def _segment_distance(px, py, ax, ay, bx, by) -> float:
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    length2 = vx * vx + vy * vy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / length2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def render(size: int, maskable: bool) -> bytes:
    """RGBA pixels of one icon, row major."""
    radius = 0.0 if maskable else size * 0.22
    # Content of a maskable icon must stay inside the middle 80% of the canvas.
    scale = 0.78 if maskable else 0.86
    inner = size * scale
    origin = (size - inner) / 2.0

    # A sparkline: the shape of the dashboard the icons open.
    points = [(0.05, 0.62), (0.26, 0.62), (0.38, 0.30), (0.55, 0.72), (0.70, 0.44), (0.95, 0.44)]
    path = [(origin + x * inner, origin + y * inner) for x, y in points]
    stroke = max(2.0, inner * 0.075)
    dot = stroke * 0.95

    pixels = bytearray()
    for py in range(size):
        row = bytearray()
        y = py + 0.5
        for px in range(size):
            x = px + 0.5
            coverage = _rounded_alpha(x, y, size, radius) if radius else 1.0
            if coverage <= 0.0:
                row += b"\x00\x00\x00\x00"
                continue
            # Diagonal gradient, slightly brighter towards the top left.
            t = max(0.0, min(1.0, (x / size) * 0.65 + (py / size) * 0.35))
            rgb = _mix(GRADIENT_FROM, GRADIENT_TO, t)
            alpha = int(round(coverage * 255))

            # White stroke on top of the gradient.
            distance = min(
                _segment_distance(x, y, path[i][0], path[i][1], path[i + 1][0], path[i + 1][1])
                for i in range(len(path) - 1)
            )
            distance = min(distance, min(math.hypot(x - cx, y - cy) - dot for cx, cy in path))
            if distance <= stroke / 2.0 - 0.5:
                rgb = INK
            elif distance < stroke / 2.0 + 0.5:
                blend = stroke / 2.0 + 0.5 - distance
                rgb = _mix(rgb, INK, max(0.0, min(1.0, blend)))
            row += bytes((rgb[0], rgb[1], rgb[2], alpha))
        pixels += row
    return bytes(pixels)


def png(size: int, pixels: bytes) -> bytes:
    raw = bytearray()
    stride = size * 4
    for y in range(size):
        raw.append(0)  # filter type: none
        raw += pixels[y * stride:(y + 1) * stride]

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


ICONS = [
    ("icon-192.png", 192, False),
    ("icon-512.png", 512, False),
    ("icon-180.png", 180, False),
    ("icon-maskable-512.png", 512, True),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report stale icons, write nothing")
    args = parser.parse_args()

    TARGET.mkdir(parents=True, exist_ok=True)
    stale = []
    for name, size, maskable in ICONS:
        data = png(size, render(size, maskable))
        path = TARGET / name
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                stale.append(name)
            continue
        path.write_bytes(data)
        print(f"{name}: {size}x{size} maskable={maskable} {len(data)} bytes")
    if args.check:
        if stale:
            print("stale icons: " + ", ".join(stale))
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
