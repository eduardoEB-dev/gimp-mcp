"""Existing SVG -> one SVG per color (aligned, non-overlapping), keeping the
original vector curves. For Bambu Studio multi-color prints.

Shapes are taken in paint order; each shape loses whatever is painted on top
of it (skia-pathops), so the layers tile without overlaps. Same-color shapes
are merged into one outline per layer. Strokes become filled outlines.

usage:
  python svg_to_layers.py in.svg --suggest                      # list fill colors, stop
  python svg_to_layers.py in.svg out_dir --name Grinch
  python svg_to_layers.py in.svg out_dir --colors "Red,White,Green=#9FC52A,Black"
      (each SVG color goes to the nearest listed color = merge/recolor)
options:
  --map "#00ff00=Green,#fff=White"  explicit SVG color -> layer
  --drop "White"                    don't write these layers (e.g. a background);
                                    they still hide what is under them
  --drop-bg                         drop shapes that cover >=90% of the canvas
  --width-mm / --height-mm          output size (default: keep the SVG's size)

Supports path, rect (incl. rx), circle, ellipse, polygon, polyline, line, g,
use, transform, style/fill/stroke/opacity/display inheritance. Gradients use
their first stop color (warned). Text must be converted to paths first.
"""
import argparse
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pathops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layers_common as L  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out_dir", nargs="?")
ap.add_argument("--name")
ap.add_argument("--title")
ap.add_argument("--suggest", action="store_true")
ap.add_argument("--colors")
ap.add_argument("--map")
ap.add_argument("--drop")
ap.add_argument("--drop-bg", action="store_true")
ap.add_argument("--merge-de", type=float, default=6, help="auto mode: merge SVG colors closer than this (Lab)")
g = ap.add_mutually_exclusive_group()
g.add_argument("--width-mm", type=float)
g.add_argument("--height-mm", type=float)
ap.add_argument("--force", action="store_true")
args = ap.parse_args()

NS = "{http://www.w3.org/2000/svg}"
XL = "{http://www.w3.org/1999/xlink}href"
CSS = {"black": "#000000", "white": "#FFFFFF", "red": "#FF0000", "green": "#008000", "lime": "#00FF00",
       "blue": "#0000FF", "yellow": "#FFFF00", "orange": "#FFA500", "gray": "#808080", "grey": "#808080",
       "purple": "#800080", "pink": "#FFC0CB", "brown": "#A52A2A", "navy": "#000080", "silver": "#C0C0C0"}
warn = set()
root = ET.parse(args.src).getroot()
ids = {e.get("id"): e for e in root.iter() if e.get("id")}


# --- styles ------------------------------------------------------------------
def color(v):
    if v is None:
        return None
    v = v.strip()
    if v in ("none", "transparent"):
        return "none"
    if v.startswith("url("):
        gid = re.search(r"#([^)]+)", v).group(1)
        grad = ids.get(gid)
        while grad is not None and not list(grad.iter(NS + "stop")) and grad.get(XL):
            grad = ids.get(grad.get(XL).lstrip("#"))
        stops = list(grad.iter(NS + "stop")) if grad is not None else []
        warn.add(f"gradient {gid}: using its first stop color")
        if not stops:
            return "#808080"
        st = dict(kv.split(":") for kv in (stops[0].get("style") or "").split(";") if ":" in kv)
        return color(st.get("stop-color", stops[0].get("stop-color", "#000")))
    if v.startswith("#"):
        return L.rgb2hex(L.hex2rgb(v))
    m = re.match(r"rgba?\(([^)]+)\)", v)
    if m:
        n = [float(x.strip().rstrip("%")) * (2.55 if "%" in x else 1) for x in m.group(1).split(",")[:3]]
        return L.rgb2hex(n)
    if v.lower() in CSS:
        return CSS[v.lower()]
    warn.add(f"unknown color '{v}' -> black")
    return "#000000"


INHERIT = ("fill", "stroke", "stroke-width", "fill-rule", "opacity", "fill-opacity", "display",
           "visibility", "stroke-linejoin", "stroke-linecap")


