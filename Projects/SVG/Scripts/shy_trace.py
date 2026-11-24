"""Trace red "SANTA HATES YOU" lettering off the Grinch mug in SHY.png into a
smooth single-color SVG for 3D printing (Bambu Studio). Heavy blur before
tracing removes brush texture so only the overall letter shapes remain.

usage: python shy_trace.py <in.png> <out.svg> [--color #D2232A] [--blur 2.2]
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
ap.add_argument("out")
ap.add_argument("--color", default="#D2232A")
ap.add_argument("--box", default="150,360,350,575", help="crop x0,y0,x1,y1 (mug face)")
ap.add_argument("--up", type=int, default=8, help="supersample factor before tracing")
ap.add_argument("--blur", type=float, default=2.2, help="smoothing radius in source px")
ap.add_argument("--grow", type=float, default=0.0, help="bias threshold (+ = fatter strokes)")
ap.add_argument("--mm", type=float, default=80.0, help="output width in mm")
args = ap.parse_args()

x0, y0, x1, y1 = map(int, args.box.split(","))
rgb = np.asarray(Image.open(args.src).convert("RGB").crop((x0, y0, x1, y1))).astype(int)
# continuous "redness" keeps anti-aliased edge info -> sub-pixel smooth outlines
rd = np.minimum(rgb[..., 0] - rgb[..., 1], rgb[..., 0] - rgb[..., 2])
soft = np.clip((rd - 15) / (130 - 15), 0, 1)
red = soft > 0.5

# drop specks
lab, n = ndimage.label(ndimage.binary_dilation(red))
sizes = ndimage.sum(red, lab, range(1, n + 1))
soft = soft * np.isin(lab, 1 + np.where(sizes >= 40)[0])

ys, xs = np.where(soft > 0.5)
pad = 6
soft = soft[ys.min() - pad:ys.max() + pad, xs.min() - pad:xs.max() + pad]

# supersample + blur = smooth outlines
m = Image.fromarray((soft * 255).astype(np.uint8))
w, h = m.size
big = m.resize((w * args.up, h * args.up), Image.BICUBIC)
big = big.filter(ImageFilter.GaussianBlur(args.blur * args.up))
cut = 127 - args.grow * 40
big = big.point(lambda v: 0 if v > cut else 255)  # letters black for vtracer

tmp = tempfile.mkdtemp()
mpath, spath = os.path.join(tmp, "mask.png"), os.path.join(tmp, "trace.svg")
big.convert("RGB").save(mpath)
vtracer.convert_image_to_svg_py(mpath, spath, colormode="binary", mode="spline",
                                filter_speckle=64, corner_threshold=100,
                                length_threshold=10.0, splice_threshold=45,
                                path_precision=1)


def bake(p):
    """apply translate(...) into absolute path coords"""
    t = re.search(r'translate\(([-\d.]+),([-\d.]+)\)', p)
    dx, dy = (float(t.group(1)), float(t.group(2))) if t else (0, 0)
    d = re.search(r'\sd="([^"]+)"', p).group(1)
    out, i = [], 0
    for tok in re.findall(r"[A-Za-z]|-?\d*\.?\d+(?:e-?\d+)?", d):
        if tok.isalpha():
            out.append(tok); i = 0
        else:
            v = float(tok) + (dx if i % 2 == 0 else dy); i += 1
            out.append(f"{v:.1f}")
    return re.sub(r"\s+(?=[A-Za-z])", "", " ".join(out)).replace(" ", " ")


paths = [bake(p) for p in re.findall(r"<path[^>]*/>", open(spath, encoding="utf-8").read())]
W, H = big.size
mmw = args.mm
mmh = mmw * H / W
out = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{mmw:.2f}mm" height="{mmh:.2f}mm" viewBox="0 0 {W} {H}">\n'
       f'  <title>Santa Hates You</title>\n'
       f'  <g fill="{args.color}" fill-rule="evenodd">\n'
       + "".join(f'    <path d="{d}"/>\n' for d in paths) + "  </g>\n</svg>\n")
os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
open(args.out, "w", encoding="utf-8").write(out)
print(f"{len(paths)} paths, {W}x{H}, {mmw:.1f}x{mmh:.1f}mm -> {os.path.abspath(args.out)}")
