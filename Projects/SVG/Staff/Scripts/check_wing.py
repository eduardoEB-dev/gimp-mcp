"""Stacked fill preview + hole count for left_wing_svg. python check_wing.py out.png"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import left_wing_svg as w

S = 8; x0, y0 = 418, 986
T = lambda p: ((p[0] - x0) * S, (p[1] - y0) * S)
im = Image.new('RGB', (192 * S, 128 * S), 'white'); d = ImageDraw.Draw(im)
m = Image.new('L', im.size, 0); dm = ImageDraw.Draw(m)
fill = {'row3': (196, 150, 60), 'row2': (214, 172, 80), 'row1': (230, 192, 104)}
for g, row in reversed(w.ROWS):                 # row3 at the back, row1 in front
    for f, b, t, hw, bd, tm in reversed(row):   # each feather lies over the one below it
        P = [T(p) for p in w.path_poly(w.feather_clipped(g, f, b, t, hw, bd, tm))]
        d.polygon(P, fill=fill[g]); d.line(P + [P[0]], fill=(0, 0, 0), width=2)
        d.line([T(p) for p in w.spine_clipped(b, t, bd)], fill=(120, 85, 30), width=2)
        dm.polygon(P, fill=255)
A = [T(p) for p in w.path_poly(w.arm_path())]
d.polygon(A, fill=(240, 205, 120)); d.line(A + [A[0]], fill=(0, 0, 0), width=2); dm.polygon(A, fill=255)
cx, cy = T(w.BALL_C); r = w.BALL_R * S
d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 0, 0), width=2)
lab, n = ndimage.label(~(np.array(m) > 0)); bg = lab[0, 0]
holes = sorted((int((lab == i).sum()) for i in range(1, n + 1) if i != bg), reverse=True)
for i in range(1, n + 1):
    if i != bg: im.paste((255, 0, 0), mask=Image.fromarray(((lab == i) * 255).astype('uint8')))
im.save(sys.argv[1])
print('holes:', len(holes), holes[:8])
