"""Overlay TryCatch logo card on images. usage: brand.py logo.png out_dir img1 [img2 ...]"""
import sys, os
from PIL import Image, ImageDraw, ImageFilter, ImageChops

logo_p, out_dir, imgs = sys.argv[1], sys.argv[2], sys.argv[3:]
logo = Image.open(logo_p).convert("RGB")
# crop to non-white content
diff = ImageChops.difference(logo, Image.new("RGB", logo.size, (255, 255, 255))).convert("L").point(lambda v: 255 if v > 24 else 0)
logo = logo.crop(diff.getbbox())
# white -> transparent (soft key on lightness distance from white)
la = logo.convert("RGBA"); px = la.load()
for y in range(la.height):
    for x in range(la.width):
        r, g, b, _ = px[x, y]; d = 255 - min(r, g, b)
        px[x, y] = (r, g, b, max(0, min(255, int((d - 8) * 255 / 40))))

def brand(path, frac=0.36, margin=0.03, pos="br"):
    im = Image.open(path).convert("RGBA"); W, H = im.size
    lw = int(W * frac); lh = int(lw * la.height / la.width)
    lg = la.resize((lw, lh), Image.LANCZOS)
    pad = int(lw * 0.06); cw, ch = lw + 2 * pad, lh + 2 * pad; m = int(W * margin)
    x0 = W - cw - m if pos.endswith("r") else (m if pos.endswith("l") else (W - cw) // 2)
    y0 = H - ch - m if pos.startswith("b") else m
    rad = int(ch * 0.22)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0 + 6, y0 + 10, x0 + cw + 6, y0 + ch + 10), rad, fill=(0, 0, 0, 120))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(14)))
    card = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle((x0, y0, x0 + cw, y0 + ch), rad, fill=(255, 255, 255, 238))
    im = Image.alpha_composite(im, card)
    im.alpha_composite(lg, (x0 + pad, y0 + pad))
    out = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + "_logo.png")
    im.convert("RGB").save(out); print("WROTE", out)

for p in imgs:
    if "44fe50ef" in p: brand(p, frac=0.31, margin=0.025, pos="tl")
    else: brand(p)
