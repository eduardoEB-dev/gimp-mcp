"""Write text in the PEANUTS logo lettering (PeanutsFont.png) as Bambu Studio
layers: White letters + Red outline (one solid backing, counters filled).

Letters in the logo (P E A N U T S) are cut straight from it; missing ones are
assembled from their strokes so stroke weight and wobble match:
  I = E stem, H = E stem + mirrored stem + E middle arm, M = left half of N +
  its mirror, R = P + A right leg, C = U widened at the bowl, cut down and
  rotated, Y = A apex flipped (V) + T stem.

usage: python peanuts_text_svg.py <PeanutsFont.png> <out_dir> [--lines "MERRY|CHRISTMAS"]
       [--mm 90] [--outline 13] [--sheet layout.png]
"""
import argparse
import os
import re
import tempfile

import numpy as np
import vtracer
from PIL import Image, ImageFilter
from scipy import ndimage

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out_dir")
ap.add_argument("--lines", default="MERRY|CHRISTMAS", help="text lines, | separated")
ap.add_argument("--name", default="MerryChristmas")
ap.add_argument("--title", default="Merry Christmas")
ap.add_argument("--mm", type=float, default=90.0, help="output width in mm")
ap.add_argument("--outline", type=float, default=13, help="red outline width in source px (cap ~205px)")
ap.add_argument("--gap", type=int, default=16, help="white gap between letters, source px")
ap.add_argument("--up", type=int, default=4)
ap.add_argument("--blur", type=float, default=0.9)
ap.add_argument("--white", default="#FFFFFF")
ap.add_argument("--red", default="#D2232A")
ap.add_argument("--sheet", help="save raster preview of the layout")
args = ap.parse_args()

rgb = np.asarray(Image.open(args.src).convert("RGB")).astype(float)
sat = rgb.max(-1) - rgb.min(-1)
lum = rgb.mean(-1)
# white face + grey inner shading, soft edge
SOFT = np.clip((lum - 120) / 60, 0, 1) * np.clip((60 - sat) / 30, 0, 1)
SOFT[:110] = 0
SOFT[380:] = 0
LAB, _ = ndimage.label(SOFT > 0.5)


def trim(g):
    ys, xs = np.where(g > 0.05)
    return g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


# the 7 biggest face components, left to right = P E A N U T S
_sz = ndimage.sum(SOFT > 0.5, LAB, range(1, LAB.max() + 1))
_ids = 1 + np.argsort(-_sz)[:7]
_ids = sorted(_ids, key=lambda i: np.where((LAB == i).any(0))[0][0])


def letter(i):
    m = ndimage.binary_dilation(LAB == _ids[i], iterations=2)
    return trim(SOFT * m)


def runs(row, th=0.5):
    """[(start, end)] of filled spans in a row"""
    b = np.concatenate([[0], (row > th).astype(int), [0]])
    d = np.diff(b)
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def place(canvas, g, x, y):
    h, w = g.shape
    canvas[y:y + h, x:x + w] = np.maximum(canvas[y:y + h, x:x + w], g)


def resize(g, sx, sy):
    h, w = g.shape
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((max(1, round(w * sx)), max(1, round(h * sy))), Image.BICUBIC)
    return np.asarray(im).astype(float) / 255


# --- glyphs straight off the logo ----------------------------------------
P, E, A, N, U, T, S = (letter(i) for i in range(7))
CAP = int(np.median([g.shape[0] for g in (P, E, A, N, U, T, S)]))

# --- assembled glyphs ----------------------------------------------------
eh, ew = E.shape
# stem width = first-run length on rows that hold only the stem (between arms)
single = [runs(E[y]) for y in range(eh)]
sw = int(np.median([r[0][1] - r[0][0] for r in single if len(r) == 1]))


I = trim(E[:, :sw + 4])  # E's left stem (arm stubs lie inside the stem width)

