"""Left caduceus wing (front view) -> mm SVG for 3D modeling.

Feathers are parametric teardrops (base, tip, width, bend) placed in source-image
pixel coords of guide.png, then scaled so the center ball = 44.45 mm.
python left_wing_svg.py out.svg [--overlay overlay.png]
"""
import math, sys
import pathops
from PIL import Image, ImageDraw

# center ball in guide.png px (measured)
BALL_C = (574.5, 1080.0)
BALL_R = 27.5
K = 44.45 / (2 * BALL_R)          # mm per px
ORIGIN = (418.0, 986.0)           # px mapped to (0,0) mm
W_MM, H_MM = 192 * K, 128 * K
STROKE = 0.2

# (id, base(x,y), tip(x,y), max half-width px, bend px (+ = left of base->tip), widest at t)
ROW1 = [
    ("a", (537, 1031), (510, 1030), 4.0, 0.6, 0.75),
    ("b", (538, 1039), (514, 1040), 4.2, 0.6, 0.75),
    ("c", (538, 1047), (518, 1050), 4.2, 0.5, 0.75),
    ("d", (539, 1055), (521, 1058), 3.6, 0.4, 0.75),
]
ROW2 = [
    ("a", (537, 1029), (484, 1027), 5.6, 1.0, 0.80),
    ("b", (537, 1038), (487, 1039), 5.8, 1.0, 0.80),
    ("c", (537, 1048), (496, 1051), 6.0, 0.8, 0.80),
    ("d", (541, 1058), (502, 1064), 6.0, 0.6, 0.80),
    ("e", (543, 1067), (509, 1078), 5.6, 0.5, 0.80),
    ("f", (545, 1075), (524, 1092), 4.8, 0.3, 0.80),
    ("g", (544, 1078), (538, 1099), 4.2, 0.2, 0.80),
]
ROW3 = [
    ("a", (536, 1039), (427, 1002), 8.5, -1.5, 0.84),
    ("b", (536, 1047), (434, 1029), 9.0, 1.2, 0.84),
    ("c", (536, 1058), (449, 1054), 8.5, 1.0, 0.84),
    ("d", (536, 1066), (466, 1074), 8.0, 0.8, 0.84),
    ("e", (537, 1071), (484, 1087), 7.5, 0.6, 0.84),
    ("f", (538, 1075), (504, 1099), 7.0, 0.5, 0.84),
    ("g", (540, 1079), (521, 1105), 6.0, 0.4, 0.84),
    ("h", (543, 1081), (534, 1108), 5.5, 0.3, 0.84),
]
ROWS = [("row1", ROW1), ("row2", ROW2), ("row3", ROW3)]

# arm outline, px, clockwise from the free tip: upper/outer edge then lower/inner edge
ARM = [
    (482.3, 1014.0), (490, 1013.0), (503.7, 1014.4), (525, 1018.9), (536.6, 1025.8),
    (542.3, 1033), (544.9, 1043), (545.5, 1053), (544.6, 1063),
    (547.5, 1071.5),                                         # into ball
    (542.3, 1077.4), (538.7, 1070.3), (537.3, 1060.3), (537.3, 1049), (535.9, 1039),
    (531.6, 1029.8), (523.7, 1023.6), (503.7, 1021.0), (488, 1020.0), (483.5, 1017.8),
]


UP = 1.7        # upper (hidden) side width factor: tucks each feather under the one above
BASE_W = 0.75   # base width as fraction of max width (no wedge gaps between bases)


def feather_shape(gid, fid, base, tip, hw, bend, tmax):
    """Top flight feather keeps its visible upper edge; the rest tuck under their neighbour/the arm."""
    return feather_pts(base, tip, hw, bend, tmax, up=1.0 if (gid, fid) == ("row3", "a") else UP)


