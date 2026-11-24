"""Flatten a keychain mockup photo into a clean flat graphic for Bambu image-to-keychain.

Usage: python flatten_keychain.py <input.png> <out_dir> [outline_px]
Output: exactly 3 colors (navy, light blue, white), smooth edges, full navy outline.
"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

src, out_dir = sys.argv[1], sys.argv[2]
outline_px = int(sys.argv[3]) if len(sys.argv) > 3 else 45  # output px; ~0.8mm at 60mm wide
SCALE = 4
NAVY, LIGHT, WHITE = 0, 1, 2
PALETTE = np.array([[3, 54, 116], [38, 126, 193], [255, 255, 255]], np.uint8)
name = os.path.splitext(os.path.basename(src))[0]

im = Image.open(src).convert("RGB")
rgb = np.asarray(im).astype(np.float32) / 255
hsv = np.asarray(im.convert("HSV")).astype(np.float32) / 255
h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]

# Saturated blue = printed design (acrylic/marble/metal are low-sat)
blue = (h > 0.52) & (h < 0.75) & (s > 0.45) & (v > 0.25)
blue = ndi.binary_opening(blue, iterations=1)

# Bright bluish-white touching blue = stars/text (marble is darker + warmer)
white = (rgb.min(-1) > 0.90) & (rgb[..., 2] >= rgb[..., 0])
wl, _ = ndi.label(white)
touch = np.unique(wl[ndi.binary_dilation(blue, iterations=3) & white])
white = np.isin(wl, touch[touch > 0])

def largest(m):
    lab, n = ndi.label(m)
    return lab == (np.argmax(ndi.sum(m, lab, range(1, n + 1))) + 1)

mask = ndi.binary_fill_holes(ndi.binary_closing(blue | white, np.ones((3, 3)), iterations=4))
mask = ndi.binary_fill_holes(largest(mask))

# Classify each pixel to fixed palette by nearest color
pal = PALETTE.astype(np.float32) / 255
d = ((rgb[..., None, :] - pal[None, None]) ** 2).sum(-1)
d[..., WHITE] *= 0.6  # bias shaded white toward white
lbl = np.argmin(d, -1)

# Drop acrylic bevel: light-blue pixels in outer band
band = mask & ~ndi.binary_erosion(mask, iterations=10)
mask &= ~(band & (lbl == LIGHT))
mask = ndi.binary_fill_holes(largest(ndi.binary_opening(mask, iterations=2)))

# Smooth upscale: blur per-class soft masks, argmax
def soft(m, sigma):
    return ndi.gaussian_filter(ndi.zoom(m.astype(np.float32), SCALE, order=1), sigma)

sig = SCALE * 0.9
votes = np.stack([soft((lbl == k) & mask, sig) for k in range(3)])
mask_up = soft(mask, sig) > 0.5
lbl_up = np.argmax(votes, 0)

# Light blue only as interior accent: never near the outer rim
dist_in = ndi.distance_transform_edt(mask_up)
lbl_up[(lbl_up == LIGHT) & (dist_in < 12 * SCALE)] = NAVY

# Merge tiny islands of each color into surroundings
min_area = {NAVY: (5 * SCALE) ** 2, LIGHT: (12 * SCALE) ** 2, WHITE: (5 * SCALE) ** 2}
for _ in range(2):
    for k in range(3):
        lab, n = ndi.label((lbl_up == k) & mask_up)
        if not n:
            continue
        areas = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
        small = np.isin(lab, np.where(areas < min_area[k])[0] + 1)
        if small.any():
            idx = ndi.distance_transform_edt(small, return_distances=False, return_indices=True)
            lbl_up = np.where(small, lbl_up[idx[0], idx[1]], lbl_up)

# Replace white stars with clean geometric stars (fit center/radius/rotation)
def fit_star(comp):
    ys, xs = np.nonzero(comp)
    cy, cx = ys.mean(), xs.mean()
    edge = comp & ~ndi.binary_erosion(comp)
    ey, ex = np.nonzero(edge)
    ang = np.arctan2(ey - cy, ex - cx)
    r = np.hypot(ey - cy, ex - cx)
    bins = ((ang + np.pi) / (2 * np.pi) * 360).astype(int) % 360
    prof = np.zeros(360)
    np.maximum.at(prof, bins, r)
    empty = prof == 0
    if empty.sum() > 25:  # not star-shaped around centroid
        return None
    if empty.any():  # fill gaps in edge sampling (circular interp)
        idx = np.arange(360)
        prof[empty] = np.interp(idx[empty], idx[~empty], prof[~empty], period=360)
    f = np.fft.rfft(prof) / 360
    if abs(f[5]) / abs(f[0]) < 0.12:  # not 5-fold symmetric
        return None
    theta = np.deg2rad(np.arange(360)) - np.pi
    smooth = np.fft.irfft(np.where(np.arange(len(f)) % 5 == 0, f, 0) * 360, 360)
    phase = -np.angle(f[5]) / 5  # angle of first peak (in bin space)
    peaks = [phase + k * 2 * np.pi / 5 for k in range(5)]
    r_out = np.percentile(prof, 97)
    r_in = np.percentile(smooth, 3)
    return cx, cy, r_out, r_in, peaks[0] - np.pi

def star_poly(cx, cy, r_out, r_in, a0):
    pts = []
    for i in range(10):
        a = a0 + i * np.pi / 5
        rr = r_out if i % 2 == 0 else r_in
        pts.append((cx + rr * np.cos(a), cy + rr * np.sin(a)))
    return pts

def offset_poly(pts, w):
    """Mitered outward offset of a simple polygon (keeps sharp star points)."""
    P = np.asarray(pts, float)
    area = 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
    sgn = 1 if area > 0 else -1
    E = np.roll(P, -1, 0) - P
    N = sgn * np.stack([E[:, 1], -E[:, 0]], 1) / np.linalg.norm(E, axis=1)[:, None]
    out = []
    for i in range(len(P)):
        a1, d1 = P[i - 1] + w * N[i - 1], E[i - 1]
        a2, d2 = P[i] + w * N[i], E[i]
        t = np.linalg.solve(np.stack([d1, -d2], 1), a2 - a1)[0]
        out.append(tuple(a1 + t * d1))
    return out

def poly_mask(polys):
    im_ = Image.new("L", lbl_up.shape[::-1], 0)
    dr = ImageDraw.Draw(im_)
    for pts in polys:
        dr.polygon(pts, fill=255)
    return np.asarray(im_) > 127

from PIL import ImageDraw
lab, n = ndi.label((lbl_up == WHITE) & mask_up)
areas = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
star_polys = []
for i, sl in enumerate(ndi.find_objects(lab)):
    if areas[i] < (25 * SCALE) ** 2:
        continue
    hgt, wid = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
    if not 0.7 < hgt / wid < 1.4:
        continue
    pad_sl = (slice(max(sl[0].start - 2, 0), sl[0].stop + 2), slice(max(sl[1].start - 2, 0), sl[1].stop + 2))
    fit = fit_star(lab[pad_sl] == i + 1)
    if fit is None:
        continue
    cx, cy, r_out, r_in, a0 = fit
    lbl_up[lab == i + 1] = NAVY
    star_polys.append(star_poly(cx + pad_sl[1].start, cy + pad_sl[0].start, r_out, r_in, a0))
stars = poly_mask(star_polys)
lbl_up[stars] = WHITE
mask_up |= stars
lbl_up = np.where(mask_up, lbl_up, NAVY)
print("stars replaced:", len(star_polys))

def save(final, colors, suffix, preview_bg):
    out = np.zeros((*final.shape, 4), np.uint8)
    out[final, :3] = colors[final]
    out[final, 3] = 255
    img = Image.fromarray(out, "RGBA")
    bbox = img.getbbox()
    pad = 40
    img = img.crop((bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad))
    os.makedirs(out_dir, exist_ok=True)
    img.save(os.path.join(out_dir, f"{name}_{suffix}_transparent.png"))
    bg = Image.new("RGBA", img.size, preview_bg)
    bg.alpha_composite(img)
    bg.convert("RGB").save(os.path.join(out_dir, f"{name}_{suffix}_preview.png"))
    print(suffix, "colors:", len(np.unique(out[final, :3].reshape(-1, 3), axis=0)), "size:", img.size)

def opening(m, r):
    return ndi.distance_transform_edt(~(ndi.distance_transform_edt(m) > r)) <= r

# A) thick navy outline around everything
final = ndi.binary_fill_holes(ndi.distance_transform_edt(~mask_up) <= outline_px)
save(final, PALETTE[lbl_up], "navyborder", (255, 255, 255, 255))

# B) crisp navy outline per star + white border where clear acrylic was
star_w = 9 * SCALE       # navy outline around each star
white_w = 16 * SCALE     # white border width
star_out = poly_mask([offset_poly(p, star_w) for p in star_polys])
near_star = ndi.distance_transform_edt(~star_out) < 14 * SCALE
body = opening(mask_up, 22 * SCALE)
navy = body | star_out | (mask_up & ~near_star)
navy = ndi.binary_fill_holes(largest(ndi.binary_closing(navy, iterations=2 * SCALE)))  # largest drops keyring loop
navy |= ndi.distance_transform_edt(~navy) <= 3 * SCALE  # thin even navy rim
rest = opening(navy & ~star_out, 6 * SCALE)  # strip ragged bits, keep star points crisp
rest = ndi.gaussian_filter(rest.astype(np.float32), 3 * SCALE) > 0.5
navy = ndi.binary_fill_holes(rest | star_out)
# every white letter/shape keeps a navy margin before the white border
navy |= ndi.distance_transform_edt(~(mask_up & (lbl_up == WHITE) & ~stars)) <= 13 * SCALE
navy = ndi.binary_fill_holes(navy)
cols = PALETTE[lbl_up].copy()
cols[~mask_up | ~navy] = PALETTE[NAVY]
final = ndi.binary_fill_holes(ndi.distance_transform_edt(~navy) <= white_w)
cols[final & ~navy] = PALETTE[WHITE]
save(final, cols, "whiteborder", (200, 200, 200, 255))
