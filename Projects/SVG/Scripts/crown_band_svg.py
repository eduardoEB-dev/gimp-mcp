"""Penelope crown: front band scroll ornament (no laurel leaves, no beads).
Center: mirrored double volute + upward tip. Sides: running vine scroll
(wave stem, alternating curls, small leaves) ending in a curl.
Merged into one outline (Blender-friendly). Optional straight rails file.

usage: python crown_band_svg.py <out.svg> [--rails rails.svg] [--color #C9A227] [--height 600]
"""
import argparse
import math
import os

import pathops

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--rails", help="also write top/bottom rail strips to this file")
ap.add_argument("--color", default="#C9A227")
ap.add_argument("--height", type=int, default=600, help="output px height")
args = ap.parse_args()

H = 200                 # band height (ornament lives in y 0..H)
STEM_W = 15             # vine stem width
P = 340                 # wave period
A = 45                  # wave amplitude
X0 = 60                 # wave starts here (at a low point)
N_HALF = 4              # half-periods per side after X0 (even: ends in a curl)
VOLUTE = dict(c=(68, 118), R=48, th0=95, sweep=470, w0=15, w1=9)
CURL = dict(R=40, th0=90, sweep=500, w0=13, w1=8)
LEAF = dict(L=72, W=14, ang=-50)
RAIL_W, RAIL_GAP = 22, 8


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def catmull(pts):
    n = len(pts)
    sp = pathops.Path()
    sp.moveTo(*pts[0])
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        sp.cubicTo(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                   p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, *p2)
    sp.close()
    return sp


def stroke(pts, widths, step=7, cap_end=True):
    """Variable-width stroke along a dense centerline, round caps."""
    keep = [0]
    for i in range(1, len(pts)):
        if math.dist(pts[i], pts[keep[-1]]) >= step:
            keep.append(i)
    if keep[-1] != len(pts) - 1:
        keep.append(len(pts) - 1)
    L, R = [], []
    for i in keep:
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        m = math.hypot(tx, ty)
        tx, ty = tx / m, ty / m
        w = widths[i] / 2
        L.append((pts[i][0] + ty * w, pts[i][1] - tx * w))
        R.append((pts[i][0] - ty * w, pts[i][1] + tx * w))

    def cap(p, q, w, n=5):   # semicircle from L-side to R-side around p, bulging away from q
        a0 = math.atan2(p[1] - q[1], p[0] - q[0])
        return [(p[0] + w * math.cos(a0 + math.pi / 2 - math.pi * k / (n + 1)),
                 p[1] + w * math.sin(a0 + math.pi / 2 - math.pi * k / (n + 1))) for k in range(1, n + 1)]
    end = cap(pts[-1], pts[-2], widths[-1] / 2)[::-1] if cap_end else []
    start = cap(pts[0], pts[1], widths[0] / 2)[::-1]
    sp = catmull(L + end + R[::-1] + start)
    sp.simplify(fix_winding=True)
    return sp


def circle(c, r, n=16):
    sp = catmull([(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)])
    sp.simplify(fix_winding=True)
    return sp


def spiral(c, R, th0, sweep, w0, w1, n=200, lead=()):
    """Spiral from angle th0 (deg, screen coords), angle decreasing, radius R -> 0.25R.
    `lead` = centerline points prepended (stem flowing into the curl)."""
    pts, ws = list(lead), [w0] * len(lead)
    for k in range(n + 1):
        t = k / n
        th = math.radians(th0 - sweep * t)
        r = R * (1 - 0.75 * t)
        pts.append((c[0] + r * math.cos(th), c[1] + r * math.sin(th)))
        ws.append(w0 + (w1 - w0) * t)
    return [stroke(pts, ws), circle(pts[-1], w1 * 0.9)]


def leaf(base, ang, L, W, neck=0.45, n=24):
    a = math.radians(ang)
    tx, ty = math.cos(a), math.sin(a)
    Lp, Rp = [], []
    for k in range(n + 1):
        t = (1 - math.cos(math.pi * k / n)) / 2
        w = W * (4 * t * (1 - t)) ** 0.75 + neck * W * (1 - t) ** 3
        x, y = base[0] + (t - 0.04) * L * tx, base[1] + (t - 0.04) * L * ty
        Lp.append((x + ty * w, y - tx * w))
        Rp.append((x - ty * w, y + tx * w))
    sp = catmull(Lp[:-1] + [Lp[-1]] + Rp[::-1][1:])
    sp.simplify(fix_winding=True)
    return sp


def rot180(sp, c):
    """Point-reflect a path through c."""
    out = pathops.Path()
    pen = out.getPen()
    t = lambda p: (2 * c[0] - p[0], 2 * c[1] - p[1])
    for verb, ps in sp:
        ps = [t(p) for p in ps]
        {pathops.PathVerb.MOVE: lambda: pen.moveTo(*ps), pathops.PathVerb.LINE: lambda: pen.lineTo(*ps),
         pathops.PathVerb.CUBIC: lambda: pen.curveTo(*ps), pathops.PathVerb.QUAD: lambda: pen.qCurveTo(*ps),
         pathops.PathVerb.CLOSE: lambda: pen.closePath()}[verb]()
    out.simplify(fix_winding=True)
    return out