def style_of(e, parent):
    st = dict(parent)
    st["opacity"] = "1"           # opacity multiplies, handled below
    for k in INHERIT:
        if e.get(k) is not None:
            st[k] = e.get(k)
    for kv in (e.get("style") or "").split(";"):
        if ":" in kv:
            k, v = kv.split(":", 1)
            st[k.strip()] = v.strip()
    st["_op"] = parent.get("_op", 1.0) * float(st.get("opacity", 1))
    return st


# --- transforms --------------------------------------------------------------
def mul(a, b):   # affine (a b c d e f), apply b then a
    return (a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1], a[0] * b[2] + a[2] * b[3],
            a[1] * b[2] + a[3] * b[3], a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5])


def parse_tf(s):
    m = (1, 0, 0, 1, 0, 0)
    for name, a in re.findall(r"(\w+)\s*\(([^)]*)\)", s or ""):
        n = [float(v) for v in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", a)]
        if name == "matrix":
            t = tuple(n)
        elif name == "translate":
            t = (1, 0, 0, 1, n[0], n[1] if len(n) > 1 else 0)
        elif name == "scale":
            t = (n[0], 0, 0, n[1] if len(n) > 1 else n[0], 0, 0)
        elif name == "rotate":
            c, s_ = math.cos(math.radians(n[0])), math.sin(math.radians(n[0]))
            t = (c, s_, -s_, c, 0, 0)
            if len(n) == 3:
                t = mul(mul((1, 0, 0, 1, n[1], n[2]), t), (1, 0, 0, 1, -n[1], -n[2]))
        elif name == "skewX":
            t = (1, 0, math.tan(math.radians(n[0])), 1, 0, 0)
        elif name == "skewY":
            t = (1, math.tan(math.radians(n[0])), 0, 1, 0, 0)
        else:
            continue
        m = mul(m, t)
    return m


# --- geometry ----------------------------------------------------------------
def num(e, k, d=0.0):
    v = e.get(k)
    return float(re.match(r"-?\d*\.?\d+(?:e-?\d+)?", v).group(0)) if v else d


def path_from_d(d):
    p = pathops.Path()
    toks = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d)
    i, cmd = 0, None
    cx = cy = sx = sy = 0.0
    lc = lq = None   # last cubic / quad control point (for S/T)
    open_ = False

    def nxt():
        nonlocal i
        i += 1
        return float(toks[i - 1])

    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                if open_:
                    p.close()
                open_ = False
                cx, cy = sx, sy
                lc = lq = None
                continue
        rel = cmd.islower()
        C = cmd.upper()
        ox, oy = (cx, cy) if rel else (0.0, 0.0)
        if C == "M":
            cx, cy = nxt() + ox, nxt() + oy
            sx, sy = cx, cy
            p.moveTo(cx, cy)
            open_ = True
            cmd = "l" if rel else "L"   # extra pairs are lineTo
            lc = lq = None
            continue
        if not open_:                   # drawing after Z starts at the last start point
            p.moveTo(cx, cy)
            open_ = True
        if C == "L":
            cx, cy = nxt() + ox, nxt() + oy
            p.lineTo(cx, cy)
            lc = lq = None
        elif C == "H":
            cx = nxt() + ox
            p.lineTo(cx, cy)
            lc = lq = None
        elif C == "V":
            cy = nxt() + (cy if rel else 0)
            p.lineTo(cx, cy)
            lc = lq = None
        elif C == "C":
            x1, y1, x2, y2, x, y = (nxt() + o for o in (ox, oy, ox, oy, ox, oy))
            p.cubicTo(x1, y1, x2, y2, x, y)
            lc, lq, cx, cy = (x2, y2), None, x, y
        elif C == "S":
            x1, y1 = (2 * cx - lc[0], 2 * cy - lc[1]) if lc else (cx, cy)
            x2, y2, x, y = (nxt() + o for o in (ox, oy, ox, oy))
            p.cubicTo(x1, y1, x2, y2, x, y)
            lc, lq, cx, cy = (x2, y2), None, x, y
        elif C == "Q":
            x1, y1, x, y = (nxt() + o for o in (ox, oy, ox, oy))
            p.quadTo(x1, y1, x, y)
            lq, lc, cx, cy = (x1, y1), None, x, y
        elif C == "T":
            x1, y1 = (2 * cx - lq[0], 2 * cy - lq[1]) if lq else (cx, cy)
            x, y = nxt() + ox, nxt() + oy
            p.quadTo(x1, y1, x, y)
            lq, lc, cx, cy = (x1, y1), None, x, y
        elif C == "A":
            rx, ry, rot, la, sw = nxt(), nxt(), nxt(), nxt(), nxt()
            x, y = nxt() + ox, nxt() + oy
            if rx == 0 or ry == 0:
                p.lineTo(x, y)
            else:
                p.arcTo(abs(rx), abs(ry), rot, pathops.ArcSize.LARGE if la else pathops.ArcSize.SMALL,
                        pathops.Direction.CW if sw else pathops.Direction.CCW, x, y)
            cx, cy = x, y
            lc = lq = None
    return p


