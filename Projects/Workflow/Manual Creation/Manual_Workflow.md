# TryCatch Designs: Manual Creation Workflow

**For Claude:** the user will give you this file (or its folder), an assembled `.blend`, a Bambu `.3mf`, assembly notes and an **output path**. Make a Word assembly manual with labeled step renders of the real model. Do every step below without being asked. Stop and ask only where a step says **ASK**. Show the user the test contact sheet before spending time on final renders.

## Inputs from the user

| # | What | Required? | Notes |
|---|---|---|---|
| 1 | Assembled `.blend` | Yes | Parts positioned as built, in mm. Each part its own mesh object with a clear name. |
| 2 | `.3mf` | Yes | Part colors and the print plates come from here. |
| 3 | Assembly notes | Yes | A `.txt`, an old manual or rough bullets: build order, how parts fit, cut lengths, hole depths, glue or no glue, and anything learned while building. Missing? **ASK**. Don't invent steps. |
| 4 | Output path | Yes | Convention: `G:\gimp-mcp\Projects\<Model>\Manual\`. Not given? **ASK**. |
| 5 | Which side is the front | If unclear | Used for left/right and the view angles. Our models face -Y. |
| 6 | Cover image | Optional | A real print photo is best, with the logo already on it (`Render_Workflow.md` → `brand.py`). No cover? Use a `Drafts\hero_logo.png` from the Renders workflow, or a shot from this workflow. |
| 7 | Print details | Optional | Plates that need a different nozzle, filament or hardware the buyer supplies. Otherwise take the plate list from the 3MF and **ASK** about anything unusual. |
| 8 | Accent color, model title | Optional | Accent defaults to `C12E1F` red. Pick one from the model's filaments if red doesn't fit. |

Ad renders aren't needed. The step images are rendered here from the `.blend`.

## Tools

Everything is in `G:\gimp-mcp\Projects\Workflow\Manual Creation\`. Run the Python scripts with `python -I` (3.11 with Pillow). Blender 5.1 at `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`, Microsoft Word, PowerShell 7 (`pwsh`) and Node are also needed.

| File | Role |
|---|---|
| `run_manual.py` | **Entry point.** Stages: `prep`, `test`, `final`, `doc`. |
| `render_steps.py` | Blender side: one shot (part subset, exploded offsets, studio set). Writes the PNG and its label positions. Uses `..\Renders\scene_env.py`. |
| `annotate.py` | Draws labels and arrows on the renders. |
| `probe_parts.py` | Finds positions on parts, for placing labels. |
| `build_manual.js` | Builds the `.docx` from `manual.json`. |
| `check_doc.py` | Opens the `.docx` in Word, makes a page sheet, reports size, near-empty pages and missing numbers. |
| `examples\CatInHat_manual.json` | **Worked example. Copy its structure for a new model.** |

Colors come from `..\Renders\run_blend.py --plan`, the same matching the ad renders use.

If `node_modules` or `.venv` is missing, recreate them in this folder:
```
npm install
python -m venv .venv
.venv\Scripts\python -m pip install pymupdf pillow
```

## Output layout

```
<output>\
  manual.json                    the model's manual definition (keep it, re-runs and fixes start here)
  Work\                          blend_shots.json (part colors), part_points.json (part positions)
  Renders\test_contact_sheet.png quick labeled previews
  Renders\final_labeled\         full-size labeled PNGs
  Renders\jpg\                   the images that go in the document
  Renders\pages.png              every page of the document, for checking
  <name> - Assembly Instructions.docx
