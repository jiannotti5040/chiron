#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""Draw the app icon and fold it into an .icns. Stdlib only.

The mark is the three verdicts, as three bars of descending length:
VERIFIED full, REFUTED shorter, REFUSED shortest and dimmest — the shape of a
system that says less as certainty falls off, which is the whole point.
"""
import os
import struct
import subprocess
import sys
import tempfile
import zlib

BG = (14, 17, 22)
BARS = [((64, 196, 122), 1.00),    # VERIFIED
        ((226, 92, 84), 0.72),     # REFUTED
        ((132, 141, 156), 0.46)]   # REFUSED


def draw(size):
    """Return an RGBA pixel buffer, drawn at `size` square."""
    px = bytearray()
    r_corner = size * 0.22
    bar_h = size * 0.105
    gap = size * 0.075
    left = size * 0.20
    top = size * 0.28
    for y in range(size):
        row = bytearray()
        for x in range(size):
            # rounded-rect background mask
            dx = min(x, size - 1 - x)
            dy = min(y, size - 1 - y)
            inside = True
            if dx < r_corner and dy < r_corner:
                inside = ((r_corner - dx) ** 2 + (r_corner - dy) ** 2) <= r_corner ** 2
            if not inside:
                row += bytes((0, 0, 0, 0))
                continue
            colour = BG
            for i, (rgb, frac) in enumerate(BARS):
                y0 = top + i * (bar_h + gap)
                if y0 <= y < y0 + bar_h and left <= x < left + (size - 2 * left) * frac:
                    colour = rgb
                    break
            row += bytes(colour) + b"\xff"
        px += row
    return bytes(px)


def png(size, path):
    raw = draw(size)
    stride = size * 4
    scan = b"".join(b"\x00" + raw[i * stride:(i + 1) * stride] for i in range(size))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(scan, 9)))
        f.write(chunk(b"IEND", b""))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "icon"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        iconset = os.path.join(tmp, "icon.iconset")
        os.makedirs(iconset)
        for base in (16, 32, 128, 256, 512):
            png(base, os.path.join(iconset, "icon_%dx%d.png" % (base, base)))
            png(base * 2, os.path.join(iconset, "icon_%dx%d@2x.png" % (base, base)))
        try:
            subprocess.run(["iconutil", "-c", "icns", iconset, "-o", out + ".icns"],
                           check=True, capture_output=True)
            print(out + ".icns")
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            # No iconutil (or it refused): say so rather than shipping a bundle
            # that silently has no icon.
            print("iconutil unavailable: %s" % exc, file=sys.stderr)
            png(512, out + ".png")
            print(out + ".png")


if __name__ == "__main__":
    main()
