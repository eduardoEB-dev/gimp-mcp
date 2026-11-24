"""Build gold + purple SVG layers of the clock face for 3D printing (Bambu). No 13 (add separately).

Geometry measured from Images/Screenshot 2026-10-15 092237.png (native px coords),
redrawn clean, then scaled to mm. All shapes are filled paths (no strokes).

Usage: python make_clock_svgs.py [ring_diameter_mm]
"""
import math, os, sys
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from shapely.geometry import Point, Polygon, MultiPolygon, LineString, box
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from shapely import affinity

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "svg")
FONTS = r"C:\Windows\Fonts"
RING_MM = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0  # outer ring diameter

# ---- measured geometry (image px) ----
CX, CY = 253.0, 229.5
RING_IN, RING_OUT = 172.0, 184.0
PURPLE_R, PURPLE_W = 108.0, 4.5
TICK_R, TICK_LEN, TICK_W = 138.0, 37.0, 5.5
NUM_R, NUM_H, XII_W = 138.0, 40.0, 48.0
HUB_R, HUB_HOLE = 12.0, 4.0
FINIAL = [(248.5, 3.1), (257.5, 24.4), (267.5, 21.9), (252.5, 69.4), (239.4, 25.6)]
# hands: (angle deg cw from 12, tip dist, widest dist, half-width, pinch dist, shaft half-width)
MINUTE = (-12.8, 149.0, 83.0, 11.5, 71.0, 2.5)
HOUR = (3.2, 116.0, 70.0, 10.5, 62.5, 3.0)
Q = 64  # circle smoothness (segments per quarter)


# ---- font glyphs -> shapely ----
class FlatPen(BasePen):
    def __init__(self, gs):
        super().__init__(gs)
        self.contours, self.cur = [], []
    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, 17)[1:]:
            u = 1 - t
            self.cur.append(tuple(u**3*np.array(p0) + 3*u*u*t*np.array(p1) + 3*u*t*t*np.array(p2) + t**3*np.array(p3)))
    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, 17)[1:]:
            u = 1 - t
            self.cur.append(tuple(u*u*np.array(p0) + 2*u*t*np.array(p1) + t*t*np.array(p2)))
    def _closePath(self):
        if len(self.cur) > 2: self.contours.append(self.cur)
        self.cur = []
    _endPath = _closePath

def text_shape(text, font_file):
    f = TTFont(os.path.join(FONTS, font_file))
    gs, cmap, hmtx = f.getGlyphSet(), f.getBestCmap(), f["hmtx"]
    x, polys = 0, []
    for ch in text:
        g = cmap[ord(ch)]
        pen = FlatPen(gs); gs[g].draw(pen)
        shape = Polygon()
        for c in sorted((Polygon(c).buffer(0) for c in pen.contours), key=lambda p: -p.area):
            shape = shape.symmetric_difference(c)  # even-odd nesting -> holes
        polys.append(affinity.translate(shape, x, 0))
        x += hmtx[g][0]
    s = unary_union(polys)
    return affinity.scale(s, 1, -1, origin=(0, 0))  # font y-up -> svg y-down

def polar(r, deg):  # deg clockwise from 12 o'clock
    a = math.radians(deg)
    return CX + r * math.sin(a), CY - r * math.cos(a)


# ---- gold ----
ring = Point(CX, CY).buffer(RING_OUT, quad_segs=Q).difference(Point(CX, CY).buffer(RING_IN, quad_segs=Q))
finial = Polygon(FINIAL)

ticks = []
for deg in (30, 60, 120, 150, 210, 240, 300, 330):
    t = box(-TICK_W / 2, -TICK_LEN / 2, TICK_W / 2, TICK_LEN / 2)
    t = affinity.rotate(t, deg, origin=(0, 0))
    ticks.append(affinity.translate(t, *polar(TICK_R, deg)))

# Roman numerals: Times regular, condensed to match photo, tops facing outward
xii = text_shape("XII", "times.ttf")
bx0, by0, bx1, by1 = xii.bounds
sx, sy = XII_W / (bx1 - bx0), NUM_H / (by1 - by0)
numerals = []
for txt, deg in (("XII", 0), ("III", 90), ("VI", 180), ("IX", 270)):
    s = affinity.scale(text_shape(txt, "times.ttf"), sx, sy, origin=(0, 0))
    c = Point((s.bounds[0] + s.bounds[2]) / 2, (s.bounds[1] + s.bounds[3]) / 2)
    s = affinity.translate(s, -c.x, -c.y)
    s = affinity.rotate(s, deg, origin=(0, 0))
    numerals.append(affinity.translate(s, *polar(NUM_R, deg)))

def hand(angle, tip, wide, hw, pinch, shw):
    # symmetric spear in local coords (y up = toward tip), then rotate about hub
    right = [(0, tip), (hw, wide)]
    for t in np.linspace(0, 1, 12)[1:]:  # concave curve widest -> pinch
        right.append((hw + (shw - hw) * math.sin(t * math.pi / 2), wide + (pinch - wide) * t))
    right.append((shw, 0))
    pts = right + [(-x, y) for x, y in reversed(right[1:])]
    p = Polygon([(CX + x, CY - y) for x, y in pts])
    return affinity.rotate(p, angle, origin=(CX, CY))

hands = unary_union([hand(*MINUTE), hand(*HOUR)])
hub = Point(CX, CY).buffer(HUB_R, quad_segs=Q).difference(Point(CX, CY).buffer(HUB_HOLE, quad_segs=Q))