# E middle arm: rows in the middle third whose first run is long
mid = [y for y in range(eh // 3, 2 * eh // 3) if single[y] and single[y][0][1] - single[y][0][0] > 2 * sw]
ARM = trim(E[min(mid) - 2:max(mid) + 3, sw:])

HW = N.shape[1]
H = np.zeros((CAP + 4, HW))
place(H, I[:CAP + 4], 0, 0)
place(H, I[:CAP + 4, ::-1], HW - I.shape[1], 0)
bar = ARM[:, :HW - 2 * sw + 8]
place(H, bar, sw - 4, (CAP - bar.shape[0]) // 2)
H = trim(H)

nh, nw = N.shape
half = trim(N[:, :nw // 2 + 2])
M = np.zeros((nh, 2 * half.shape[1] - 4))
place(M, half, 0, 0)
place(M, half[:, ::-1], M.shape[1] - half.shape[1], 0)
M = trim(M)

# A crossbar = middle-height rows with a single wide run
ah, aw = A.shape
arows = [runs(A[y]) for y in range(ah)]
cross = [y for y in range(ah // 4, ah) if len(arows[y]) == 1 and arows[y][0][1] - arows[y][0][0] > aw * 0.45]
cb0, cb1 = min(cross), max(cross)

# R = P + A's right leg below the crossbar
ph, pw = P.shape
cnt = ndimage.binary_fill_holes(P > 0.5) & ~(P > 0.5)   # P's counter
bowl_end = np.where(cnt.any(1))[0].max() + sw  # bottom of the bowl's lower stroke
# A's right stroke over the needed height: per row keep the rightmost span,
# clipped to the leg width (cuts the crossbar off)
L = ph - bowl_end + sw
lw = int(np.median([r[-1][1] - r[-1][0] for r in arows[cb1 + 1:] if len(r) == 2]))
leg = np.zeros((L, aw))
for i, y in enumerate(range(ah - L, ah)):
    r = runs(A[y], 0.05)
    if r:
        e = r[-1][1]
        leg[i, e - min(r[-1][1] - r[-1][0], lw + 2):e] = A[y, e - min(r[-1][1] - r[-1][0], lw + 2):e]
leg = trim(leg)
R = np.zeros((ph, max(pw, int(pw * 0.30) + leg.shape[1])))
place(R, P, 0, 0)
place(R, leg, int(pw * 0.30), ph - leg.shape[0])
R = trim(R)

# C: U widened in the middle of its bowl, arms cut, rotated (opening right)
uh, uw = U.shape
cw_target = int(CAP * 0.72)          # C width (before rotation = U height)
mc = uw // 2
Uw = np.concatenate([U[:, :mc], np.repeat(U[:, mc:mc + 1], CAP - uw, 1), U[:, mc:]], 1)
C = np.rot90(Uw[uh - cw_target:], k=-1)
C = trim(C)

# Y: A apex (above crossbar) flipped into a V, plus T's stem
V = trim(A[:cb0][::-1])
th_, tw = T.shape
trows = [runs(T[y]) for y in range(th_)]
bar_end = max(y for y in range(th_ // 2) if trows[y] and trows[y][0][1] - trows[y][0][0] > tw * 0.5)
TS = trim(T[bar_end + 2:])
yw = max(V.shape[1], TS.shape[1])
Y = np.zeros((CAP, yw))
place(Y, V, (yw - V.shape[1]) // 2, 0)
ts = TS[-(CAP - V.shape[0] + sw):]
place(Y, ts, (yw - ts.shape[1]) // 2, CAP - ts.shape[0])
Y = trim(Y)

GLYPHS = dict(P=P, E=E, A=A, N=N, U=U, T=T, S=S, I=I, H=H, M=M, R=R, C=C, Y=Y)

# --- layout ----------------------------------------------------------------
LINES = args.lines.split("|")
O = int(np.ceil(args.outline))
LEAD = 2 * O


def line_img(text):
    parts, x = [], 0
    for ch in text:
        if ch == " ":
            x += CAP // 3
            continue
        g = GLYPHS[ch]
        parts.append((g, x))
        x += g.shape[1] + args.gap
    hmax = max(g.shape[0] for g, _ in parts)
    img = np.zeros((hmax, x - args.gap))
    for g, gx in parts:
        place(img, g, gx, (hmax - g.shape[0]) // 2)
    return img


rows = [line_img(t) for t in LINES]
pad = O + 6
Wd = max(r.shape[1] for r in rows) + 2 * pad
Hd = sum(r.shape[0] for r in rows) + LEAD * (len(rows) - 1) + 2 * pad
page = np.zeros((Hd, Wd))
y = pad
for r in rows:
    place(page, r, (Wd - r.shape[1]) // 2, y)
    y += r.shape[0] + LEAD

# --- layers at supersampled res -------------------------------------------
up = args.up
big = Image.fromarray((page * 255).astype(np.uint8)).resize((Wd * up, Hd * up), Image.BICUBIC)
white = np.asarray(big.filter(ImageFilter.GaussianBlur(args.blur * up))) > 127
yy, xx = np.mgrid[-O * up:O * up + 1, -O * up:O * up + 1]
disk = xx * xx + yy * yy <= (args.outline * up) ** 2
# outline = dilated letters, holes filled -> one solid backing; smooth its edge
back = ndimage.binary_dilation(white[::2, ::2], structure=disk[::2, ::2])
holes = ndimage.binary_fill_holes(back) & ~back   # fill only slivers between letters, keep counters open
hl, hn = ndimage.label(holes)
if hn:
    hs = ndimage.sum(holes, hl, range(1, hn + 1))
    back |= np.isin(hl, 1 + np.where(hs < (O * up // 2) ** 2 * 3)[0])
back = np.asarray(Image.fromarray((back * 255).astype(np.uint8)).resize((Wd * up, Hd * up), Image.BICUBIC)
                  .filter(ImageFilter.GaussianBlur(2 * up))) > 127
red = back & ~white

if args.sheet:
    pv = np.zeros(white.shape + (3,), np.uint8)
    pv[:] = (125, 185, 230)
    pv[red] = (210, 35, 42)
    pv[white] = 255
    im = Image.fromarray(pv)
    im.thumbnail((1400, 1400))
    im.save(args.sheet)


# --- trace ------------------------------------------------------------------
def bake(p):
    t = re.search(r'translate\(([-\d.]+),([-\d.]+)\)', p)
    dx, dy = (float(t.group(1)), float(t.group(2))) if t else (0, 0)
    d = re.search(r'\sd="([^"]+)"', p).group(1)
    out, i = [], 0
    for tok in re.findall(r"[A-Za-z]|-?\d*\.?\d+(?:e-?\d+)?", d):
        if tok.isalpha():
            out.append(tok); i = 0
        else:
            out.append(f"{float(tok) + (dx if i % 2 == 0 else dy):.1f}"); i += 1
    return " ".join(out)


def trace(mask):
    tmp = tempfile.mkdtemp()
    mp, sp = os.path.join(tmp, "m.png"), os.path.join(tmp, "m.svg")
    Image.fromarray(np.where(mask, 0, 255).astype(np.uint8)).convert("RGB").save(mp)
    vtracer.convert_image_to_svg_py(mp, sp, colormode="binary", mode="spline",
                                    filter_speckle=up * up * 4, corner_threshold=90,
                                    length_threshold=8.0, splice_threshold=45, path_precision=1)
    return [bake(p) for p in re.findall(r"<path[^>]*/>", open(sp, encoding="utf-8").read())]


# identical width/height/viewBox in every file so layers line up in Bambu
BW, BH = Wd * up, Hd * up
mmh = args.mm * BH / BW
head = f'<svg xmlns="http://www.w3.org/2000/svg" width="{args.mm:.2f}mm" height="{mmh:.2f}mm" viewBox="0 0 {BW} {BH}">\n'
os.makedirs(args.out_dir, exist_ok=True)
groups = []
for nm, hexc, mask in (("Red", args.red, red), ("White", args.white, white)):
    paths = trace(mask)
    grp = (f'  <g fill="{hexc}" fill-rule="evenodd">\n'
           + "".join(f'    <path d="{d}"/>\n' for d in paths) + "  </g>\n")
    groups.append(grp)
    out = os.path.join(args.out_dir, f"{args.name}_{nm}.svg")
    open(out, "w", encoding="utf-8").write(head + f"  <title>{args.title} {nm}</title>\n" + grp + "</svg>\n")
    print(f"{nm}: {len(paths)} paths -> {out}")
open(os.path.join(args.out_dir, f"{args.name}_AllColors_preview.svg"), "w", encoding="utf-8").write(
    head + f"  <title>{args.title}</title>\n" + "".join(groups) + "</svg>\n")
print(f"canvas {BW}x{BH} -> {args.mm:.1f}x{mmh:.1f}mm")
