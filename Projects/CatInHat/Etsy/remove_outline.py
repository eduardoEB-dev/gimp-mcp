"""Remove a thin dark cartoon outline the AI drew around the product: thin lines much darker than their surroundings -> inpaint.
usage: <python with numpy, opencv> remove_outline.py <in.jpg> <out.jpg> <x0,y0,x1,y1> [--keep x0,y0,x1,y1 ...] [--thr 40] [--vmax 150]
--keep boxes are never touched (e.g. the logo card)."""
import sys, numpy as np, cv2
a = sys.argv[1:]; src, dst, box = a[0], a[1], [int(v) for v in a[2].split(",")]
keep, thr, vmax, i = [], 40, 150, 3
while i < len(a):
    if a[i] == "--keep": keep.append([int(v) for v in a[i + 1].split(",")])
    elif a[i] == "--thr": thr = int(a[i + 1])
    elif a[i] == "--vmax": vmax = int(a[i + 1])
    i += 2
im = cv2.imread(src); x0, y0, x1, y1 = box
v = im.max(axis=2)                                                           # brightness: red, white and sky all have a bright channel
bh = cv2.morphologyEx(v, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))  # thin dark lines
line = ((bh > thr) & (v < vmax)).astype(np.uint8) * 255
line = cv2.morphologyEx(line, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))  # drop single-pixel texture noise
m = np.zeros_like(line); m[y0:y1, x0:x1] = line[y0:y1, x0:x1]
for kx0, ky0, kx1, ky1 in keep: m[ky0:ky1, kx0:kx1] = 0
m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=2)                 # include the anti-aliased fringe
for kx0, ky0, kx1, ky1 in keep: m[ky0:ky1, kx0:kx1] = 0
out = cv2.inpaint(im, m, 4, cv2.INPAINT_TELEA)
cv2.imwrite(dst, out, [cv2.IMWRITE_JPEG_QUALITY, 93]); cv2.imwrite(dst.rsplit(".", 1)[0] + "_mask.png", m)
print("masked px:", int((m > 0).sum()))
