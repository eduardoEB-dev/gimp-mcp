import sys
from PIL import Image, ImageFilter, ImageDraw, ImageFont
src, out, prev = sys.argv[1:4]
S = float(sys.argv[4]) if len(sys.argv) > 4 else 1.35
W, H = 2560, 1440
im = Image.open(src).convert("RGB")
w, h = im.size
sw, sh = round(w*S), round(h*S)
big = im.resize((sw, sh), Image.LANCZOS)
# center key content (logo+tagline band y~185-455, x center ~1012) on safe area center
cy, cx = 320*S, 1012*S
ox, oy = round(W/2 - cx), round(H/2 - cy)
# background: blurred stretch of full image covering canvas
# fill: stretch edge strips of scaled image into top/bottom pads, then blur
F = 200
canvas = Image.new("RGB", (W, H))
row = big.crop((-ox, 0, -ox+W, 8)).resize((W, 1), Image.BOX).filter(ImageFilter.GaussianBlur(25)).resize((W, oy + F))
canvas.paste(row.filter(ImageFilter.GaussianBlur(30)), (0, 0))
bpad = H - (oy + sh) + F
if bpad > 0:
    row = big.crop((-ox, sh-8, -ox+W, sh)).resize((W, 1), Image.BOX).filter(ImageFilter.GaussianBlur(25)).resize((W, bpad))
    canvas.paste(row.filter(ImageFilter.GaussianBlur(30)), (0, oy+sh-F))
# feather mask for edges of pasted image (top/bottom only)
mask = Image.new("L", (sw, sh), 255)
d = ImageDraw.Draw(mask)
for i in range(F):
    a = int(255*i/F)
    if oy > 0: d.line([(0, i), (sw, i)], fill=a)
    if oy + sh < H: d.line([(0, sh-1-i), (sw, sh-1-i)], fill=a)
canvas.paste(big, (ox, oy), mask)

# shift right-side app icons down into desktop band (rects in source px)
import numpy as np
ICON_SHIFT = 105  # output px
ICONS = [(1523,108,1620,205),(1675,108,1772,205),(1825,108,1905,205),
         (1548,245,1631,325),(1681,245,1762,325),(1818,245,1892,325)]
PAD = 22
a = np.asarray(canvas).astype(np.float32)
m = np.ones(a.shape[:2], np.float32)
rects = []
for x0, y0, x1, y1 in ICONS:
    r = (round(x0*S)+ox-PAD, round(y0*S)+oy-PAD, round(x1*S)+ox+PAD, round(y1*S)+oy+PAD)
    rects.append(r); m[r[1]:r[3], r[0]:r[2]] = 0
# normalized blur for clean wall behind icons
mi = Image.fromarray((m*255).astype(np.uint8))
mb = np.asarray(mi.filter(ImageFilter.GaussianBlur(45)), np.float32)/255
am = Image.fromarray((a*m[..., None]).astype(np.uint8))
ab = np.asarray(am.filter(ImageFilter.GaussianBlur(45)), np.float32)
clean = ab/np.maximum(mb, 1e-3)[..., None]
# icon-shaped mask: pixels differing from clean wall, dilated + softened
d = np.abs(a - clean).max(axis=2) * (1 - m)
M = Image.fromarray((np.clip(d/12, 0, 1)*255).astype(np.uint8))
M = M.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(8))
M = np.clip(np.asarray(M, np.float32)[..., None]/255*2, 0, 1)
a2 = a*(1-M) + clean*M
# paste icons shifted down using same mask
Ms = np.zeros_like(M); As = np.zeros_like(a)
Ms[ICON_SHIFT:] = M[:-ICON_SHIFT]; As[ICON_SHIFT:] = a[:-ICON_SHIFT]
a2 = a2*(1-Ms) + As*Ms
out_im = Image.fromarray(np.clip(a2, 0, 255).astype(np.uint8))
canvas = out_im

# replace tagline: erase old text, draw new (Montserrat, spaced caps, blue separators)
import os
TAGLINE = ["CODE", "AUTOMATE", "BUILD"]
SEP = "-"
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "Montserrat.ttf")
tx0, ty0, tx1, ty1 = 715, 418, 1270, 452  # old tagline box, source px
r = (round(tx0*S)+ox, round(ty0*S)+oy, round(tx1*S)+ox, round(ty1*S)+oy)
a = np.asarray(canvas).astype(np.float32)
m = np.ones(a.shape[:2], np.float32); m[r[1]:r[3], r[0]:r[2]] = 0
mb = np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(30)), np.float32)/255
ab = np.asarray(Image.fromarray((a*m[..., None]).astype(np.uint8)).filter(ImageFilter.GaussianBlur(30)), np.float32)
clean = ab/np.maximum(mb, 1e-3)[..., None]
hm = np.asarray(Image.fromarray(((1-m)*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)), np.float32)[..., None]/255
canvas = Image.fromarray(np.clip(a*(1-hm) + clean*hm, 0, 255).astype(np.uint8))
font = ImageFont.truetype(FONT, round(26*S)); font.set_variation_by_name("Medium")
TRACK = round(0.24*font.size)      # letter spacing
GAP = round(30*S)                  # space each side of slash
def word_w(w):
    return sum(font.getlength(ch) for ch in w) + TRACK*(len(w)-1)
slash_w = font.getlength(SEP)
total = sum(word_w(w) for w in TAGLINE) + (len(TAGLINE)-1)*(slash_w + 2*GAP)
cx_t = round(992.5*S)+ox
base = round(444*S)+oy                 # baseline
d = ImageDraw.Draw(canvas)
x = cx_t - total/2
for i, w in enumerate(TAGLINE):
    for ch in w:
        d.text((x, base), ch, font=font, fill=(240, 244, 250), anchor="ls")
        x += font.getlength(ch) + TRACK
    x -= TRACK
    if i < len(TAGLINE)-1:
        x += GAP
        d.text((x, base), SEP, font=font, fill=(90, 170, 235), anchor="ls")
        x += slash_w + GAP
canvas.save(out, quality=93, subsampling=0)
# preview with guides
p = canvas.copy(); d = ImageDraw.Draw(p)
def box(bw, bh, c):
    x0, y0 = (W-bw)//2, (H-bh)//2
    d.rectangle([x0, y0, x0+bw, y0+bh], outline=c, width=6)
box(2560, 423, (0, 200, 255)); box(1546, 423, (255, 60, 60)); box(1235, 338, (255, 220, 0))
p.resize((1280, 720)).save(prev)
print("offset", ox, oy, "scaled", sw, sh)