def ellipse(cx, cy, rx, ry):
    k = 0.5522847498
    p = pathops.Path()
    p.moveTo(cx + rx, cy)
    p.cubicTo(cx + rx, cy + k * ry, cx + k * rx, cy + ry, cx, cy + ry)
    p.cubicTo(cx - k * rx, cy + ry, cx - rx, cy + k * ry, cx - rx, cy)
    p.cubicTo(cx - rx, cy - k * ry, cx - k * rx, cy - ry, cx, cy - ry)
    p.cubicTo(cx + k * rx, cy - ry, cx + rx, cy - k * ry, cx + rx, cy)
    p.close()
    return p


def shape(e, tag):
    if tag == "path":
        return path_from_d(e.get("d", ""))
    if tag == "rect":
        x, y, w, h = num(e, "x"), num(e, "y"), num(e, "width"), num(e, "height")
        rx = num(e, "rx", num(e, "ry", 0))
        ry = num(e, "ry", rx)
        rx, ry = min(rx, w / 2), min(ry, h / 2)
        if rx or ry:
            d = (f"M{x + rx},{y} H{x + w - rx} A{rx},{ry} 0 0 1 {x + w},{y + ry} V{y + h - ry} "
                 f"A{rx},{ry} 0 0 1 {x + w - rx},{y + h} H{x + rx} A{rx},{ry} 0 0 1 {x},{y + h - ry} "
                 f"V{y + ry} A{rx},{ry} 0 0 1 {x + rx},{y} Z")
        else:
            d = f"M{x},{y} H{x + w} V{y + h} H{x} Z"
        return path_from_d(d)
    if tag == "circle":
        r = num(e, "r")
        return ellipse(num(e, "cx"), num(e, "cy"), r, r)
    if tag == "ellipse":
        return ellipse(num(e, "cx"), num(e, "cy"), num(e, "rx"), num(e, "ry"))
    if tag in ("polygon", "polyline", "line"):
        if tag == "line":
            pts = [num(e, "x1"), num(e, "y1"), num(e, "x2"), num(e, "y2")]
        else:
            pts = [float(v) for v in re.findall(r"-?\d*\.?\d+(?:e-?\d+)?", e.get("points", ""))]
        d = "M" + " L".join(f"{pts[i]},{pts[i + 1]}" for i in range(0, len(pts) - 1, 2))
        return path_from_d(d + (" Z" if tag == "polygon" else ""))
    return None


# --- walk the tree in paint order -------------------------------------------
items = []   # (hex, pathops.Path) bottom first
SKIP = {"defs", "clipPath", "mask", "symbol", "marker", "pattern", "linearGradient", "radialGradient",
        "metadata", "title", "desc", "style", "script"}


