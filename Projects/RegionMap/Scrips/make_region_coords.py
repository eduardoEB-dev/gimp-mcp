# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy", "opencv-python-headless"]
# ///
"""Write one polygon per region (HTML image-map style "x1,y1,x2,y2,...")
to RegionMap/Coordinates/Coordinates.txt, in pixels of US_RegionsMain.png.

Run: uv run RegionMap/Scrips/make_region_coords.py
"""

import cv2
import numpy as np
from PIL import Image

from make_region_maps import HERE, REGIONS, SRC, hue_and_chroma

OUT = HERE.parent / "Coordinates" / "Coordinates.txt"
CLOSE_PX = 15     # bridges white borders, label gaps and small water gaps
TOLERANCE = 2.0   # max distance (px) of simplified outline from the true edge


def region_polygon(mask, labels):
    m = mask.astype(np.uint8) * 255
    # Labels sit on top of regions (e.g. "Northeast" splits New England off), so
    # count label pixels inside the region's convex hull as part of the region.
    # Hull of the substantial pieces only; stray specks elsewhere would inflate it.
    pieces, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    big = np.vstack([p for p in pieces if cv2.contourArea(p) > 2000])
    hull = np.zeros_like(m)
    cv2.fillPoly(hull, [cv2.convexHull(big)], 255)
    m[(labels > 0) & (hull > 0)] = 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (CLOSE_PX, CLOSE_PX))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    main = contours[0]
    dropped = [cv2.contourArea(c) for c in contours[1:] if cv2.contourArea(c) > 50]
    poly = cv2.approxPolyDP(main, TOLERANCE, True).reshape(-1, 2)
    return poly, dropped


def main():
    rgb = np.array(Image.open(SRC).convert("RGB")).astype(float)
    hue, chroma = hue_and_chroma(rgb)
    colored = chroma > 8
    # Pink label text, grown to cover its white outline and dark shadow.
    text = ((hue >= 300) & (hue < 355) & (chroma > 40)).astype(np.uint8) * 255
    labels = cv2.dilate(text, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    lines = []
    for name, (_, ranges) in REGIONS.items():
        m = np.zeros(hue.shape, bool)
        for lo, hi in ranges:
            m |= (hue >= lo) & (hue < hi)
        poly, dropped = region_polygon(m & colored, labels)
        coords = ",".join(f"{x},{y}" for x, y in poly)
        lines += [f"US_{name}:", f"Coordinates: {coords}", ""]
        print(f"US_{name}: {len(poly)} points" + (f", dropped pieces (px area): {dropped}" if dropped else ""))
    OUT.write_text("\n".join(lines).rstrip() + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
