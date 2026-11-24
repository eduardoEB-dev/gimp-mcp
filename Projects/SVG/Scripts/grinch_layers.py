"""Split GrinchPIc.png into 4 aligned single-color SVG layers (red, white,
green, black) for multi-color 3D printing in Bambu Studio.

Keeps only the character (hat, face, hands, the ledge line). Drops snowflakes,
stars, "merry" text, grid and ruler. Layers come from one shared label map so
they tile without gaps/overlaps; all files share the same canvas so they
line up when loaded together.

usage: python grinch_layers.py <in.png> <out_dir> [--mm 100] [--debug dbg.png]
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
ap.add_argument("--name", default="Grinch")
ap.add_argument("--up", type=int, default=6, help="supersample factor")
ap.add_argument("--blur", type=float, default=0.8, help="smoothing radius in source px")
ap.add_argument("--min_black", type=int, default=600, help="black components smaller than this are dropped")
ap.add_argument("--mm", type=float, default=100.0, help="output width in mm")
ap.add_argument("--debug")
args = ap.parse_args()

rgb = np.asarray(Image.open(args.src).convert("RGB")).astype(float)
R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
lum = 0.299 * R + 0.587 * G + 0.114 * B

# soft per-class scores (0..1)
s_black = np.clip((110 - lum) / 70, 0, 1)
s_red = np.clip(((R - G) - 60) / 60, 0, 1) * (lum >= 40)
s_green = np.clip(((G - B) - 50) / 50, 0, 1) * np.clip((G - R + 40) / 40, 0, 1)
s_white = np.clip((lum - 200) / 40, 0, 1)

# --- character silhouette -------------------------------------------------
black = s_black > 0.5
lab, n = ndimage.label(black, structure=np.ones((3, 3)))
sizes = ndimage.sum(black, lab, range(1, n + 1))
keep_ids = 1 + np.where(sizes >= args.min_black)[0]
black_keep = np.isin(lab, keep_ids)
print("black comps kept:", sorted(int(s) for s in sizes[sizes >= args.min_black]))

# close the open bottom edge (hands run off the image) so fill_holes works
closed = black_keep.copy()
closed[-1, :] = True
sil = ndimage.binary_fill_holes(closed)
sil[-1, :] = black_keep[-1, :] | sil[-2, :]
# fill_holes with a closed bottom also captures the area under the ledge
# between the hands ("merry" zone): restrict to colored/black pixels there and
# drop components that don't touch the main black outline
col = (s_red > 0.5) | (s_green > 0.5) | (s_white > 0.5) | black_keep
sil &= col
lab2, n2 = ndimage.label(sil)
touch = np.unique(lab2[ndimage.binary_dilation(black_keep, iterations=2) & sil])
sil = np.isin(lab2, touch[touch > 0])
sil = ndimage.binary_fill_holes(sil)  # grid lines crossing white fur left pinholes

# --- label map --------------------------------------------------------------
H, W = black.shape
scores = np.stack([s_red, s_white, s_green, s_black])
ys, xs = np.where(sil)
pad = 4
y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, H)
x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, W)
scores = scores[:, y0:y1, x0:x1]
silc = sil[y0:y1, x0:x1].astype(float)
h, w = silc.shape
up = args.up


def upsm(a):
    im = Image.fromarray((a * 255).astype(np.uint8)).resize((w * up, h * up), Image.BICUBIC)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(args.blur * up))).astype(float) / 255


big = np.stack([upsm(s) for s in scores])
inside = upsm(silc) > 0.5
lbl = np.argmax(big, 0)
lbl[big.max(0) < 0.15] = 3  # ambiguous edge pixels -> outline
lbl[~inside] = -1

# remove tiny islands per class (merge into black)
for c in range(3):
    m = lbl == c
    l, k = ndimage.label(m)
    if k:
        sz = ndimage.sum(m, l, range(1, k + 1))
        lbl[np.isin(l, 1 + np.where(sz < (up * up * 6))[0])] = 3

if args.debug:
    pal = np.array([[210, 35, 37], [255, 255, 255], [160, 184, 53], [20, 20, 20], [120, 160, 200]], np.uint8)
    Image.fromarray(pal[np.where(lbl < 0, 4, lbl)]).save(args.debug)

# --- trace each layer -------------------------------------------------------
NAMES = [("Red", "#D2232A"), ("White", "#FFFFFF"), ("Green", "#9FB836"), ("Black", "#111111")]
BH, BW = lbl.shape
mmw, mmh = args.mm, args.mm * BH / BW
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
for c, (nm, hexc) in enumerate(NAMES):
    m = lbl == c
    # white/red/green trace slightly fat (0.5px) so seams overlap the black,
    # black traced exact -> no gaps between parts
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
    # invisible full-canvas rect is NOT used (Bambu would print it); alignment
    # relies on identical viewBox/size in every file
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
