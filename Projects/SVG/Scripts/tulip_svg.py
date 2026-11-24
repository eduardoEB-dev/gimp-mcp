"""Simplified tulip (from papel2.png side panel): leaning tapered stem, two
curved base leaves, two smaller stem leaves, solid 3-point tulip head.
All parts merged into one smooth non-overlapping outline (Blender-friendly).

usage: python tulip_svg.py <out.svg> [--color #D2232A] [--height 2000]
"""
import argparse
import math
import os
import re

import pathops

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--color", default="#D2232A")
ap.add_argument("--height", type=int, default=2000, help="output px height")
args = ap.parse_args()

# stem: cubic bezier, base bottom, leaning right going up (screen coords)
P = [(300, 960), (318, 780), (372, 560), (410, 360)]
STEM_W0, STEM_W1 = 18, 12

# (t on stem, side +1 right / -1 left, angle off stem tangent, length, half-width, bend deg)
BASE_LEAVES = [  # absolute screen angle instead of offset
    (0.025, -145, 330, 36, 0),
    (0.025, -35, 300, 34, 0),
]
STEM_LEAVES = [
    (0.42, +1, 48, 180, 25, 0),
    (0.64, -1, 50, 155, 22, 0),
]
HEAD_SCALE = 1.35  # tulip head size vs original key points
NECK = 0.4        # leaf width at base / max half-width
BOUNDS = []


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def bez(t):
    u = 1 - t
    return tuple(u**3 * P[0][i] + 3 * u * u * t * P[1][i] + 3 * u * t * t * P[2][i] + t**3 * P[3][i] for i in (0, 1))


def tangent(t):
    u = 1 - t
    d = [3 * u * u * (P[1][i] - P[0][i]) + 6 * u * t * (P[2][i] - P[1][i]) + 3 * t * t * (P[3][i] - P[2][i]) for i in (0, 1)]
    n = math.hypot(*d)
    return d[0] / n, d[1] / n


def catmull(pts):
    """Closed smooth C1 cubic path through pts."""
    n = len(pts)
    BOUNDS.extend(pts)
    d = f"M{f(pts[0][0])},{f(pts[0][1])}"
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(p2[0])},{f(p2[1])}"
    return d + "Z"


