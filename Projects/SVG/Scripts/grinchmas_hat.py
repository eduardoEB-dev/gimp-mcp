"""Trace "GRINCHMAS" + Santa hat (movie-style title) into 4 aligned SVG layers:
red (hat), white (hat trim/pom), green (letters), black (outline around all).

Reference has no black; outline is added as a sticker-style border. Layers
come from one shared label map, so they tile without gaps/overlaps, and all
files share one canvas so they line up when loaded together in Bambu Studio.

usage: python grinchmas_hat.py <in.png> <out_dir> [--outline 2.5] [--mm 100] [--debug dbg.png]
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
ap.add_argument("--name", default="GrinchmasHat")
ap.add_argument("--box", default="25,18,325,90", help="crop x0,y0,x1,y1 (drops 'merry' + fur)")
ap.add_argument("--up", type=int, default=10, help="supersample factor")
ap.add_argument("--blur", type=float, default=0.9, help="smoothing radius in source px")
ap.add_argument("--outline", type=float, default=2.5, help="black border width in source px")
ap.add_argument("--mm", type=float, default=100.0, help="output width in mm")
ap.add_argument("--no_hat", action="store_true", help="letters only (drops red/white hat)")
ap.add_argument("--complete_g", action="store_true", help="rebuild G top-left hidden under the hat")
ap.add_argument("--white_only", action="store_true", help="black outlines only the white hat trim")
ap.add_argument("--debug")
args = ap.parse_args()

bx0, by0, bx1, by1 = map(int, args.box.split(","))
rgb = np.asarray(Image.open(args.src).convert("RGB").crop((bx0, by0, bx1, by1))).astype(float)
R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]

s_red = np.clip(((R - G) - 50) / 60, 0, 1)
s_white = np.clip((np.minimum(np.minimum(R, G), B) - 150) / 50, 0, 1)
s_lime = np.clip((R - 150) / 40, 0, 1) * np.clip((G - 185) / 20, 0, 1) * np.clip((140 - B) / 30, 0, 1)

# white only belongs to the hat (left end); keep blobs touching red
hat_zone = np.zeros_like(s_white, bool)
hat_zone[:, :60] = True
s_white *= hat_zone


def keep_big(score, min_px):
    m = score > 0.5
    lab, n = ndimage.label(m)
    if not n:
        return score
    sz = ndimage.sum(m, lab, range(1, n + 1))
    ok = np.isin(lab, 1 + np.where(sz >= min_px)[0])
    return score * ndimage.binary_dilation(ok, iterations=2)


s_red, s_white, s_lime = keep_big(s_red, 20), keep_big(s_white, 6), keep_big(s_lime, 40)
if args.no_hat:
    s_red, s_white = s_red * 0, s_white * 0

# pad so outline fits
pad = max(9, int(args.outline * 2) + 4)  # fixed 9 keeps canvas identical across versions
s_red, s_white, s_lime = (np.pad(s, pad) for s in (s_red, s_white, s_lime))
h, w = s_red.shape
up = args.up


def upsm(a, blur):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((w * up, h * up), Image.BICUBIC)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(blur * up))).astype(float) / 255


big = np.stack([upsm(s, args.blur) for s in (s_red, s_white, s_lime)])
if args.complete_g:
    # G's top-left arc was under the hat: add an elliptical ring segment matching
    # the G's left-side stroke (~120px @ up=10) and the cap height of R/I
    k = up / 10
    yy, xx = np.mgrid[:big.shape[1], :big.shape[2]] / k
    outer = ((xx - 560) / 225) ** 2 + ((yy - 470) / 270) ** 2 <= 1
    inner = ((xx - 560) / 95) ** 2 + ((yy - 480) / 140) ** 2 <= 1
    fill = outer & ~inner & (yy <= 470) & (xx <= 630) & ~((xx > 560) & (yy > 330))
    fill = np.asarray(Image.fromarray((fill * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(args.blur * up))).astype(float) / 255
    big[2] = np.maximum(big[2], fill)
fg = big.max(0) > 0.5
lbl = np.full(fg.shape, -1)
lbl[fg] = np.argmax(big, 0)[fg]

# black = smooth rounded border around everything (also fills small counters/gaps),
# or with --white_only just a ring around the hat's white trim/pom (cut into red/green)
src_mask = (lbl == 1) if args.white_only else fg
dist = ndimage.distance_transform_edt(~src_mask)
border = Image.fromarray(((dist <= args.outline * up) * 255).astype(np.uint8))
border = np.asarray(border.filter(ImageFilter.GaussianBlur(args.outline * up * 0.4))) > 127
lbl[border & ~src_mask] = 3

# drop tiny islands of red/white/green into black
for c in range(3):
    m = lbl == c
    l, k = ndimage.label(m)
    if k:
        sz = ndimage.sum(m, l, range(1, k + 1))
        lbl[np.isin(l, 1 + np.where(sz < up * up * 3)[0])] = 3

if args.debug:
    pal = np.array([[220, 40, 40], [255, 255, 255], [190, 215, 60], [20, 20, 20], [120, 160, 200]], np.uint8)
    Image.fromarray(pal[np.where(lbl < 0, 4, lbl)]).save(args.debug)

NAMES = [("Red", "#D2232A"), ("White", "#FFFFFF"), ("Green", "#B5CF3A"), ("Black", "#111111")]
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


head = f'<svg xmlns="http://www.w3.org/2000/svg" width="{mmw:.2f}mm" height="{mmh:.2f}mm" viewBox="0 0 {BW} {BH}">\n'
combined = []
for c, (nm, hexc) in enumerate(NAMES):
    img = Image.fromarray(np.where(lbl == c, 0, 255).astype(np.uint8)).convert("RGB")
    mp, sp = os.path.join(tmp, f"{nm}.png"), os.path.join(tmp, f"{nm}.svg")
    img.save(mp)
    vtracer.convert_image_to_svg_py(mp, sp, colormode="binary", mode="spline",
                                    filter_speckle=up * 2, corner_threshold=80,
                                    length_threshold=8.0, splice_threshold=45, path_precision=1)
    paths = [bake(p) for p in re.findall(r"<path[^>]*/>", open(sp, encoding="utf-8").read())]
    if (lbl == c).sum() < up * up * 20 or not paths:
        continue  # empty layer (e.g. --no_hat) -> no file
    grp = (f'  <g id="{nm}" fill="{hexc}" fill-rule="evenodd">\n'
           + "".join(f'    <path d="{d}"/>\n' for d in paths) + "  </g>\n")
    combined.append(grp)
    out = os.path.join(args.out_dir, f"{args.name}_{nm}.svg")
    open(out, "w", encoding="utf-8").write(head + f"  <title>Grinchmas {nm}</title>\n" + grp + "</svg>\n")
    print(f"{nm}: {len(paths)} paths -> {out}")

open(os.path.join(args.out_dir, f"{args.name}_AllColors_preview.svg"), "w", encoding="utf-8").write(
    head + "  <title>Grinchmas</title>\n" + "".join(combined) + "</svg>\n")
print(f"canvas {BW}x{BH} -> {mmw:.1f}x{mmh:.1f}mm")
