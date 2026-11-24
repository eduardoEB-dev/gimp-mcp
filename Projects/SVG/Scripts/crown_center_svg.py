"""Penelope crown: front-center scroll (from user's Paint sketch).
Bottom bowl whose ends curl into two inner spirals + two arches over the top
that wind into the same spirals (true double spiral, even gaps) and end in
small outer curls. Geometric (spirals, ellipse arcs), left half mirrored.

usage: python crown_center_svg.py <out.svg> [--color #C9A227] [--height 800] [--w 13]
"""
import argparse
import math
import os

import pathops

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--color", default="#C9A227")
ap.add_argument("--height", type=int, default=800)
ap.add_argument("--w", type=float, default=13, help="max stroke width")
ap.add_argument("--w-end", type=float, default=8, help="stroke width at the ends")
ap.add_argument("--w-fat", type=float, default=19, help="bowl inner curl width (comma head)")
args = ap.parse_args()

CX = 162            # mirror axis
C = (110, 80)       # left double-spiral center
R0 = 46             # bowl radius at spiral bottom (= arch radius at spiral top)
PITCH = 50          # radius lost per turn; arms interleave half a pitch apart
A_BOWL_END = 330    # bowl curl ends here (deg): fat comma head near the center
A_ARCH_END = 120    # arch arm stops at the bottom-left, does not wind in
SAG = 0             # bowl bottom dips this much at the center
E = (52, 80)        # outer arch ellipse center
ERX, ERY = 46, 46   # its radii (top meets the spiral top at y = C.y - R0)
K = (52, 115)       # small outer end curl center
K_R = (4, 11)       # its radius inner -> outer (outer reaches the ellipse bottom)


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def spiral(a0, a1, r_at, n_per_deg=1.0):
    """Points around C for screen angles a0..a1 (deg, increasing = clockwise on screen)."""
    n = max(2, int(abs(a1 - a0) * n_per_deg))
    out = []
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        r = r_at(a)
        out.append((C[0] + r * math.cos(math.radians(a)), C[1] + r * math.sin(math.radians(a))))
    return out


r_bowl = lambda a: R0 - PITCH * (a - 90) / 360           # bowl arm: r=R0 at bottom
r_arch = lambda a: R0 - PITCH * (a + 90) / 360           # arch arm: r=R0 at top (a=-90)


def smooth(t):
    t = min(max(t, 0), 1)
    return t * t * (3 - 2 * t)


def bowl_pts():
    """Center bottom -> spiral bottom -> fat inner curl. Returns (points, widths)."""
    y0 = C[1] + R0
    flat = [(CX - i / 4, y0 + SAG * math.cos(math.pi * i / (8 * (CX - C[0]))) ** 2)
            for i in range(0, int(4 * (CX - C[0])))]
    # flat: x from CX down to C.x, y dips by SAG at CX with zero slope at both ends
    sp = spiral(90, A_BOWL_END, r_bowl)
    ws = [W] * len(flat)
    for k in range(len(sp)):
        a = 90 + (A_BOWL_END - 90) * k / (len(sp) - 1)
        ws.append(W + (WF - W) * smooth((a - 90) / 130))
    return flat + sp, ws


def arch_pts():
    """Outer end curl -> ellipse (bottom, left, top) -> top line -> spiral -> inner end."""
    pts = []
    for k in range(121):                       # end curl, inner -> outer, clockwise
        t = k / 120
        a = math.radians(-150 + 240 * t)
        r = K_R[0] + (K_R[1] - K_R[0]) * t
        pts.append((K[0] + r * math.cos(a), K[1] + r * math.sin(a)))
    for k in range(1, 181):                    # ellipse bottom (90) -> left (180) -> top (270)
        a = math.radians(90 + k)
        pts.append((E[0] + ERX * math.cos(a), E[1] + ERY * math.sin(a)))
    x0, x1 = E[0], C[0]                        # straight top run into the spiral
    pts += [(x0 + (x1 - x0) * k / 40, C[1] - R0) for k in range(1, 40)]
    return pts + spiral(-90, A_ARCH_END, r_arch)


