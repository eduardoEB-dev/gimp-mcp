"""Sharpen the bottom of a photo (soft-focus foreground), feathered so the top stays untouched.
usage: python -I sharpen.py <src> <out> [y0 y1]   y0/y1 = feather band as fraction of height (default 0.62 0.72)"""
import sys
from PIL import Image, ImageOps, ImageFilter
src, out = sys.argv[1], sys.argv[2]
im = ImageOps.exif_transpose(Image.open(src)).convert("RGB"); W, H = im.size
sh = im.filter(ImageFilter.UnsharpMask(radius=2, percent=85, threshold=2))
sh = sh.filter(ImageFilter.UnsharpMask(radius=1.2, percent=90, threshold=2))
f0, f1 = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (0.62, 0.72)
y0, y1 = int(H * f0), int(H * f1)              # feather: none above y0, full below y1
m = Image.new("L", (1, H)); m.putdata([0 if y < y0 else 255 if y > y1 else int(255 * (y - y0) / (y1 - y0)) for y in range(H)])
Image.composite(sh, im, m.resize((W, H))).save(out, quality=97)
