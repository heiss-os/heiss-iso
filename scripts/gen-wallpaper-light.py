#!/usr/bin/env python3
"""Developer tool: make the Heiss-Everyday-Light wallpaper from the Heiss-Everyday (dark) one.

Same composition, light palette: the dark image is neutral grey (background 35, logo 78, thin ring up to 237), so
its luminance is mapped through a three-anchor colour ramp: background -> light paper, logo -> a slightly darker
warm grey (calm, like the dark one: the logo is a watermark, not a poster), ring -> dark warm grey. The anchor
colours come from branding/tokens/heiss-tokens.json (window and text colours of the Light theme).

Needs Pillow (not shipped, not used at build time): python3 -m venv v && v/bin/pip install pillow
    v/bin/python scripts/gen-wallpaper-light.py [--check]
The output PNGs are committed; --check regenerates in memory and exits 1 when they differ.
"""
import io
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALL = os.path.join(ROOT, "profile/airootfs/usr/share/wallpapers")
SIZES = ("1920x1080", "2560x1440", "3840x2160")
SRC_BG, SRC_LOGO, SRC_RING = 35, 78, 237


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def ramp():
    tokens = json.load(open(os.path.join(ROOT, "branding/tokens/heiss-tokens.json"), encoding="utf-8"))
    base = tokens["themes"]["light"]["base"]
    bg, fg = hex_rgb(base["window"]), hex_rgb(base["text"])
    logo = mix(bg, fg, 0.16)       # a quiet mark: 16% of the way from paper to ink
    ring = mix(bg, fg, 0.62)
    return bg, logo, ring


def lut(bg, logo, ring):
    out = [[], [], []]
    for v in range(256):
        if v <= SRC_BG:
            c = bg
        elif v <= SRC_LOGO:
            c = mix(bg, logo, (v - SRC_BG) / (SRC_LOGO - SRC_BG))
        elif v <= SRC_RING:
            c = mix(logo, ring, (v - SRC_LOGO) / (SRC_RING - SRC_LOGO))
        else:
            c = ring
        for i in range(3):
            out[i].append(c[i])
    return out[0] + out[1] + out[2]


def render(size):
    src = Image.open(os.path.join(WALL, "Heiss-Everyday/contents/images/%s.png" % size)).convert("L")
    return Image.merge("RGB", [src.point(lut(*ramp())[i * 256:(i + 1) * 256]) for i in range(3)])


def main():
    check = "--check" in sys.argv
    bad = 0
    for size in SIZES:
        path = os.path.join(WALL, "Heiss-Everyday-Light/contents/images/%s.png" % size)
        buf = io.BytesIO()
        render(size).save(buf, "PNG", optimize=True)
        if check:
            same = os.path.exists(path) and open(path, "rb").read() == buf.getvalue()
            print("%s: %s" % (size, "ok" if same else "DIFFERENT"))
            bad += not same
        else:
            open(path, "wb").write(buf.getvalue())
            print("wrote", path)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
