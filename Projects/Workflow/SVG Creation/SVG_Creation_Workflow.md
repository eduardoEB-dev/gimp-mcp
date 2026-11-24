# TryCatch Designs: SVG Creation Workflow (multi-color 3D prints)

**For Claude:** the user will give you this file (or its folder), a **project folder path**, and an image or SVG plus what they want. Turn it into **one SVG per color** that lines up in Bambu Studio, so each color can be embedded in a 3D model as its own part. Do every step below without being asked. Stop and ask only where a step says **ASK**.

## Rule: flat basics only (always)

Layer sets are for **3D printing**, so every color region must be a flat, basic shape. Drop all **shading, highlights and accents**: each part gets its one base color.
- Highlight on a shape (white/light streak on the nose, shine on a tongue) -> base color of that shape.
- Shading/shadow (darker band under the chin, on the neck, inside ears, hat folds) -> base color of that area.
- Gradient tones inside a shape (nostrils, mouth interior shading) -> that shape's single color.
- Keep real design features: outline, eyes + eye highlights, teeth, paw pads, nose as one solid shape.

How: always run `image_to_layers.py` with `--flat <R>` (removes accents narrower than 2R source px, refills from neighbors; ~6-8 for a 1200 px image) and `--flat-skip "<outline color>"` so outlines survive. Map shading tones to the base color with `--map` (sample them from the source). Raise `--island` (~300-500) to drop leftover specks. In step 5, look at `_check.png` side by side with the source and list any shading still left.

## Tools

Everything is in `D:\gimp-mcp\Projects\Workflow\SVG Creation\`. Run the tools with `python` (3.11; needs `vtracer skia-pathops pillow numpy scipy`).

| Tool | Use |
|---|---|
| `new_project.py` | Creates the project folders, copies sources into `Images/`, finds the next draft version, copies an approved draft to `Final/` |
| `image_to_layers.py` | Image (PNG/JPG) → one SVG per color. Removes the background, smooths the edges, and makes the colors tile with no gaps or overlaps |
| `svg_to_layers.py` | Existing SVG → one SVG per color, keeping the exact curves. Shapes on top cut away what's under them; strokes become filled shapes |
| `check_layers.py` | Renders a layer set and reports parts too thin to print, tiny islands, overlaps and slivers. Writes `_check.png` |
| `layers_common.py` | Shared code: color names, tracing, writing the layer set. `MAX_COLORS = 5` (the user's AMS limit) |
| `examples/` | `lettering_from_logo_peanuts.py` (font copied from a logo image), `hand_tuned_layers_snoopy.py` (the original Snoopy script) |

## Project folder (created automatically)

The user gives a path, for example `D:\gimp-mcp\Projects\SVG\Snoopy`. Step 1 creates:

```
<project>\
  Images\    sources (copied in)
  Scripts\   scripts written only for this project (tweaks, lettering)
  Drafts\    <Name>_v1\, <Name>_v2\ ... each one is a layer set
  Final\     <Name>\  the approved layer set, ready for Bambu
  PROJECT.md goal, colors, size, version log
```

A **layer set** is a folder holding:
- `<Name>_<Color>.svg`, one file per color. These are the files to print.
- `<Name>_AllColors_preview.svg`, for viewing only. **Never print it.**
- `layers.json`, listing the colors, size and source.
- `_check.png`, the composite render from `check_layers.py`.

Every SVG in a set has the same width, height and viewBox, so the layers line up when they're placed at the same position. There is **no** full-canvas background rectangle, because Bambu would print it.

## Steps

1. **Set up the project.**
   `python new_project.py "<project>" "<source file>"`
   Then fill in the Goal section of `PROJECT.md`: what it's for (cup wrap, keychain, sign...), size, colors, and what to keep or drop.

2. **Look at the source.** Read the image or SVG yourself. Work out:
   - **What to keep.** Usually just the subject (the character, the text) with no sky, ground, props or watermark. **ASK** if it isn't obvious whether something belongs to the subject (for example a gift held in the character's lap belongs; a doghouse in the background doesn't).
   - **Colors.** If the user names colors, use exactly those. Otherwise propose the colors you see and say so. More than 5 colors → **ASK** which ones to merge (e.g. yellow eyes → white).
   - **Size in mm.** Use the user's size. If none, use 70 mm tall and say so.

3. **Build the layers.** Get the output folder from `python new_project.py "<project>" --next <Name>`.

   **From an image:**
   ```
   python image_to_layers.py in.png --suggest            # lists the image's colors, stops
   python image_to_layers.py in.png "<Drafts\Name_v1>" --name Name --colors "Red,White,Green,Yellow,Black" --height-mm 70 --debug "<Drafts\Name_v1>\_labels.png"
   ```
   `--colors` takes plain names (default shades) or `Name=#RRGGBB`. Without it, colors are detected automatically, but that often splits edge blends into extra colors and misses small details like eyes, so prefer `--colors`. Open `_labels.png` and check that every region got the right color before trusting the trace.

   **From an SVG:**
   ```
   python svg_to_layers.py in.svg --suggest              # lists the fill colors, stops
   python svg_to_layers.py in.svg "<Drafts\Name_v1>" --name Name [--colors "..."] [--drop-bg] [--width-mm 90]
   ```
   Text elements are skipped. They must be converted to paths first (Inkscape: Path > Object to Path).

