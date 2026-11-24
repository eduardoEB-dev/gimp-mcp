"""Remove the white sticker halo around the logo (outside + inside the P counter).
White/near-transparent px connected to the transparent background -> transparent."""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

src, dst = sys.argv[1], sys.argv[2]
a = np.array(Image.open(src).convert("RGBA"))
rgb = a[..., :3].astype(int)
whiteish = (rgb.min(axis=2) > 150) | (a[..., 3] < 128)
lab, _ = ndimage.label(whiteish)
bg_ids = np.unique(lab[a[..., 3] == 0])
halo = np.isin(lab, bg_ids[bg_ids > 0])
a[halo] = 0
Image.fromarray(a).save(dst)
print(f"cleared {halo.sum()} px -> {dst}")
