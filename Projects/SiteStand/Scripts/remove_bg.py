import sys, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
src, out = sys.argv[1], sys.argv[2]
im = np.asarray(Image.open(src).convert('RGB')).astype(float)
H, W, _ = im.shape
v = im.max(2)
g = ndi.maximum_filter(ndi.gaussian_gradient_magnitude(v, 1.5), 25)
fg = ndi.binary_opening((v > 150) & (g > 18), iterations=1)
# tagline: thin text, lower threshold, band only
band = np.zeros_like(fg); band[598:628, 195:830] = True
fg |= band & (v > 110)
lab, n = ndi.label(ndi.binary_closing(fg, iterations=2))
objs = ndi.find_objects(lab)
sizes = ndi.sum(fg, lab, range(1, n+1))
white = [(15,185,598,625),(840,1005,604,625),(45,110,760,795),(890,990,675,800)]
keep = np.zeros_like(fg)
for i, sl in enumerate(objs):
    if sizes[i] < (15 if 598 <= sl[0].start and sl[0].stop <= 630 and 195 < sl[1].start < 830 else 150): continue
    y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
    cx, cy = (x0+x1)/2, (y0+y1)/2
    if cy > 965: 
        if not (120 < cx < 300 or 730 < cx < 900) or y1 > 1260: continue  # arrows only
    elif cx < 130 or cx > 890:
        if not any(a<=cx<=b and c<=cy<=d for a,b,c,d in white): continue
    keep |= lab == (i+1)
keep = ndi.binary_fill_holes(ndi.binary_closing(keep, iterations=3))
# explicit shapes: QR panel + URL pill
m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
d.rounded_rectangle((306, 973, 718, 1358), radius=36, fill=255)
d.rounded_rectangle((135, 1370, 890, 1466), radius=48, fill=255)
keep |= np.asarray(m) > 0
keep = ndi.binary_dilation(keep, iterations=2)
a = ndi.gaussian_filter(keep.astype(float), 0.8)
Image.fromarray(np.dstack([im, a*255]).astype(np.uint8)).save(out)
prev = (im*a[...,None] + 128*(1-a[...,None])).astype(np.uint8)
Image.fromarray(prev).save(out.replace('.png', '_preview.png'))
