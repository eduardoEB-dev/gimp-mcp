"""Build "YOU'RE A / MEAN ONE / MR. / GRINCH" in the hand-drawn mug lettering
from SHY.png (same style + smoothing as SantaHatesYou_v4.svg).

Letters present on the mug (Y O U E A N H) are cut straight from it; missing
ones are assembled from strokes of those letters:
  I = H left stem, C = O with right side opened, G = C + bar + spur,
  M = left half of N + its mirror, R = stem + half-height O bowl + A leg,
  ' = short Y arm, . = blob.

usage: python mean_one_svg.py <SHY.png> <out.svg> [--sheet glyphs.png] [--blur 1.4]
       python mean_one_svg.py <SHY.png> MerryGrinchmas.svg --lines "MERRY|GRINCHMAS" \
           --line_colors "Red:#D2232A|Green:#4CA341" --title "Merry Grinchmas"
"""
import argparse
import os
import re
import tempfile

import numpy as np
import vtracer
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out")
ap.add_argument("--color", default="#D2232A")
ap.add_argument("--up", type=int, default=8)
ap.add_argument("--blur", type=float, default=1.4)
ap.add_argument("--mm", type=float, default=80.0)
ap.add_argument("--sheet", help="also save raster preview of the layout")
ap.add_argument("--lines", default="YOU'RE A|MEAN ONE|MR.|GRINCH", help="text lines, | separated")
ap.add_argument("--line_colors", help="per-line Name:#hex, | separated -> one SVG per color "
                "(<out>_<Name>.svg, shared canvas for Bambu alignment)")
ap.add_argument("--title", default="You're a Mean One Mr. Grinch")
args = ap.parse_args()

x0, y0, x1, y1 = 150, 360, 350, 575
rgb = np.asarray(Image.open(args.src).convert("RGB").crop((x0, y0, x1, y1))).astype(int)
rd = np.minimum(rgb[..., 0] - rgb[..., 1], rgb[..., 0] - rgb[..., 2])
SOFT = np.clip((rd - 15) / 115, 0, 1)
LAB, _ = ndimage.label(ndimage.binary_dilation(SOFT > 0.5))


def cut(xa, xb, ya, yb, comp=None):
    """soft crop; comp limits to one connected component (no neighbor bleed)"""
    g = SOFT[ya:yb, xa:xb].copy()
    if comp is not None:
        g *= LAB[ya:yb, xa:xb] == comp
    return trim(g)


def trim(g):
    ys, xs = np.where(g > 0.05)
    return g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def place(canvas, g, x, y):
    h, w = g.shape
    canvas[y:y + h, x:x + w] = np.maximum(canvas[y:y + h, x:x + w], g)


def resize(g, sx, sy):
    h, w = g.shape
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((max(1, round(w * sx)), max(1, round(h * sy))), Image.BICUBIC)
    return np.asarray(im).astype(float) / 255


def comp_at(x, y):
    return LAB[y, x]


# --- glyphs straight off the mug -------------------------------------------
Y = cut(46, 83, 149, 197, comp_at(52, 158))
O = cut(81, 112, 152, 202, comp_at(90, 175))
U = cut(112, 150, 152, 202, comp_at(140, 170))
A = cut(45, 84, 87, 136, comp_at(62, 125))
H = cut(9, 49, 83, 139, comp_at(15, 110))
E = cut(120, 152, 84, 140, comp_at(125, 120))
N = cut(84, 111, 16, 72, comp_at(90, 50))
S = cut(149, 192, 84, 138, comp_at(160, 95))

