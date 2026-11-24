# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy", "opencv-python-headless"]
# ///
"""Create one image per US region: that region keeps its color, others turn light grey.

Output images are identical in size to the source, so they overlay perfectly.
Labels and white state borders are left untouched; the black background
(including Lake Michigan and the gaps between regions) becomes transparent.
Also writes a transparent copy of the full-color map as US_RegionsMain.png.

Run: uv run RegionMap/Scrips/make_region_maps.py
"""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "Source" / "US_RegionsMain.png"  # untouched original
OUT_DIR = HERE.parent / "Regions Example"

GREY = np.array([200, 200, 200], dtype=float)

# name: (base RGB sampled from the map, hue ranges in degrees)
REGIONS = {
    "West":      ((41, 183, 157), [(150, 195)]),
    "Midwest":   ((45, 208, 68),  [(100, 150)]),
    "Northeast": ((60, 96, 189),  [(200, 245)]),
    "Southwest": ((226, 61, 49),  [(0, 18), (355, 360)]),
    "Southeast": ((184, 164, 71), [(30, 70)]),
}


def hue_and_chroma(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    safe = np.where(d > 0, d, 1)
    h = np.where(mx == r, ((g - b) / safe) % 6,
        np.where(mx == g, (b - r) / safe + 2, (r - g) / safe + 4)) * 60
    return h, d


def background_alpha(rgb):
    """Alpha channel that makes the black background transparent with soft edges."""
    value = rgb.max(-1)
    # All near-black is background: outside, gaps, and enclosed water (Chesapeake, specks).
    bg = value < 30
    # Edge pixels are blends of land and black: alpha = brightness relative to
    # the nearby solid land color.
    kernel = np.ones((7, 7), np.uint8)
    ref = cv2.dilate(np.where(bg, 0, value).astype(np.float32), kernel)
    edge = cv2.dilate(bg.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    alpha = np.ones(value.shape)
    alpha[edge] = np.clip((value[edge] - 8) / np.maximum(ref[edge] - 8, 1), 0, 1)
    alpha[bg & (value < 30) & (alpha < 0.5)] = 0
    # Drop isolated specks of noise floating in the background.
    n, labels, stats, _ = cv2.connectedComponentsWithStats((alpha > 0).astype(np.uint8))
    alpha[np.isin(labels, np.nonzero(stats[:, cv2.CC_STAT_AREA] < 15)[0])] = 0
    return alpha


def save_rgba(path, rgb, alpha):
    # Un-mix the black from edge pixels so they don't leave a dark halo.
    # Fully transparent pixels store white, so tools that ignore alpha show white, not black.
    color = np.where(alpha[..., None] > 0, rgb / np.maximum(alpha[..., None], 1e-6), 255)
    rgba = np.dstack([np.clip(color, 0, 255), alpha * 255]).round().astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(path)
    print(f"wrote {path}")


def main():
    rgb = np.array(Image.open(SRC).convert("RGB")).astype(float)
    hue, chroma = hue_and_chroma(rgb)
    colored = chroma > 8  # ignore near-grey pixels (borders, background)
    alpha = background_alpha(rgb)
    save_rgba(OUT_DIR / "US_RegionsMain.png", rgb, alpha)

    masks = {}
    for name, (_, ranges) in REGIONS.items():
        m = np.zeros(hue.shape, bool)
        for lo, hi in ranges:
            m |= (hue >= lo) & (hue < hi)
        masks[name] = m & colored

    for keep in REGIONS:
        out = rgb.copy()
        for name, (base, _) in REGIONS.items():
            if name == keep:
                continue
            m = masks[name]
            base = np.array(base, dtype=float)
            # Treat each pixel as a mix of the region color and grey/white/black
            # (anti-aliased edges). Swap only the colored share for GREY.
            share = np.clip(chroma[m] / (base.max() - base.min()), 0, 1)[:, None]
            out[m] = share * GREY + (rgb[m] - share * base)
        save_rgba(OUT_DIR / f"US_{keep}.png", out, alpha)


if __name__ == "__main__":
    main()
