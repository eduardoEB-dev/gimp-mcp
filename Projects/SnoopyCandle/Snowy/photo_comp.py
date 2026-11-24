"""Cut Snoopy (snowy base) out of user photos and place on christmas render bg.
usage: python -I photo_comp.py <photo> <bg.png> <out.png> [height_frac] [cx_frac] [bottom_frac]
"""
import sys, numpy as np, onnxruntime as ort
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

MODEL = r"C:\Users\eduar\.rembg\models\birefnet-general\birefnet-general.onnx"

def mask_of(img):
    s = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    x = np.asarray(img.resize((1024, 1024), Image.BICUBIC), np.float32) / 255.0
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    y = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
    y = 1 / (1 + np.exp(-y))
    m = Image.fromarray((np.clip(y, 0, 1) * 255).astype(np.uint8)).resize(img.size, Image.BICUBIC)
    return m

def _blur(x, r):
    n = int(r * 3); t = np.arange(-n, n + 1); k = np.exp(-t * t / (2 * r * r)); k /= k.sum()
    x = x.astype(np.float32)
    x = np.apply_along_axis(lambda v: np.convolve(np.pad(v, n, mode="edge"), k, "valid"), 0, x)
    x = np.apply_along_axis(lambda v: np.convolve(np.pad(v, n, mode="edge"), k, "valid"), 1, x)
    return x

def lift_white_shadows(a, mk, target=228.0, strength=0.85, max_gain=1.9):
    """Fill-light: brighten shadowed white PLA (e.g. under the bowl) toward target.
    White = low chroma & not dark part (ear/nose/eyes). Gain is smooth, limited to white px."""
    lum = a.mean(2)
    chroma = (a.max(2) - a.min(2)) / np.maximum(lum, 1)
    ss = lambda e0, e1, x: np.clip((x - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((x - e0) / (e1 - e0), 0, 1))
    # soft whiteness: bright-ish and low chroma (red bowl/collar, black parts excluded)
    w = ss(70, 120, lum) * (1 - ss(0.25, 0.45, chroma)) * mk
    # illumination estimate: non-white px filled with target so they don't read as shadow
    fill = lum * w + target * (1 - w)
    local = _blur(fill, max(2, a.shape[0] * 0.02))
    gain = np.clip(target / np.maximum(local, 1), 1.0, max_gain)
    gain = 1 + (gain - 1) * strength
    g = 1 + (gain - 1) * w
    return np.clip(a * g[..., None], 0, 255)

def grade(img, m):
    a = np.asarray(img, np.float32)
    mk = np.asarray(m, np.float32) / 255 > 0.5
    # white balance: brightest product pixels (white PLA) -> warm neutral
    lum = a.mean(2)
    sel = mk & (lum > np.percentile(lum[mk], 80))
    ref = a[sel].mean(0)
    target = np.array([236, 230, 220], np.float32)  # warm white like renders
    a = a * (target / ref)
    a = np.clip(a, 0, 255)
    a = lift_white_shadows(a, mk)
    out = Image.fromarray(a.astype(np.uint8))
    out = ImageEnhance.Contrast(out).enhance(1.06)
    out = ImageEnhance.Color(out).enhance(1.08)
    # soft warm key from left-top, slight falloff to right/bottom
    w, h = out.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    g = 1.04 - 0.10 * (xx / w) - 0.06 * (yy / h)
    a = np.asarray(out, np.float32) * g[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def main():
    photo, bgp, outp = sys.argv[1:4]
    hf = float(sys.argv[4]) if len(sys.argv) > 4 else 0.80
    cx = float(sys.argv[5]) if len(sys.argv) > 5 else 0.53
    bf = float(sys.argv[6]) if len(sys.argv) > 6 else 0.93
    img = ImageOps.exif_transpose(Image.open(photo)).convert("RGB")
    m = mask_of(img)
    bb = m.point(lambda v: 255 if v > 128 else 0).getbbox()
    img, m = img.crop(bb), m.crop(bb)
    img = grade(img, m)
    bg = Image.open(bgp).convert("RGB")
    W, H = bg.size
    th = int(H * hf); tw = int(img.width * th / img.height)
    img = img.resize((tw, th), Image.LANCZOS); m = m.resize((tw, th), Image.LANCZOS)
    m = m.filter(ImageFilter.GaussianBlur(0.8))
    x0 = int(W * cx - tw / 2); y0 = int(H * bf - th)
    # contact shadow: ellipse under base
    sh = Image.new("L", (W, H), 0)
    from PIL import ImageDraw
    d = ImageDraw.Draw(sh)
    ew, eh = tw * 0.92, th * 0.07
    ccx, ccy = W * cx + tw * 0.02, H * bf - eh * 0.25
    d.ellipse([ccx - ew / 2, ccy - eh / 2, ccx + ew / 2, ccy + eh / 2], fill=170)
    sh = sh.filter(ImageFilter.GaussianBlur(th * 0.025))
    bga = np.asarray(bg, np.float32) * (1 - np.asarray(sh, np.float32)[..., None] / 255 * 0.75)
    bg = Image.fromarray(bga.astype(np.uint8))
    bg.paste(img, (x0, y0), m)
    bg.save(outp)
    print("saved", outp, (x0, y0, tw, th))

main()