def walk(e, st, tf, depth=0):
    tag = e.tag.replace(NS, "")
    if tag in SKIP or depth > 50:
        return
    st = style_of(e, st)
    if st.get("display") == "none" or st.get("visibility") == "hidden":
        return
    tf = mul(tf, parse_tf(e.get("transform")))
    if e.get("clip-path") or e.get("mask"):
        warn.add("clip-path/mask ignored (shape drawn unclipped)")
    if tag in ("svg", "g", "a", "switch"):
        if tag == "svg" and depth > 0:
            tf = mul(tf, (1, 0, 0, 1, num(e, "x"), num(e, "y")))
        for c in e:
            walk(c, st, tf, depth + 1)
        return
    if tag == "use":
        ref = ids.get((e.get(XL) or e.get("href") or "").lstrip("#"))
        if ref is not None:
            walk_ref = mul(tf, (1, 0, 0, 1, num(e, "x"), num(e, "y")))
            if ref.tag.replace(NS, "") == "symbol":
                for c in ref:
                    walk(c, st, walk_ref, depth + 1)
            else:
                walk(ref, st, walk_ref, depth + 1)
        return
    if tag == "text":
        warn.add("text element skipped: convert text to paths first (Inkscape: Path > Object to Path)")
        return
    p = shape(e, tag)
    if p is None:
        return
    fop = st["_op"] * float(st.get("fill-opacity", 1))
    fill = color(st.get("fill", "#000000"))
    if fill != "none" and fop >= 0.5:
        q = pathops.Path(p)
        q.fillType = pathops.FillType.EVEN_ODD if st.get("fill-rule") == "evenodd" else pathops.FillType.WINDING
        items.append((fill, q.transform(*tf)))
    elif fill != "none":
        warn.add("shapes under 50% opacity skipped")
    stroke = color(st.get("stroke"))
    sw = float(re.match(r"-?\d*\.?\d+(?:e-?\d+)?", st.get("stroke-width", "1")).group(0)) * math.sqrt(abs(tf[0] * tf[3] - tf[1] * tf[2]))
    if stroke and stroke != "none" and sw > 0 and st["_op"] >= 0.5:
        q = pathops.Path(p)
        cap = {"round": pathops.LineCap.ROUND_CAP, "square": pathops.LineCap.SQUARE_CAP}.get(
            st.get("stroke-linecap"), pathops.LineCap.BUTT_CAP)
        join = {"round": pathops.LineJoin.ROUND_JOIN, "bevel": pathops.LineJoin.BEVEL_JOIN}.get(
            st.get("stroke-linejoin"), pathops.LineJoin.MITER_JOIN)
        q = q.transform(*tf)   # stroke after transform so width is in canvas units
        q.stroke(sw, cap, join, 4)
        items.append((stroke, q))


# root canvas
vb = root.get("viewBox")
if vb:
    vb = [float(v) for v in re.split(r"[\s,]+", vb.strip())]
else:
    vb = [0, 0, num(root, "width", 100), num(root, "height", 100)]
walk(root, {"_op": 1.0}, (1, 0, 0, 1, 0, 0))
if not items:
    sys.exit("no filled shapes found")
for w in sorted(warn):
    print("warning:", w)

# --- colors ------------------------------------------------------------------
if args.drop_bg:
    keep = []
    for h, p in items:
        x0, y0, x1, y1 = p.bounds
        if (x1 - x0) * (y1 - y0) >= 0.9 * vb[2] * vb[3]:
            print(f"dropping background shape {h}")
            continue
        keep.append((h, p))
    items = keep

area = {}
for h, p in items:
    x0, y0, x1, y1 = p.bounds
    area[h] = area.get(h, 0) + (x1 - x0) * (y1 - y0)
svg_cols = sorted(area, key=lambda h: -area[h])
canvas = vb[2] * vb[3]
if args.suggest or not args.out_dir:
    print(f"{len(items)} shapes, canvas {vb[2]:g} x {vb[3]:g}")
    for h in svg_cols:
        print(f"  {h}  bbox-area {100 * area[h] / canvas:6.1f}%  ~{L.name_of(L.hex2rgb(h))}")
    sys.exit(0)

if args.colors:
    layers = L.parse_colors(args.colors)
    assign = {h: L.nearest(L.hex2rgb(h), layers)[0] for h in svg_cols}
