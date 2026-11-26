"""Replace the garbled AI-drawn logo in each image: inpaint it away, then add the real TryCatch logo card (brand.py style) in that corner.
usage: <python with numpy, opencv, pillow> fix_logos.py <src_dir> <out_dir>
BOXES: per image, the fake logo's bounding box (x0, y0, x1, y1) in pixels."""
import sys, os
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps

LOGO = r"G:\gimp-mcp\Projects\Cup\Ad Images\TryCatch Designs_ From Code to Creation.png"
BOXES = {
    "868220974_1437294624524276_8684537879893658309_n.jpg": (715, 14, 1068, 152),
    "869218399_2338707393624661_5479986963673536984_n.jpg": (650, 1256, 1062, 1402),
    "869795223_2611754996007876_5145266184249851245_n.jpg": (638, 22, 1070, 178),
    "873126905_1149473051094562_6289181131594192038_n.jpg": (28, 34, 412, 152),
    "876812748_1643325537575858_727277409829989406_n.jpg": (608, 22, 1062, 188),
    "877507047_28371037199240472_8127008427304596827_n.jpg": (808, 28, 1058, 114),
}
src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)

logo = Image.open(LOGO).convert("RGB")
mask = ImageChops.difference(logo, Image.new("RGB", logo.size, "white")).convert("L").point(lambda v: 255 if v > 24 else 0)
la = logo.crop(mask.getbbox()).convert("RGBA"); px = la.load()
for y in range(la.height):  # white -> transparent (soft key), as brand.py
    for x in range(la.width):
        r, g, b, _ = px[x, y]; d = 255 - min(r, g, b); px[x, y] = (r, g, b, max(0, min(255, int((d - 8) * 255 / 40))))
AR = la.width / la.height

FRAC = 0.30  # logo width as fraction of image width (brand.py uses 0.34 on 2000px renders)
for name, (x0, y0, x1, y1) in BOXES.items():
    im = ImageOps.exif_transpose(Image.open(os.path.join(src, name))).convert("RGB"); W, H = im.size
    # 1. erase the fake logo: inpaint its box at 1/2 scale (smoother fill), paste back with a soft edge, add a little grain
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((x0 - 8, y0 - 8, x1 + 8, y1 + 8), 20, fill=255)
    a8 = np.array(im); sm = cv2.resize(a8, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    mm = cv2.resize(np.array(m), (W // 2, H // 2), interpolation=cv2.INTER_NEAREST)
    fill = cv2.resize(cv2.inpaint(sm, mm, 12, cv2.INPAINT_TELEA), (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    fill += np.random.default_rng(1).normal(0, 2.0, fill.shape)
    soft = np.array(m.filter(ImageFilter.GaussianBlur(6)), np.float32)[..., None] / 255
    im = Image.fromarray(np.clip(a8 * (1 - soft) + fill * soft, 0, 255).astype(np.uint8)).convert("RGBA")
    # 2. real logo card in the same corner the fake one was in
    lw = int(max(W * FRAC, (x1 - x0 + 4) / 1.12))  # never narrower than the fake (its edge may overlap the product)
    lh = int(lw / AR); pad = int(lw * 0.06); cw, ch = lw + 2 * pad, lh + 2 * pad
    right, bottom = (x0 + x1) / 2 > W / 2, (y0 + y1) / 2 > H / 2
    X = int(min(x1 + 2, W - 14) - cw) if right else int(max(x0 - 2, 14))
    Y = int(min(y1 + 2, H - 14) - ch) if bottom else int(max(y0 - 2, 14))
    rad = int(ch * 0.22)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((X + 4, Y + 7, X + cw + 4, Y + ch + 7), rad, fill=(0, 0, 0, 110))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(10)))
    card = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle((X, Y, X + cw, Y + ch), rad, fill=(255, 255, 255, 245))
    im = Image.alpha_composite(im, card); im.alpha_composite(la.resize((lw, lh), Image.LANCZOS), (X + pad, Y + pad))
    o = os.path.join(out, os.path.splitext(name)[0] + "_logo.jpg")
    im.convert("RGB").save(o, quality=93, subsampling=0); print("WROTE", o, (X, Y, X + cw, Y + ch))
