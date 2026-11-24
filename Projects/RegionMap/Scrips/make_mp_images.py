"""Build 1366x768 Microsoft Partner Center images for Image Hotspots,
reusing the PointTask marketing template (Examples/PT_1366x768_v1.png)."""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path("C:/Windows/Fonts")
TEMPLATE = ROOT / "Examples" / "PT_1366x768_v1.png"
LOGO = ROOT / "Image Hotspots_300x300.png"
OUT = ROOT / "MP IMages"

SCREEN = (235, 154, 1130, 560)  # monitor viewport in template (x0,y0,x1,y1)
TITLE_COLOR = (20, 30, 70)
CAPTION_COLOR = (40, 58, 100)


def erase(im, x0, y0, x1, y1):
    """Paint box with per-row horizontal gradient sampled just outside it."""
    a = np.array(im).astype(float)
    for y in range(y0, y1):
        l, r = a[y, x0 - 4], a[y, x1 + 4]
        t = np.linspace(0, 1, x1 - x0)[:, None]
        a[y, x0:x1] = l * (1 - t) + r * t
    return Image.fromarray(a.astype(np.uint8))


def screen_content(src):
    """Fit a 1703x1079 SharePoint screenshot into the wide monitor viewport:
    keep header/nav, rescale the map so the whole thing stays visible."""
    sw, sh = SCREEN[2] - SCREEN[0], SCREEN[3] - SCREEN[1]
    W = src.width
    H = round(W * sh / sw)
    canvas = src.crop((0, 0, W, H)).copy()
    d = ImageDraw.Draw(canvas)
    d.rectangle((83, 188, 1668, H), fill=src.getpixel((900, 1000))[:3])
    mp = src.crop((285, 225, 1455, 940))
    avail_h = H - 200 - 10
    s = avail_h / mp.height
    mp = mp.resize((round(mp.width * s), avail_h), Image.LANCZOS)
    canvas.paste(mp, (885 - mp.width // 2, 200), mp if mp.mode == "RGBA" else None)
    return canvas.resize((sw, sh), Image.LANCZOS)


def build(screenshot, caption, out_name):
    im = Image.open(TEMPLATE).convert("RGB")

    # badge: grab before erasing, re-place after new title
    badge = im.crop((370, 38, 632, 90))
    im = erase(im, 40, 18, 636, 112)

    logo = Image.open(LOGO).convert("RGBA").resize((72, 72), Image.LANCZOS)
    im.paste(logo, (54, 27), logo)

    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(FONTS / "segoeuib.ttf"), 38)
    title = "Image Hotspots"
    d.text((143, 63), title, font=f, fill=TITLE_COLOR, anchor="lm")
    tx1 = 143 + d.textlength(title, font=f)
    im.paste(badge, (round(tx1) + 30, 38))

    # monitor viewport
    src = Image.open(screenshot).convert("RGB")
    im.paste(screen_content(src), SCREEN[:2])

    # caption
    im = erase(im, 880, 672, 1340, 728)
    d = ImageDraw.Draw(im)
    fc = ImageFont.truetype(str(FONTS / "segoeui.ttf"), 16)
    y = 688
    for line in caption:
        d.text((1322, y), line, font=fc, fill=CAPTION_COLOR, anchor="rm")
        y += 23

    OUT.mkdir(exist_ok=True)
    assert im.size == (1366, 768)
    im.save(OUT / out_name)
    print("wrote", OUT / out_name)


if __name__ == "__main__":
    build(
        ROOT / "WPImages" / "FullPageWPView_anon.png",
        ["Turn any image into an interactive region map. Hover to highlight",
         "a region, click to navigate to related pages, sites or documents."],
        "IH_1366x768_v1.png",
    )
