"""PEANUTS word (gold on black card photo) -> single-color SVG for engraving.
Usage: python peanuts_word_svg.py <photo.jpg> <out_dir> [--width-mm 100]
Steps: exif-rotate, crop word, gold mask, keep 7 letter blobs, fit top/bottom/
left/right lines -> perspective-straighten, 5x supersample + blur, trace."""
import sys, os, argparse
import numpy as np
from PIL import Image, ImageOps, ImageFilter
from scipy import ndimage as ndi
sys.path.insert(0, r"D:\gimp-mcp\Projects\Workflow\SVG Creation")
from layers_common import trace_mask, write_layer_set

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--width-mm", type=float, default=100)
ap.add_argument("--crop", default="180,120,820,370")
a = ap.parse_args()

im = ImageOps.exif_transpose(Image.open(a.src)).convert("RGB")
crop = im.crop(tuple(int(v) for v in a.crop.split(",")))
c = np.asarray(crop).astype(int)
gold = ((c[..., 0] - c[..., 2]) > 45) & (c[..., 0] > 110)
gold = ndi.binary_opening(gold, iterations=1)
lab, n = ndi.label(gold)
sizes = ndi.sum(gold, lab, range(1, n + 1))
keep = np.argsort(sizes)[::-1][:7] + 1          # 7 letters, drops (R) + specks
letters = np.isin(lab, keep)
blobs = [(sl, i + 1) for i, sl in enumerate(ndi.find_objects(lab)) if i + 1 in keep]
blobs.sort(key=lambda b: b[0][1].start)          # left -> right

def fit(xs, ys):                                  # y = m x + b
    return np.polyfit(xs, ys, 1)

# top / bottom lines: per letter top-most and bottom-most points
tops, bots = [], []
for sl, i in blobs:
    yy, xx = np.nonzero(lab == i)
    tops.append((xx[yy == yy.min()].mean(), yy.min()))
    bots.append((xx[yy == yy.max()].mean(), yy.max()))
tl = fit(*zip(*tops)); bl = fit(*zip(*bots))

def side(i, pick, frac):                          # x = m y + b for a letter edge
    m = lab == i; ys = np.nonzero(m.any(1))[0]
    y0, y1 = ys.min(), ys.max(); h = y1 - y0
    rows = [y for y in ys if y0 + frac[0] * h <= y <= y0 + frac[1] * h]
    xs = [pick(np.nonzero(m[y])[0]) for y in rows]
    return np.polyfit(rows, xs, 1)
ll = side(blobs[0][1], np.min, (0.1, 0.9))        # P left edge
rl = side(blobs[-1][1], np.max, (0.6, 0.85))      # S lower-bowl right edge

def inter(hl, vl):                                # y=m1x+b1, x=m2y+b2
    m1, b1 = hl; m2, b2 = vl
    y = (m1 * b2 + b1) / (1 - m1 * m2); return (m2 * y + b2, y)
src = [inter(tl, ll), inter(tl, rl), inter(bl, rl), inter(bl, ll)]
W = (np.hypot(*np.subtract(src[1], src[0])) + np.hypot(*np.subtract(src[2], src[3]))) / 2
H = (np.hypot(*np.subtract(src[3], src[0])) + np.hypot(*np.subtract(src[2], src[1]))) / 2
S = 5; pad = 6
dst = [(pad, pad), (pad + W, pad), (pad + W, pad + H), (pad, pad + H)]
dst = [(x * S, y * S) for x, y in dst]
# PIL perspective: coeffs map output -> input
A, B = [], []
for (x, y), (u, v) in zip(dst, src):
    A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]; B += [u, v]
coef = np.linalg.solve(np.array(A, float), np.array(B, float))
size = (int((W + 2 * pad) * S), int((H + 2 * pad) * S))
mimg = Image.fromarray((letters * 255).astype(np.uint8))
warp = mimg.transform(size, Image.PERSPECTIVE, tuple(coef), Image.BICUBIC)
warp = warp.filter(ImageFilter.GaussianBlur(S * 0.9))
mask = np.asarray(warp) > 127
lab2, n2 = ndi.label(mask); sz = ndi.sum(mask, lab2, range(1, n2 + 1))
mask = np.isin(lab2, np.nonzero(sz > 500)[0] + 1)

ys, xs = np.nonzero(mask)
y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
mask = mask[y0:y1, x0:x1]
h, w = mask.shape
paths = trace_mask(mask, speckle=30)
write_layer_set(a.out, "Peanuts", (0, 0, w, h), (a.width_mm, a.width_mm * h / w),
                [({"name": "Black", "hex": "#000000"}, paths)], title="PEANUTS", source=a.src)
Image.fromarray(np.where(mask, 0, 255).astype(np.uint8)).save(os.path.join(a.out, "_mask.png"))
print("corners", [tuple(round(v, 1) for v in p) for p in src], "W,H", round(W), round(H))
