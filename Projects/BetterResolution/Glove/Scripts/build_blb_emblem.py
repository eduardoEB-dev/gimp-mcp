"""BLB shield emblem, redrawn as clean geometry from image-1872906647201986.webp
(trace of the embroidered art is wobbly at this size). Coordinates are measured
in source px, axis x=240. Output: 33 x 38 mm emblem, Black + Gold, tiled.

usage: python build_blb_emblem.py <out_dir>
"""
import math
import sys

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

sys.path.insert(0, r"D:\gimp-mcp\Projects\Workflow\SVG Creation")
import layers_common as L  # noqa: E402

W, H = 33.0, 38.0          # pocket size, mm
K = W / 408                # art scale, mm per source px (letters, star: uniform)
RIM, GAP, LINE = 18 * K, 8 * K, 0.6   # source line = 0.4 mm, widened for 0.4 nozzle
SOFT = 0.1                 # mm, rounds outer tips so they print

# half outline: (dx from axis, y), measured
TOP = [(0, 9), (9, 12), (40, 30), (79, 48), (131, 66), (188, 78), (204, 84)]
LOW = [(204, 250), (203.5, 260), (199, 280), (191.5, 300), (181.5, 320), (168.5, 340),
       (152.5, 360), (133, 380), (110, 400), (84, 420), (55, 440), (22, 460), (0, 469)]


def bez_fit(pts, n=60):
    """cubic bezier least-squares fit, ends fixed"""
    p = np.array(pts, float)
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    t = s / s[-1]
    b0, b1, b2, b3 = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
    A = np.c_[b1, b2]
    c = np.linalg.lstsq(A, p - np.outer(b0, p[0]) - np.outer(b3, p[-1]), rcond=None)[0]
    T = np.linspace(0, 1, n)[:, None]
    return (1 - T) ** 3 * p[0] + 3 * T * (1 - T) ** 2 * c[0] + 3 * T * T * (1 - T) * c[1] + T ** 3 * p[-1]


half = np.vstack([bez_fit(TOP), bez_fit(LOW)])
half[0, 0] = half[-1, 0] = 0
sx, sy = W / 408, H / (469 - 9)   # outline only: fills 33 x 38
right = [(W / 2 + dx * sx, (y - 9) * sy) for dx, y in half]
left = [(W / 2 - dx * sx, (y - 9) * sy) for dx, y in half[-2:0:-1]]
outer = Polygon(right + left).buffer(0)

ring_in = outer.buffer(-RIM, join_style="mitre", mitre_limit=8)
line_out = ring_in.buffer(-GAP, join_style="mitre", mitre_limit=8)
field = line_out.buffer(-LINE, join_style="mitre", mitre_limit=8)


def art(x, y):
    """source px -> mm; centered on axis and on the art's own center"""
    return (W / 2 + (x - 240) * K, H / 2 + (y - 239) * K)


def poly(pts, dx=0):
    return Polygon([art(x + dx, y) for x, y in pts])


# B: stem left, chamfered bowls, waist notch, counters w/ small chamfers
B_OUT = [(98, 135), (171, 135), (189, 156), (189, 202), (177, 215), (189, 228), (189, 273), (168, 295), (98, 295)]
B_C1 = [(127, 163), (156, 163), (159, 166), (159, 195), (154, 200), (127, 200)]
B_C2 = [(127, 228), (154, 228), (159, 233), (159, 264), (156, 267), (127, 267)]


def letter_b(dx):
    return poly(B_OUT, dx).difference(unary_union([poly(B_C1, dx), poly(B_C2, dx)]))


SHIFT = -1.5   # word centered on axis
letters = [letter_b(SHIFT), letter_b(194.5 + SHIFT),
           poly([(208, 135), (237, 135), (237, 267), (281, 267), (281, 295), (208, 295)], SHIFT)]

R, r = 42.8, 42.8 * 0.42
star = poly([(240 + (R if i % 2 == 0 else r) * math.sin(i * math.pi / 5),
              358.8 - (R if i % 2 == 0 else r) * math.cos(i * math.pi / 5)) for i in range(10)])

gold = unary_union([outer.difference(ring_in), line_out.difference(field), *letters, star])
gold = gold.buffer(-SOFT, join_style="mitre").buffer(SOFT, quad_segs=8).simplify(0.003)
black = outer.difference(gold).simplify(0.003)


def paths(g):
    out = []
    for p in (g.geoms if hasattr(g, "geoms") else [g]):
        if p.area < 0.05:      # hairline leftovers from the soften step
            continue
        d = ""
        for ring in [p.exterior, *p.interiors]:
            c = list(ring.coords)[:-1]
            d += "M " + " L ".join(f"{x:.3f} {y:.3f}" for x, y in c) + " Z "
        out.append(d.strip())
    return out


L.write_layer_set(sys.argv[1], "BLB", (0, 0, W, H), (W, H),
                  [({"name": "Black", "hex": "#0F0D0C"}, paths(black)),
                   ({"name": "Gold", "hex": "#D49C2A"}, paths(gold))],
                  source="image-1872906647201986.webp (redrawn)")
