"""Generate vector recreation of Papel1.png (green papel picado banner).

Coords in 6x-upscale space of source (876x714); output size 5x source (730x595).
Cutouts done via mask so holes are truly transparent.
"""
import math
import os
import sys

GREEN = "#8AD33C"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(__file__), "..", "SVGs Drafts", "Papel1.svg")

L, R, T, B = 84, 770, 130, 545          # banner body
PX0, PX1, PY0, PY1 = 112, 742, 158, 522  # inner lattice panel
CX = 427                                 # center skull x
N_LOBES = 5

cut = []    # black (cut) mask elements
keep = []   # white (paper) mask elements, drawn after lattice cut


def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def teardrop(cx, cy, ang, length, width):
    """Teardrop slit pointing along ang (deg) from (cx,cy)."""
    a = math.radians(ang)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx
    tip = (cx + dx * length, cy + dy * length)
    c1 = (cx + nx * width, cy + ny * width)
    c2 = (cx - nx * width, cy - ny * width)
    return (f'<path d="M{f(cx)},{f(cy)} Q{f(c1[0])},{f(c1[1])} {f(tip[0])},{f(tip[1])} '
            f'Q{f(c2[0])},{f(c2[1])} {f(cx)},{f(cy)}Z" fill="#000"/>')


def flower(cx, cy, r, petals=6, color="#000"):
    out = []
    for i in range(petals):
        a = 360 / petals * i - 90
        rad = math.radians(a)
        px, py = cx + math.cos(rad) * r, cy + math.sin(rad) * r
        out.append(f'<ellipse cx="{f(px)}" cy="{f(py)}" rx="{f(r*0.75)}" ry="{f(r*0.42)}" '
                   f'transform="rotate({f(a)} {f(px)} {f(py)})" fill="{color}"/>')
    return out


# --- banner outline with scalloped bottom ---
lw = (R - L) / N_LOBES
d = f"M{L},{T} H{R} V{B}"
for i in range(N_LOBES, 0, -1):
    x0 = L + lw * (i - 1)
    d += f" A{f(lw/2)} 58 0 0 1 {f(x0)},{B}"
d += "Z"
body = f'<path d="{d}" fill="#fff"/>'

# --- serrated edge: tiny cut dots on outline ---
step = 11
for x in range(L, R + 1, step):
    cut.append(f'<circle cx="{x}" cy="{T}" r="2.6" fill="#000"/>')
for y in range(T + step, B, step):
    cut.append(f'<circle cx="{L}" cy="{y}" r="2.6" fill="#000"/>')
    cut.append(f'<circle cx="{R}" cy="{y}" r="2.6" fill="#000"/>')
for i in range(N_LOBES):
    cx = L + lw * (i + 0.5)
    for k in range(1, 14):
        t = math.pi * k / 14
        cut.append(f'<circle cx="{f(cx + math.cos(t) * lw/2)}" cy="{f(B + math.sin(t) * 58)}" '
                   f'r="2.6" fill="#000"/>')

# --- lattice panel: cut rect, add back diagonal strips ---
cut.append(f'<rect x="{PX0}" y="{PY0}" width="{PX1-PX0}" height="{PY1-PY0}" rx="4" fill="#000"/>')
lat = []
sp = 42
span = (PX1 - PX0) + (PY1 - PY0)
for k in range(-span, span * 2, sp):
    x = PX0 + k
    lat.append(f'<line x1="{x}" y1="{PY0}" x2="{x + (PY1-PY0)}" y2="{PY1}"/>')
    lat.append(f'<line x1="{x}" y1="{PY1}" x2="{x + (PY1-PY0)}" y2="{PY0}"/>')
keep.append(f'<g clip-path="url(#panel)" stroke="#fff" stroke-width="10">{"".join(lat)}</g>')
# little diamonds at lattice crossings for paper-cut look
for i, x in enumerate(range(PX0 - span, PX1 + span, sp)):
    pass

# --- center solid panel ---
keep.append(f'<path d="M282,{PY0} H573 V300 C580,420 560,470 520,{PY1} H334 C294,470 274,420 282,300Z" fill="#fff"/>')

# --- side skull heads (paper over lattice) ---
SIDE = [(210, 398), (644, 392)]
for sx, sy in SIDE:
    keep.append(f'<path d="M{sx-78},{sy-5} A78,82 0 0 1 {sx+78},{sy-5} '
                f'Q{sx+80},{sy+50} {sx+52},{sy+68} V{sy+88} H{sx-52} V{sy+68} '
                f'Q{sx-80},{sy+50} {sx-78},{sy-5}Z" fill="#fff"/>')

# ---------- details cut into paper (drawn last) ----------
det = []

# center: top flower + garland
det += flower(CX, 182, 11)
det.append(f'<circle cx="{CX}" cy="182" r="5" fill="#000"/>')
for side in (-1, 1):
    # garland swag of slits
    for k in range(9):
        t = k / 8
        x = CX + side * (28 + t * 105)
        y = 196 + math.sin(t * math.pi) * 28
        ang = (90 + side * 60) if side < 0 else (90 - 60)
        det.append(teardrop(x, y, 90 + side * (40 - 80 * t), 16, 4.5))
    # hanging drops
    for dx, dy in ((48, 240), (100, 238)):
        det.append(teardrop(CX + side * dx, dy - 14, 90, 22, 6))
    # upper side sprigs
    for k in range(3):
        det.append(teardrop(CX + side * 60, 178, -90 + side * (30 + 35 * k), 20, 5))

