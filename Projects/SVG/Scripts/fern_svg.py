"""Arched fern (from papel2.png): tapered bezier stem + alternating smooth
lens-shaped leaves, shrinking toward a terminal leaf. Pure geometry.

usage: python fern_svg.py <out.svg> [--color #D2232A] [--height 2000] [--pairs 8]
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
ap.add_argument("--pairs", type=int, default=8, help="leaves per side")
ap.add_argument("--leaf-scale", type=float, default=0.8 * (4 / 3) ** 2, help="leaf length multiplier")
ap.add_argument("--leaf-width", type=float, default=0.13 * (3 / 4) ** 2 * 1.2, help="leaf half-width / length")
ap.add_argument("--neck", type=float, default=0.7, help="neck half-width at stem / W")
ap.add_argument("--tip", type=float, default=0.5, help="tip roundness / W (0 = sharp)")
args = ap.parse_args()

# stem: cubic bezier, base bottom-left arching up/right (screen coords)
P = [(165, 850), (118, 560), (175, 300), (370, 118)]
STEM_W0, STEM_W1 = 11, 5      # base / tip width
LEAF_ANGLE = {-1: 40, 1: 46}     # deg off stem tangent (inner-right / outer-left)


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


def catmull(pts, closed=False):
    """Smooth C1 cubic path through pts."""
    n = len(pts)
    d = f"M{f(pts[0][0])},{f(pts[0][1])}"
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if (closed or i > 0) else pts[i]
        p1, p2 = pts[i], pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(p2[0])},{f(p2[1])}"
    return d


BOUNDS = []


def leaf(base, ang, L, W, neck=None):
    """Leaf widest (2W) at middle; wide neck at stem (2*NECK*W) for a solid
    joint, softly rounded tip (vertical tangent, TIP*W). 4 cubic segments."""
    c, s = math.cos(ang), math.sin(ang)

    def tr(x, y):
        q = (base[0] + x * c - y * s, base[1] + x * s + y * c)
        BOUNDS.append(q)
        return f"{f(q[0])},{f(q[1])}"

    k = 0.42 * L                 # mid handle length: higher = fuller shoulders
    nb, tp = (args.neck * W if neck is None else neck), args.tip * W
    b = -nb if neck is None else 0   # side leaves: start behind stem center, trimmed at centerline later
    return (f"M{tr(b, -nb)} "
            f"C{tr(L * 0.16, -nb)} {tr(L / 2 - k / 2, -W)} {tr(L / 2, -W)} "
            f"C{tr(L / 2 + k / 2, -W)} {tr(L, -tp)} {tr(L, 0)} "
            f"C{tr(L, tp)} {tr(L / 2 + k / 2, W)} {tr(L / 2, W)} "
            f"C{tr(L / 2 - k / 2, W)} {tr(L * 0.16, nb)} {tr(b, nb)}Z")


# ---- stem outline (tapered) ----
N = 48
left, right = [], []
for i in range(N + 1):
    t = i / N
    x, y = bez(t)
    tx, ty = tangent(t)
    w = (STEM_W0 + (STEM_W1 - STEM_W0) * t) / 2
    left.append((x + ty * w, y - tx * w))
    right.append((x - ty * w, y + tx * w))
x0, y0 = bez(0)
tx, ty = tangent(0)
base_cap = (x0 - tx * STEM_W0 / 2, y0 - ty * STEM_W0 / 2)
stem = catmull([base_cap] + left + right[::-1], closed=True) + "Z"

# ---- leaves ----
paths = [stem]
clips = []   # (path index, half-plane polygon)
n = args.pairs
for side in (-1, 1):          # -1 = right (inner curve), 1 = left (outer curve)
    for k in range(n):
        u = k / (n - 1)
        t = 0.05 + 0.86 * u ** 0.9 + (0.5 * 0.86 / (n - 1) if side > 0 else 0)
        t = min(t, 0.95)
        frac = k / (n - 1)
        L = (136 if side < 0 else 120) * (1 - 0.5 * frac) * args.leaf_scale
        W = L * args.leaf_width
        tx, ty = tangent(t)
        ta = math.atan2(ty, tx)
        ang = ta - side * math.radians(LEAF_ANGLE[side])
        bp = bez(t)
        nx, ny = (ty, -tx) if side > 0 else (-ty, tx)   # normal toward leaf side
        half = [(bp[0] - tx * 3000, bp[1] - ty * 3000), (bp[0] + tx * 3000, bp[1] + ty * 3000),
                (bp[0] + tx * 3000 + nx * 3000, bp[1] + ty * 3000 + ny * 3000),
                (bp[0] - tx * 3000 + nx * 3000, bp[1] - ty * 3000 + ny * 3000)]
        clips.append((len(paths), half))
        paths.append(leaf(bp, ang, L, W))
# terminal leaf continues the stem
tx, ty = tangent(1)
paths.append(leaf(bez(0.97), math.atan2(ty, tx), 68 * args.leaf_scale, 68 * args.leaf_scale * args.leaf_width,
                  neck=STEM_W1 / 2))  # terminal leaf: neck = stem width, continues stem

xs = [q[0] for q in BOUNDS] + [P[0][0]]
ys = [q[1] for q in BOUNDS] + [P[0][1] + STEM_W0]
M = 15
vb = (round(min(xs) - M), round(min(ys) - M), round(max(xs) - min(xs) + 2 * M), round(max(ys) - min(ys) + 2 * M))
oh = args.height
ow = round(oh * vb[2] / vb[3])


def to_skia(d):
    """Parse absolute M/C/Q/Z path string into a pathops.Path."""
    sp = pathops.Path()
    for cmd, args_ in re.findall(r"([MLCQZ])([^MLCQZ]*)", d):
        n = [float(v) for v in re.findall(r"-?[\d.]+", args_)]
        if cmd == "M":
            sp.moveTo(*n)
        elif cmd == "L":
            sp.lineTo(*n)
        elif cmd == "C":
            sp.cubicTo(*n)
        elif cmd == "Q":
            sp.quadTo(*n)
        else:
            sp.close()
    return sp


def from_skia(sp):
    out = []
    for verb, pts in sp:
        xy = " ".join(f"{f(x)},{f(y)}" for x, y in pts)
        out.append({pathops.PathVerb.MOVE: "M", pathops.PathVerb.LINE: "L", pathops.PathVerb.QUAD: "Q",
                    pathops.PathVerb.CUBIC: "C", pathops.PathVerb.CLOSE: "Z"}[verb] + xy)
    return " ".join(out)


# merge stem + leaves into one non-overlapping outline (clean extrude/boolean in Blender)
merged = pathops.Path()
clip_of = dict(clips)
for i, d in enumerate(paths):
    sp = to_skia(d)
    if i in clip_of:
        hp = pathops.Path()
        hp.moveTo(*clip_of[i][0])
        for q in clip_of[i][1:]:
            hp.lineTo(*q)
        hp.close()
        sp = pathops.op(sp, hp, pathops.PathOp.INTERSECTION)
    merged.addPath(sp)
merged.simplify(fix_winding=True)
paths = [from_skia(merged)]

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ow}" height="{oh}" viewBox="{" ".join(map(str, vb))}">\n'
       f'  <title>Papel picado fern</title>\n'
       f'  <g fill="{args.color}">\n    ' + "\n    ".join(f'<path d="{d}"/>' for d in paths) + "\n  </g>\n</svg>\n")
os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
open(args.out, "w", encoding="utf-8").write(svg)
print("wrote", os.path.abspath(args.out), f"{ow}x{oh}")
