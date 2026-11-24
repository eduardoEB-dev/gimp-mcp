import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
src, outdir = sys.argv[1], sys.argv[2]
im = np.asarray(Image.open(src).convert('RGBA')).astype(float)
rgb, a = im[..., :3], im[..., 3]
mx, mn = rgb.max(2), rgb.min(2)
sat = (mx - mn) / np.maximum(mx, 1)
solid = a > 128
white = solid & (mx > 170) & (sat < 0.25)
black = solid & (mx < 70) & ~white
neon = solid & ~white & ~black
# clean specks: majority-ish smoothing per class
lab = np.zeros(a.shape, np.uint8); lab[white]=1; lab[black]=2; lab[neon]=3
raw = lab.copy()
for _ in range(1):
    votes = np.stack([ndi.uniform_filter((lab==k).astype(float), 3) for k in (1,2,3)])
    lab = np.where(solid, votes.argmax(0)+1, 0).astype(np.uint8)
for k in (1,2,3):  # merge tiny islands into neighbor
    m = lab==k; l, n = ndi.label(m); s = ndi.sum(m, l, range(1,n+1))
    small = np.isin(l, np.where(s < 8)[0]+1)
    if small.any():
        nb = ndi.grey_dilation(np.where(small, 0, lab), size=3)
        lab[small] = nb[small]
# QR: crisp threshold, no smoothing
qy0,qy1,qx0,qx1 = 990,1342,322,702
q = rgb[qy0:qy1,qx0:qx1].mean(2)
lab[qy0:qy1,qx0:qx1] = np.where(q > 128, 1, 2)
pal = {1:(255,255,255), 2:(0,0,0), 3:(170,60,255)}
out = np.zeros((*a.shape, 4), np.uint8)
for k, c in pal.items(): out[lab==k] = (*c, 255)
Image.fromarray(out).save(f'{outdir}/poster_3color.png')
for k, name in [(1,'white'),(2,'black'),(3,'neoncity')]:
    o = np.zeros_like(out); o[lab==k] = (*pal[k], 255)
    Image.fromarray(o).save(f'{outdir}/poster_3color_{name}.png')
prev = out.copy(); prev[lab==0] = (128,128,128,255)
Image.fromarray(prev).save(f'{outdir}/poster_3color_preview.png')
print({n:int((lab==k).sum()) for k,n in [(1,'white'),(2,'black'),(3,'neon')]})
