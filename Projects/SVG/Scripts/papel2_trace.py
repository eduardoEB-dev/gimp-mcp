"""Trace papel2.png into a rectangular single-color papel picado SVG.

Outer scalloped/zigzag edges replaced by a straight rectangle; only enclosed
cut-outs kept. Output size = 5x the cropped banner.

usage: python papel2_trace.py <in.png> <out.svg> [--color #C8102E]
"""
import argparse
import os
import re
import tempfile

import numpy as np
import vtracer
from PIL import Image, ImageDraw, ImageFilter

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out")
ap.add_argument("--color", default="#D2232A")
ap.add_argument("--thresh", type=int, default=75, help="R-G diff that counts as paper")
ap.add_argument("--up", type=int, default=3, help="supersample factor before tracing")
ap.add_argument("--scale", type=float, default=5.0, help="output size vs cropped source")
args = ap.parse_args()

rgb = np.asarray(Image.open(args.src).convert("RGB")).astype(int)
paper = (rgb[..., 0] - rgb[..., 1]) > args.thresh

# banner body bbox: rows/cols with substantial paper (ignores thin hanging rod)
rows = np.where(paper.sum(1) > paper.shape[1] * 0.3)[0]
cols = np.where(paper.sum(0) > paper.shape[0] * 0.3)[0]
x0, x1, y0, y1 = cols.min(), cols.max() + 1, rows.min(), rows.max() + 1
# extend bottom to lowest scallop so no cuts are lost
y1 = max(y1, np.where(paper[:, x0:x1].any(1))[0].max() + 1)

# holes = non-paper regions not connected to outside background
lab = Image.fromarray(np.where(paper, 255, 0).astype(np.uint8))
lab = lab.crop((x0 - 2, y0 - 2, x1 + 2, y1 + 2))
pad = Image.new("L", (lab.width + 4, lab.height + 4), 0)
pad.paste(lab, (2, 2))
ImageDraw.floodfill(pad, (0, 0), 128)
a = np.asarray(pad)[4:-4, 4:-4]  # back to rect x0..x1, y0..y1
holes = a == 0

# rectangle paper minus holes; drop specks (e.g. watermark noise)
keep = Image.fromarray(np.where(holes, 0, 255).astype(np.uint8))
keep = keep.filter(ImageFilter.MedianFilter(3))

# supersample + smooth for clean curves
w, h = keep.size
big = keep.resize((w * args.up, h * args.up), Image.LANCZOS).filter(ImageFilter.GaussianBlur(args.up * 0.6))
big = big.point(lambda v: 255 if v > 127 else 0)
# vtracer binary traces black shapes -> invert so holes are black? trace paper as black
big = Image.eval(big, lambda v: 255 - v)

tmp = tempfile.mkdtemp()
mpath, spath = os.path.join(tmp, "mask.png"), os.path.join(tmp, "trace.svg")
big.convert("RGB").save(mpath)
vtracer.convert_image_to_svg_py(mpath, spath, colormode="binary", mode="spline",
                                filter_speckle=8, corner_threshold=60,
                                length_threshold=4.0, splice_threshold=45,
                                path_precision=2)

svg = open(spath, encoding="utf-8").read()
paths = re.findall(r"<path[^>]*/>", svg)
body = []
for p in paths:
    p = re.sub(r'fill="[^"]*"', "", p)
    body.append(p.replace("<path", "<path", 1))

W, H = big.size
ow, oh = round(w * args.scale), round(h * args.scale)
out = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ow}" height="{oh}" viewBox="0 0 {W} {H}">\n'
       f'  <title>Papel picado - calaveras (rect)</title>\n'
       f'  <g fill="{args.color}" fill-rule="evenodd">\n    ' + "\n    ".join(body) + "\n  </g>\n</svg>\n")
os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
open(args.out, "w", encoding="utf-8").write(out)
print(f"crop {w}x{h} at ({x0},{y0}); out {ow}x{oh}; {len(body)} paths -> {os.path.abspath(args.out)}")
