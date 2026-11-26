# TryCatch Designs: SVG Creation Workflow (multi-color 3D prints)

The user may give you this workflow folder and a project or `Images/` folder. Resolve the paths from the current workspace and inspect the artwork in `Images/` or the source file the user names. The goal is **one aligned SVG per print color**, suitable for adding the design to a 3D model such as the front of a cup. For cup placement and 3MF output, use the [SVG Cup Append workflow](../SVG%20Cup%20Append/SVG_Cup_Append_Workflow.md) when requested. In a planning pass, inspect the sources and propose a sample without writing files.

## Rule: flat basics only (always)

Give each intentional design region one flat base color. Use the region's boundary and role in the artwork to decide what belongs together.

- Merge lighting and rendering detail into the base color of the region it sits on. Flatten gradients, shadow bands, shine streaks, and shading hatches. For example, a paw with a blue base, a darker blue shadow, and a pale blue shine becomes one solid blue paw.
- Preserve separately drawn features with their own base colors. A blue paw and a cheek drawn in a different shade of blue can stay on separate layers. Apply the same decision to intentional markings, outlines, eyes, teeth, and paw pads. Features that share a print color belong in the same SVG, even when they are disconnected.
- Visually inspect the artwork and list the feature, its chosen base color, and which tones will merge into it. Use `--suggest` as a starting point for sampling. If you can only see filenames, state that the region and palette decisions are provisional. Different poses or silhouettes are separate artwork candidates. Treat an image as a recolor reference only when the user or project files support that role.
- Keep the whites of the eyes and deliberately drawn white catchlights as eye details. Flatten soft glare and shading into the local base color. Preserve drawn eye details in the sample and check them at print size. Use the checker and preview to identify any detail that needs simplification.
- Count distinct print colors after flattening and grouping features that share a layer. Use nine colors as the default ceiling and keep the intentional colors that fit within it. In the plan, give the proposed palette and count for each candidate image, with the features assigned to each color.
- Show a palette preview for each candidate in the plan when the interface can display inline color swatches. Sample representative base colors from the artwork and show one swatch per proposed print color, labeled with its plain color name and every feature it covers. When inline swatches are unavailable, give the plain color names and feature assignments with optional hex values. Leave files untouched during planning. During the sample build, show `_check.png` so the user can see where the colors actually landed on the artwork.
- If the palette exceeds the project's limit, **ASK** which features should share a filament color or whether to build the larger set with `--force`. Include the current palette and the affected features in the question.

**Olaf example** (`Projects\Olaf\Olaf-molded-vinyl.png`). Flatten the pale reflections on the ears into the ears' base brown. On the cap, keep the lighter brown crown and the darker brown band as separate print colors because the band has its own defined boundary. Apply the same rule to pale tones by keeping the intentional off-white face and body fill.

For raster sources, use `--colors` for the chosen palette and `--map` for sampled shading tones where a color hint preserves the intended regions. If the same source color plays different roles in different places, use a region-aware edit or a hand-tuned label map. Use `--flat` for thin shading only when it preserves intentional features, and use `--flat-skip` to protect affected layers such as outlines. Tune `--island` for leftover specks while checking small features at the intended print size. Build one sample first and compare `_labels.png` and `_check.png` with the source before producing the remaining sets.

## Tools

