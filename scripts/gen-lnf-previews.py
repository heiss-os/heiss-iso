#!/usr/bin/env python3
"""Developer tool: draw the preview images of the Heiss Dark and Heiss Light global themes.

System Settings and the Quick Settings theme list show contents/previews/preview.png (and fullscreenpreview.jpg
when the preview is opened) of a Look-and-Feel package. Each image is the theme's own wallpaper with a small window
and a floating dock, drawn from the design tokens: no new literal colours. Needs Pillow (see gen-wallpaper-light.py).

    v/bin/python scripts/gen-lnf-previews.py [--check]
"""
import io
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LNF = os.path.join(ROOT, "profile/airootfs/usr/share/plasma/look-and-feel")
WALL = {"dark": "Heiss-Everyday", "light": "Heiss-Everyday-Light"}
FONT = os.path.join(ROOT, "branding/fonts/static/Inter-SemiBold.ttf")
LABEL = {"dark": "Heiss Dark", "light": "Heiss Light"}


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def draw(theme, width):
    base = json.load(open(os.path.join(ROOT, "branding/tokens/heiss-tokens.json"), encoding="utf-8"))["themes"][theme]["base"]
    wall = Image.open(os.path.join(ROOT, "profile/airootfs/usr/share/wallpapers", WALL[theme], "contents/images/1920x1080.png")).convert("RGB")
    h = width * 9 // 16
    im = wall.resize((width, h), Image.LANCZOS)
    d = ImageDraw.Draw(im, "RGBA")
    u = width / 100.0
    # window
    x0, y0, x1, y1 = 12 * u, 14 * u, 62 * u, 40 * u
    d.rounded_rectangle((x0, y0, x1, y1), radius=1.2 * u, fill=rgb(base["window"]), outline=rgb(base["button"]), width=max(1, round(u / 4)))
    d.rounded_rectangle((x0, y0, x1, y0 + 4 * u), radius=1.2 * u, fill=rgb(base["panel"]))
    d.rectangle((x0, y0 + 2.5 * u, x1, y0 + 4 * u), fill=rgb(base["panel"]))
    for i in range(3):
        d.ellipse((x0 + (1.6 + 2.2 * i) * u, y0 + 1.4 * u, x0 + (2.8 + 2.2 * i) * u, y0 + 2.6 * u), fill=rgb(base["text_secondary"]))
    for i, wd in enumerate((30, 24, 34)):
        d.rounded_rectangle((x0 + 3 * u, y0 + (7 + 3 * i) * u, x0 + (3 + wd) * u, y0 + (8.4 + 3 * i) * u), radius=0.7 * u, fill=rgb(base["text_secondary"]))
    d.rounded_rectangle((x0 + 3 * u, y1 - 6 * u, x0 + 14 * u, y1 - 2.6 * u), radius=0.9 * u, fill=rgb(base["accent"]))
    d.rounded_rectangle((x0 + 16 * u, y1 - 6 * u, x0 + 27 * u, y1 - 2.6 * u), radius=0.9 * u, fill=rgb(base["button"]))
    # floating dock
    dw, dh = 34 * u, 5.4 * u
    dx, dy = (100 * u - dw) / 2, h - dh - 2.2 * u
    d.rounded_rectangle((dx, dy, dx + dw, dy + dh), radius=2 * u, fill=rgb(base["panel"]) + (235,))
    for i in range(5):
        cx = dx + (3.4 + 6.6 * i) * u
        d.rounded_rectangle((cx, dy + 1.1 * u, cx + 3.2 * u, dy + 4.3 * u), radius=0.8 * u,
                            fill=rgb(base["accent"] if i == 0 else base["text_secondary"]))
    font = ImageFont.truetype(FONT, round(4.2 * u))
    d.text((x0, y1 + 2 * u), LABEL[theme], font=font, fill=rgb(base["text"]) if theme == "dark" else rgb(base["text"]))
    return im


def main():
    check, bad = "--check" in sys.argv, 0
    for theme in ("dark", "light"):
        for name, width, fmt, opts in (("preview.png", 600, "PNG", {"optimize": True}),
                                       ("fullscreenpreview.jpg", 1920, "JPEG", {"quality": 88, "optimize": True})):
            path = os.path.join(LNF, "org.heiss.%s.desktop/contents/previews" % theme, name)
            buf = io.BytesIO()
            draw(theme, width).save(buf, fmt, **opts)
            if check:
                same = os.path.exists(path) and open(path, "rb").read() == buf.getvalue()
                print("%s %s: %s" % (theme, name, "ok" if same else "DIFFERENT"))
                bad += not same
            else:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                open(path, "wb").write(buf.getvalue())
                print("wrote", path)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
