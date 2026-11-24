"""Full papel picado flower: center dot + 12 radial leaf petals (mirrored from
the half-flower on the blue banner). Pure bezier geometry, no tracing.

usage: python flower_svg.py <out_dir> [--color #077DAD] [--size 1000]
writes Flower_shapes.svg (petals filled) and Flower_cutout.svg (disc w/ holes)
"""
import argparse
import math
import os

ap = argparse.ArgumentParser()
ap.add_argument("out_dir")
ap.add_argument("--color", default="#077DAD")
ap.add_argument("--size", type=int, default=1000)
args = ap.parse_args()

N = 12           # petals
R_DOT = 38       # center dot radius
R_IN, R_OUT = 110, 330
HW = 29          # petal half width
R_DISC = 400     # cutout disc radius

# one petal along +x: rounded inner end, widest ~45%, soft tapered tip
PETAL = [
    ("M", [(R_IN, 0)]),
    ("C", [(R_IN, -HW * 0.78), (160, -HW), (210, -HW)]),
    ("C", [(272, -HW), (R_OUT, -HW * 0.62), (R_OUT, 0)]),
    ("C", [(R_OUT, HW * 0.62), (272, HW), (210, HW)]),
    ("C", [(160, HW), (R_IN, HW * 0.78), (R_IN, 0)]),
]


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def petal_d(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    out = []
    for cmd, pts in PETAL:
        out.append(cmd + " ".join(f"{f(x*c - y*s)},{f(x*s + y*c)}" for x, y in pts))
    return " ".join(out) + "Z"


def circle_d(r):
    # two arcs; drawn counter-clockwise relative to petals is irrelevant w/ evenodd
    return f"M{-r},0 A{r},{r} 0 1 0 {r},0 A{r},{r} 0 1 0 {-r},0Z"


holes = [circle_d(R_DOT)] + [petal_d(360 / N * i) for i in range(N)]
vb = f"-{R_DISC + 20} -{R_DISC + 20} {2 * (R_DISC + 20)} {2 * (R_DISC + 20)}"


def write(name, d, title):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{args.size}" height="{args.size}" viewBox="{vb}">\n'
           f'  <title>{title}</title>\n'
           f'  <path fill="{args.color}" fill-rule="evenodd" d="{d}"/>\n'
           f'</svg>\n')
    p = os.path.join(args.out_dir, name)
    open(p, "w", encoding="utf-8").write(svg)
    print("wrote", os.path.abspath(p))


os.makedirs(args.out_dir, exist_ok=True)
write("Flower_shapes.svg", " ".join(holes), "Papel picado flower")
write("Flower_cutout.svg", " ".join([circle_d(R_DISC)] + holes), "Papel picado flower (cut-out)")