def mirror_x(sp):
    out = pathops.Path()
    pen = out.getPen()
    for verb, ps in sp:
        ps = [(-x, y) for x, y in ps]
        {pathops.PathVerb.MOVE: lambda: pen.moveTo(*ps), pathops.PathVerb.LINE: lambda: pen.lineTo(*ps),
         pathops.PathVerb.CUBIC: lambda: pen.curveTo(*ps), pathops.PathVerb.QUAD: lambda: pen.qCurveTo(*ps),
         pathops.PathVerb.CLOSE: lambda: pen.closePath()}[verb]()
    out.simplify(fix_winding=True)
    return out


# ---------------- right half ----------------
parts = []

# center volute: tail from x=0 along the bottom, curling up and inward
v = VOLUTE
s0 = (v["c"][0] + v["R"] * math.cos(math.radians(v["th0"])), v["c"][1] + v["R"] * math.sin(math.radians(v["th0"])))
lead = [(x, 170 + (s0[1] - 170) * x / s0[0]) for x in range(-4, int(s0[0]), 2)]
parts += spiral(v["c"], v["R"], v["th0"], v["sweep"], v["w0"], v["w1"], lead=lead)

# center tip (drawn full, both halves) - drop pointing up between the volutes
tip = leaf((0, 160), -90, 115, 13, neck=0.5)

# vine wave: blends from the volute tail (y=172 at x=0) into the wave
xe = X0 + N_HALF * P / 2           # last half-period ends at a low point -> final curl


def wave_y(x):
    w = min(max(x / (X0 + 60), 0), 1)
    w = w * w * (3 - 2 * w)
    return (1 - w) * 172 + w * (100 + A * math.cos(2 * math.pi * (x - X0) / P))


# curls: crest (k odd) -> curl below, low point (k even, k>0) -> curl above
lows = [X0 + k * P / 2 for k in range(1, N_HALF + 1)]
stem_pts = [(x / 2, wave_y(x / 2)) for x in range(-8, int(2 * xe) + 1)]
parts.append(stroke(stem_pts, [STEM_W] * len(stem_pts)))
for k, xb in enumerate(lows, start=1):
    if k % 2 == 0:   # low point: curl above (the last one is the stem's terminal curl)
        c = CURL
        parts += spiral((xb, wave_y(xb) - c["R"]), c["R"], c["th0"], c["sweep"], c["w0"], c["w1"])
    else:            # crest: same curl rotated 180 about the wave center line
        c = CURL
        xm = xb - P / 2   # mirror low point of this crest
        for sp in spiral((xm, 100 + A - c["R"]), c["R"], c["th0"], c["sweep"], c["w0"], c["w1"]):
            parts.append(rot180(sp, (xb - P / 4, 100)))

# leaves on the stem: above on descending runs, rotated copy below on ascending runs
for k in range(1, N_HALF):
    xc = X0 + k * P / 2 + P / 4    # zero crossing after the k-th extreme
    if xc > xe - P / 4:
        break
    base = (xc, wave_y(xc))
    lf = leaf(base, LEAF["ang"], LEAF["L"], LEAF["W"])
    parts.append(lf if k % 2 == 1 else rot180(lf, base))

right = None
for sp in parts:
    right = sp if right is None else pathops.op(right, sp, pathops.PathOp.UNION)
merged = pathops.op(right, mirror_x(right), pathops.PathOp.UNION)
merged = pathops.op(merged, tip, pathops.PathOp.UNION)

VERB = {pathops.PathVerb.MOVE: "M", pathops.PathVerb.LINE: "L", pathops.PathVerb.QUAD: "Q",
        pathops.PathVerb.CUBIC: "C", pathops.PathVerb.CLOSE: "Z"}


def to_d(sp):
    return " ".join(VERB[v] + " ".join(f"{f(x)},{f(y)}" for x, y in pts) for v, pts in sp)


xs = [p[0] for _, ps in merged for p in ps]
ys = [p[1] for _, ps in merged for p in ps]
WX = max(abs(min(xs)), max(xs)) + 10
top, bot = (-RAIL_GAP - RAIL_W, H + RAIL_GAP + RAIL_W) if args.rails else (min(ys) - 10, max(ys) + 10)
vb = (-WX, top - 10, 2 * WX, bot - top + 20)
oh = args.height
ow = round(oh * vb[2] / vb[3])


def write(path, d, title):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ow}" height="{oh}" viewBox="{" ".join(f(v) for v in vb)}">\n'
           f'  <title>{title}</title>\n  <path fill="{args.color}" d="{d}"/>\n</svg>\n')
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    open(path, "w", encoding="utf-8").write(svg)
    print("wrote", os.path.abspath(path), f"{ow}x{oh}")


write(args.out, to_d(merged), "Crown band scroll")
print("contours", sum(1 for v, _ in merged if v == pathops.PathVerb.MOVE), "ornament y", f(min(ys)), f(max(ys)))
if args.rails:
    r = pathops.Path()
    for y0 in (-RAIL_GAP - RAIL_W, H + RAIL_GAP):
        r.moveTo(-WX, y0); r.lineTo(WX, y0); r.lineTo(WX, y0 + RAIL_W); r.lineTo(-WX, y0 + RAIL_W); r.close()
    write(args.rails, to_d(r), "Crown band rails")
