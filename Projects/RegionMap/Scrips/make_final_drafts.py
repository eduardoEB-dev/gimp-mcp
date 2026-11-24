"""Fix the Microsoft certified badge on both MP mockups, pop out the showcase
cards from the monitor, and save 1366x768 copies to FinalDrafts."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "MP IMages"
OUT = ROOT / "FinalDrafts"
FONT = "C:/Windows/Fonts/segoeuib.ttf"

PILL = (216, 234, 252)
NAVY = (12, 48, 112)
TEXT = (14, 52, 118)


def erase(im, x0, y0, x1, y1):
    """Fill box by blending horizontal and vertical interpolation of its border."""
    a = np.array(im.convert("RGB")).astype(float)
    L, R = a[y0:y1, x0 - 1], a[y0:y1, x1]
    T, B = a[y0 - 1, x0:x1], a[y1, x0:x1]
    tx = np.linspace(0, 1, x1 - x0)[None, :, None]
    ty = np.linspace(0, 1, y1 - y0)[:, None, None]
    h = L[:, None] * (1 - tx) + R[:, None] * tx
    v = T[None] * (1 - ty) + B[None] * ty
    a[y0:y1, x0:x1] = (h + v) / 2
    return Image.fromarray(a.astype(np.uint8))


def shield(d, x, y, w, h, fill):
    pts = [(x + w / 2, y), (x + w, y + h * 0.16), (x + w, y + h * 0.5)]
    for i in range(1, 21):  # right curve to point
        t = i / 20
        px = (1 - t) ** 2 * (x + w) + 2 * (1 - t) * t * (x + w * 0.98) + t * t * (x + w / 2)
        py = (1 - t) ** 2 * (y + h * 0.5) + 2 * (1 - t) * t * (y + h * 0.82) + t * t * (y + h)
        pts.append((px, py))
    left = [(2 * x + w - px, py) for px, py in reversed(pts[3:-1])]
    pts += left + [(x, y + h * 0.5), (x, y + h * 0.16)]
    d.polygon(pts, fill=fill)


def badge(im, x0, y0, h, text="Microsoft 365 Certified"):
    """Draw pill badge (4x supersampled) with top-left at x0,y0 and height h."""
    S = 4
    f = ImageFont.truetype(FONT, round(h * 0.5) * S)
    tw = f.getlength(text)
    pad, sw = h * 0.42 * S, h * 0.5 * S
    W = round(pad + sw + h * 0.3 * S + tw + pad)
    H = h * S
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((0, 0, W - 1, H - 1), radius=H // 2, fill=PILL + (255,))
    sh = sw * 1.12
    sx, sy = pad, (H - sh) / 2
    shield(d, sx, sy, sw, sh, NAVY + (255,))
    lw = round(sw * 0.13)
    d.line([(sx + sw * 0.27, sy + sh * 0.5), (sx + sw * 0.45, sy + sh * 0.66),
            (sx + sw * 0.75, sy + sh * 0.34)], fill=(255, 255, 255, 255), width=lw, joint="curve")
    d.text((sx + sw + h * 0.3 * S, H / 2), text, font=f, fill=TEXT + (255,), anchor="lm")
    layer = layer.resize((W // S, h), Image.LANCZOS)
    im = im.convert("RGBA")
    im.alpha_composite(layer, (x0, y0))
    return im.convert("RGB")


def float_card(base, card, x, y, k, radius=14):
    card = card.resize((round(card.width * k), round(card.height * k)), Image.LANCZOS)
    w, h = card.size
    m = 40
    sh = Image.new("L", (w + 2 * m, h + 2 * m), 0)
    ImageDraw.Draw(sh).rounded_rectangle((m, m, m + w, m + h), radius, fill=70)
    sh = sh.filter(ImageFilter.GaussianBlur(16))
    shadow = Image.new("RGBA", sh.size, (20, 35, 70, 0))
    shadow.putalpha(sh)
    base.alpha_composite(shadow, (x - m, y - m + 12))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
    c = card.convert("RGBA")
    c.putalpha(mask)
    base.alpha_composite(c, (x, y))
    ImageDraw.Draw(base).rounded_rectangle((x, y, x + w - 1, y + h - 1), radius,
                                           outline=(222, 230, 242, 255), width=1)


def map_mockup():
    im = Image.open(SRC / "IH_SharePointMapMockup_1366x768.png").convert("RGB")
    im = erase(im, 506, 8, 846, 100)
    im = badge(im, 522, 35, 46)
    return im


def showcase():
    im = Image.open(SRC / "Image Hotspots Dashboard Showcase.png").convert("RGB")
    im = erase(im, 622, 18, 988, 114)
    im = badge(im, 642, 41, 54)

    cards = {  # source boxes in 1672x940 original
        "facility": (295, 233, 655, 495),
        "equipment": (667, 233, 1020, 495),
        "product": (1029, 233, 1380, 495),
        "training": (295, 508, 775, 722),
        "process": (789, 508, 1380, 722),
    }
    crops = {k: im.crop(b) for k, b in cards.items()}

    # clear screen content below the "Interactive Visuals" header
    d = ImageDraw.Draw(im)
    d.rectangle((277, 226, 1395, 735), fill=(246, 249, 253))
    base = im.convert("RGBA")

    # (x, y, scale) - cards break out past the bezel like ReportSessions_v4
    layout = {
        "equipment": (650, 238, 1.05),
        "facility": (140, 250, 1.12),
        "product": (1140, 205, 1.12),
        "training": (190, 585, 1.08),
        "process": (765, 532, 1.08),
    }
    for k in ("equipment", "facility", "product", "training", "process"):
        x, y, s = layout[k]
        float_card(base, crops[k], x, y, s)
    return base.convert("RGB")


def canvas_config():
    """Config canvas on the monitor, hotspot table + coordinate form popped out."""
    im = map_mockup()
    canvas = Image.open(SRC / "canvasImage.png").convert("RGB")
    form = Image.open(SRC / "Form.png").convert("RGB")

    im.paste(canvas.crop((0, 0, 1691, 800)).resize((958, 453), Image.LANCZOS), (204, 131))

    im = erase(im, 1060, 632, 1346, 730)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 17)
    lines = ["Configure hotspots on a visual",
             "canvas. Use the form to enter exact",
             "image coordinates, links, hover",
             "images and accessibility text."]
    for i, line in enumerate(lines):
        d.text((1068, 637 + i * 23), line, font=f, fill=(20, 35, 95))

    base = im.convert("RGBA")
    float_card(base, canvas.crop((440, 855, 1672, 1162)), 110, 548, 0.56)
    float_card(base, form.crop((240, 0, 624, 660)), 1040, 112, 0.76)
    return base.convert("RGB")


ICONS = "C:/Windows/Fonts/SegoeIcons.ttf"
TEAL = (14, 112, 120)


def hotspot_scene(c):
    """SharePoint page on the monitor showing a hotspot image with one region
    hovered, plus a popped-out detail card. `c` is a scene config dict."""
    im = map_mockup()
    d = ImageDraw.Draw(im)
    fb = lambda s: ImageFont.truetype(FONT, s)
    fr = lambda s: ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", s)
    fi = lambda s: ImageFont.truetype(ICONS, s)

    # site tile + title
    d.rounded_rectangle((268, 177, 304, 213), 2, fill=(1, 109, 232))
    d.text((286, 195), c["site"][0], font=fb(18), fill="white", anchor="mm")
    im = erase(im, 316, 182, 412, 210)
    d = ImageDraw.Draw(im)
    d.text((321, 196), c["site"], font=fb(17), fill=(0, 15, 113), anchor="lm")

    # page content; dim everything but the hovered region
    d.rectangle((206, 250, 1149, 582), fill=(255, 255, 255))
    photo, mask = c["photo"], c["mask"]
    hovered = Image.composite(photo, c["dim"](photo), c.get("keep", mask))
    full_hover = hovered

    H = 324
    s = H / photo.height
    W = round(photo.width * s)
    hovered = hovered.resize((W, H), Image.LANCZOS)
    m = mask.resize((W, H), Image.LANCZOS)
    px, py = c.get("px", 228), 254
    base = im.convert("RGBA")
    edge = m.filter(ImageFilter.MaxFilter(5))
    glow = Image.new("RGBA", (W, H), (0, 120, 212, 0))
    glow.putalpha(edge.filter(ImageFilter.GaussianBlur(6)).point(lambda v: min(255, v * 2)))
    page = Image.new("RGBA", (W, H))
    page.paste(hovered, (0, 0))
    if c.get("radius"):
        pm = Image.new("L", (W, H), 0)
        ImageDraw.Draw(pm).rounded_rectangle((0, 0, W - 1, H - 1), c["radius"], fill=255)
        page.putalpha(pm)
    base.alpha_composite(page, (px, py))
    ring = Image.new("RGBA", (W, H), (0, 120, 212, 0))
    ring.putalpha(Image.fromarray((np.array(edge).astype(int) - np.array(m).astype(int)).clip(0, 255).astype(np.uint8)))
    base.alpha_composite(glow, (px, py))
    re = Image.composite(Image.new("RGBA", (W, H), (0, 0, 0, 0)), page, m.point(lambda v: 255 - v))
    base.alpha_composite(re, (px, py))
    base.alpha_composite(ring, (px, py))

    # optional hover pill + cursor over the region
    mb = np.array(m) > 128
    yy, xx = np.where(mb)
    cx, cy = px + int(xx.mean()), py + int(yy.mean())
    top = py + yy.min()
    d = ImageDraw.Draw(base)
    label = c["title"]
    if c.get("pill", True):
        f = fb(14)
        tw = d.textlength(label, font=f)
        lx0, ly0 = cx - tw / 2 - 14, top - 44
        d.rounded_rectangle((lx0, ly0, lx0 + tw + 28, ly0 + 30), 15, fill=(12, 48, 112, 245))
        d.text((cx, ly0 + 15), label, font=f, fill="white", anchor="mm")
        d.polygon([(cx - 6, ly0 + 30), (cx + 6, ly0 + 30), (cx, ly0 + 37)], fill=(12, 48, 112, 245))
    if c.get("dot", True):
        d.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill="white", outline=(0, 120, 212), width=3)
    cur = [(0, 0), (0, 17), (4, 13), (7, 20), (10, 19), (7, 12), (12, 12)]
    kx, ky = c.get("cursor", (10, 8))
    cur = [(cx + kx + x, cy + ky + y) for x, y in cur]
    d.polygon(cur, fill="white", outline=(20, 20, 20))

    # caption
    rgb = base.convert("RGB")
    rgb = erase(rgb, 1060, 632, 1346, 730)
    d = ImageDraw.Draw(rgb)
    for i, line in enumerate(c["caption"]):
        d.text((1068, 637 + i * 23), line, font=fr(17), fill=(20, 35, 95))
    base = rgb.convert("RGBA")

    # detail card
    S = 2
    CW, CH = 300, 496
    card = Image.new("RGB", (CW * S, CH * S), "white")
    cd = ImageDraw.Draw(card)
    def T(x, y, t, f, fill, anchor="la"):
        cd.text((x * S, y * S), t, font=f, fill=fill, anchor=anchor)
    T(282, 14, "\uE711", fi(11 * S), (110, 110, 120), "ra")
    T(18, 16, label, fb(17 * S), (20, 30, 70))
    T(18, 40, c["subtitle"], fr(12 * S), (90, 100, 120))
    tb = (18, 64, 282, 174)
    tw_, th_ = (tb[2] - tb[0]) * S, (tb[3] - tb[1]) * S
    cd.rounded_rectangle((tb[0] * S, tb[1] * S, tb[2] * S, tb[3] * S), 8 * S, fill=(244, 247, 251))
    thumb = full_hover.crop(c["thumb"])
    if c.get("thumb_cover"):  # fill the box (dark-background images)
        ts = max(tw_ / thumb.width, th_ / thumb.height)
        thumb = thumb.resize((round(thumb.width * ts), round(thumb.height * ts)), Image.LANCZOS)
        l, t = (thumb.width - tw_) // 2, (thumb.height - th_) // 2
        thumb = thumb.crop((l, t, l + tw_, t + th_))
        tmask = Image.new("L", (tw_, th_), 0)
        ImageDraw.Draw(tmask).rounded_rectangle((0, 0, tw_ - 1, th_ - 1), 8 * S, fill=255)
    else:  # fit inside, knock out white background
        ts = min((tw_ - 8 * S) / thumb.width, (th_ - 8 * S) / thumb.height)
        thumb = thumb.resize((round(thumb.width * ts), round(thumb.height * ts)), Image.LANCZOS)
        tmask = Image.fromarray((np.array(thumb.convert("L")) < 250).astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(1))
    card.paste(thumb, (tb[0] * S + (tw_ - thumb.width) // 2, tb[1] * S + (th_ - thumb.height) // 2), tmask)
    y = 186
    for k, v in c["details"]:
        T(18, y, k, fr(12 * S), (100, 110, 125))
        T(282, y, v, fb(12 * S), (20, 30, 70), "ra")
        y += 20
    cd.line((18 * S, (y + 4) * S, 282 * S, (y + 4) * S), fill=(230, 234, 240), width=S)
    y += 14
    T(18, y, c["section"], fb(10 * S), TEAL)
    y += 22
    for ic, col, t, sub in c["resources"]:
        cd.rounded_rectangle((18 * S, y * S, 48 * S, (y + 30) * S), 7 * S,
                             fill=tuple(int(v * 0.14 + 255 * 0.86) for v in col))
        T(33, y + 15, ic, fi(14 * S), col, "mm")
        T(58, y + 1, t, fb(13 * S), (20, 30, 70))
        T(58, y + 17, sub, fr(11 * S), (110, 118, 132))
        T(282, y + 15, "\uE76C", fi(10 * S), (140, 148, 160), "rm")
        y += 38
    cd.rounded_rectangle((18 * S, (CH - 52) * S, 282 * S, (CH - 18) * S), 6 * S, fill=TEAL)
    T(150, CH - 35, c["button"] + "  \u2192", fb(13 * S), "white", "mm")
    card = card.resize((CW, CH), Image.LANCZOS)
    float_card(base, card, 1036, 110, 1.0)
    return base.convert("RGB")


def equipment():
    """Machine photo, control panel hovered, part/maintenance card."""
    photo = Image.open(SRC / "motorImage.jpeg").convert("RGB")
    # drop the photo's own panel label + leader; the hover pill replaces it
    pd = ImageDraw.Draw(photo)
    pd.rectangle((1915, 175, 2300, 292), fill="white")
    pd.line((1922, 262, 1812, 368), fill="white", width=10)
    a = np.array(photo).astype(int)
    ys, xs = np.where(a.sum(2) < 720)
    photo = photo.crop((xs.min() - 10, ys.min() - 10, xs.max() + 10, ys.max() + 10))
    ox, oy = xs.min() - 10, ys.min() - 10

    # control panel mask (red box, right side)
    p = np.array(photo).astype(int)
    r, g, b = p[..., 0], p[..., 1], p[..., 2]
    red = (r > 110) & (r > g * 2) & (r > b * 2)
    box = np.zeros_like(red)
    box[390 - oy:800 - oy, 1800 - ox:2060 - ox] = True
    mask = Image.fromarray(((red & box) * 255).astype(np.uint8))
    mask = mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(5))

    def dim(ph):
        gray = ph.convert("L").convert("RGB")
        return Image.blend(Image.blend(ph, gray, 0.6), Image.new("RGB", ph.size, "white"), 0.35)

    return hotspot_scene({
        "site": "Equipment", "photo": photo, "mask": mask, "dim": dim,
        "title": "Electrical Control Panel", "subtitle": "3-Roll Plate Bending Machine",
        "thumb": (1400 - ox, 300 - oy, 2110 - ox, 840 - oy),
        "details": [("Part number", "ECP-4471-B"), ("Location", "Bay 3 \u00b7 Line 2"),
                    ("Last serviced", "Sep 12, 2026")],
        "section": "RELATED RESOURCES",
        "resources": [("\ue90f", (196, 43, 28), "Maintenance manual", "PDF \u00b7 4.2 MB"),
                      ("\ue9d5", (14, 112, 120), "Lockout / Tagout SOP", "SharePoint document"),
                      ("\ue714", (107, 64, 196), "Training video", "Stream \u00b7 8 min"),
                      ("\ue8f1", (1, 109, 232), "Spare parts library", "Document library")],
        "button": "Open equipment page",
        "caption": ["Turn equipment photos into visual",
                    "navigation. Hover a component to",
                    "highlight it, click for part details,",
                    "SOPs, manuals and training videos."],
    })


def anatomy():
    """Anatomy figure, liver hovered, training-module card."""
    ox, oy = 160, 110
    photo = Image.open(SRC / "Anatomy.jpeg").convert("RGB").crop((ox, oy, 670, 430))
    liver = [(365, 291), (372, 288), (390, 285), (400, 285), (415, 287), (420, 290),
             (415, 293), (410, 300), (402, 306), (392, 308), (381, 311), (372, 315),
             (366, 316), (364, 308), (363, 298)]
    K = 4  # supersample the polygon for a smooth edge
    big = Image.new("L", (photo.width * K, photo.height * K), 0)
    ImageDraw.Draw(big).polygon([((x - ox) * K, (y - oy) * K) for x, y in liver], fill=255)
    mask = big.resize(photo.size, Image.LANCZOS)
    keep = mask.copy()  # also keep the baked-in "Liver" label bright
    ImageDraw.Draw(keep).rounded_rectangle((213 - ox, 286 - oy, 272 - ox, 313 - oy), 4, fill=255)

    def dim(ph):
        gray = ph.convert("L").convert("RGB")
        return Image.blend(Image.blend(ph, gray, 0.5), Image.new("RGB", ph.size, (18, 44, 84)), 0.4)

    return hotspot_scene({
        "site": "Training", "photo": photo, "mask": mask, "keep": keep, "dim": dim,
        "pill": False, "dot": False, "cursor": (14, 4), "radius": 10, "px": 360,
        "title": "Liver", "subtitle": "Digestive system \u00b7 Module 4",
        "thumb": (300 - ox, 262 - oy, 480 - ox, 337 - oy), "thumb_cover": True,
        "details": [("Course", "Anatomy Fundamentals"), ("Lesson length", "25 min"),
                    ("Progress", "2 of 5 lessons")],
        "section": "LEARNING RESOURCES",
        "resources": [("\ue714", (107, 64, 196), "Lesson video", "Stream \u00b7 12 min"),
                      ("\ue8a5", (196, 43, 28), "Liver structure & function", "PDF reading \u00b7 12 pages"),
                      ("\ue9d5", (14, 112, 120), "Knowledge check", "Microsoft Forms \u00b7 10 questions"),
                      ("\ue7be", (1, 109, 232), "Course page", "SharePoint page")],
        "button": "Start lesson",
        "caption": ["Bring anatomy and medical",
                    "training to life. Hover a structure",
                    "to highlight it, click to open",
                    "lessons, readings and quizzes."],
    })


if __name__ == "__main__":
    import sys
    if "anatomy" in sys.argv:
        im = anatomy()
        assert im.size == (1366, 768)
        im.save(SRC / "IH_AnatomyTraining_1366x768.png")
        print("wrote", SRC / "IH_AnatomyTraining_1366x768.png")
        sys.exit()
    if "equipment" in sys.argv:
        im = equipment()
        assert im.size == (1366, 768)
        im.save(SRC / "IH_EquipmentHotspots_1366x768.png")
        print("wrote", SRC / "IH_EquipmentHotspots_1366x768.png")
        sys.exit()
    if "canvas" in sys.argv:
        im = canvas_config()
        assert im.size == (1366, 768)
        im.save(SRC / "IH_CanvasConfig_1366x768.png")
        print("wrote", SRC / "IH_CanvasConfig_1366x768.png")
        sys.exit()
    OUT.mkdir(exist_ok=True)
    for name, im in (("IH_SharePointMapMockup_1366x768.png", map_mockup()),
                     ("IH_DashboardShowcase_1366x768.png", showcase())):
        if im.size != (1366, 768):
            im = im.resize((1366, 768), Image.LANCZOS)
        im.save(OUT / name)
        print("wrote", OUT / name, im.size)
