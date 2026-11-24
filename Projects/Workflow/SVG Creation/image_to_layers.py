"""Image -> one SVG per color (aligned, non-overlapping) for multi-color 3D
printing in Bambu Studio. Generalized from Snoopy/snoopy_layers.py.

Pipeline: background removal -> per-pixel color class (soft scores) ->
supersample + blur (smooth edges) -> argmax label map (no gaps/overlaps) ->
tiny islands merged into neighbors -> vtracer per class.

usage:
  python image_to_layers.py in.png --suggest                 # list image colors, stop
  python image_to_layers.py in.png out_dir --name Snoopy     # auto colors from image
  python image_to_layers.py in.png out_dir --colors "Red,White,Green,Yellow=#F5E11E,Black"
options:
  --bg outline|color|alpha|none   outline = flood from border through non-dark px
                                  (cartoons with black outlines); color = flood
                                  through px close to the border colors; alpha =
                                  transparency; none = keep whole image
  --keep largest|all  --open R    keep biggest blob / all; opening radius that cuts
                                  thin background lines off (outline/color modes)
  --erase "x0,y0,x1,y1;..."       force regions to background (source px)
  --cut-white N                   cut all enclosed near-white regions >= N px (letter counters)
  --cut-hole "x,y;..."            enclosed background gap (e.g. between hat parts):
                                  near-white px connected to each seed -> background
  --box "x0,y0,x1,y1"             only keep inside this box
  --map "#B0D122=Green,..."       extra image-color -> layer hints
  --grow "Black=1.5"              thicken a layer (px) when lines print too thin
  --height-mm 70 | --width-mm 90  output size
  --debug dbg.png                 label map preview
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layers_common as L  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out_dir", nargs="?")
ap.add_argument("--name", default=None)
ap.add_argument("--title", default=None)
ap.add_argument("--suggest", action="store_true")
ap.add_argument("--colors", help='layer colors, e.g. "Red,White,Green=#9FC52A" (default: from image)')
ap.add_argument("--map", help='image color hints "#hex=LayerName,..."')
ap.add_argument("--k", type=int, default=8, help="color clusters to look for")
ap.add_argument("--min-pct", type=float, default=0.8, help="clusters smaller than this %% are edge blends, dropped")
ap.add_argument("--merge-de", type=float, default=15, help="auto mode: merge clusters closer than this (Lab)")
ap.add_argument("--bg", default="outline", choices=["outline", "color", "alpha", "none"])
ap.add_argument("--ink", type=float, default=110, help="luminance below which a px counts as outline ink")
ap.add_argument("--bg-tol", type=float, default=20, help="color mode: Lab distance to border colors")
ap.add_argument("--keep", default="largest", choices=["largest", "all"])
ap.add_argument("--min-blob", type=int, default=400, help="keep=all: drop blobs smaller than this (px)")
ap.add_argument("--open", type=int, default=5, help="opening radius (px) cutting thin lines off the subject")
ap.add_argument("--erase")
ap.add_argument("--cut-hole", help="x,y;... seeds of enclosed bg gaps to make transparent")
ap.add_argument("--cut-white", type=int, default=0, help="cut every enclosed near-white region >= N px (letter counters)")
ap.add_argument("--hole-lum", type=float, default=235, help="cut-hole: min luminance of gap px")
ap.add_argument("--box")
ap.add_argument("--up", type=int, default=5, help="supersample factor")
ap.add_argument("--blur", type=float, default=0.8, help="edge smoothing radius, source px")
ap.add_argument("--sigma", type=float, default=30, help="color class softness (Lab units)")
ap.add_argument("--grow", help='thicken layers, source px: "Black=1.5,Red=1" (thin outlines)')
ap.add_argument("--island", type=float, default=6, help="merge regions smaller than this many source px")
ap.add_argument("--flat", type=float, default=0, help="3D-print basics: remove accents/highlights narrower than 2x this (source px) and refill from neighbors")
ap.add_argument("--island-skip", help='layers never merged away by --island, e.g. "White" (teeth, eye shines)')
ap.add_argument("--split-thick", help='"Black=DarkBlue:6": thick parts of Black whose source color is nearer DarkBlue become DarkBlue (pads vs outline)')
ap.add_argument("--flat-skip", help='layers --flat leaves alone, usually the outline: "DarkBlue,Black"')
g = ap.add_mutually_exclusive_group()
g.add_argument("--height-mm", type=float)
g.add_argument("--width-mm", type=float)
ap.add_argument("--debug")
ap.add_argument("--force", action="store_true", help=f"allow more than {L.MAX_COLORS} colors")
args = ap.parse_args()

img = Image.open(args.src)
alpha = np.asarray(img.convert("RGBA"))[..., 3] if "A" in img.getbands() else None
rgb = np.asarray(img.convert("RGB")).astype(float)
H, W = rgb.shape[:2]
lab = L.rgb2lab(rgb)
lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def rects(s):
    return [tuple(int(v) for v in r.split(",")) for r in s.split(";") if r.strip()]


def disk(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return xx * xx + yy * yy <= r * r


def kmeans(X, k, iters=25, seed=0):
    rng = np.random.default_rng(seed)
    C = X[[rng.integers(len(X))]]
    for _ in range(1, k):   # k-means++ init
        d = ((X[:, None] - C[None]) ** 2).sum(-1).min(1)
        if d.sum() == 0:    # flat-color input: fewer distinct colors than k
            break
        C = np.vstack([C, X[rng.choice(len(X), p=d / d.sum())]])
    for _ in range(iters):
        a = ((X[:, None] - C[None]) ** 2).sum(-1).argmin(1)
        C = np.array([X[a == i].mean(0) if (a == i).any() else C[i] for i in range(len(C))])
    a = ((X[:, None] - C[None]) ** 2).sum(-1).argmin(1)
    return C, np.bincount(a, minlength=len(C))


# --- subject mask -----------------------------------------------------------
if args.bg == "alpha":
    if alpha is None:
        sys.exit("--bg alpha: image has no transparency")
    fg = alpha > 127
elif args.bg == "none":
    fg = np.ones((H, W), bool)
else:
    if args.bg == "outline":
        passable = lum >= args.ink
    else:
        border = np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])
        C, n = kmeans(border[::max(1, len(border) // 4000)], 3)
        C = C[n > n.sum() * 0.1]
        passable = np.min([np.linalg.norm(lab - c, axis=-1) for c in C], 0) < args.bg_tol
    lab_, _ = ndimage.label(passable)
    edge = np.unique(np.concatenate([lab_[0], lab_[-1], lab_[:, 0], lab_[:, -1]]))
    fg = ~np.isin(lab_, edge[edge > 0])
for x0, y0, x1, y1 in rects(args.erase or ""):
    fg[y0:y1, x0:x1] = False
if args.box:
    x0, y0, x1, y1 = rects(args.box)[0]
    m = np.zeros_like(fg)
    m[y0:y1, x0:x1] = True
    fg &= m
if args.bg in ("outline", "color") and args.open > 0:
    # cut thin strokes (horizon lines, branches) off the subject, then restore its outline
    core = ndimage.binary_opening(fg, structure=disk(args.open))
    lb, nb = ndimage.label(core)
    if nb:
        sz = ndimage.sum(core, lb, range(1, nb + 1))
        keep = [1 + int(np.argmax(sz))] if args.keep == "largest" else 1 + np.where(sz >= args.min_blob)[0]
        core = np.isin(lb, keep)
    fg = ndimage.binary_fill_holes(ndimage.binary_dilation(core, structure=disk(args.open)) & fg)
for pt in (args.cut_hole or "").split(";"):
    if not pt.strip():
        continue
    hx, hy = (int(float(v)) for v in pt.split(","))
    near_white = (lum >= args.hole_lum) & (rgb.max(-1) - rgb.min(-1) < 40)
    lb_h, _ = ndimage.label(near_white)
    if not lb_h[hy, hx]:
        sys.exit(f"--cut-hole {hx},{hy}: seed is not on near-white background")
    hole = ndimage.binary_dilation(lb_h == lb_h[hy, hx], structure=disk(1))  # eat AA fringe
    fg &= ~hole
    print(f"cut hole at {hx},{hy}: {int(hole.sum())} px")
if args.cut_white:
    near_white = (lum >= args.hole_lum) & (rgb.max(-1) - rgb.min(-1) < 40)
    lb_w, nw = ndimage.label(near_white & fg)
    if nw:
        sz = ndimage.sum(np.ones_like(lb_w), lb_w, range(1, nw + 1))
        big = np.isin(lb_w, 1 + np.where(sz >= args.cut_white)[0])
        fg &= ~ndimage.binary_dilation(big, structure=disk(1))
        print(f"cut-white: {int((sz >= args.cut_white).sum())} regions")
if not fg.any():
    sys.exit("nothing left after background removal; try --bg color/none or --ink")

# --- colors -----------------------------------------------------------------
pix = rgb[fg][:: max(1, fg.sum() // 30000)]
C, n = kmeans(L.rgb2lab(pix), args.k)
# cluster centers back to RGB = mean rgb of members
a = ((L.rgb2lab(pix)[:, None] - C[None]) ** 2).sum(-1).argmin(1)
crgb = np.array([pix[a == i].mean(0) if (a == i).any() else [0, 0, 0] for i in range(len(C))])
pct = 100 * n / n.sum()
order = np.argsort(-pct)
clusters = [(crgb[i], pct[i]) for i in order if pct[i] >= args.min_pct]

if args.suggest or not args.out_dir:
    print(f"subject: {fg.sum()} px of {H * W}  (bg mode {args.bg})")
    for c, p in clusters:
        print(f"  {L.rgb2hex(c)}  {p:5.1f}%  ~{L.name_of(c)}")
    print("dropped (edge blends):", ", ".join(f"{L.rgb2hex(crgb[i])} {pct[i]:.1f}%" for i in order if pct[i] < args.min_pct) or "none")
    sys.exit(0)

if args.colors:
    layers = L.parse_colors(args.colors)
    refs = [[L.hex2rgb(c["hex"])] for c in layers]
    for c, _ in clusters:            # each image color teaches its closest layer
        refs[L.nearest(c, layers)[0]].append(c)
else:
    layers, refs = [], []
    for c, _ in clusters:            # auto: one layer per distinct image color
        for i, r in enumerate(refs):
            if np.linalg.norm(L.rgb2lab(c) - L.rgb2lab(r[0])) < args.merge_de:
                r.append(c)
                break
        else:
            nm = L.name_of(c)
            k = sum(l["name"].startswith(nm) for l in layers)
            layers.append({"name": nm + (str(k + 1) if k else ""), "hex": L.rgb2hex(c)})
            refs.append([c])
for h, nm in [p.split("=") for p in (args.map or "").split(",") if p.strip()]:
    i = [l["name"].lower() for l in layers].index(nm.strip().lower())
    refs[i].append(L.hex2rgb(h.strip()))

print("layers:")
for l, r in zip(layers, refs):
    print(f"  {l['name']:>10} {l['hex']}  <- image colors {', '.join(L.rgb2hex(c) for c in r)}")
if len(layers) > L.MAX_COLORS and not args.force:
    sys.exit(f"{len(layers)} colors > {L.MAX_COLORS}: merge some with --colors (or --force)")

# --- label map --------------------------------------------------------------
ys, xs = np.where(fg)
pad = 4
y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, H)
x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, W)
labc = lab[y0:y1, x0:x1]
h, w = labc.shape[:2]
up = args.up


def upsm(a):
    im = Image.fromarray((a * 255).astype(np.uint8)).resize((w * up, h * up), Image.BICUBIC)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(args.blur * up))).astype(float) / 255


scores = []
for r in refs:
    d = np.min([np.linalg.norm(labc - L.rgb2lab(c), axis=-1) for c in r], 0)
    scores.append(upsm(np.exp(-(d / args.sigma) ** 2)))
big = np.stack(scores)
inside = upsm(fg[y0:y1, x0:x1].astype(float)) > 0.5
lbl = np.argmax(big, 0)
darkest = int(np.argmin([L.rgb2lab(L.hex2rgb(l["hex"]))[0] for l in layers]))
lbl[big.max(0) < 0.05] = darkest      # no color fits -> darkest (outline ink)
lbl[~inside] = -1

for part in (args.grow or "").split(","):
    if part.strip():
        nm, r = part.split("=")
        c = [l["name"].lower() for l in layers].index(nm.strip().lower())
        rr = max(1, round(float(r) * up))
        lbl[ndimage.binary_dilation(lbl == c, structure=disk(rr)) & inside] = c

# --flat: 3D-print basics. Thin highlights/shading streaks (narrower than 2*R) are
# removed from every class except --flat-skip (outline/line colors), then refilled
# with the nearest surviving color. EDT-based opening = fast at supersampled scale.
if args.flat:
    rr = args.flat * up
    skip = {s.strip().lower() for s in (args.flat_skip or "").split(",") if s.strip()}
    removed = np.zeros(lbl.shape, bool)
    for c, l in enumerate(layers):
        if l["name"].lower() in skip:
            continue
        m = lbl == c
        if not m.any():
            continue
        core = ndimage.distance_transform_edt(m) > rr
        opened = ndimage.distance_transform_edt(~core) <= rr
        removed |= m & ~opened
    valid = (lbl >= 0) & ~removed
    _, (iy, ix) = ndimage.distance_transform_edt(~valid, return_indices=True)
    lbl[removed] = lbl[iy[removed], ix[removed]]
    print(f"flat: {100 * removed.sum() / max(1, (lbl >= 0).sum()):.1f}% px recolored (accents < {2 * args.flat:g} px wide)")

# --split-thick "Black=DarkBlue:6": thick parts (wider than 2*R src px) of a line color
# whose source px are closer to the other color move there (navy paw pads vs navy outline).
for part in (args.split_thick or "").split(","):
    if not part.strip():
        continue
    a_nm, rest = part.split("=")
    b_nm, r = rest.split(":")
    names = [l["name"].lower() for l in layers]
    a, b = names.index(a_nm.strip().lower()), names.index(b_nm.strip().lower())
    m = lbl == a
    core = ndimage.distance_transform_edt(m) > float(r) * up
    thick = m & (ndimage.distance_transform_edt(~core) <= float(r) * up)
    src_lab = labc[np.minimum(np.arange(lbl.shape[0]) // up, h - 1)][:, np.minimum(np.arange(lbl.shape[1]) // up, w - 1)]
    da = np.min([np.linalg.norm(src_lab - L.rgb2lab(c), axis=-1) for c in refs[a]], 0)
    db = np.min([np.linalg.norm(src_lab - L.rgb2lab(c), axis=-1) for c in refs[b]], 0)
    mv = thick & (db < da)
    # whole thick blobs move together (majority vote) so pads don't come out speckled
    lb, nb = ndimage.label(thick)
    if nb:
        frac = ndimage.mean(mv, lb, range(1, nb + 1))
        lbl[np.isin(lb, np.where(frac > 0.5)[0] + 1)] = b
    print(f"split-thick {a_nm}->{b_nm}: {int((lbl == b).sum() - 0)} px now {b_nm}")

# tiny islands -> most common neighboring label
min_px = up * up * args.island
iskip = {s.strip().lower() for s in (args.island_skip or "").split(",") if s.strip()}
for c in range(len(layers)):
    if layers[c]["name"].lower() in iskip:
        continue
    m = lbl == c
    lb, nb = ndimage.label(m)
    if not nb:
        continue
    sz = ndimage.sum(m, lb, range(1, nb + 1))
    for i in np.where(sz < min_px)[0]:
        isl = lb == i + 1
        ring = lbl[ndimage.binary_dilation(isl, iterations=2) & ~isl]
        ring = ring[(ring >= 0) & (ring != c)]
        if len(ring):
            lbl[isl] = np.bincount(ring).argmax()

if args.debug:
    pal = np.array([L.hex2rgb(l["hex"]) for l in layers] + [[120, 160, 200]], np.uint8)
    dbg = Image.fromarray(pal[np.where(lbl < 0, len(layers), lbl)])
    dbg.thumbnail((1400, 1400))
    os.makedirs(os.path.dirname(os.path.abspath(args.debug)), exist_ok=True)
    dbg.save(args.debug)

# --- trace + write ----------------------------------------------------------
BH, BW = lbl.shape
if args.width_mm:
    size = (args.width_mm, args.width_mm * BH / BW)
else:
    hm = args.height_mm or 70.0
    size = (hm * BW / BH, hm)
name = args.name or os.path.splitext(os.path.basename(args.src))[0]
out = [(l, L.trace_mask(lbl == i, speckle=up * up)) for i, l in enumerate(layers)]
L.write_layer_set(args.out_dir, name, (0, 0, BW, BH), size, out, args.title, os.path.abspath(args.src))