# ---- 13: built from plain geometry (no font) ----
def ellipse(cx, cy, rx, ry):
    return affinity.scale(Point(cx, cy).buffer(1, quad_segs=Q), rx, ry, origin=(cx, cy))

def wedge(cx, cy, a0, a1, r=200):  # angles deg, screen coords (0=right, 90=down)
    angs = np.radians(np.linspace(a0, a1, 64))
    return Polygon([(cx, cy)] + [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angs])

def bowl(c, outer, inner_c, inner, a0, a1):
    ring_ = ellipse(*c, *outer).difference(ellipse(*inner_c, *inner))
    return ring_.intersection(wedge(*c, a0, a1))

def bracket(x, y, dx, dy):  # curved serif bracket in corner (x, y), legs dx, dy
    pts = [(x, y), (x + dx, y)]
    for t in np.linspace(0, 1, 10)[1:-1]:
        pts.append((x + dx * (1 - math.sin(t * math.pi / 2)), y + dy * (1 - math.cos(t * math.pi / 2))))
    return Polygon(pts + [(x, y + dy)])

one = unary_union([
    Polygon([(222, 237), (233, 237), (233, 340), (216, 340), (216, 262), (206, 266), (204, 261)]),  # stem + flag
    box(204, 339, 241, 348),                                  # base serif
    bracket(233, 339, 7, -7), bracket(216, 339, -7, -7),       # serif brackets
])
three = unary_union([
    bowl((274, 268), (25, 26), (271, 269), (15, 19), -165, 122),   # upper bowl
    bowl((276, 318), (31, 32), (271, 316), (18, 24), -125, 155),   # lower bowl
    ellipse(264, 293, 6, 3.5),                                     # rounded waist spur
    ellipse(253.5, 262, 5.5, 7), ellipse(251.5, 330, 5.5, 7.5),    # terminals
])
three = three.buffer(2.5).buffer(-2.5)  # smooth seams where bowls/spur meet
n13 = unary_union([one, three]).buffer(0.6).buffer(-0.6)  # soften tiny corners
N13_OUTLINE = 1.8
# purple ring = two arcs (clock hours): right 1 -> 4, left 7 -> 11; rounded ends
PURPLE_ARCS = [(1, 4), (7, 11)]
def arc(h0, h1):
    degs = np.linspace(h0 * 30, h1 * 30, 200)
    return LineString([polar(PURPLE_R, d) for d in degs]).buffer(PURPLE_W / 2, quad_segs=16)
pring = unary_union([arc(*a) for a in PURPLE_ARCS])

def build(with_13):
    """Return (gold, purple) geometry, with or without the 13."""
    nums, extra_gold, covers = numerals, [], [hands, Point(CX, CY).buffer(HUB_R, quad_segs=Q)]
    if with_13:
        nums = [n.difference(n13.buffer(N13_OUTLINE + 2.0)) for n in numerals]  # 13 sits on VI
        extra_gold = [n13.buffer(N13_OUTLINE, quad_segs=4).difference(n13)]
        covers.append(n13.convex_hull.buffer(N13_OUTLINE))
    gold = unary_union([ring, finial, *ticks, *nums, hands, hub, *extra_gold])
    gold = gold.difference(Point(CX, CY).buffer(HUB_HOLE, quad_segs=Q))  # keep hub hole open over hands
    purple = pring.difference(unary_union(covers).buffer(1.5))  # ring cut under hands/hub(/13)
    if with_13:
        purple = unary_union([purple, n13])
    return gold.difference(purple), purple  # no overlap between layers


# ---- SVG output (mm) ----
MM = RING_MM / (2 * RING_OUT)
VB = (CX - RING_OUT - 2, min(FINIAL, key=lambda p: p[1])[1] - 2)
VW, VH = 2 * RING_OUT + 4, (CY + RING_OUT + 2) - VB[1]

def path_ds(geom):
    """One path string per polygon; simplified, consistent winding (works evenodd or nonzero)."""
    geom = geom.simplify(0.08)
    polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    out = []
    for p in polys:
        if p.is_empty or p.area < 1:
            continue
        p = orient(p, sign=1.0)
        subs = []
        for ring_ in [p.exterior, *p.interiors]:
            pts = [((x - VB[0]) * MM, (y - VB[1]) * MM) for x, y in ring_.coords[:-1]]
            subs.append("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in pts) + " Z")
        out.append(" ".join(subs))
    return out

def write_svg(fname, layers):
    w, h = VW * MM, VH * MM
    body = "\n".join(f'  <path fill="{c}" fill-rule="evenodd" d="{d}"/>' for g, c in layers for d in path_ds(g))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" '
           f'viewBox="0 0 {w:.3f} {h:.3f}">\n{body}\n</svg>\n')
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, fname), "w") as f:
        f.write(svg)
    print(fname, f"{w:.1f} x {h:.1f} mm")

GOLD, PURPLE = "#E8B422", "#8E3FD0"
for suffix, with_13 in (("", True), ("_no13", False)):
    gold, purple = build(with_13)
    write_svg(f"clock{suffix}_gold.svg", [(gold, GOLD)])
    write_svg(f"clock{suffix}_purple.svg", [(purple, PURPLE)])
    write_svg(f"clock{suffix}_combined_preview.svg", [(gold, GOLD), (purple, PURPLE)])
