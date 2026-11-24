"""Horizontal header logo: LL emblem left, LAYERED / Legacy text right, transparent bg.

usage: python make_header_logo.py [out_dir]   (default ../Drafts/HeaderLogo_v1)
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "Images", "13c2e3c4-b615-4db0-9791-64728dccb5df.jpeg")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "Drafts", "HeaderLogo_v1")

EMBLEM_BOX = (95, 22, 645, 412)   # LL + ring + leaves + plane + box (source px)
TEXT_BOX = (40, 416, 705, 618)    # LAYERED over Legacy script
TEXT_H = 0.62                     # text block height / emblem height
GAP = 0.06                        # gap emblem→text, fraction of emblem height
SCALE = 3                         # output upscale


def white_to_alpha(img, bg, lo=18, hi=60, keep=None):
    """Matte against the paper color: solid colors stay opaque (works on dark heroes too),
    soft ramp only at edges. keep(labels, n) -> ids of blobs to keep."""
    a = np.asarray(img, dtype=np.float32)
    d = np.abs(a - bg).max(axis=2)
    alpha = np.clip((d - lo) / (hi - lo), 0, 1)
    if keep:
        # gold divider under Legacy + box corner above D: gold-ish (B well below R,G) at the crop edges
        y = np.arange(a.shape[0])[:, None] + TEXT_BOX[1]
        gold = (a[..., 2] < a[..., 1] - 25) & (a[..., 0] - a[..., 2] > 40)
        alpha[gold & (y >= 598)] = 0
        alpha[(y < 424) & (a.sum(axis=2) > 300)] = 0  # anything not navy above LAYERED
        lab, n = ndimage.label(alpha > 0.3, structure=np.ones((3, 3)))
        ok = np.isin(lab, keep(lab, n))
        ok = ndimage.binary_dilation(ok, iterations=2)
        alpha *= ok
    # pull the paper color out of the soft edge so it doesn't halo on dark backgrounds
    safe = np.maximum(alpha, 0.25)[..., None]
    rgb = np.clip((a - bg * (1 - safe)) / safe, 0, 255)
    return Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")


def text_blobs(lab, n):
    """Drop blobs that are only box/leaf bits above LAYERED or divider/heart below Legacy."""
    ids = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        y0, y1 = sl[0].start + TEXT_BOX[1], sl[0].stop + TEXT_BOX[1]
        if y1 <= 424 or y0 >= 596:
            continue
        ids.append(i)
    return ids


def trim(im):
    return im.crop(im.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox())


src = Image.open(SRC).convert("RGB")
arr = np.asarray(src, dtype=np.float32)
bg = np.median(np.concatenate([arr[:15, :15].reshape(-1, 3), arr[:15, -15:].reshape(-1, 3)]), axis=0)

emblem = trim(white_to_alpha(src.crop(EMBLEM_BOX), bg))
text = trim(white_to_alpha(src.crop(TEXT_BOX), bg, keep=text_blobs))

eh = emblem.height * SCALE
ew = round(emblem.width * SCALE)
emblem = emblem.resize((ew, eh), Image.LANCZOS)
th = round(eh * TEXT_H)
tw = round(text.width * th / text.height)
text = text.resize((tw, th), Image.LANCZOS)

gap = round(eh * GAP)
canvas = Image.new("RGBA", (ew + gap + tw, eh), (0, 0, 0, 0))
canvas.alpha_composite(emblem, (0, 0))
canvas.alpha_composite(text, (ew + gap, (eh - th) // 2))

os.makedirs(OUT, exist_ok=True)
canvas.save(os.path.join(OUT, "LayeredLegacy_header.png"), optimize=True)
for h in (80, 160):  # 1x / 2x header sizes
    w = round(canvas.width * h / canvas.height)
    canvas.resize((w, h), Image.LANCZOS).save(os.path.join(OUT, f"LayeredLegacy_header_{h}h.png"), optimize=True)
canvas.save(os.path.join(OUT, "LayeredLegacy_header.webp"), quality=92)

# previews on light + dark hero backgrounds
for name, col in (("light", (253, 247, 242)), ("dark", (20, 33, 61))):
    p = Image.new("RGBA", (canvas.width + 120, canvas.height + 120), col + (255,))
    p.alpha_composite(canvas, (60, 60))
    p.convert("RGB").resize((p.width // 2, p.height // 2), Image.LANCZOS).save(os.path.join(OUT, f"_preview_{name}.png"))
print(OUT, canvas.size)
