"""Add the TryCatch Designs logo card (bottom-right, white rounded card + soft shadow).
usage: python -I brand.py [--pos br|tr|bl|tl] [--frac F] <out_dir> <img1> [img2 ...]   -> <out_dir>/<name>_logo.png"""
import sys, os
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps

LOGO = r"G:\gimp-mcp\Projects\Cup\Ad Images\TryCatch Designs_ From Code to Creation.png"
FRAC, MARGIN = 0.34, 0.03          # card width as fraction of image width, margin from edges

WM = 0.14  # watermark opacity: tiled diagonal "TryCatch Designs" in white over the whole image (0 = off)
FONT = r"C:\Windows\Fonts\arialbd.ttf"

args, POS = sys.argv[1:], "br"
while args and args[0].startswith("--"):
    k, v, args = args[0], args[1], args[2:]
    if k == "--pos": POS = v
    elif k == "--frac": FRAC = float(v)
    elif k == "--wm": WM = float(v)

def watermark(im):
    from PIL import ImageFont
    W, H = im.size; D = int((W ** 2 + H ** 2) ** 0.5) + 40
    font = ImageFont.truetype(FONT, int(W * 0.042)); txt = "TryCatch Designs"
    tw, th = font.getbbox(txt)[2:]; gx, gy = int(tw * 0.45), int(th * 3.2)
    lay = Image.new("RGBA", (D, D), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); a = int(255 * WM)
    for r, y in enumerate(range(0, D, th + gy)):
        for x in range(-(r % 2) * (tw + gx) // 2, D, tw + gx):
            d.text((x, y), txt, font=font, fill=(255, 255, 255, a))
    lay = lay.rotate(30, resample=Image.BICUBIC)
    return Image.alpha_composite(im, lay.crop(((D - W) // 2, (D - H) // 2, (D - W) // 2 + W, (D - H) // 2 + H)))
out_dir, imgs = args[0], args[1:]
logo = Image.open(LOGO).convert("RGB")
mask = ImageChops.difference(logo, Image.new("RGB", logo.size, "white")).convert("L").point(lambda v: 255 if v > 24 else 0)
la = logo.crop(mask.getbbox()).convert("RGBA"); px = la.load()
for y in range(la.height):                     # white -> transparent (soft key)
    for x in range(la.width):
        r, g, b, _ = px[x, y]; d = 255 - min(r, g, b); px[x, y] = (r, g, b, max(0, min(255, int((d - 8) * 255 / 40))))

for path in imgs:
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGBA"); W, H = im.size
    if WM > 0: im = watermark(im)
    lw = int(W * FRAC); lh = int(lw * la.height / la.width); lg = la.resize((lw, lh), Image.LANCZOS)
    pad = int(lw * 0.06); cw, ch = lw + 2 * pad, lh + 2 * pad; m = int(W * MARGIN)
    x0 = W - cw - m if "r" in POS else m
    y0, rad = (H - ch - m if "b" in POS else m), int(ch * 0.22)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0 + 6, y0 + 10, x0 + cw + 6, y0 + ch + 10), rad, fill=(0, 0, 0, 120))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(14)))
    card = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle((x0, y0, x0 + cw, y0 + ch), rad, fill=(255, 255, 255, 238))
    im = Image.alpha_composite(im, card); im.alpha_composite(lg, (x0 + pad, y0 + pad))
    out = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + "_logo.png")
    im.convert("RGB").save(out); print("WROTE", out)