4. **Check.** Run `python check_layers.py "<Drafts\Name_v1>"`, then **look at `_check.png`** (magenta = slivers). Fix whatever it flags (see the table below) and run it again. The report's "holes" are usually intended, like letter counters. Mention them but don't "fix" them.

5. **Show the user.** Give the folder path, list the colors, size and checker summary, and describe what you see in `_check.png`.

6. **Iterate.** When the user asks for a tweak, **overwrite the same `_vN`**. Only make a new `_vN` for a new direction (different colors, a different crop or style). Add a row to `PROJECT.md` → Versions for each run, with the exact command.

7. **Finalize** when the user approves: `python new_project.py "<project>" --finalize Drafts\<Name>_vN`. This copies the set to `Final\<Name>\`; an earlier final is kept as `_old_<timestamp>`. Note it in `PROJECT.md` → Final.

8. **Report back.** Final path, files (one per color), size in mm, and anything the checker flagged that was left as is.

## Fixing problems (image input)

| Problem | Fix |
|---|---|
| Background, sky or ground lines left in | `--bg outline` (default: the subject has a dark outline). Raise `--open` (5 → 8) to cut thicker lines off the subject |
| Subject has no outline | `--bg color` (removes the colors touching the border; tune `--bg-tol`). `--bg alpha` for transparent PNGs. `--bg none` keeps everything |
| A prop touching the subject should go | `--erase "x0,y0,x1,y1;..."` (source pixels), or `--box` to keep only one area |
| Background trapped inside the subject (e.g. gap between hat pompom and brim) stays filled white | `--cut-hole "x,y"` (source px seed inside the gap). Near-white px connected to it become transparent. `--erase` can't do this: hole filling refills enclosed areas |
| Lettering on white: letter counters (inside e, a, loops) filled with a color | `--cut-white 30` cuts every enclosed near-white region ≥ N source px |
| Several separate pieces wanted (e.g. a word plus a character) | `--keep all --min-blob 400` |
| A color grabs the wrong pixels | Add a hint: `--map "#B0D122=Green"` (image color → layer), or lower `--sigma` |
| Lines too thin to print (checker: thin > 3%) | Print bigger, or `--grow "Black=1.5"` |
| Specks / tiny islands | Raise `--island` (default 6 source px) |
| Jagged edges | Raise `--blur` (0.8 → 1.2). Lower it if small details melt away |
| Shading / highlights / accents left in | `--flat 7 --flat-skip "<outline>"`; `--map "#shade=Base"` for wide shaded areas; raise `--island` |
| Outline color = pad/nose color (e.g. navy outline + navy paw pads) | Map the outline to Black, then `--split-thick "Black=DarkBlue:6"` moves thick navy blobs back to DarkBlue. Outline gaps: `--map` the lighter edge tones to Black, `--grow "Black=1"` |
| Too many colors | Merge them in `--colors`; every image color goes to the nearest listed color |

## Fixing problems (SVG input)

| Problem | Fix |
|---|---|
| A full-size background rectangle | `--drop-bg` |
| Remove a color but keep what it hides | `--drop "White"` (the layer isn't written, but it still cuts away what's under it) |
| Recolor or merge colors | `--colors "Red,White,Black"`, or force one with `--map "#00ff00=Green"` |
| Gradients | The first stop color is used (a warning is printed). Ask the user which color they want |
| Slivers between colors (layers from separate traces) | Rebuild from a PNG export with `image_to_layers.py` (it shares one label map, so there are no gaps) |

## Recipes

- **Text in a font copied from an image (logo lettering).** See `examples\lettering_from_logo_peanuts.py`. It cuts the letters that exist in the logo, builds the missing ones from their strokes (I = E's stem, M = N half + mirror, R = P + A's leg, C = a rotated U, Y = a flipped A apex + T's stem), and adds a solid outline backing (dilate the letters, fill the small gaps) as a second color. Copy it into `<project>\Scripts\`, then change the source crop and glyph recipes. Always render a glyph sheet and look at every assembled letter.
- **Outline or backing color around a design** (sticker look, one solid base): dilate the union of all layers by N px and subtract the design, as in the lettering example's `back`/`red`.
- **Hand-tuned color classes** (when nearest-color isn't enough): see `examples\hand_tuned_layers_snoopy.py`. It writes per-class score formulas (e.g. red = R−G), then uses the same label map and trace.
- **Blender use** (extrude or boolean, not multi-color): follow the Blender rules in `D:\gimp-mcp\Projects\SVG\Scripts\README.md`. Merge everything into one outline, no hairline joints, rounded tips.

## Bambu Studio notes

- Each `<Name>_<Color>.svg` is one part. Assign the matching filament in Bambu; the colors inside the SVG are only labels.
- Because the files share a canvas, import them at the same position and scale so they line up. Don't move them individually afterwards.
- Leave `_AllColors_preview.svg` out of the print.

## Lessons learned

- Build every color from **one shared label map** (that's what `image_to_layers.py` does). Tracing each color on its own leaves slivers between colors.
- Supersample about 5× and blur lightly before tracing, so the curves come out smooth instead of pixel-stepped.
- 0.4 mm is the nozzle limit. Thinner lines disappear or print broken, so check at the real print size.
- Names and colors come from the user or the image. Bambu ignores SVG fill colors.

## Log

| Date | Project | Result |
|---|---|---|
| 2026-10-21 | `Projects\SVG` Snoopy Grinchy (`SVGs Drafts\Snoopy\Snoopy_v1`) | 5 colors, 44.8×70 mm |
| 2026-10-21 | `Projects\SVG` Merry Christmas Peanuts lettering | White + Red outline, 90×34 mm |
| 2026-11-01 | `Projects\SVG\Providence` P logo (`Drafts\Providence_v1`) | Pink/White/Navy, 48.8×70 mm; source PNG had white sticker halo, stripped by `Scripts\strip_halo.py` |
| 2026-11-04 | `Projects\BetterResolution\Glove` BLB shield (`SVG`) | Black/Gold, 33×38 mm; redrawn as geometry by `Scripts\build_blb_emblem.py` (embroidered source traced wobbly) |
| 2026-11-04 | `Projects\BetterResolution\Glove\SVG\Laces` 4 views | Black laces + Outline reference, 101.6 mm tall; hand-tuned class + erase polygons in `Scripts\lace_layers.py` |
| 2026-11-08 | `Projects\Cup\Stitch\SVGs` Stitch Santa onesie (`Drafts\Stitch_v1`) | 9 colors (`--force`), 55.1×70 mm; pompom/brim gap via new `--cut-hole` |
| 2026-11-09 | `Projects\Cup\Stitch\XmasOhana` X-mas Ohana lettering (`Drafts\XmasOhana_v1`) | Red/Green, 85.3x70 mm; flat-color PNG made by `Scripts\make_xmas_image.py`; fixed kmeans crash on flat-color input |
| 2026-11-09 | `Projects\Cup\Stitch\SVGs` Stitch Santa hat (`Drafts\Stitch_v2`) | 7 colors (`--force`), 70.4x70 mm; user: no shading/accents -> new `--flat` option + flat-basics rule |

| 2026-11-12 | `Projects\SVG\SVGPeanuts` PEANUTS word from card photo (`Drafts\Peanuts_v1`) | 1 color for engraving, 100x38.3 mm; perspective-straightened by `Scripts\peanuts_word_svg.py` |

Add a row per project.