def curved_leaf(base, ang_deg, L, W, bend_deg, n=28):
    """Leaf along a curved spine; wide neck, widest ~60%, rounded tip.
    Spine starts slightly behind base so it can be trimmed at stem centerline."""
    a0, a1 = math.radians(ang_deg), math.radians(ang_deg + bend_deg)
    p1 = (base[0] + 0.5 * L * math.cos(a0), base[1] + 0.5 * L * math.sin(a0))
    p2 = (p1[0] + 0.5 * L * math.cos(a1), p1[1] + 0.5 * L * math.sin(a1))

    def spine(t):
        u = 1 - t
        return (u * u * base[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * base[1] + 2 * u * t * p1[1] + t * t * p2[1])

    def tan(t):
        dx = 2 * (1 - t) * (p1[0] - base[0]) + 2 * t * (p2[0] - p1[0])
        dy = 2 * (1 - t) * (p1[1] - base[1]) + 2 * t * (p2[1] - p1[1])
        m = math.hypot(dx, dy)
        return dx / m, dy / m

    def width(t):
        t = max(t, 0)
        g = (4 * t * (1 - t)) ** 0.75          # symmetric almond, widest at middle
        return W * g + NECK * W * (1 - t) ** 3

    ts = [-0.08] + [(1 - math.cos(math.pi * i / n)) / 2 for i in range(n)]   # dense near both ends
    left, right = [], []
    for t in ts:
        if t < 0:   # extend behind base along initial direction
            x, y = base[0] + t * L * math.cos(a0), base[1] + t * L * math.sin(a0)
            tx, ty = math.cos(a0), math.sin(a0)
        else:
            (x, y), (tx, ty) = spine(t), tan(t)
        w = width(t)
        left.append((x + ty * w, y - tx * w))
        right.append((x - ty * w, y + tx * w))
    tip = spine(1)
    return catmull(left + [tip] + right[::-1])


def head(origin, T):
    """Solid tulip cup: rounded base, 2 side petal tips + taller center tip.
    Local (v across, u along axis) key points -> smooth closed curve."""
    N = (-T[1], T[0])
    key = [(0, -8), (-34, 2), (-62, 30), (-78, 72), (-80, 115), (-76, 158), (-70, 192), (-66, 212),
           (-60, 215), (-48, 196), (-36, 176), (-26, 166), (-18, 182), (-9, 210), (-3, 236),
           (3, 236), (9, 210), (18, 182), (26, 166), (36, 176), (48, 196), (60, 215),
           (66, 212), (70, 192), (76, 158), (80, 115), (78, 72), (62, 30), (34, 2)]
    k = HEAD_SCALE
    pts = [(origin[0] + k * (u * T[0] + v * N[0]), origin[1] + k * (u * T[1] + v * N[1])) for v, u in key]
    return catmull(pts)


def half_plane(bp, tx, ty, side):
    nx, ny = (-ty, tx) if side > 0 else (ty, -tx)   # toward leaf side (screen right = (-ty, tx))
    B = 4000
    return [(bp[0] - tx * B, bp[1] - ty * B), (bp[0] + tx * B, bp[1] + ty * B),
            (bp[0] + tx * B + nx * B, bp[1] + ty * B + ny * B), (bp[0] - tx * B + nx * B, bp[1] - ty * B + ny * B)]


# ---- stem outline (tapered, rounded base) ----
NS = 40
left, right = [], []
for i in range(NS + 1):
    t = i / NS
    x, y = bez(t)
    tx, ty = tangent(t)
    w = (STEM_W0 + (STEM_W1 - STEM_W0) * t) / 2
    left.append((x + ty * w, y - tx * w))
    right.append((x - ty * w, y + tx * w))
x0, y0 = bez(0)
tx, ty = tangent(0)
cap = (x0 - tx * STEM_W0 / 2, y0 - ty * STEM_W0 / 2)
shapes = [(catmull([cap] + right + left[::-1]), None)]

# ---- base leaves (absolute angles) ----
for t, ang, L, W, bend in BASE_LEAVES:
    bp = bez(t)
    tx, ty = tangent(t)
    side = 1 if math.cos(math.radians(ang)) > 0 else -1
    shapes.append((curved_leaf(bp, ang, L, W, bend), half_plane(bp, tx, ty, side)))

# ---- stem leaves (angle off tangent) ----
for t, side, off, L, W, bend in STEM_LEAVES:
    bp = bez(t)
    tx, ty = tangent(t)
    ang = math.degrees(math.atan2(ty, tx)) + side * off
    shapes.append((curved_leaf(bp, ang, L, W, bend), half_plane(bp, tx, ty, side)))

# ---- head ----
T = tangent(1)
shapes.append((head(bez(1), T), None))


def to_skia(d):
    sp = pathops.Path()
    for cmd, a in re.findall(r"([MLCZ])([^MLCZ]*)", d):
        n = [float(v) for v in re.findall(r"-?[\d.]+", a)]
        {"M": lambda: sp.moveTo(*n), "L": lambda: sp.lineTo(*n), "C": lambda: sp.cubicTo(*n), "Z": sp.close}[cmd]()
    return sp


def poly(pts):
    sp = pathops.Path()
    sp.moveTo(*pts[0])
    for q in pts[1:]:
        sp.lineTo(*q)
    sp.close()
    return sp


VERB = {pathops.PathVerb.MOVE: "M", pathops.PathVerb.LINE: "L", pathops.PathVerb.QUAD: "Q",
        pathops.PathVerb.CUBIC: "C", pathops.PathVerb.CLOSE: "Z"}

merged = None
for d, clip in shapes:
    sp = to_skia(d)
    sp.simplify(fix_winding=True)          # normalize orientation per shape
    if clip:
        sp = pathops.op(sp, poly(clip), pathops.PathOp.INTERSECTION)
    merged = sp if merged is None else pathops.op(merged, sp, pathops.PathOp.UNION)
d_out = " ".join(VERB[v] + " ".join(f"{f(x)},{f(y)}" for x, y in pts) for v, pts in merged)

M = 20
xs, ys = [q[0] for q in BOUNDS], [q[1] for q in BOUNDS]
vb = (round(min(xs) - M), round(min(ys) - M), round(max(xs) - min(xs) + 2 * M), round(max(ys) - min(ys) + 2 * M))
oh = args.height
ow = round(oh * vb[2] / vb[3])
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ow}" height="{oh}" viewBox="{" ".join(map(str, vb))}">\n'
       f'  <title>Papel picado tulip</title>\n'
       f'  <path fill="{args.color}" d="{d_out}"/>\n</svg>\n')
os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
open(args.out, "w", encoding="utf-8").write(svg)
print("wrote", os.path.abspath(args.out), f"{ow}x{oh}", f"contours={sum(1 for v, _ in merged if v == pathops.PathVerb.MOVE)}")