def feather_pts(base, tip, hw, bend, tmax, up=1.0, n=28):
    """Closed outline: tapered base, widest near tmax, round tip. Returns px points."""
    bx, by = base; tx, ty = tip
    L = math.hypot(tx - bx, ty - by)
    ux, uy = (tx - bx) / L, (ty - by) / L
    nx, ny = -uy, ux                       # left normal
    def axis(t):
        b = bend * math.sin(math.pi * t)
        return bx + ux * L * t + nx * b, by + uy * L * t + ny * b
    def width(t):
        if t <= tmax:                      # base -> widest: smooth rise from 40%, round base cap
            s = t / tmax
            cap = math.sqrt(max(0.0, 1 - (1 - t / 0.06) ** 2)) if t < 0.06 else 1.0
            return hw * (BASE_W + (1 - BASE_W) * math.sin(s * math.pi / 2)) * cap
        s = (t - tmax) / (1 - tmax)        # widest -> tip: elliptical round-off
        return hw * math.sqrt(max(0.0, 1 - s * s))
    ts = [0.5 - 0.5 * math.cos(math.pi * i / n) for i in range(n + 1)]   # dense at ends
    left, right = [], []
    for t in ts:
        ax, ay = axis(t)
        dt = 1e-3
        a2 = axis(min(1, t + dt)); a1 = axis(max(0, t - dt))
        dx, dy = a2[0] - a1[0], a2[1] - a1[1]; d = math.hypot(dx, dy) or 1
        px, py = -dy / d, dx / d
        w = width(t)
        left.append((ax + px * w * up, ay + py * w * up))
        right.append((ax - px * w, ay - py * w))
    # both sides meet at t=0 and t=1: left base->tip, right tip->base
    return left + right[::-1][1:-1]


def spine_pts(base, tip, bend, n=8):
    bx, by = base; tx, ty = tip
    L = math.hypot(tx - bx, ty - by)
    ux, uy = (tx - bx) / L, (ty - by) / L
    nx, ny = -uy, ux
    out = []
    for i in range(n + 1):
        t = i / n * 0.96                    # stop just short of the tip
        b = bend * math.sin(math.pi * t)
        out.append((bx + ux * L * t + nx * b, by + uy * L * t + ny * b))
    return out


def mm(p):
    return ((p[0] - ORIGIN[0]) * K, (p[1] - ORIGIN[1]) * K)


def catmull_segs(pts, closed):
    """Catmull-Rom -> (start, [(c1, c2, end), ...]) cubic Beziers in mm."""
    P = [mm(p) for p in pts]
    n = len(P)
    segs = []
    for i in range(n if closed else n - 1):
        p0 = P[(i - 1) % n] if closed or i > 0 else P[0]
        p1, p2 = P[i], P[(i + 1) % n]
        p3 = P[(i + 2) % n] if closed or i + 2 < n else P[-1]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segs.append((c1, c2, p2))
    return P[0], segs


def fmt(v):
    return f"{v[0]:.3f},{v[1]:.3f}"


def catmull(pts, closed):
    """Catmull-Rom -> cubic Bezier path data (mm)."""
    start, segs = catmull_segs(pts, closed)
    d = [f"M{fmt(start)}"] + [f"C{fmt(a)} {fmt(b)} {fmt(c)}" for a, b, c in segs]
    return " ".join(d + (["Z"] if closed else []))


def skpath(pts):
    start, segs = catmull_segs(pts, True)
    p = pathops.Path(); p.moveTo(*start)
    for a, b, c in segs:
        p.cubicTo(*a, *b, *c)
    p.close()
    return p


def path_d(p):
    out = []
    for verb, pts in p.segments:
        if verb == "moveTo": out.append(f"M{fmt(pts[0])}")
        elif verb == "lineTo": out.append(f"L{fmt(pts[0])}")
        elif verb == "curveTo": out.append("C" + " ".join(fmt(q) for q in pts))
        elif verb == "qCurveTo": out.append("Q" + " ".join(fmt(q) for q in pts))
        elif verb == "closePath": out.append("Z")
    return " ".join(out)


ARM_PATH = None


def arm_path():
    global ARM_PATH
    if ARM_PATH is None:
        ARM_PATH = skpath(ARM)
    return ARM_PATH


