# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy"]
# ///
"""Animated GIF of the SharePoint page: a cursor visits each region and the
map switches to that region's highlight image while it hovers.

Run: uv run RegionMap/Scrips/make_hover_gif.py
"""

import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SHOT = ROOT / "WPImages" / "FullPageWPView_anon.png"
MAPS = ROOT / "Regions Example"
COORDS = ROOT / "Coordinates" / "Coordinates.txt"
OUT = ROOT / "WPImages" / "RegionsHover.gif"

# Where the 1610x977 map sits in the screenshot (fitted by pixel comparison).
MAP_POS = (292, 236)
MAP_SIZE = (1174, 712)
SCALE = MAP_SIZE[0] / 1610

# Hover targets in original map pixels, visited in this order.
TOUR = [
    ("West", (330, 400)),
    ("Midwest", (900, 420)),
    ("Northeast", (1370, 320)),
    ("Southeast", (1150, 760)),
    ("Southwest", (560, 760)),
]
START = (1560, 960)       # cursor start/end, screenshot pixels
MOVE_FRAMES, HOLD_FRAMES = 14, 22
FRAME_MS = 40

ARROW = [(0, 0), (0, 17), (4, 13), (7, 20), (10, 19), (7, 12), (12, 12)]


def to_shot(pt):
    return (MAP_POS[0] + pt[0] * SCALE, MAP_POS[1] + pt[1] * SCALE)


def load_polygons():
    polys = {}
    for name, coords in re.findall(r"US_(\w+):\s*Coordinates:\s*([\d,]+)", COORDS.read_text()):
        pts = np.array(list(map(int, coords.split(",")))).reshape(-1, 2)
        polys[name] = [to_shot(p) for p in pts]
    return polys


def region_at(polys, pt):
    for name, poly in polys.items():
        # Point-in-polygon via ray casting.
        x, y = pt
        inside = False
        for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
        if inside:
            return name
    return None


def render_state(base, map_file):
    frame = base.copy()
    frame.paste((255, 255, 255, 255), (*MAP_POS, MAP_POS[0] + MAP_SIZE[0], MAP_POS[1] + MAP_SIZE[1]))
    m = Image.open(map_file).convert("RGBA").resize(MAP_SIZE, Image.LANCZOS)
    frame.alpha_composite(m, MAP_POS)
    return frame


def draw_cursor(frame, pos):
    x, y = round(pos[0]), round(pos[1])
    d = ImageDraw.Draw(frame)
    d.polygon([(x + px, y + py) for px, py in ARROW], fill="white", outline="black", width=1)


def ease(t):
    return t * t * (3 - 2 * t)


def main():
    base = Image.open(SHOT).convert("RGBA")
    polys = load_polygons()
    states = {None: render_state(base, MAPS / "US_RegionsMain.png")}
    for name in polys:
        states[name] = render_state(base, MAPS / f"US_{name}.png")

    # One shared palette for every frame so colors don't flicker.
    sheet = Image.new("RGB", (base.width, base.height * len(states)))
    for i, s in enumerate(states.values()):
        sheet.paste(s.convert("RGB"), (0, i * base.height))
    palette = sheet.quantize(256, method=Image.Quantize.MEDIANCUT)

    path = [START] + [to_shot(p) for _, p in TOUR] + [START]
    frames = []
    for a, b in zip(path, path[1:]):
        for i in range(1, MOVE_FRAMES + 1):
            t = ease(i / MOVE_FRAMES)
            frames.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        frames += [b] * HOLD_FRAMES

    out = []
    for pos in frames:
        f = states[region_at(polys, pos)].copy()
        draw_cursor(f, pos)
        out.append(f.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE))
    out[0].save(OUT, save_all=True, append_images=out[1:], duration=FRAME_MS, loop=0, optimize=False)
    print(f"wrote {OUT} ({len(out)} frames, {OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