```

## Steps

1. **Read the notes.** Turn them into build steps in order. Unclear step, missing cut length or contradiction? **ASK**. The user's wording, reasons and numbers go in the manual as given. Don't add a reason for a step that the user didn't give.

2. **Write `<output>\manual.json`** with `name`, `blend`, `3mf`, and an empty `"render": {"shots": []}` plus `"doc": {"blocks": []}` for now. Then run:
   ```
   python -I run_manual.py prep "<output>\manual.json" "<output>"
   ```
   **Read the printed color list.** A part with no match stops the run: add it to `"assign"`, and **ASK** which filament if the 3MF doesn't say. Exclude unrelated parts with `"exclude_collections"` / `"exclude"`. If the notes, the 3MF and real photos disagree on a color, **ASK** which is right (see Known issues).

3. **Plan the shots.** Aim for 1–2 per step, showing the action rather than the finished state: lift the new part above where it goes, or pull it out along its insertion direction. Add a final hero shot. Get label positions from `Work\part_points.json`; for a hole, nub or key, query the mesh:
   ```
   blender -b "<model.blend>" --python probe_parts.py -- --query BaseCloud "v.z > 70"
   ```
   `blender` = the full path above. `v` is the vertex in mm, `r` its distance from the Z axis. Never guess a label position.

4. **Test pass** (about 5 seconds per shot):
   ```
   python -I run_manual.py test "<output>\manual.json" "<output>"
   ```
   **Look at** `Renders\test_contact_sheet.png` and fix before going on. Check: is the action obvious, is anything cropped, does each label's dot sit on the right feature, do arrows run the right way, do boxes avoid covering the action. Use `--only shot1,shot2` to re-run a few. Show the sheet to the user.

5. **Final pass** (about 10 seconds per shot, so run it in the background):
   ```
   python -I run_manual.py final "<output>\manual.json" "<output>"
   ```
   Look at the contact sheet and at least one full-size image.

6. **Write the document blocks** in `manual.json` (see below), then build:
   ```
   python -I run_manual.py doc "<output>\manual.json" "<output>"
   ```

7. **Verify.** All of these must be clean:
   - `numbers in the notes but not in the document`: every number from the notes has to be there, unless the user changed it. Set `"source_notes"` so this runs.
   - `near-empty pages`: look at those pages in `Renders\pages.png`. Fix orphans by shrinking images (`"width"`) or removing a page break.
   - Size under 20 MB (Etsy's limit per file).
   - Look at `pages.png` and read one page with a table at full size.

8. **Report.** Give the `.docx` path, page count, size, and anything you assumed. Add a row to the log below.

## manual.json reference

```json
{
  "name": "Model Name",
  "blend": "G:\\...\\model.blend",
  "3mf": "G:\\...\\model.3mf",
  "exclude_collections": ["OtherProject"],
  "exclude": ["SomePart"],
  "assign": {"String_": 3},
  "render": {
    "all_parts": ["Base", "Lid", "String_"],
    "rod_extruder": 3,
    "shots": []
  },
  "doc": {
    "accent": "C12E1F",
    "source_notes": "G:\\...\\notes.txt",
    "cover": {"image": "G:\\...\\cover.png", "title": "MODEL NAME", "subtitle": "Second line", "kicker": "optional, replaces Assembly Instructions"},
    "blocks": []
  }
}
```

- `assign`: name prefix → extruder number. Beats the 3MF. Use it for parts that aren't printed objects in the 3MF (filament strings, rods).
- Other `render` keys: `layer_lines` (default 0, the user rejected visible ridges; only raise it if asked), `exposure` (0), `cyc_rgb` (backdrop color), `samples` (128), `res` (1400), `rod_radius_mm` (0.875).
- Part names in `parts`, `drop`, `move` are **name prefixes**. `prep`/`test` warn about any prefix that matches nothing.

### Shots

```json
{"name": "s3_levers",
 "parts": ["Base", "Couch_", "Lever_"], "drop": ["String_"],
 "move": {"Lever_": [0, -16, 0]},
 "az": -18, "el": 18,
 "target_mm": [3, -22, 26], "frame_mm": 75,
 "labels": [{"text": "Left lever (17)", "p": [-9.5, -21, 25], "part": "Lever_L_Brass", "dx": -0.2, "dy": -0.15}],
 "arrows": [{"a": [-9.5, -15, 21], "b": [-9.5, -15, 21], "part_a": "Lever_L_Brass"}]}