The tools are beside this file in `Projects\Workflow\SVG Creation\`. Run them with `python` (3.11; needs `vtracer skia-pathops pillow numpy scipy`).

| Tool | Use |
|---|---|
| `new_project.py` | Creates the project folders, copies sources into `Images/`, finds the next draft version, copies an approved draft to `Final/` |
| `image_to_layers.py` | Image (PNG/JPG) → one SVG per color. Removes the background, smooths the edges, and makes the colors tile with no gaps or overlaps |
| `svg_to_layers.py` | Existing SVG → one SVG per color, keeping the exact curves. Shapes on top cut away what's under them; strokes become filled shapes |
| `check_layers.py` | Renders a layer set and reports parts too thin to print, tiny islands, overlaps and slivers. Writes `_check.png` |
| `layers_common.py` | Shared code: color names, tracing, writing the layer set. `MAX_COLORS = 9` is the default SVG layer-set limit |
| `examples/` | `lettering_from_logo_peanuts.py` (font copied from a logo image), `hand_tuned_layers_snoopy.py` (the original Snoopy script) |

## Project folder (created automatically)

The user gives a path, for example `G:\gimp-mcp\Projects\SVG\Snoopy`. Step 1 creates:

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

## Standard cup front sizing

Use this preset when the prompt or the project's `PROJECT.md` specifies the standard cooler cup front from `NewCupProject`. Read the project file during planning and carry its target forward without asking for usage or size again. An explicit size from the user takes precedence.

- **Usable area:** 60 mm wide along the curve × 80.75 mm tall. The front band runs from 32.50 to 113.25 mm above the cup bottom.
- **Default artwork box:** 54 mm wide × 72 mm tall. When centered, a full box leaves 3 mm on each side and about 4.4 mm above and below within the usable band.
- **Size the visible artwork.** Use the combined foreground bounds after removing the background and any empty margins. Preserve proportions and use whichever limit is reached first. For a width-to-height ratio of 0.75 or more, use `--width-mm 54`. For a narrower design, use `--height-mm 72`. Measure each artwork separately and report its resulting width and height. If an SVG source has an oversized viewBox, fit it to the art before using these sizing flags.
- **Check the sample at print size.** Verify the dimensions in `layers.json` and run `check_layers.py` on the sample. Flag thin features that need simplification or a size decision before building the remaining sets. Use identical dimensions and alignment for all layers and recolors of the same artwork.
- Treat these dimensions as the working scale for print checks. The full aligned set can be resized together in Bambu Studio. If it is scaled down, reassess fine details at the smaller size.
- **Handoff.** Record the target and actual artwork dimensions in `PROJECT.md`. The [SVG Cup Append workflow](../SVG%20Cup%20Append/SVG_Cup_Append_Workflow.md) handles centering, wrapping, and fit verification on the actual cup.

## Steps

1. **Set up the project.**
   `python new_project.py "<project>" "<source file>"`
   Then fill in the Goal section of `PROJECT.md`: what it's for (cup wrap, keychain, sign...), size, colors, and what to keep or drop.

2. **Look at the source.** Read the image or SVG yourself. Work out:
   - **What to keep.** Usually just the subject (the character, the text) with no sky, ground, props or watermark. **ASK** if it isn't obvious whether something belongs to the subject (for example a gift held in the character's lap belongs; a doghouse in the background doesn't).
   - **Colors.** Use the colors the user specifies. Otherwise derive the palette from the source using the flat basics rule above. If recolor variants are requested, keep the feature boundaries from the approved sample and change the assigned print colors. If the user still needs to choose reassignments, include the current palette for each artwork in the question. Pair every color with all features that use it, and label close shades as estimates when uncertain. For example, “Current palette: dark brown outline and pupils, tan body, medium brown muzzle and paws, pink cheeks, white eye details. Which colors would you like to change, and to what?” Use the colors and features you actually observed for each source.
   - **Size in mm.** Use the user's size if given. Otherwise read `PROJECT.md` and apply the standard cup front preset when that target is specified there or in the prompt. State the preset and resulting dimensions in the plan and proceed without asking for confirmation. For other projects with no size specified, use 70 mm tall and say so.

3. **Build the layers.** Get the output folder from `python new_project.py "<project>" --next <Name>`.

   **From an image:**
   ```
   python image_to_layers.py in.png --suggest            # lists the image's colors, stops
   python image_to_layers.py in.png "<Drafts\Name_v1>" --name Name --colors "Red,White,Green,Yellow,Black" --height-mm 70 --debug "<Drafts\Name_v1>\_labels.png"
   ```
   Carry the approved color-to-feature assignments into the build. Choose the foreground mask first. For PNGs with a transparent exterior, use `--bg alpha` and check that the complete silhouette, including its outline, is retained. Use `--suggest` to sample candidate colors, then pass every approved print color explicitly with `--colors` and save `_labels.png` with `--debug`. `--colors` takes plain names (default shades) or `Name=#RRGGBB` (sampled or specified shades). A cluster count such as `--k 6` only controls automatic color detection. A filter such as `--min-pct` can discard small sampled colors, so recover any missing approved color from the source before tracing. Open `_labels.png` and check the foreground and feature assignments before evaluating the SVG trace.
   Replace the example size flag with the width or height selected for the project.

   **From an SVG:**
   ```
   python svg_to_layers.py in.svg --suggest              # lists the fill colors, stops
   python svg_to_layers.py in.svg "<Drafts\Name_v1>" --name Name [--colors "..."] [--drop-bg] [--width-mm 90]
   ```
   Text elements are skipped. They must be converted to paths first (Inkscape: Path > Object to Path).