# --- assembled glyphs ------------------------------------------------------
I = trim(H[:, :H.shape[1] * 34 // 100])          # left stem of H

oh, ow = O.shape
yy, xx = np.mgrid[:oh, :ow]
ang = np.degrees(np.arctan2(-(yy - oh / 2) * (ow / oh), xx - ow / 2))
C = O * ~((np.abs(ang) < 38) & (xx > ow * 0.5))  # open right side
C = trim(C)

# missing letters drawn as brush strokes at the mug's stroke weight (~9px @ 50px cap)
SW = 9.5


def strokes(w, h, polys, sw=SW):
    k = 4
    im = Image.new("L", (int(w * k), int(h * k)), 0)
    dr = ImageDraw.Draw(im)
    for pts in polys:
        P = [(x * k, y * k) for x, y in pts]
        dr.line(P, fill=255, width=int(sw * k), joint="curve")
        for x, y in (P[0], P[-1]):
            r = sw * k / 2
            dr.ellipse((x - r, y - r, x + r, y + r), fill=255)
    im = im.resize((int(w), int(h)), Image.LANCZOS)
    return trim(np.asarray(im).astype(float) / 255)


def arc(cx, cy, rx, ry, a0, a1, n=24):
    t = np.radians(np.linspace(a0, a1, n))
    return list(zip(cx + rx * np.cos(t), cy - ry * np.sin(t)))


g = 5  # margin so round caps fit
M = strokes(54, 60, [[(g + 1, g + 48), (g + 4, g + 1), (g + 22, g + 33), (g + 39, g + 1), (g + 42, g + 48)]])
R = strokes(42, 60, [[(g + 3, g + 49), (g + 3, g + 1)],
                     [(g + 3, g + 2)] + arc(g + 14, g + 13, 15, 11, 90, -90) + [(g + 3, g + 24)],
                     [(g + 13, g + 25), (g + 30, g + 49)]])
G = strokes(46, 60, [arc(g + 18, g + 25, 18, 24, 45, 360),
                     [(g + 21, g + 27), (g + 36, g + 27), (g + 36, g + 44)]])
APOS = strokes(16, 22, [[(g + 4, g), (g + 2, g + 11)]], sw=7.5)
DOT = strokes(18, 18, [[(g + 3, g + 3), (g + 3.5, g + 3.5)]], sw=10)

GLYPHS = {"Y": Y, "O": O, "U": U, "A": A, "H": H, "E": E, "N": N, "I": I, "C": C,
          "G": G, "M": M, "S": S, "R": R, "'": APOS, ".": DOT}

# --- layout ----------------------------------------------------------------
LINES = args.lines.split("|")
GAP, SPACE, LEAD, CAP = 2, 14, 10, 50


def line_img(text):
    parts, x = [], 0
    for ch in text:
        if ch == " ":
            x += SPACE
            continue
        g = GLYPHS[ch]
        if ch not in "'.":   # normalise cap height, keep the hand-drawn jitter
            s = CAP / g.shape[0]
            g = resize(g, s, s)
        yoff = 0 if ch != "." else CAP - g.shape[0]
        parts.append((g, x, yoff))
        x += g.shape[1] + GAP
    img = np.zeros((CAP + 4, x + 4))
    for g, gx, gy in parts:
        place(img, g, gx + 2, gy + 2)
    return img


rows = [line_img(t) for t in LINES]
if args.line_colors:
    COLS = [tuple(c.split(":")) for c in args.line_colors.split("|")]
    assert len(COLS) == len(LINES), "need one Name:#hex per line"
else:
    COLS = [("", args.color)] * len(LINES)
Wd = max(r.shape[1] for r in rows) + 12
Hd = sum(r.shape[0] for r in rows) + LEAD * (len(rows) - 1) + 12
pages = {}  # color name -> (hex, page)
y = 6
for r, (nm, hexc) in zip(rows, COLS):
    pg = pages.setdefault(nm, (hexc, np.zeros((Hd, Wd))))[1]
    place(pg, r, (Wd - r.shape[1]) // 2, y)
    y += r.shape[0] + LEAD

if args.sheet:
    allp = np.maximum.reduce([p for _, p in pages.values()])
    Image.fromarray(((1 - allp) * 255).astype(np.uint8)).resize((Wd * 4, Hd * 4), Image.NEAREST).save(args.sheet)


# --- smooth + trace (same as shy_trace.py) ---------------------------------
def bake(p):
    t = re.search(r'translate\(([-\d.]+),([-\d.]+)\)', p)
    dx, dy = (float(t.group(1)), float(t.group(2))) if t else (0, 0)
    d = re.search(r'\sd="([^"]+)"', p).group(1)
    out, i = [], 0
    for tok in re.findall(r"[A-Za-z]|-?\d*\.?\d+(?:e-?\d+)?", d):
        if tok.isalpha():
            out.append(tok); i = 0
        else:
            out.append(f"{float(tok) + (dx if i % 2 == 0 else dy):.1f}"); i += 1
    return " ".join(out)


def trace(page):
    up = args.up
    m = Image.fromarray((page * 255).astype(np.uint8))
    big = m.resize((Wd * up, Hd * up), Image.BICUBIC).filter(ImageFilter.GaussianBlur(args.blur * up))
    big = big.point(lambda v: 0 if v > 127 else 255)
    tmp = tempfile.mkdtemp()
    mpath, spath = os.path.join(tmp, "mask.png"), os.path.join(tmp, "trace.svg")
    big.convert("RGB").save(mpath)
    vtracer.convert_image_to_svg_py(mpath, spath, colormode="binary", mode="spline",
                                    filter_speckle=64, corner_threshold=100,
                                    length_threshold=10.0, splice_threshold=45, path_precision=1)
    return [bake(p) for p in re.findall(r"<path[^>]*/>", open(spath, encoding="utf-8").read())]


# identical width/height/viewBox in every file so parts line up when loaded together
W, H_ = Wd * args.up, Hd * args.up
mmh = args.mm * H_ / W
head = f'<svg xmlns="http://www.w3.org/2000/svg" width="{args.mm:.2f}mm" height="{mmh:.2f}mm" viewBox="0 0 {W} {H_}">\n'
os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
stem = os.path.splitext(args.out)[0]
groups = []
for nm, (hexc, pg) in pages.items():
    paths = trace(pg)
    grp = (f'  <g fill="{hexc}" fill-rule="evenodd">\n'
           + "".join(f'    <path d="{d}"/>\n' for d in paths) + "  </g>\n")
    groups.append(grp)
    out = f"{stem}_{nm}.svg" if nm else args.out
    title = f"{args.title} {nm}".strip()
    open(out, "w", encoding="utf-8").write(head + f"  <title>{title}</title>\n" + grp + "</svg>\n")
    print(f"{len(paths)} paths, {args.mm:.1f}x{mmh:.1f}mm -> {os.path.abspath(out)}")
if len(pages) > 1:
    out = f"{stem}_AllColors_preview.svg"
    open(out, "w", encoding="utf-8").write(head + f"  <title>{args.title}</title>\n" + "".join(groups) + "</svg>\n")
    print("preview ->", os.path.abspath(out))