def feather_clipped(gid, fid, base, tip, hw, bend, tmax):
    """Feather minus the arm: feathers hang below the arm, never over it.
    Any sliver left above the arm is dropped (keep the largest piece)."""
    f = skpath(feather_shape(gid, fid, base, tip, hw, bend, tmax))
    f.simplify(fix_winding=True)
    d = pathops.op(f, arm_path(), pathops.PathOp.DIFFERENCE)
    return max(d.contours, key=lambda c: abs(c.area))


def spine_clipped(base, tip, bend):
    """Spine starting where the quill comes out from under the arm."""
    pts = spine_pts(base, tip, bend, n=24)
    a = arm_path()
    keep = [q for q in pts if not a.contains(mm(q))]
    return keep if len(keep) >= 2 else pts


def path_poly(p, steps=12):
    """Flatten a pathops path to px points (for previews)."""
    inv = lambda q: (q[0] / K + ORIGIN[0], q[1] / K + ORIGIN[1])
    out, cur = [], None
    for verb, pts in p.segments:
        if verb == "moveTo": cur = pts[0]; out.append(inv(cur))
        elif verb == "lineTo": cur = pts[0]; out.append(inv(cur))
        elif verb == "curveTo":
            (a, b, c) = pts
            for i in range(1, steps + 1):
                t = i / steps; u = 1 - t
                out.append(inv((u**3*cur[0] + 3*u*u*t*a[0] + 3*u*t*t*b[0] + t**3*c[0],
                                u**3*cur[1] + 3*u*u*t*a[1] + 3*u*t*t*b[1] + t**3*c[1])))
            cur = c
        elif verb == "qCurveTo":
            for q in pts: out.append(inv(q))
            cur = pts[-1]
    return out


def build():
    st = f'fill="none" stroke="#000" stroke-width="{STROKE}"'
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_MM:.3f}mm" height="{H_MM:.3f}mm" '
           f'viewBox="0 0 {W_MM:.3f} {H_MM:.3f}">']
    c = mm(BALL_C)
    out.append(f'  <circle id="ref_ball" cx="{c[0]:.3f}" cy="{c[1]:.3f}" r="{44.45/2:.3f}" {st}/>')
    out.append(f'  <path id="arm" d="{catmull(ARM, True)}" {st}/>')
    for gid, row in ROWS:
        out.append(f'  <g id="{gid}">')
        for fid, base, tip, hw, bend, tm in row:
            i = f"{gid}_{fid}"
            out.append(f'    <path id="{i}" d="{path_d(feather_clipped(gid, fid, base, tip, hw, bend, tm))}" {st}/>')
            out.append(f'    <path id="{i}_spine" d="{catmull(spine_clipped(base, tip, bend), False)}" {st}/>')
        out.append('  </g>')
    out.append('</svg>')
    return "\n".join(out)


def overlay(path, S=7):
    im = Image.open(GUIDE).convert("RGB")
    x0, y0, x1, y1 = 418, 986, 610, 1114
    im = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * S, (y1 - y0) * S), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    T = lambda p: ((p[0] - x0) * S, (p[1] - y0) * S)
    cols = {"row1": (0, 200, 255), "row2": (255, 0, 255), "row3": (255, 40, 40)}
    d.polygon([T(p) for p in ARM], outline=(0, 255, 0))
    cx, cy = T(BALL_C); r = BALL_R * S
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 255, 0), width=2)
    for gid, row in ROWS:
        for fid, base, tip, hw, bend, tm in row:
            P = [T(p) for p in path_poly(feather_clipped(gid, fid, base, tip, hw, bend, tm))]
            d.line(P + [P[0]],
                   fill=cols[gid], width=2)
            d.text(T(tip), fid, fill=cols[gid])
    im.save(path)


GUIDE = r"G:\gimp-mcp\Projects\SVG\Staff\Images\guide.png"

if __name__ == "__main__":
    open(sys.argv[1], "w").write(build())
    if "--overlay" in sys.argv:
        overlay(sys.argv[sys.argv.index("--overlay") + 1])
