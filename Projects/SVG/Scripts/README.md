# SVG scripts

Turn reference images into SVGs that import cleanly into **Blender** (extrude / boolean cut on 3D models).

## Folders

- `Projects/SVG/Images/`: source images
- `Projects/SVG/SVGs Drafts/`: all output SVGs (`Name_v1.svg`, `Name_v2.svg`, ...)
- `Projects/SVG/Scripts/`: all scripts (keep new ones here too)

## Setup

```
pip install vtracer skia-pathops pillow numpy
```

## Two approaches

**1. Trace**: for images that are big and clean (crisp line art, high-res cut paper).

| Script | Use |
|---|---|
| `trace_lineart.py` | Black-on-light line art → single-color SVG, light areas transparent. `python trace_lineart.py in.png out.svg [--color #000] [--scale 5] [--thresh 128]` |
| `papel2_trace.py` | Colored cut-paper banner → SVG; outer scalloped edges replaced by a straight rectangle, only enclosed holes kept. Thresholds on red (R−G); adapt for other colors. |

| `Snoopy/snoopy_layers.py` | Multi-color **Bambu Studio** layers (Red/White/Green/Yellow/Black), one SVG per color on a shared canvas, background (sky/snow/tree/doghouse) dropped. `python Snoopy/snoopy_layers.py in.png out_dir [--mm 70] [--no-yellow] [--debug dbg.png]`. Based on `grinch_layers.py`. |
| `Snoopy/MerryChristmas/peanuts_text_svg.py` | Text in the PEANUTS logo lettering (`PeanutsFont.png`) → Bambu layers White letters + Red outline. P E A N U T S cut from logo; I H M R C Y assembled from their strokes (others not supported yet). `python Snoopy/MerryChristmas/peanuts_text_svg.py PeanutsFont.png out_dir [--lines "MERRY\|CHRISTMAS"] [--mm 90] [--outline 13] [--gap 16]` |

How they work: threshold → supersample 3× + light blur (smooth edges) → `vtracer` binary spline trace → recolor.

**2. Rebuild from geometry**: for small, blurry, or watermarked sources, or when the result must be very smooth or simplified. Measure the shape from a zoomed crop, then build it from Bézier curves.

| Script | Use |
|---|---|
| `flower_svg.py` | Radial flower: center dot + N petals. Writes shapes and cut-out-disc versions. |
| `fern_svg.py` | Arched fern: tapered stem + alternating leaves. Flags: `--pairs --leaf-scale --leaf-width --neck --tip --color --height` |
| `tulip_svg.py` | Tulip: stem, 2 base leaves, 2 stem leaves, solid 3-point head. Constants at top of file: `BASE_LEAVES`, `STEM_LEAVES`, `HEAD_SCALE`, `NECK` |
| `papel1_svg.py` | Early hand-built banner (superseded by tracing). |

## Blender rules (learned the hard way)

1. **Merge everything into ONE outline.** Overlapping separate shapes give stair-step seams when extruded or boolean-cut. Use `skia-pathops`: `simplify(fix_winding=True)` **each shape first** (otherwise an opposite-winding shape becomes a hole), then `pathops.op(a, b, PathOp.UNION)`. See `tulip_svg.py`.
2. **No hairline joints.** Leaves meet the stem with a wide base ("neck"), never a point.
3. **No nubs at joints.** Start the leaf slightly behind the stem centerline, then intersect it with the half-plane on the leaf's side of the stem (`half_plane()` in `tulip_svg.py`, clip in `fern_svg.py`).
4. **Rounded tips** (not needle points): end each leaf with a vertical-tangent cap.
5. **Leave gaps** between leaves (about one leaf-width). Leaves on the inner side of a curve crowd together, so angle them out more or shorten them.
6. **Keep leaves straight and symmetric.** A curved leaf centerline makes leaves look lopsided.
7. Smooth curves: Catmull-Rom → cubic Béziers (`catmull()`), with denser sampling near tips.
8. In Blender, raise the curve's **Resolution Preview U** (24–32) before converting to a mesh.

## Previewing

- `svg_preview.py in.svg out.png [--height 900] [--outline]`: PIL renderer, no browser needed. Handles absolute M/L/C/Q/Z. `--outline` dots the curve points.
- Headless Edge also works but often fails silently. Retry with a fresh `--user-data-dir`.

## User preferences

- Size about 5× the source, or ~2000px tall for rebuilt shapes.
- Iterate on the same version file when asked; only bump `_vN` for a new direction.
- Default color: papel red `#D2232A` (blue banner `#077DAD`).