# cranium dashed arc
det.append(f'<path d="M310,345 C310,250 544,250 544,345" fill="none" stroke="#000" '
           f'stroke-width="7" stroke-linecap="round" stroke-dasharray="20 11"/>')
# eyes
det.append('<ellipse cx="365" cy="326" rx="48" ry="37" fill="#000"/>')
det.append('<ellipse cx="489" cy="326" rx="48" ry="37" fill="#000"/>')
# nose
det.append(f'<path d="M{CX},356 L{CX+17},392 Q{CX},386 {CX-17},392Z" fill="#000" '
           f'stroke="#000" stroke-width="3" stroke-linejoin="round"/>')
# cheeks / jaw arcs
det.append('<path d="M326,372 Q308,430 352,478" fill="none" stroke="#000" stroke-width="7" stroke-linecap="round"/>')
det.append('<path d="M528,372 Q546,430 502,478" fill="none" stroke="#000" stroke-width="7" stroke-linecap="round"/>')
# smile line + teeth
det.append(f'<path d="M352,418 Q{CX},434 502,418" fill="none" stroke="#000" stroke-width="6" stroke-linecap="round"/>')
tw, tg = 13, 4.5
n = 8
x0 = CX - (n * tw + (n - 1) * tg) / 2
for r, (ty, th) in enumerate(((436, 14), (455, 14))):
    for k in range(n):
        det.append(f'<rect x="{f(x0 + k*(tw+tg))}" y="{ty}" width="{tw}" height="{th}" rx="3" fill="#000"/>')
det.append(f'<path d="M362,478 Q{CX},494 492,478" fill="none" stroke="#000" stroke-width="5" stroke-linecap="round"/>')
# chin flower + lower side sprigs
det += flower(CX, 506, 7)
for side in (-1, 1):
    for k in range(3):
        det.append(teardrop(CX + side * 95, 505, 180 * (side < 0) + side * (-30 + 30 * k), 18, 4.5))

# side skulls
for sx, sy in SIDE:
    det.append(f'<path d="M{sx-62},{sy-5} A62,64 0 0 1 {sx+62},{sy-5}" fill="none" stroke="#000" '
               f'stroke-width="5" stroke-linecap="round" stroke-dasharray="12 8"/>')
    det += flower(sx, sy - 48, 7)
    det.append(f'<circle cx="{sx}" cy="{sy-48}" r="3" fill="#000"/>')
    for side in (-1, 1):
        for k in range(3):
            det.append(teardrop(sx + side * 24, sy - 42, -90 + side * (35 + 30 * k), 13, 3.5))
    det.append(f'<ellipse cx="{sx-28}" cy="{sy}" rx="23" ry="18" fill="#000"/>')
    det.append(f'<ellipse cx="{sx+28}" cy="{sy}" rx="23" ry="18" fill="#000"/>')
    det.append(f'<path d="M{sx},{sy+20} L{sx+9},{sy+38} L{sx-9},{sy+38}Z" fill="#000" '
               f'stroke="#000" stroke-width="2" stroke-linejoin="round"/>')
    det.append(f'<path d="M{sx-50},{sy+20} Q{sx-58},{sy+50} {sx-36},{sy+70}" fill="none" stroke="#000" stroke-width="5" stroke-linecap="round"/>')
    det.append(f'<path d="M{sx+50},{sy+20} Q{sx+58},{sy+50} {sx+36},{sy+70}" fill="none" stroke="#000" stroke-width="5" stroke-linecap="round"/>')
    for r, ty in enumerate((sy + 50, sy + 63)):
        for k in range(5):
            det.append(f'<rect x="{sx - 33 + k*14}" y="{ty}" width="10" height="9" rx="2" fill="#000"/>')

# scallop fans
for i in range(N_LOBES):
    cx = L + lw * (i + 0.5)
    for k in range(5):
        det.append(teardrop(cx, B + 2, 30 + k * 30, 38, 6))
    det.append(f'<circle cx="{f(cx)}" cy="{B-4}" r="4.5" fill="#000"/>')
    for side in (-1, 1):
        det.append(f'<circle cx="{f(cx + side*48)}" cy="{B+4}" r="4" fill="#000"/>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="730" height="595" viewBox="-11 9.5 876 714">
  <title>Papel picado - calaveras</title>
  <defs>
    <clipPath id="panel"><rect x="{PX0}" y="{PY0}" width="{PX1-PX0}" height="{PY1-PY0}"/></clipPath>
    <mask id="cuts" maskUnits="userSpaceOnUse" x="-11" y="9.5" width="876" height="714">
      {body}
      {"".join(cut)}
      {"".join(keep)}
      {"".join(det)}
    </mask>
  </defs>
  <rect x="-11" y="9.5" width="876" height="714" fill="{GREEN}" mask="url(#cuts)"/>
</svg>
'''

os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(svg)
print("wrote", os.path.abspath(OUT))
