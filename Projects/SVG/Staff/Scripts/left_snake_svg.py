"""Left caduceus snake (exploded view) -> mm SVG for 3D modeling.

Body = centerline + width profile (tube outline), unioned with a hand-traced head.
Coords are guide.png px of the exploded-view left snake; scaled so the center
connector ball (51.5 px wide there) = 44.45 mm. The right snake is the mirror.
python left_snake_svg.py out.svg [--overlay overlay.png]
"""
import math, sys
import pathops
from PIL import Image, ImageDraw

GUIDE = r"G:\gimp-mcp\Projects\SVG\Staff\Images\guide.png"
K = 44.45 / 51.5                  # mm per px
AXIS_X = 615.0                    # dashed attach line beside the snake = dowel axis
# assembled ball position: front view puts the ball center ~0.94 ball diameters above the head top
BALL_C = (AXIS_X, 254 - 41.7 / K)
BALL_R = 44.45 / 2 / K
ORIGIN = (AXIS_X - 52, BALL_C[1] - BALL_R - 6)
W_MM, H_MM = 104 * K, (494 - ORIGIN[1]) * K
STROKE = 0.2

# centerline head -> tail tip: (x, y, full width px)
SPINE = [
    (591.2, 263, 12), (585.2, 267, 13), (581.7, 275, 13.5), (581.2, 284, 14), (583.2, 294, 14),
    (588.2, 303, 14), (597.2, 311, 14), (607.2, 319, 14), (617.2, 327, 14.5), (623.7, 336, 15),
    (624.2, 345, 14.5), (617.2, 352, 14), (607.2, 359, 13.5), (599.2, 367, 13), (598.7, 375, 13),
    (603.2, 386, 12.5), (612.2, 393, 12.5), (620.2, 400, 12.5), (624.7, 409, 12.5), (620.2, 417, 12),
    (612.2, 423, 11.5), (605.2, 430, 11), (604.7, 438, 10.5), (608.2, 446, 10), (615.2, 453, 9.5),
    (620.7, 460, 9), (621.2, 467, 8), (617.2, 473, 6.5), (616.2, 479, 5), (618.2, 484, 3),
    (619.2, 486.5, 1.2),
]
# head outline, clockwise from back of skull; open mouth notch at the snout
HEAD = [
    (584, 262), (588, 256.5), (595, 253.6), (602, 254.6), (608, 256.8), (612, 258.8),
    (613.4, 261.5), (612, 263.8), (604.5, 265.2),            # upper jaw -> mouth corner
    (611, 266.4), (612.6, 268.6), (610, 270.8), (603, 272.4), # lower jaw
    (595, 273.2), (588, 272.5), (583, 269),
]
EYE = (597.5, 258.3, 1.6, 1.2)    # cx, cy, rx, ry px
MOUTH = [(604.5, 265.2), (611, 265.4)]  # jaw line (open)


def mm(p):
    return ((p[0] - ORIGIN[0]) * K, (p[1] - ORIGIN[1]) * K)


def catmull_dense(pts, per=10):
    """Catmull-Rom sample of an open polyline -> dense points (keeps any extra coords linear)."""
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, n - 1)]
        for k in range(per):
            t = k / per
            q = [0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                        + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)]
            q.append(p1[2] + (p2[2] - p1[2]) * t)
            out.append(tuple(q))
    out.append(pts[-1])
    return out


