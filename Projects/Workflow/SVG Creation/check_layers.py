"""Verify a layer set: render every color SVG, composite them, and report
problems that matter for printing.

Reports per layer: area, parts thinner than --min-width mm (nozzle can't
print them), islands smaller than --min-area mm2; across layers: overlap and
gaps between colors.

usage: python check_layers.py <layer_dir> [--png preview.png] [--px-per-mm 20]
       [--min-width 0.4] [--min-area 0.3]
Reads layers.json if present, else every *.svg except *_AllColors_preview.svg.
Handles absolute M/L/C/Q/Z paths (what this workflow writes).
"""
import argparse
import glob
import json
import os
import re
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layers_common as L  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("dir")
ap.add_argument("--png", help="composite preview (default <dir>/_check.png)")
ap.add_argument("--px-per-mm", type=float, default=20)
ap.add_argument("--min-width", type=float, default=0.4, help="mm; thinner parts get flagged")
ap.add_argument("--min-area", type=float, default=0.3, help="mm2; smaller islands get flagged")
args = ap.parse_args()

mf = os.path.join(args.dir, "layers.json")
if os.path.exists(mf):
    files = [os.path.join(args.dir, l["file"]) for l in json.load(open(mf, encoding="utf-8"))["layers"]]
else:
    files = [f for f in sorted(glob.glob(os.path.join(args.dir, "*.svg"))) if "_AllColors_preview" not in f]


def flatten(d):
    contours, poly, cur, start = [], [], (0, 0), (0, 0)
    for cmd, a in re.findall(r"([MLCQZ])([^MLCQZ]*)", d):
        n = [float(v) for v in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", a)]
        pts = list(zip(n[0::2], n[1::2]))
        if cmd == "M":
            if len(poly) > 2:
                contours.append(poly)
            cur = start = pts[0]
            poly = [cur] + pts[1:]
            cur = poly[-1]
        elif cmd == "L":
            poly += pts
            cur = pts[-1]
        elif cmd in "CQ":
            k = 3 if cmd == "C" else 2
            for i in range(0, len(pts), k):
                seg = [cur] + pts[i:i + k]
                for j in range(1, 13):
                    t, u = j / 12, 1 - j / 12
                    if k == 3:
                        poly.append(tuple(u**3 * seg[0][q] + 3 * u * u * t * seg[1][q] + 3 * u * t * t * seg[2][q] + t**3 * seg[3][q] for q in (0, 1)))
                    else:
                        poly.append(tuple(u * u * seg[0][q] + 2 * u * t * seg[1][q] + t * t * seg[2][q] for q in (0, 1)))
                cur = seg[-1]
        else:
            if len(poly) > 2:
                contours.append(poly)
            poly, cur = [], start
    if len(poly) > 2:
        contours.append(poly)
    return contours


masks, info, size = [], [], None
for f in files:
    svg = open(f, encoding="utf-8").read()
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
    wmm = float(re.search(r'width="([\d.]+)mm"', svg).group(1))
    hmm = float(re.search(r'height="([\d.]+)mm"', svg).group(1))
    if size is None:
        size = (vb, wmm, hmm)
    elif (vb, wmm, hmm) != size:
        print(f"!! {os.path.basename(f)}: canvas differs from first layer -> layers won't line up")
    sc = args.px_per_mm * wmm / vb[2]
    W, H = round(wmm * args.px_per_mm), round(hmm * args.px_per_mm)
    m = Image.new("1", (W, H), 0)
    for d in re.findall(r'\sd="([^"]+)"', svg):
        for c in flatten(d):   # even-odd via XOR
            t = Image.new("1", (W, H), 0)
            ImageDraw.Draw(t).polygon([((x - vb[0]) * sc, (y - vb[1]) * sc) for x, y in c], fill=1)
            m = ImageChops.logical_xor(m, t)
    hexc = re.search(r'fill="(#[0-9A-Fa-f]{6})"', svg)
    masks.append(np.asarray(m, bool))
    info.append((os.path.basename(f), hexc.group(1) if hexc else "#FF00FF"))

ppm = args.px_per_mm
cover = np.sum(masks, 0)
allm = cover > 0
print(f"canvas {size[1]:.1f} x {size[2]:.1f} mm, {len(masks)} layers")
r = max(1, round(args.min_width * ppm / 2))
yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
k = xx * xx + yy * yy <= r * r
problems = 0
for m, (fn, hexc) in zip(masks, info):
    area = m.sum() / ppm ** 2
    thin = m & ~ndimage.binary_opening(m, structure=k)
    lb, nb = ndimage.label(m)
    sz = ndimage.sum(m, lb, range(1, nb + 1)) / ppm ** 2 if nb else np.array([])
    small = int((sz < args.min_area).sum())
    thin_pct = 100 * thin.sum() / max(m.sum(), 1)
    flag = "  <-- check" if thin_pct > 3 or small else ""
    problems += bool(flag)
    print(f"  {fn:40s} {hexc}  {area:8.1f} mm2  {nb:4d} parts  thin<{args.min_width}mm {thin_pct:4.1f}%  "
          f"tiny<{args.min_area}mm2 {small}{flag}")
ov = (cover > 1).sum() / max(allm.sum(), 1) * 100
# enclosed empty areas: big ones are usually intended holes (letter counters),
# small ones are slivers between colors that will print as pinholes
holes = ndimage.binary_fill_holes(allm) & ~allm
hl, hn = ndimage.label(holes)
hs = ndimage.sum(holes, hl, range(1, hn + 1)) / ppm ** 2 if hn else np.array([])
sl = (hs >= 0.02) & (hs < 1.0)   # <0.02mm2 = trace seams, slicer closes them
gaps = np.isin(hl, 1 + np.where(sl)[0])
print(f"overlap between colors {ov:.2f}%   slivers (0.02-1mm2, magenta) {int(sl.sum())}"
      f" = {gaps.sum() / ppm ** 2:.2f} mm2   holes {int((hs >= 1).sum())} (intended?)")
print("OK" if not problems and ov < 1 and gaps.sum() / ppm ** 2 < 1 else "review flagged items")

out = np.zeros(allm.shape + (3,), np.uint8)
out[:] = (125, 160, 200)   # stand-in background so white layers show
for m, (_, hexc) in zip(masks, info):
    out[m] = L.hex2rgb(hexc)
out[gaps] = (255, 0, 255)
png = args.png or os.path.join(args.dir, "_check.png")
im = Image.fromarray(out)
im.thumbnail((1600, 1600))
im.save(png)
print("preview ->", png)