4. **Check.** Compare the color names and count in `layers.json` with the approved palette. Run `python check_layers.py "<Drafts\Name_v1>"` and compare `_check.png` with the source and approved feature assignments. Confirm that small intentional details are present and that every feature is on the right layer. If a color or feature is missing or misassigned, correct the draft and repeat the checks before presenting it as ready. Fix slivers and other geometry issues using the table below. The report's "holes" are usually intended, like letter counters. Mention intended holes and preserve them.

   - Verify that the exterior stays transparent wherever the source shows empty space. The checker shows empty canvas in blue. A colored path can cover the exterior even when the SVG contains no background rectangle.
   - For each approved feature, check its full shape in `_check.png`. A marking should fill its intended region, and a small solid detail should have a clean interior. If a feature looks missing or mottled, open its individual SVG to confirm where that layer actually ended up.
   - Use `_labels.png` to locate the failure. If it already shows the wrong silhouette or color placement, correct the foreground mask or labels and rebuild. If the labels are correct and `_check.png` differs, inspect the SVG trace for the affected layer and check it again after correcting it.

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
| An intentional marking is missing, or a solid detail is mottled | Sample solid source pixels for the feature and map them to its approved layer. Use a region-aware label map if shared source tones belong to different features. If cleanup erodes a small detail, reduce it or protect its layer with `--flat-skip` or `--island-skip` as applicable, then check the preview at print size |
| Lines too thin to print (checker: thin > 3%) | Print bigger, or `--grow "Black=1.5"` |
| Specks / tiny islands | Raise `--island` (default 6 source px) |
| Jagged edges | Raise `--blur` (0.8 → 1.2). Lower it if small details melt away |
| Shading / highlights / accents left in | `--flat 7 --flat-skip "<outline>"`; `--map "#shade=Base"` for wide shaded areas; raise `--island` |
| Outline color = pad/nose color (e.g. navy outline + navy paw pads) | Map the outline to Black, then `--split-thick "Black=DarkBlue:6"` moves thick navy blobs back to DarkBlue. Outline gaps: `--map` the lighter edge tones to Black, `--grow "Black=1"` |
| Too many colors | Merge shading into each region's base color first. If the intentional palette exceeds the project's limit, follow the palette decision above |

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
- **Blender use** (extrude or boolean, not multi-color): follow the Blender rules in `G:\gimp-mcp\Projects\SVG\Scripts\README.md`. Merge everything into one outline, no hairline joints, rounded tips.

## Bambu Studio notes

- Each `<Name>_<Color>.svg` is one part. Assign the matching filament in Bambu; the colors inside the SVG are only labels.
- A print can use more colors in total than it has loaded at once when the sliced layer sequence allows a pause and filament swap. Check that the colors needed at each layer are available and that a filament being replaced can be swapped back in before it is needed again.
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
