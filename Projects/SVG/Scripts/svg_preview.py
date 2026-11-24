"""Quick PNG preview of simple SVG paths (M/L/C/Q/Z, absolute), even-odd fill.
No browser needed. Handles one <path> or many; ignores transforms/styles.

usage: python svg_preview.py <in.svg> <out.png> [--height 900] [--outline]
"""
import argparse
import re

from PIL import Image, ImageChops, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out")
ap.add_argument("--height", type=int, default=900)
ap.add_argument("--outline", action="store_true", help="draw on-curve points")
args = ap.parse_args()

svg = open(args.src, encoding="utf-8").read()
vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
m_ = re.search(r"#[0-9A-Fa-f]{6}", svg)
color = m_.group(0) if m_ else "#D2232A"
sc = args.height / vb[3]
W, H = round(vb[2] * sc), args.height


def tx(p):
    return ((p[0] - vb[0]) * sc, (p[1] - vb[1]) * sc)


contours, knots = [], []
for d in re.findall(r'\sd="([^"]+)"', svg):
    cur, start, poly = (0, 0), (0, 0), []
    for cmd, a in re.findall(r"([MLCQZ])([^MLCQZ]*)", d):
        n = [float(v) for v in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", a)]
        pts = list(zip(n[0::2], n[1::2]))
        if cmd == "M":
            if len(poly) > 2:
                contours.append(poly)
            cur = start = pts[0]
            poly = [cur]
        elif cmd == "L":
            for p in pts:
                poly.append(p)
                cur = p
        elif cmd in "CQ":
            k = 3 if cmd == "C" else 2
            for i in range(0, len(pts), k):
                seg = [cur] + pts[i:i + k]
                for j in range(1, 25):
                    t, u = j / 24, 1 - j / 24
                    if k == 3:
                        poly.append(tuple(u**3 * seg[0][q] + 3 * u * u * t * seg[1][q] + 3 * u * t * t * seg[2][q] + t**3 * seg[3][q] for q in (0, 1)))
                    else:
                        poly.append(tuple(u * u * seg[0][q] + 2 * u * t * seg[1][q] + t * t * seg[2][q] for q in (0, 1)))
                cur = seg[-1]
                knots.append(cur)
        else:
            if len(poly) > 2:
                contours.append(poly)
            poly, cur = [], start
    if len(poly) > 2:
        contours.append(poly)

mask = Image.new("1", (W, H), 0)
for c in contours:   # even-odd via XOR
    m = Image.new("1", (W, H), 0)
    ImageDraw.Draw(m).polygon([tx(p) for p in c], fill=1)
    mask = ImageChops.logical_xor(mask, m)
img = Image.new("RGB", (W, H), "white")
img.paste(Image.new("RGB", (W, H), color), mask=mask)
if args.outline:
    dr = ImageDraw.Draw(img)
    for p in knots:
        x, y = tx(p)
        dr.ellipse((x - 1.5, y - 1.5, x + 1.5, y + 1.5), fill="blue")
img.save(args.out)
print(f"{args.out} {W}x{H}, {len(contours)} contours")
