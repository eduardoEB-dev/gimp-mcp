"""Trace dark line art (black on light bg) into a single-color SVG.

Light areas become transparent. Output size = scale x cropped source.

usage: python trace_lineart.py <in.png> <out.svg> [--color #000] [--scale 5]
"""
import argparse
import os
import re
import tempfile

import numpy as np
import vtracer
from PIL import Image, ImageFilter

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out")
ap.add_argument("--color", default="#000000")
ap.add_argument("--thresh", type=int, default=128, help="luminance below this = ink")
ap.add_argument("--up", type=int, default=3, help="supersample factor before tracing")
ap.add_argument("--scale", type=float, default=5.0, help="output size vs cropped source")
ap.add_argument("--margin", type=int, default=20, help="px kept around ink when cropping")
args = ap.parse_args()

gray = Image.open(args.src).convert("L")
ink = np.asarray(gray) < args.thresh
ys, xs = np.where(ink)
m = args.margin
x0, y0 = max(xs.min() - m, 0), max(ys.min() - m, 0)
x1, y1 = min(xs.max() + 1 + m, gray.width), min(ys.max() + 1 + m, gray.height)
gray = gray.crop((x0, y0, x1, y1))

# supersample + smooth antialiased edges, then threshold
w, h = gray.size
big = gray.resize((w * args.up, h * args.up), Image.LANCZOS).filter(ImageFilter.GaussianBlur(args.up * 0.5))
big = big.point(lambda v: 0 if v < args.thresh else 255)

tmp = tempfile.mkdtemp()
mpath, spath = os.path.join(tmp, "mask.png"), os.path.join(tmp, "trace.svg")
big.convert("RGB").save(mpath)
vtracer.convert_image_to_svg_py(mpath, spath, colormode="binary", mode="spline",
                                filter_speckle=8, corner_threshold=60,
                                length_threshold=4.0, splice_threshold=45,
                                path_precision=2)

paths = [re.sub(r'fill="[^"]*"', "", p) for p in re.findall(r"<path[^>]*/>", open(spath, encoding="utf-8").read())]

W, H = big.size
ow, oh = round(w * args.scale), round(h * args.scale)
title = os.path.splitext(os.path.basename(args.out))[0]
out = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ow}" height="{oh}" viewBox="0 0 {W} {H}">\n'
       f'  <title>{title}</title>\n'
       f'  <g fill="{args.color}" fill-rule="evenodd">\n    ' + "\n    ".join(paths) + "\n  </g>\n</svg>\n")
os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
open(args.out, "w", encoding="utf-8").write(out)
print(f"crop {w}x{h} at ({x0},{y0}); out {ow}x{oh}; {len(paths)} paths -> {os.path.abspath(args.out)}")