def catmull_closed(pts):
    n = len(pts)
    sp = pathops.Path()
    sp.moveTo(*pts[0])
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        sp.cubicTo(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                   p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, *p2)
    sp.close()
    sp.simplify(fix_winding=True)
    return sp


def stroke(pts, wfun, step=0.75):
    """Variable-width stroke with round caps.
    wfun: fn(s), s = 0..1 arc-length fraction, or a per-point width list."""
    keep = [0]
    for i in range(1, len(pts)):
        if math.dist(pts[i], pts[keep[-1]]) >= step:
            keep.append(i)
    keep[-1] = len(pts) - 1
    q = [pts[i] for i in keep]
    wl_ok = None if callable(wfun) else [wfun[i] for i in keep]
    acc = [0]
    for a, b in zip(q, q[1:]):
        acc.append(acc[-1] + math.dist(a, b))
    L, R = [], []
    for i, p in enumerate(q):
        a, b = q[max(i - 1, 0)], q[min(i + 1, len(q) - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        m = math.hypot(tx, ty)
        tx, ty = tx / m, ty / m
        w = (wfun(acc[i] / acc[-1]) if not wl_ok else wl_ok[i]) / 2
        L.append((p[0] + ty * w, p[1] - tx * w))
        R.append((p[0] - ty * w, p[1] + tx * w))

    def cap(p, prev, w, n=7):
        a0 = math.atan2(p[1] - prev[1], p[0] - prev[0])
        return [(p[0] + w * math.cos(a0 - math.pi / 2 + math.pi * k / (n + 1)),
                 p[1] + w * math.sin(a0 - math.pi / 2 + math.pi * k / (n + 1))) for k in range(1, n + 1)]
    return catmull_closed(L + cap(q[-1], q[-2], (wl_ok[-1] if wl_ok else wfun(1)) / 2) + R[::-1]
                          + cap(q[0], q[1], (wl_ok[0] if wl_ok else wfun(0)) / 2))


W, WE, WF = args.w, args.w_end, args.w_fat
w_arch = lambda s: WE + (W - WE) * math.sin(math.pi * s) ** 0.7     # thin ends, thick over the top


def mirror(pts):
    return [(2 * CX - x, y) for x, y in pts]


parts = []
for side in (lambda p: p, mirror):
    bp, bw = bowl_pts()
    parts.append(stroke(side(bp), bw))
    parts.append(stroke(side(arch_pts()), w_arch))

merged = parts[0]
for sp in parts[1:]:
    merged = pathops.op(merged, sp, pathops.PathOp.UNION)

VERB = {pathops.PathVerb.MOVE: "M", pathops.PathVerb.LINE: "L", pathops.PathVerb.QUAD: "Q",
        pathops.PathVerb.CUBIC: "C", pathops.PathVerb.CLOSE: "Z"}
d = " ".join(VERB[v] + " ".join(f"{f(x)},{f(y)}" for x, y in pts) for v, pts in merged)
xs = [p[0] for _, ps in merged for p in ps]
ys = [p[1] for _, ps in merged for p in ps]
M = 6
vb = (min(xs) - M, min(ys) - M, max(xs) - min(xs) + 2 * M, max(ys) - min(ys) + 2 * M)
oh = args.height
ow = round(oh * vb[2] / vb[3])
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ow}" height="{oh}" viewBox="{" ".join(f(v) for v in vb)}">\n'
       f'  <title>Crown center scroll</title>\n  <path fill="{args.color}" d="{d}"/>\n</svg>\n')
os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
open(args.out, "w", encoding="utf-8").write(svg)
print("wrote", os.path.abspath(args.out), f"{ow}x{oh}",
      "contours", sum(1 for v, _ in merged if v == pathops.PathVerb.MOVE))
