"""Favicon: LL monogram inside a clean gold ring on a cream disc.
Writes favicon.ico (16-256), favicon.png (256), favicon.svg (raster in SVG), like the DVLMNT site assets.

usage: python make_favicon.py [out_dir]   (default ../Drafts/Favicon_v1)
"""
import base64
import io
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "Images", "13c2e3c4-b615-4db0-9791-64728dccb5df.jpeg")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "Drafts", "Favicon_v1")

LL_BOX = (240, 62, 524, 362)      # both L's incl. gold rim (source px)
N = 1024                          # work size
CREAM = (251, 245, 238, 255)
GOLD = (201, 160, 96, 255)
RING_W = 0.06                     # ring stroke / N
LL_FILL = 0.70                    # LL height / N


src = Image.open(SRC).convert("RGB")
a = np.asarray(src.crop(LL_BOX), dtype=np.float32)
arr = np.asarray(src, dtype=np.float32)
bg = np.median(arr[:15, :15].reshape(-1, 3), axis=0)

# letters only: strong color difference from paper drops the pale pink wash
d = np.abs(a - bg).max(axis=2)
alpha = np.clip((d - 55) / 35, 0, 1)
alpha[(a[..., 1] > a[..., 0] - 5) & (a[..., 1] > a[..., 2] + 10)] = 0  # leaves (green)
lab, n = ndimage.label(alpha > 0.3, structure=np.ones((3, 3)))
sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 0.05 * sizes.max()])  # drop gold dots/specks
alpha *= ndimage.binary_dilation(keep, iterations=2)
safe = np.maximum(alpha, 0.25)[..., None]
rgb = np.clip((a - bg * (1 - safe)) / safe, 0, 255)
ll = Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")
ll = ll.crop(ll.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox())

canvas = Image.new("RGBA", (N, N), (0, 0, 0, 0))
draw = ImageDraw.Draw(canvas)
w = round(N * RING_W)
draw.ellipse((0, 0, N - 1, N - 1), fill=GOLD)
draw.ellipse((w, w, N - 1 - w, N - 1 - w), fill=CREAM)
h = round(N * LL_FILL)
lw = round(ll.width * h / ll.height)
ll = ll.resize((lw, h), Image.LANCZOS)
canvas.alpha_composite(ll, ((N - lw) // 2, (N - h) // 2))

os.makedirs(OUT, exist_ok=True)
big = canvas.resize((256, 256), Image.LANCZOS)
big.save(os.path.join(OUT, "favicon.png"), optimize=True)
canvas.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "logo_mark.png"), optimize=True)
big.save(os.path.join(OUT, "favicon.ico"), sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])
buf = io.BytesIO()
canvas.resize((128, 128), Image.LANCZOS).save(buf, "PNG", optimize=True)
with open(os.path.join(OUT, "favicon.svg"), "w") as f:
    f.write('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            'viewBox="0 0 128 128" width="128" height="128">'
            f'<image width="128" height="128" href="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"/></svg>')

# preview: tab sizes on light + dark
sizes = (16, 32, 48, 64, 128, 256)
pv = Image.new("RGBA", (sum(sizes) + 20 * (len(sizes) + 1), 2 * 256 + 60), (255, 255, 255, 255))
ImageDraw.Draw(pv).rectangle((0, 256 + 30, pv.width, pv.height), fill=(32, 33, 36, 255))
x = 20
for s in sizes:
    im = canvas.resize((s, s), Image.LANCZOS)
    pv.alpha_composite(im, (x, 10 + (256 - s)))
    pv.alpha_composite(im, (x, 256 + 40 + (256 - s) // 2))
    x += s + 20
pv.convert("RGB").save(os.path.join(OUT, "_preview.png"))
print(OUT)
