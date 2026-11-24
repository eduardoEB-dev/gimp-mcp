"""Stitch raw demo panels into captioned figures (JPEG) + sizes.json; also a contact sheet for review.
usage: python -I compose.py <raw_dir> <jpg_dir> [sheet.png]"""
import sys, os, json, glob
from PIL import Image, ImageDraw, ImageFont

RAW, JPG = sys.argv[1], sys.argv[2]; SHEET = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(JPG, exist_ok=True)
F = lambda s, b=False: ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if b else "C:/Windows/Fonts/segoeui.ttf", s)
INK, MUTED, ACC = (31, 41, 51), (91, 102, 112), (232, 125, 13)
sizes_f = os.path.join(JPG, "sizes.json"); sizes = json.load(open(sizes_f)) if os.path.exists(sizes_f) else {}

def wrap(d, text, font, w):
    out, line = [], ""
    for word in text.split():
        t = (line + " " + word).strip()
        if d.textlength(t, font=font) <= w: line = t
        else: out.append(line); line = word
    return out + [line] if line else out

def flat(im):
    im = im.convert("RGBA"); bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); return Image.alpha_composite(bg, im).convert("RGB")

NOARROW = {"extrude_opts", "recess", "shading", "topology", "views", "viewshade", "select_modes", "align", "transform", "origin", "bevel"}
figs = []
for jf in sorted(glob.glob(os.path.join(RAW, "*.json"))):
    name = os.path.basename(jf)[:-5]; meta = json.load(open(jf)); caps = meta["captions"]
    ims = [(flat(Image.open(os.path.join(RAW, f"{name}__{i}.png"))), c) for i, c in enumerate(caps) if c is not None and os.path.exists(os.path.join(RAW, f"{name}__{i}.png"))]
    if name == "cover":
        im = ims[0][0]; im.save(os.path.join(JPG, "cover.jpg"), quality=88); sizes["cover"] = im.size; continue
    n = len(ims); cols = min(n, meta.get("cols", 3)); rows = (n + cols - 1) // cols
    PW = {1: 1300, 2: 900, 3: 700, 4: 560}[cols]; PH = PW * 3 // 4; gap = 40 if n > 1 else 0
    font = F(30 if cols < 4 else 26); fb = F(30 if cols < 4 else 26, True)
    d0 = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    caph = max(len(wrap(d0, c, font, PW - 30)) for _, c in ims) * 40 + 30
    W = cols * PW + (cols - 1) * gap; H = rows * (PH + caph)
    out = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(out)
    for i, (im, c) in enumerate(ims):
        r, k = divmod(i, cols); x, y = k * (PW + gap), r * (PH + caph)
        out.paste(im.resize((PW, PH), Image.LANCZOS), (x, y))
        d.rectangle([x, y, x + PW - 1, y + PH - 1], outline=(214, 218, 223), width=2)
        if n > 1:
            tag = str(i + 1); d.ellipse([x + 14, y + 14, x + 62, y + 62], fill=ACC); d.text((x + 38, y + 38), tag, font=F(28, True), fill="white", anchor="mm")
        for j, line in enumerate(wrap(d, c, font, PW - 30)):
            d.text((x + PW // 2, y + PH + 18 + j * 40), line, font=font, fill=INK, anchor="ma")
        if n > 1 and k < cols - 1 and i < n - 1 and name not in NOARROW:
            cx, cy = x + PW + gap // 2, y + PH // 2
            d.polygon([(cx - 14, cy - 22), (cx + 16, cy), (cx - 14, cy + 22)], fill=ACC)
    out.save(os.path.join(JPG, name + ".jpg"), quality=85, optimize=True, progressive=True); sizes[name] = out.size; figs.append((name, out))

json.dump(sizes, open(sizes_f, "w"), indent=1)
if SHEET and figs:
    th = [(n, f.resize((800, round(800 * f.height / f.width)))) for n, f in figs]
    c = 3; colh = []
    W = c * 820; rows = [th[i:i + c] for i in range(0, len(th), c)]
    H = sum(max(t.height for _, t in r) + 50 for r in rows)
    S = Image.new("RGB", (W, H), (120, 120, 120)); d = ImageDraw.Draw(S); y = 0
    for r in rows:
        for k, (n, t) in enumerate(r): S.paste(t, (k * 820, y + 40)); d.text((k * 820 + 5, y + 5), n, font=F(28, True), fill="white")
        y += max(t.height for _, t in r) + 50
    S.save(SHEET); print("SHEET", SHEET)
print("FIGS", len(figs))