def body_outline():
    """Offset the dense centerline both sides; round cap at the tail tip."""
    C = catmull_dense(SPINE)
    L, R = [], []
    for i, (x, y, w) in enumerate(C):
        a, b = C[max(i - 1, 0)], C[min(i + 1, len(C) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        L.append((x + nx * w / 2, y + ny * w / 2)); R.append((x - nx * w / 2, y - ny * w / 2))
    tx, ty, tw = C[-1]
    ux, uy = tx - C[-2][0], ty - C[-2][1]; d = math.hypot(ux, uy); ux, uy = ux / d, uy / d
    cap = [(tx + ux * tw / 2 * math.sin(a) - uy * tw / 2 * math.cos(a),
            ty + uy * tw / 2 * math.sin(a) + ux * tw / 2 * math.cos(a)) for a in
           [math.pi * k / 8 for k in range(1, 8)]]
    return L[::3] + [L[-1]] + cap + [R[-1]] + R[::-3]


def smooth_closed(pts):
    """Closed Catmull-Rom through pts -> pathops Path in mm."""
    P = [mm(p) for p in pts]; n = len(P)
    p = pathops.Path(); p.moveTo(*P[0])
    for i in range(n):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % n], P[(i + 2) % n]
        p.cubicTo(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                  p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, *p2)
    p.close(); p.simplify(fix_winding=True)
    return p


def fmt(v):
    return f"{v[0]:.3f},{v[1]:.3f}"


def path_d(p):
    out = []
    for verb, pts in p.segments:
        if verb == "moveTo": out.append(f"M{fmt(pts[0])}")
        elif verb == "lineTo": out.append(f"L{fmt(pts[0])}")
        elif verb == "curveTo": out.append("C" + " ".join(fmt(q) for q in pts))
        elif verb == "qCurveTo": out.append("Q" + " ".join(fmt(q) for q in pts))
        elif verb == "closePath": out.append("Z")
    return " ".join(out)


def open_d(pts):
    P = [mm(p[:2]) for p in pts]; n = len(P)
    d = [f"M{fmt(P[0])}"]
    for i in range(n - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, n - 1)]
        d.append(f"C{fmt((p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6))} "
                 f"{fmt((p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6))} {fmt(p2)}")
    return " ".join(d)


def snake_path():
    u = pathops.op(smooth_closed(body_outline()), smooth_closed(HEAD), pathops.PathOp.UNION)
    return max(u.contours, key=lambda c: abs(c.area))


def build():
    st = f'fill="none" stroke="#000" stroke-width="{STROKE}"'
    c = mm(BALL_C); ex, ey = mm(EYE[:2])
    ax0, ax1 = mm((AXIS_X, BALL_C[1])), mm((AXIS_X, 494))
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_MM:.3f}mm" height="{H_MM:.3f}mm" '
        f'viewBox="0 0 {W_MM:.3f} {H_MM:.3f}">',
        f'  <circle id="ref_ball" cx="{c[0]:.3f}" cy="{c[1]:.3f}" r="{44.45/2:.3f}" {st}/>',
        f'  <path id="ref_dowel_axis" d="M{fmt(ax0)} L{fmt(ax1)}" {st}/>',
        f'  <path id="snake" d="{path_d(snake_path())}" {st}/>',
        f'  <path id="snake_spine" d="{open_d(SPINE)}" {st}/>',
        f'  <ellipse id="eye" cx="{ex:.3f}" cy="{ey:.3f}" rx="{EYE[2]*K:.3f}" ry="{EYE[3]*K:.3f}" {st}/>',
        f'  <path id="mouth" d="{open_d([(*p, 0) for p in MOUTH])}" {st}/>',
        '</svg>'])


def overlay(path, S=6):
    x0, y0, x1, y1 = 565, 245, 645, 492
    im = Image.open(GUIDE).convert("RGB").crop((x0, y0, x1, y1))
    im = im.resize(((x1 - x0) * S, (y1 - y0) * S), Image.LANCZOS)
    d = ImageDraw.Draw(im); T = lambda p: ((p[0] - x0) * S, (p[1] - y0) * S)
    inv = lambda q: (q[0] / K + ORIGIN[0], q[1] / K + ORIGIN[1])
    pts, cur = [], None
    for verb, ps in snake_path().segments:
        if verb in ("moveTo", "lineTo"): cur = ps[0]; pts.append(inv(cur))
        elif verb == "curveTo":
            a, b, c = ps
            for i in range(1, 9):
                t = i / 8; u = 1 - t
                pts.append(inv(tuple(u**3*cur[j] + 3*u*u*t*a[j] + 3*u*t*t*b[j] + t**3*c[j] for j in range(2))))
            cur = c
    d.line([T(p) for p in pts] + [T(pts[0])], fill=(255, 0, 0), width=2)
    d.line([T(p[:2]) for p in catmull_dense(SPINE)], fill=(0, 120, 255), width=1)
    d.line([T((AXIS_X, y0)), T((AXIS_X, y1))], fill=(0, 200, 0), width=1)
    im.save(path)


if __name__ == "__main__":
    open(sys.argv[1], "w").write(build())
    if "--overlay" in sys.argv:
        overlay(sys.argv[sys.argv.index("--overlay") + 1])