else:
    layers, assign = [], {}
    for h in svg_cols:
        for i, l in enumerate(layers):
            if np.linalg.norm(L.rgb2lab(L.hex2rgb(h)) - L.rgb2lab(L.hex2rgb(l["hex"]))) < args.merge_de:
                assign[h] = i
                break
        else:
            nm = L.name_of(L.hex2rgb(h))
            k = sum(l["name"].startswith(nm) for l in layers)
            layers.append({"name": nm + (str(k + 1) if k else ""), "hex": h})
            assign[h] = len(layers) - 1
for part in (args.map or "").split(","):
    if part.strip():
        h, nm = part.split("=")
        assign[L.rgb2hex(L.hex2rgb(h.strip()))] = [l["name"].lower() for l in layers].index(nm.strip().lower())
drop = {n.strip().lower() for n in (args.drop or "").split(",") if n.strip()}

print("layers:")
for i, l in enumerate(layers):
    src = [h for h in svg_cols if assign[h] == i]
    print(f"  {l['name']:>10} {l['hex']}  <- SVG colors {', '.join(src) or '(none)'}"
          + ("  [dropped]" if l["name"].lower() in drop else ""))
n_out = sum(1 for i, l in enumerate(layers) if l["name"].lower() not in drop and any(assign[h] == i for h in svg_cols))
if n_out > L.MAX_COLORS and not args.force:
    sys.exit(f"{n_out} colors > {L.MAX_COLORS}: merge some with --colors (or --force)")

# --- occlusion: top-most shape wins -----------------------------------------
acc = [pathops.Path() for _ in layers]
covered = pathops.Path()
for h, p in reversed(items):
    p = pathops.Path(p)
    p.convertConicsToQuads()   # arcs / round caps come out as conics
    p.simplify(fix_winding=True)
    vis = pathops.op(p, covered, pathops.PathOp.DIFFERENCE, fix_winding=True)
    covered = pathops.op(covered, p, pathops.PathOp.UNION, fix_winding=True)
    i = assign[h]
    acc[i] = pathops.op(acc[i], vis, pathops.PathOp.UNION, fix_winding=True)


def to_d(p):
    """pathops path -> absolute M/L/C/Q/Z (what check_layers.py reads)"""
    out, pts = [], iter(p.points)
    f = lambda pt: f"{pt[0] - vb[0]:.2f} {pt[1] - vb[1]:.2f}"
    V = pathops.PathVerb
    for verb in p.verbs:
        if verb == V.MOVE:
            out.append("M " + f(next(pts)))
        elif verb == V.LINE:
            out.append("L " + f(next(pts)))
        elif verb == V.QUAD:
            out.append("Q " + " ".join(f(next(pts)) for _ in range(2)))
        elif verb == V.CUBIC:
            out.append("C " + " ".join(f(next(pts)) for _ in range(3)))
        elif verb == V.CLOSE:
            out.append("Z")
    return " ".join(out)


out = []
for i, l in enumerate(layers):
    if l["name"].lower() in drop or not acc[i].bounds or acc[i].area < 1e-6:
        continue
    acc[i].convertConicsToQuads()
    out.append((l, [to_d(acc[i])]))

src_w, src_h = vb[2], vb[3]
if args.width_mm:
    size = (args.width_mm, args.width_mm * src_h / src_w)
elif args.height_mm:
    size = (args.height_mm * src_w / src_h, args.height_mm)
else:   # keep the SVG's physical size if it has one, else 1 unit = 1 px @96dpi
    def mm(v, units):
        m = re.match(r"([\d.]+)\s*(mm|cm|in|pt|px)?", v or "")
        if not m:
            return units * 25.4 / 96
        k = {"mm": 1, "cm": 10, "in": 25.4, "pt": 25.4 / 72, "px": 25.4 / 96, None: 25.4 / 96}[m.group(2)]
        return float(m.group(1)) * k
    size = (mm(root.get("width"), src_w), mm(root.get("height"), src_h))
name = args.name or os.path.splitext(os.path.basename(args.src))[0]
L.write_layer_set(args.out_dir, name, (0, 0, src_w, src_h), size, out, args.title, os.path.abspath(args.src))
