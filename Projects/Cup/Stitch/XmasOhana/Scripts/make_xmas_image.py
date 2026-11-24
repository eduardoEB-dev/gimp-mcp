"""Glossy Christmas Ohana -> flat red/green 'X-mas Ohana'.
Keeps 'mas' + 'Ohana' + swash from source (flattened), builds X (Script MT Bold) + hyphen.
usage: python make_xmas_image.py <src.png> <out.png> [--keep-text]  (--keep-text: flatten only, keep "Christmas")
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage as ndi

RED = (222, 16, 16)
GREEN = (24, 140, 40)
src, out = sys.argv[1], sys.argv[2]
keep_text = '--keep-text' in sys.argv
im = np.array(Image.open(src).convert('RGB')).astype(int)
H, W = im.shape[:2]
r, g, b = im[..., 0], im[..., 1], im[..., 2]
disk = lambda k: np.hypot(*np.mgrid[-k:k + 1, -k:k + 1]) <= k

def clean(m):
    # close specular streaks, fill small enclosed gaps, keep letter counters
    m = ndi.binary_closing(np.pad(m, 10), disk(2))[10:-10, 10:-10]
    lab, n = ndi.label(~m)
    sz = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
    small = np.isin(lab, [i + 1 for i, v in enumerate(sz) if v < 400])
    return m | small

red = clean(r - g > 25)
grn = clean(g - r > 25)

# --- cut 'mas' (right of t; skip t crossbar/tail) ---
box = np.zeros_like(red); box[:, 798:] = True; box[:276, :875] = False  # drop t crossbar
lab, n = ndi.label(red & box)
sizes = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
mas = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 2000])
ys, xs = np.nonzero(mas)
mx0, mx1, my0, my1 = xs.min(), xs.max(), ys.min(), ys.max()

# --- X glyph ---
capH = 330                       # C/h ascender height approx
F = ImageFont.truetype('C:/Windows/Fonts/SCRIPTBL.TTF', 400)
gl = Image.new('L', (900, 900), 0)
ImageDraw.Draw(gl).text((100, 100), 'X', font=F, fill=255)
ga = np.array(gl) > 127
gy, gx = np.nonzero(ga)
ga = ga[gy.min():gy.max() + 1, gx.min():gx.max() + 1]
s = capH / ga.shape[0]
X = np.array(Image.fromarray((ga * 255).astype(np.uint8)).resize(
    (int(ga.shape[1] * s), capH), Image.LANCZOS)) > 127

# --- layout ---
base = 455                       # m baseline (source px)
gap = 18
hyW, hyH = 80, 34
total = X.shape[1] + gap + hyW + gap + (mx1 - mx0)
x0 = (W - total) // 2
canvas_r = np.zeros((H, W), bool)
xt = base - capH
canvas_r[xt:xt + X.shape[0], x0:x0 + X.shape[1]] |= X
hx = x0 + X.shape[1] + gap
hy = my0 + (base - my0) // 2 - hyH // 2
hy_img = Image.new('L', (W, H), 0)
ImageDraw.Draw(hy_img).rounded_rectangle((hx, hy, hx + hyW, hy + hyH), radius=hyH // 2, fill=255)
canvas_r |= np.array(hy_img) > 127
dx = hx + hyW + gap - mx0
canvas_r |= np.roll(mas, dx, axis=1)

def smooth(m):
    a = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5))
    return np.array(a) > 127

if keep_text:
    canvas_r = red
canvas_r, grn = smooth(canvas_r), smooth(grn)
outim = np.zeros((H, W, 4), np.uint8)   # transparent bg
outim[grn] = GREEN + (255,)
outim[canvas_r] = RED + (255,)
Image.fromarray(outim).save(out)
print('mas box', mx0, mx1, my0, my1, 'X', X.shape, 'x0', x0)
