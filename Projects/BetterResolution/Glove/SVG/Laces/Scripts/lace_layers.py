"""Glove views -> black lace SVGs. Hand-tuned recipe (SVG_Creation_Workflow.md):
neutral-black class, then erase what's black but not lace (slots, shadows,
wrist hole). Canvas = glove silhouette, so the views share a scale.
Writes Black (laces, for Blender) + Outline (glove reference, same canvas).

  python lace_layers.py <view|all> [--debug]
Erase areas in ERASE below (source px, polygons)."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ni
sys.path.insert(0, r"D:\gimp-mcp\Projects\Workflow\SVG Creation")
import layers_common as L

P = r"D:\gimp-mcp\Projects\BetterResolution\Glove\SVG\Laces"
HEIGHT_MM = 101.6      # 4 in, loop included (Blender Project.md)
L_MAX, CH_MAX = 36, 15 # lace = dark + neutral; brown shadow fails chroma
L_SOFT, CH_SOFT = 52, 12  # lace highlights, only kept touching core
CLOSE, OPEN = 3, 3     # px; OPEN drops stitches + rims under ~0.5 mm
MIN_BLOB = 500         # px
OUTLINE = 6            # px, reference outline width (~0.45 mm)
HOLE = 260             # px; fill highlight specks inside laces
UP, BLUR = 5, 0.9

VIEWS = {"Front": "FrontView", "Back": "BackView", "Left": "LeftSide", "Right": "RightSide"}
ERASE = {
    "Front": [
        [(500, 1392), (681, 1392), (651, 1410), (651, 1430), (500, 1430)],      # floor shadow, gaps between laces
        [(728, 1392), (800, 1392), (775, 1410), (775, 1430), (702, 1430), (702, 1410)],
        [(847, 1392), (914, 1392), (890, 1410), (890, 1430), (822, 1430), (822, 1410)],
        [(976, 1392), (1070, 1392), (1070, 1430), (950, 1430), (950, 1410)],
        [(500, 1412), (1070, 1412), (1070, 1430), (500, 1430)],                 # floor shadow, under laces
        [(775, 680), (830, 680), (862, 430), (812, 430)],                       # slot 1
        [(946, 730), (985, 730), (1052, 492), (1002, 492)],                     # slot 2
        [(1085, 850), (1125, 850), (1192, 660), (1205, 598), (1165, 598)],      # slot 3
        [(530, 815), (780, 755), (1020, 815), (1020, 835), (780, 775), (530, 835)],  # pocket lip
        [(478, 425), (556, 412), (556, 472), (478, 478)],                       # web gap shadow, upper
        [(455, 505), (552, 480), (552, 500), (455, 545)],                       # web rail edge shadow
        [(390, 535), (460, 505), (460, 540), (395, 582)],                       # web rail edge shadow, lower
        [(322, 545), (362, 512), (392, 586), (362, 602), (345, 605)],           # void behind web, upper
        [(388, 728), (412, 722), (436, 790), (412, 802)],                       # void behind web, lower
    ],
    "Back": [
        [(590, 985), (1025, 985), (1025, 1155), (590, 1155)],                   # wrist hole
        [(530, 1358), (1085, 1358), (1085, 1420), (530, 1420)],                 # floor shadow
        [(670, 440), (712, 440), (790, 835), (750, 835)],                       # slot 2
        [(872, 440), (915, 440), (950, 830), (905, 830)],                       # slot 3
        [(1060, 880), (1095, 880), (1125, 560), (1090, 560)],                   # slot 4
    ],
    "Left": [
        [(760, 120), (880, 120), (880, 262), (760, 262)],                       # loop hole
        [(640, 1372), (800, 1372), (860, 1402), (1000, 1402), (1000, 1425), (640, 1425)],  # floor shadow
    ],
    "Right": [
        [(660, 120), (810, 120), (810, 268), (660, 268)],                       # loop hole
    ],
}


def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def build(view):
    src = os.path.join(P, "Images", VIEWS[view] + ".png")
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(float)
    H, W = rgb.shape[:2]
    lab = L.rgb2lab(rgb); ll = lab[..., 0]; ch = np.hypot(lab[..., 1], lab[..., 2])
    erase = Image.new("1", (W, H)); d = ImageDraw.Draw(erase)
    for p in ERASE[view]:
        d.polygon(p, fill=1)
    erase = np.asarray(erase)

    core = (ll < L_MAX) & (ch < CH_MAX) & ~erase
    soft = (ll < L_SOFT) & (ch < CH_SOFT) & ~erase
    lb, _ = ni.label(core | soft)                 # highlights, if tied to core
    m = np.isin(lb, np.unique(lb[core]))
    m = ni.binary_closing(m, disk(CLOSE)) & ~erase
    hl, n = ni.label(~m)                          # small holes = gloss specks
    if n:
        sz = ni.sum(~m, hl, range(1, n + 1))
        m |= np.isin(hl, 1 + np.where(sz < HOLE)[0])
    m = ni.binary_opening(m, disk(OPEN)) & ~erase
    lb, n = ni.label(m)
    sz = ni.sum(m, lb, range(1, n + 1))
    m = np.isin(lb, 1 + np.where(sz >= MIN_BLOB)[0])

    # canvas = silhouette (tan or lace; not grey floor shadow)
    sil = ni.binary_closing((ch > 25) | m, disk(4))
    sil = ni.binary_opening(sil, disk(2))
    lb, n = ni.label(sil)
    sil = ni.binary_fill_holes(lb == 1 + np.argmax(ni.sum(sil, lb, range(1, n + 1))))
    sil &= ~ni.binary_opening((ll > 88) & (ch < 12), disk(4))   # real see-through: loop, web gaps
    ys, xs = np.where(sil | m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    c = m[y0:y1, x0:x1]
    h, w = c.shape
    def smooth(a):
        im = Image.fromarray((a * 255).astype(np.uint8)).resize((w * UP, h * UP), Image.BICUBIC)
        return np.asarray(im.filter(ImageFilter.GaussianBlur(BLUR * UP))) > 127
    s = sil[y0:y1, x0:x1]
    ring = s & ~ni.binary_erosion(s, disk(OUTLINE))
    return src, rgb, m, smooth(c), smooth(ring)


def run(view, debug):
    src, rgb, m, big, ring = build(view)
    name = f"Laces_{view}"
    out = os.path.join(P, "Drafts", name + "_v1")   # iterate in place until a new direction
    bw, bh = big.shape[1], big.shape[0]
    size = (HEIGHT_MM * bw / bh, HEIGHT_MM)
    layers = [({"name": "Outline", "hex": "#D98A2B"}, L.trace_mask(ring, speckle=UP * UP)),
              ({"name": "Black", "hex": "#111111"}, L.trace_mask(big, speckle=UP * UP))]
    L.write_layer_set(out, name, (0, 0, bw, bh), size, layers, f"Glove laces, {view} view", src)
    if debug:     # overlay: red edge = trace, on source
        os.makedirs(os.path.join(P, "Drafts", "_scan"), exist_ok=True)
        e = m ^ ni.binary_erosion(m, disk(2))
        o = rgb.copy(); o[e] = [0, 255, 60]
        Image.fromarray(o.astype(np.uint8)).save(os.path.join(P, "Drafts", "_scan", f"{view}_edge.png"))


views = list(VIEWS) if sys.argv[1] == "all" else [sys.argv[1]]
for v in views:
    run(v, "--debug" in sys.argv)
