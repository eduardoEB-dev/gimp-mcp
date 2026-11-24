"""Split "Snoopy's Grinchy Christmas Surprise.png" into aligned single-color SVG
layers (red, white, green, yellow, black) for multi-color printing in Bambu
Studio (cup wrap / emboss).

Keeps only the character (hat, Grinch hood, Snoopy, gift, feet). Drops sky,
snow, snow lines, tree and doghouse. Layers come from one shared label map so
they tile without gaps/overlaps; all files share the same canvas so they
line up when loaded together.

usage: python snoopy_layers.py <in.png> <out_dir> [--mm 70] [--debug dbg.png]
       [--no-yellow]  (merge yellow eyes into white -> 4 colors, one AMS)
"""
import argparse
import os
import re
import tempfile

import numpy as np
import vtracer
from PIL import Image, ImageFilter
from scipy import ndimage

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out_dir")
ap.add_argument("--name", default="Snoopy")
ap.add_argument("--up", type=int, default=5, help="supersample factor")
ap.add_argument("--blur", type=float, default=0.8, help="smoothing radius in source px")
ap.add_argument("--open", type=int, default=5, help="opening radius that cuts thin background lines off the outline")
ap.add_argument("--mm", type=float, default=70.0, help="output height in mm")
ap.add_argument("--no-yellow", action="store_true")
ap.add_argument("--debug")
args = ap.parse_args()

rgb = np.asarray(Image.open(args.src).convert("RGB")).astype(float)
R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
lum = 0.299 * R + 0.587 * G + 0.114 * B

# soft per-class scores (0..1)
s_black = np.clip((110 - lum) / 70, 0, 1)
s_red = np.clip(((R - G) - 60) / 60, 0, 1) * (lum >= 40)
s_yellow = np.clip(((R + G) / 2 - B - 120) / 40, 0, 1) * np.clip((R - 200) / 30, 0, 1)
s_green = np.clip(((G - B) - 50) / 50, 0, 1) * np.clip((G - R + 40) / 40, 0, 1) * (1 - s_yellow)
s_white = np.clip((lum - 200) / 40, 0, 1) * np.clip((40 - (B - R)) / 30, 0, 1)  # not sky blue

# --- character silhouette -------------------------------------------------
# background = everything reachable from the image border without crossing a
# black line; the character is closed by its outline, so it stays unreached
black = s_black > 0.5
H, W = black.shape
lab, _ = ndimage.label(~black)
border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
bg = np.isin(lab, border[border > 0])
fg = ~bg
# cut thin strokes (snow lines, tree, doghouse lines) off with an opening,
# keep the biggest blob (the character), then restore its own outline
yy, xx = np.mgrid[-args.open:args.open + 1, -args.open:args.open + 1]
disk = xx * xx + yy * yy <= args.open * args.open
core = ndimage.binary_opening(fg, structure=disk)
l, k = ndimage.label(core)
sz = ndimage.sum(core, l, range(1, k + 1))
core = l == 1 + int(np.argmax(sz))
sil = ndimage.binary_fill_holes(ndimage.binary_dilation(core, structure=disk, iterations=1) & fg)
print("silhouette bbox:", ndimage.find_objects(sil.astype(int))[0])

# --- label map --------------------------------------------------------------
CLASSES = [("Red", "#D2232A", s_red), ("White", "#FFFFFF", s_white),
           ("Green", "#9FC52A", s_green), ("Yellow", "#F5E11E", s_yellow),
           ("Black", "#111111", s_black)]
if args.no_yellow:
    CLASSES[1] = ("White", "#FFFFFF", np.maximum(s_white, s_yellow))
    del CLASSES[3]
BLACK = len(CLASSES) - 1

ys, xs = np.where(sil)
pad = 4
y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, H)
x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, W)
scores = np.stack([c[2] for c in CLASSES])[:, y0:y1, x0:x1]
silc = sil[y0:y1, x0:x1].astype(float)
h, w = silc.shape
up = args.up


def upsm(a):
    im = Image.fromarray((a * 255).astype(np.uint8)).resize((w * up, h * up), Image.BICUBIC)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(args.blur * up))).astype(float) / 255


big = np.stack([upsm(s) for s in scores])
inside = upsm(silc) > 0.5
lbl = np.argmax(big, 0)
lbl[big.max(0) < 0.15] = BLACK  # ambiguous edge pixels -> outline
lbl[~inside] = -1

# remove tiny islands per class (merge into black)
for c in range(BLACK):
    m = lbl == c
    l, k = ndimage.label(m)
    if k:
        sz = ndimage.sum(m, l, range(1, k + 1))
        lbl[np.isin(l, 1 + np.where(sz < (up * up * 6))[0])] = BLACK

if args.debug:
    pal = np.array([[int(c[1][i:i + 2], 16) for i in (1, 3, 5)] for c in CLASSES] + [[120, 160, 200]], np.uint8)
    Image.fromarray(pal[np.where(lbl < 0, len(CLASSES), lbl)]).save(args.debug)

# --- trace each layer -------------------------------------------------------
BH, BW = lbl.shape
mmh, mmw = args.mm, args.mm * BW / BH
os.makedirs(args.out_dir, exist_ok=True)
tmp = tempfile.mkdtemp()


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


combined = []
for c, (nm, hexc, _) in enumerate(CLASSES):
    m = lbl == c
    img = Image.fromarray(np.where(m, 0, 255).astype(np.uint8)).convert("RGB")
    mp, sp = os.path.join(tmp, f"{nm}.png"), os.path.join(tmp, f"{nm}.svg")
    img.save(mp)
    vtracer.convert_image_to_svg_py(mp, sp, colormode="binary", mode="spline",
                                    filter_speckle=up * up, corner_threshold=80,
                                    length_threshold=6.0, splice_threshold=45,
                                    path_precision=1)
    paths = [bake(p) for p in re.findall(r"<path[^>]*/>", open(sp, encoding="utf-8").read())]
    body = "".join(f'    <path d="{d}"/>\n' for d in paths)
    combined.append(f'  <g id="{nm}" fill="{hexc}" fill-rule="evenodd">\n{body}  </g>\n')
    # no full-canvas rect (Bambu would print it); alignment relies on
    # identical viewBox/size in every file
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{mmw:.2f}mm" height="{mmh:.2f}mm" '
           f'viewBox="0 0 {BW} {BH}">\n  <title>{args.name} {nm}</title>\n'
           f'  <g fill="{hexc}" fill-rule="evenodd">\n{body}  </g>\n</svg>\n')
    out = os.path.join(args.out_dir, f"{args.name}_{nm}.svg")
    open(out, "w", encoding="utf-8").write(svg)
    print(f"{nm}: {len(paths)} paths -> {out}")

open(os.path.join(args.out_dir, f"{args.name}_AllColors_preview.svg"), "w", encoding="utf-8").write(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{mmw:.2f}mm" height="{mmh:.2f}mm" viewBox="0 0 {BW} {BH}">\n'
    + "".join(combined) + "</svg>\n")
print(f"canvas {BW}x{BH} -> {mmw:.1f}x{mmh:.1f}mm")