```

| Key | Meaning |
|---|---|
| `parts` / `drop` | Parts shown (default `all_parts`) / removed from that list |
| `move` | Exploded offset in mm per part prefix |
| `az`, `el` | Camera angle. `az` 0 = front (-Y), -90 = left side, 90 = right side, 180 = back. `el` is height; negative looks up, and needs a target well above the table |
| `frame_mm`, `target_mm` | Close-up: framed size and the point to center on, in assembly mm. Without them, the shot fits the whole subset (`zoom` scales that, e.g. 0.9 is tighter) |
| `rot` | Whole-model rotation in degrees, e.g. `[-90, 0, 0]` lays a -Y-front model on its back |
| `rods` | Extra filament pieces not in the blend: `[[x, y, z], [x, y, z]]` pairs in mm. Use for an alternate string route |
| `labels` | `p` = point in assembly mm. `part` = add that part's `move` to it (full part name). `dx`, `dy` = box offset as a fraction of image width |
| `arrows` | `a` → `b` in assembly mm. `part_a` / `part_b` = add that part's `move`, so `a` = `b` with `part_a` set draws "from where it is now, to where it goes" |
| `peel` | `{"Part_name": {"x": 10, "pivot": [10, -30, 110], "deg": -25, "ramp": 15, "side": 1, "axis": [0, 0, 1]}}`: full part name. Past `x` (on the `side` of it, 1 = +X) the part swings about `axis` (default Z) through `pivot`, ramping to `deg` over `ramp` mm. Shows a strip glued down from one end |
| `layer_lines`, `exposure` | Per-shot overrides |

### Document blocks

Text may use `**bold**` and `~~muted~~`.

| Block | Example |
|---|---|
| Page heading (new page) | `{"h1": "Step 1 – Build the Hat"}`; add `"page_break": false` to stay on the page |
| Sub heading | `{"h2": "Lower strings"}`; add `"page_break": true` to start a page |
| Paragraph | `{"p": "Text"}` |
| Muted note under a table | `{"note": "→ Cut 2 at 54.7 mm"}` |
| Numbered steps | `{"steps": ["First", "Second"]}` |
| Bullets | `{"bullets": ["One", "Two"]}` |
| Callout | `{"callout": {"title": "IMPORTANT:", "lines": ["Text"], "style": "warn"}}`; styles `warn`, `info`, `tip`, `muted` |
| Image | `{"img": "shot_name", "width": 3.6, "caption": "Optional"}`; width in inches |
| Two images side by side | `{"pair": [{"shot": "a", "caption": "Option A", "accent": true}, {"shot": "b", "caption": "Option B"}]}` |
| Table | `{"table": {"head": ["Cut"], "rows": [["37.3 mm"]], "widths": [9360]}}`; widths sum to 9360 at most |
| Space | `{"gap": true}` |
| Closing line | `{"end": "Enjoy!"}` |

Standard order: `Before You Start` (what it is, left/right definition, dry-fit warning, what you need, print plate table, nozzle warnings), one `h1` per major step with its images, then `All Done` with the hero shot and the closing line. Use `h2` to keep short steps together on a page.

## Known issues

- **Colors can disagree.** On the Cat in the Hat, the instructions say silver knobs while the real print's knobs look gold. **ASK**; don't pick one silently.
- **The 3MF decides the print, not the blend's names.** A part called `_Silver` may print in another color.
- **Non-printed parts.** Filament strings and rods live in the blend but not in the 3MF, so they need `assign`. Anything hidden from render or named `Proxy` is skipped.
- **Instruction images stay plain.** The studio backdrop is deliberate: it keeps white and gold parts readable. Themed backgrounds belong in ad images.
- **Word decides page breaks.** That's why `check_doc.py` uses Word itself. Tables stay whole on one page.

## Log

| Date | Model | Output | Result |
|---|---|---|---|
| 2026-10-29 | Cat in the Hat Hot Air Balloon | `G:\gimp-mcp\Projects\CatInHat\Instructions\` | Built by hand before this workflow. 11 pages, 13 images. PNG build was 24.8 MB, so images are now always JPEG (2.2 MB) |
| 2026-11-03 | Cat in the Hat, rebuilt through this workflow as its test (`examples\CatInHat_manual.json`) | `G:\gimp-mcp\Projects\CatInHat\ManualTest\` | 11 pages, 1.3 MB, no layer lines. Text identical to the 2026-10-29 Etsy manual (202 of 202 paragraphs), no numbers missing from the notes |
| 2026-11-03 | Beagle Dog Bowl Candle Holder | `G:\gimp-mcp\Projects\SnoopyCandle\Instructions\` | 13 pages, 13 images. `render_steps.py` fixed: objects positioned by location (Bowl, keys) landed wrong, hidden parts didn't render. Dowel + GlueKey1-4 added to `Worklend_shots.json` by hand after `prep` (hidden in blend), redo after re-running `prep` |
| 2026-11-04 | Beagle Dog Bowl Candle Holder, V4 update (separate eyes + smile) | `G:\gimp-mcp\Projects\SnoopyCandle\Instructions\` (V3 in `Archive_V3\`) | 15 pages, 17 images, 1.1 MB. Added shot key `peel` to show a strip half glued. Same hidden-part fix after `prep`: Dowel + GlueKey1-4 |

Add a row per manual.
| 2026-11-08 | Blender Modeling Field Guide (learning manual, no model: procedural demo renders from `Work\demos.py`, Eevee) | `G:\gimp-mcp\Projects\Blender Manual\Manual Doc\` | 30 pages, 40 images, 2.3 MB. Built with `Work\build_doc.py` → this folder's `build_manual.js` + `check_doc.py`. Added cover `kicker` |
