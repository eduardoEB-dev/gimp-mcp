"""Trace the TryCatch logo to a true-vector SVG (scales to any size).
usage: python -I make_vector.py [--full] <logo.png> <out.svg>
  default: mark only ({TC} + nozzle + cube);  --full: whole logo incl. wordmark + tagline"""
import sys, os, re, vtracer
from PIL import Image, ImageChops
args = sys.argv[1:]; full = args[0] == "--full"; args = args[full:]
src, out = args
im = Image.open(src).convert("RGB")
if not full: im = im.crop((0, 0, 940, im.height))                   # mark only, drop wordmark
m = ImageChops.difference(im, Image.new("RGB", im.size, "white")).convert("L").point(lambda v: 255 if v > 24 else 0)
im = im.crop(m.getbbox()); im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS).convert("RGBA")
px = im.load()
for y in range(im.height):                                           # white -> transparent (hard key; tracer wants clean edges)
    for x in range(im.width):
        r, g, b, _ = px[x, y]
        if min(r, g, b) > 225: px[x, y] = (255, 255, 255, 0)
tmp = out + ".png"; im.save(tmp)
vtracer.convert_image_to_svg_py(tmp, out, colormode="color", hierarchical="stacked", mode="spline",
    filter_speckle=8, color_precision=6, layer_difference=12, corner_threshold=60,
    length_threshold=4.0, splice_threshold=45, path_precision=2)
os.remove(tmp)
s = open(out).read()                                                 # fixed size -> scalable
s = re.sub(r'width="(\d+)" height="(\d+)"', r'viewBox="0 0 \1 \2"', s, count=1)
open(out, "w").write(s)
