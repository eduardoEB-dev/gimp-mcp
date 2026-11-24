"""Shared helpers for the SVG Creation workflow: color names/distance, vtracer tracing and writing a per-color layer set.

A "layer set" = one SVG per color (<Name>_<Color>.svg), all with the same
width/height/viewBox so they line up in Bambu Studio, plus
<Name>_AllColors_preview.svg (view only, never print) and layers.json.
"""
import json
import os
import re
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


MAX_COLORS = 5   # user's AMS slots; more layers -> warn and suggest merges

# basic names for auto-detected colors (layer/file names only; Bambu ignores
# SVG colors, the user assigns a filament per part)
NAMED = {"White": "#FFFFFF", "Black": "#111111", "Grey": "#8C8C8C", "Red": "#D2232A", "DarkRed": "#8B1A1A",
         "Orange": "#F28C28", "Yellow": "#F5E11E", "Green": "#9FC52A", "DarkGreen": "#2E6B30",
         "Blue": "#2D5BD0", "Teal": "#077DAD", "LightBlue": "#7EC3EA", "Navy": "#1C2E5A", "Purple": "#6F3FA0",
         "Pink": "#F29BC0", "Brown": "#7A4B2A", "Tan": "#D8B98A", "Skin": "#F5C9A6"}


def hex2rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def rgb2hex(c):
    return "#%02X%02X%02X" % tuple(int(round(v)) for v in c)


def rgb2lab(rgb):
    """sRGB 0..255 (..., 3) -> CIELAB; good enough for nearest-color picks"""
    c = np.asarray(rgb, float) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192], [0.1805, 0.0722, 0.9505]])
    xyz /= np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def name_of(rgb):
    lab = rgb2lab(rgb)
    return min(NAMED, key=lambda n: np.linalg.norm(lab - rgb2lab(hex2rgb(NAMED[n]))))


def parse_colors(s):
    """'Red=#D2232A,White,Green' -> [{'name','hex'}] (bare names use NAMED)"""
    out = []
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        n, _, h = part.partition("=")
        n = n.strip()
        if not h:
            key = {k.lower(): k for k in NAMED}.get(n.lower())
            if not key:
                raise SystemExit(f"no default hex for '{n}', give it as {n}=#RRGGBB")
            h = NAMED[key]
        out.append({"name": n, "hex": "#" + h.strip().lstrip("#").upper()})
    return out


def nearest(rgb, colors):
    """index of the closest color dict to rgb, and its Lab distance"""
    lab = rgb2lab(rgb)
    d = [np.linalg.norm(lab - rgb2lab(hex2rgb(c["hex"]))) for c in colors]
    return int(np.argmin(d)), min(d)


# --- tracing -------------------------------------------------------------
def bake(p):
    """vtracer <path d=.. transform=translate(..)> -> absolute d string"""
    t = re.search(r'translate\(([-\d.]+),([-\d.]+)\)', p)
    dx, dy = (float(t.group(1)), float(t.group(2))) if t else (0, 0)
    d = re.search(r'\sd="([^"]+)"', p).group(1)
    out, i = [], 0
    for tok in re.findall(r"[A-Za-z]|-?\d*\.?\d+(?:e-?\d+)?", d):
        if tok.isalpha():
            out.append(tok); i = 0
        else:
            out.append(f"{float(tok) + (dx if i % 2 == 0 else dy):.1f}"); i += 1
    return " ".join(out)


def trace_mask(mask, speckle=16, corner=80, length=6.0):
    """bool mask -> list of absolute path d strings (smooth splines)"""
    import vtracer
    from PIL import Image
    tmp = tempfile.mkdtemp()
    mp, sp = os.path.join(tmp, "m.png"), os.path.join(tmp, "m.svg")
    Image.fromarray(np.where(mask, 0, 255).astype(np.uint8)).convert("RGB").save(mp)
    vtracer.convert_image_to_svg_py(mp, sp, colormode="binary", mode="spline",
                                    filter_speckle=speckle, corner_threshold=corner,
                                    length_threshold=length, splice_threshold=45, path_precision=1)
    return [bake(p) for p in re.findall(r"<path[^>]*/>", open(sp, encoding="utf-8").read())]


# --- output --------------------------------------------------------------
def write_layer_set(out_dir, name, viewbox, size_mm, layers, title=None, source=None):
    """layers = [(color_dict, [d strings])] in paint order (bottom first).
    viewbox = (x, y, w, h); size_mm = (w_mm, h_mm)."""
    os.makedirs(out_dir, exist_ok=True)
    vb = " ".join(f"{v:g}" for v in viewbox)
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size_mm[0]:.2f}mm" '
            f'height="{size_mm[1]:.2f}mm" viewBox="{vb}">\n')
    groups, manifest = [], []
    for f, paths in layers:
        if not paths:
            continue
        grp = (f'  <g id="{f["name"]}" fill="{f["hex"]}" fill-rule="evenodd">\n'
               + "".join(f'    <path d="{d}"/>\n' for d in paths) + "  </g>\n")
        groups.append(grp)
        fn = f"{name}_{f['name']}.svg"
        # no full-canvas rect (Bambu would print it); alignment relies on
        # identical width/height/viewBox in every file
        open(os.path.join(out_dir, fn), "w", encoding="utf-8").write(
            head + f"  <title>{title or name} {f['name']}</title>\n" + grp + "</svg>\n")
        manifest.append({"file": fn, "color": f["name"], "hex": f["hex"], "paths": len(paths)})
        print(f"{f['name']:>8}: {len(paths):4d} paths -> {os.path.join(out_dir, fn)}")
    open(os.path.join(out_dir, f"{name}_AllColors_preview.svg"), "w", encoding="utf-8").write(
        head + f"  <title>{title or name}</title>\n" + "".join(groups) + "</svg>\n")
    json.dump({"name": name, "source": source, "viewBox": list(viewbox),
               "size_mm": [round(size_mm[0], 2), round(size_mm[1], 2)], "layers": manifest},
              open(os.path.join(out_dir, "layers.json"), "w", encoding="utf-8"), indent=2)
    print(f"size {size_mm[0]:.1f} x {size_mm[1]:.1f} mm, {len(manifest)} colors -> {out_dir}")
    return manifest
