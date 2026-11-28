# TryCatch Designs: SVG Cup Append Workflow (art on the cooler cup and lid)

**For Qwen and other agents:** the user will give you this file (or its folder), an **SVG layer set** and a **cup 3MF**. Add the art to the **cup front** (raised relief) and/or the **lid** (flush inlay), one shell per color, merged into the part the way the Grinch and Snoopy finals were done. Cup only unless the user asks for the lid. The user paints it in Bambu afterwards. Do every step below without being asked. Stop and ask only where a step says **ASK**.

**Never create, edit, move or delete anything in a workflow folder** (`G:\gimp-mcp\Projects\Workflow\` or `G:\Blender\blender-mcp\Projects\Workflows\`), including the scripts and this doc. Only run the scripts. If a script errors or validation fails, report the output and stop; don't patch code to make it pass. Put the Log row for this run in your report instead of writing it here.

**Agent rules.** Only run the commands this doc names. Don't write helper scripts (not in Temp either), don't use heredocs or `python -c`, and don't edit the user's SVGs or hand-write a `layers.json`. If a command is blocked by a permission rule or crashes with a traceback, report the last lines and stop. Don't work around it. **Never change an input file** (SVG, `layers.json`, src 3MF). If a step must change one, write the result as a new file next to it (`<name>_fixed.<ext>`) and leave the original untouched. **Copying out of a workflow folder:** only with `python -I G:/gimp-mcp/Scripts/wf_fetch.py --why "<reason>" "<dest>" "<file>" ...`, and always tell the user which files you're copying and why, then report the `COPY ... WHY:` and `OK` lines. Keep the reason short and leave out the words *copy, move, del, ren* (e.g. "model", "current"): with "Workflow" in the same command they trip a deny rule.

## Tools

Run `python -I cup_append.py` directly from the shell. The script launches Blender headlessly. Blender MCP is optional, so continue with the shell command if the add-on is unavailable.

Everything is in `G:\gimp-mcp\Projects\Workflow\SVG Cup Append\`. Run with `python -I` (3.11; needs `shapely>=2 numpy`). Blender 5.x is found automatically under `C:\Program Files\Blender Foundation\`.

| Tool | Use |
|---|---|
| `cup_append.py` | Lays out the art, calls Blender, merges the meshes, and publishes the 3MF after validation passes |
| `validate_3mf.py` | Checks the stored 3MF meshes directly using Python and NumPy. Use it again on any later Bambu save |
| `cup_decal_blender.py` | Blender half for the cup (called by `cup_append.py`, not run by hand): wrap + extrude, STLs, previews |
| `lid_inlay_blender.py` | Blender half for the lid (called by `cup_append.py`): flush inlay pocketed into the lid, STLs, preview |

```
python -I cup_append.py "<layer set>" "<src.3mf>" "<out.3mf>" [--target cup|lid|both] [options]
```

## Inputs from the user

1. **Layer set**: a folder from the SVG Creation workflow (`G:\gimp-mcp\Projects\Workflow\SVG Creation\`) holding `<Name>_<Color>.svg` + `layers.json`. Prefer `<project>\Final\<Name>\`; a `Drafts\<Name>_vN\` is fine if the user points at it. No layer set yet → make one first with the SVG Creation workflow. **A folder with a loose SVG but no `layers.json` is not a layer set: ASK** the user before making one. Single-color traced SVGs (potrace: relative `c`/`z` commands, `<g transform="translate() scale()">`) load fine as-is (fixed 2026-11-27), so never convert or rewrite them.
2. **Cup 3MF**: normally `G:\Blender\blender-mcp\Projects\NewCupProject\Final\Cooler Cup Base - Final.3mf` (plain cup, all plates and settings). If the user names a copy of the base (e.g. `<Name> Cooler Cup - Final.3mf`) that is byte-identical to it, use the base as src and the copy as out.
3. **Output**: default `G:\Blender\blender-mcp\Projects\NewCupProject\Final\<Name> Cooler Cup - Final.3mf`. If the user names a cup's own 3MF (e.g. `NewCupProject\<Name>\<Name> Cup.3mf`, plain cup), overwrite it in place: src = out + `--force`, no backup (user, 2026-11-09). Otherwise don't overwrite the base. If the user gives a folder (e.g. `NewCupProject\<Name>\`), lay it out flat like `GrinchCup`: `<Name> Cup.3mf`, `<Name> Cup - <Art>_<Color>.stl`, `preview.png` + `preview angle.png` at the top, `work\` for the rest. The script doesn't do this, so move and rename the files after the write.

## What it does (cup, `--target cup`, default)

- **Colors tile.** The outline color (`--outline`, default Black, else White) wins overlaps; every other color is cut by the ones before it; hairline gaps go to the outline. Holes inside the art stay open (cup wall shows, e.g. the P counter) unless `--fill-holes`.
- **Placement.** Cup front (-Y, above the spigot). Size = `layers.json` size unless `--height-mm` / `--width-mm`. Centered in the free band between the spigot recess (+1 mm) and 3.592 mm below the rim (`--align top` puts it at the rim gap instead, like Grinch/Snoopy, which had text below). **The art always stays on the smooth front between the grip ribs, with padding: never wider than 60 mm of arc.** Too tall → scaled down to the band. Wider than 60 mm (layer-set size or `--width-mm`/`--height-mm`) → scaled down to 60 mm with a `NOTE`. A `--u-shift` or `--z-shift` that would push it into the ribs, rim or spigot stops with an `ERROR`.
- **Relief.** Each color is its own closed shell, sunk 0.2 mm into the wall. Outline stands 0.8 mm, others 0.6 mm (`--heights "White=0.8,Pink=0.6"`). The step edges stop Bambu's paint bucket from bleeding between colors.
- **3MF.** Appends the shells to the cup part's mesh (one part, overlapping shells, same as Grinch final) and updates its face count. The cup and lid exports carry Blender's vertex indices directly into the 3MF so touching colors keep separate vertices. Other objects, plates, paint, settings and pictures are copied unchanged. Cup geometry (wall radius, rim, recess) is read from the 3MF itself.
- **Guards.** Stops if the cup front wall isn't the plain 41.91 mm radius (already has relief, or a different cup) or if out exists. `--force` overrides both.
## What it does (lid, `--target lid` or `both`)

The lid prints **face-down** on the bed, so the art is **inlaid flush**, not raised: each color is a 0.6 mm deep prism level with the face, pocketed into the lid (one Exact boolean cut by the union outline), then lid + colors are joined into one mesh. Colors stay separate shells, so the face stays flat for the bed and the paint bucket stops at each color (same as the Grinch caps).

- **Orientation.** Art reads upright from outside with the **straw hole at 12 o'clock** (as on the Grinch "Merry Grinchmas" cap). The tool finds the hole from the lid's flat face (Ø79.2 face, Ø9.5 hole 13 mm off center on the base lid).
- **Placement** (`--lid-place`). **Never put art over the straw hole unless the user explicitly says the hole may go through the art.**
  - `best` (default): tries `below`, `miss` and `gap`, each tilted 0, ±15, ±30 and ±45°, and prints a `lid options` list (logo size + the exact flags), biggest first. The dry run previews the biggest. About 80 s.
  - `--lid-rotate DEG`: tilt the art (counterclockwise as read from outside, hole up), **at most ±45°**. The art's top always points to the top of the cap (the straw hole side); it never lies on its side or upside down. With an explicit `--lid-place` and `--lid-rotate` the run is fast.
  - `below`: centered left-right, in the space below the hole, as big as fits. Providence P: 28×41 mm; Spurs V2 spur: 35.6×44.1 mm.
  - `miss`: the biggest spot anywhere that misses the hole (can sit beside it). Providence P: 33×48 mm, right of the hole; Spurs V2 spur: 45.4×56.3 mm, right of the hole.
  - `gap`: the straw hole sits inside an open gap of the art (a counter, a ring), never on the art. `does not fit` when the art has no gap big enough (e.g. Spurs V2 spur).
  - `through`: **only when the user asks.** Centered on the lid; the hole cuts the art (0.5 mm lid rim kept around the hole). Providence P: 44×63 mm.
  - Clearance: 1 mm to the face edge and to the hole. `below`/`miss` treat the art as solid; only `gap` lets the hole sit inside the art's own gap; only `through` cuts the art.
  - `--lid-height-mm` fixes the size (stops if it doesn't fit); `--lid-shift "right,up"` nudges (mm, hole = up).
- **Guard.** Stops if the lid face is already made of several shells (has inlay). `--force` overrides.

## Shared

- **Work folder** (default `G:\Blender\blender-mcp\Projects\NewCupProject\<Name>Cup\`, `--work` to change):
  - `STL\<Name> - <Color>.stl` per color + `<Name> - Logo.stl` (all colors), in 3MF local coords: for users who want separate parts instead of painting
  - `Images\preview.png` (front, ortho) + `preview_angle.png`; lid: `preview_lid.png` (face from outside, hole up)
  - `STL\<Name> Lid - <Color>.stl` + `<Name> Lid.stl` (lid with inlay joined)
  - `Work\` triangulation JSON, indexed mesh JSON, and preview source STL

## Steps

1. **Check the inputs.** Read `layers.json` (name, colors, size). Look at the layer set's `_check.png`. Confirm the src 3MF is the plain base (or identical to it: `cmp`).
2. **Target.** Cup only, unless the user asks for the lid (`--target lid` / `both`). `--target both` puts the same layer set on both. Different art on cup and lid = **one final file, two runs**: cup run with out = `<cup work>\Work\cup_only.3mf`, then `--target lid` with src = that file and out = the Final path. Never make a separate cap 3MF.
   - **"Like on <reference>.3mf":** the reference only guides which `lid options` row to pick (size, below/miss/gap). To find the lid in it: `Metadata/model_settings.config` object named `Cap*` → its id → that id's `p:path` in `3D/3dmodel.model`. The object ids are not the `object_N.model` numbers. The tool's inlay depth is always 0.6 mm, even if the reference is deeper. For the lid, keep the default `--lid-place best` unless they ask otherwise; `through` only if they say the hole can go through the art.
3. **Pick the outline color.** The color that separates the others (black linework, a white keyline). If it isn't obvious, **ASK**.
4. **Dry run.** For a lid: after a `best` dry run, **ASK** the user which option to use. Show them the `lid options` list (top 5 that fit, sizes and flags), the preview (`preview_lid.png`, biggest option), and a suggestion (e.g. biggest, or `below --lid-rotate 0` if they want it centered and upright). Then dry-run their choice with its `--lid-place` and `--lid-rotate`, show that preview, and write only after they agree.
   Cup: `python -I cup_append.py "<layers>" "<src>" "<out>" --dry-run`. Read the printed size and z range, then **look at the previews** (in *this* run's `<work>\Images\`): cup art on the smooth front with a visible gap to the ribs on both sides, clear of the spigot recess and rim. Art touching or covering the ribs is wrong: stop and **ASK**, never write it; lid art reading upright with the hole on top, clear of the hole (unless `through`); colors right, nothing missing.
5. **Adjust** with `--height-mm`, `--width-mm`, `--align`, `--z-shift`, `--u-shift`, `--heights`, `--lid-place`, `--lid-height-mm`, `--lid-shift`, and dry-run again. If the user gave no size, use the layer-set size (the script caps it at 60 mm wide) and say so.
6. **Write and validate.** Run the same command without `--dry-run` (use `--force` for an authorized replacement). The command checks the staged 3MF before publishing it. Require both `3MF validation PASS` and `wrote <path>`. On failure, read the model member and defect counts above the verdict. The command exits nonzero and preserves any existing destination, including in-place runs. Report the validator lines and stop. `--force` does **not** skip validation. Next: the user starts the **SVG Cup Repair** workflow (`..\SVG Cup Repair\SVG_Cup_Repair_Workflow.md`) with this run's work folder. Don't diagnose or guess causes here.
7. **Report back.** Include the validated output path, validation verdict, and previews. For a cup, include art size, position in mm from the cup bottom, heights per color, and the `relief r` line. For a lid, include mode, size, and position. Plate thumbnails still show the plain cup until the file is re-saved in Bambu.
8. **Verify in Bambu Studio.** Open the export and check the cup or lid for geometry warnings. Run `python -I validate_3mf.py "<file.3mf>"` on the actual file after painting or re-saving, since Bambu can weld touching color shells during save. Record which file was checked. If Bambu Studio or the painted file is unavailable, report that check as pending.
9. **Log row.** Write the row for the Log table below in your report (same columns). Don't edit this file; the user adds it.

## Options

| Option | Effect |
|---|---|
| `--height-mm 70` / `--width-mm 50` | Art size (one of the two; aspect is kept) |
| `--align center\|top` | Center in free band (default) or top at the rim gap |
| `--z-shift 5` / `--u-shift -3` | Nudge up/down, or around the cup (arc mm, + = right when facing the front) |
| `--outline White` | Color that wins overlaps, fills gaps, stands taller |
| `--heights "White=0.8,Navy=0.6"` | Raise per color, mm above the wall |
| `--clean-px 0.5` / `--min-area-px 10` | Gentler cleanup (defaults 1.5 / 200 svg px). Use when fine details, counters or small accents get dropped |
| `--fill-holes` | Fill holes in the art with the outline color |
| `--target cup\|lid\|both` | Where the art goes (default cup) |
| `--lid-place best\|below\|miss\|gap\|through` | Lid placement (default best = largest of below/miss/gap; through only on request) |
| `--lid-height-mm 35` | Lid art height (default: largest that fits) |
| `--lid-rotate -30` | Tilt lid art (degrees, counterclockwise as read from outside, ±45 max: top stays toward the hole) |
| `--lid-shift "2,-3"` | Nudge lid art right/up (mm, hole = up) |
| `--lid-object cap` | Name substring or object id of the lid (largest single-part match wins) |
| `--object cup` | Name substring of the cup object in the 3MF (largest single-part match wins) |
| `--work DIR` / `--blender EXE` | Work folder, Blender path |
| `--dry-run` | Layout, STLs, previews only. Always exits 1 (ends with `dry run: previews in ...`): that's normal, not a failure |
| `--force` | Overwrite out / add to a cup or lid that already has art |

## Fixing problems

| Problem | Fix |
|---|---|
| "front wall R ... != 41.91" | src already has art (use the base 3MF), or it's a different cup (`--force` only if you're sure; the wrap uses the measured radius) |
| Art runs onto the grip panels | Can't happen at default shift (capped at 60 mm). If a preview shows it anyway, stop and **ASK**; for more padding use `--width-mm 55` |
| Art too close to the spigot / rim | Smaller size, or `--z-shift` |
| A color piece missing or speck-sized | It was under 200 svg px² or thinner than ~3 svg px and got cleaned out. Try `--clean-px 0.5 --min-area-px 10`, else fix the layer set (SVG Creation `--grow`) |
| Paint bucket bleeds between two colors | Give them different `--heights` (only matters where they touch) |
| "lid face already has inlaid art" | src lid already has art: use the base 3MF |
| Lid art too small | `best` already picks the largest safe spot; ask the user if the hole may go through the art (`through`) |
| Lid boolean leaves an empty lid | Cutter must be one clean outline (the tool unions all colors); check the art has no zero-width slivers |
| `AttributeError: 'NoneType' ... 'buffer'` in `load_svg` | The SVG has no paths the loader reads (M/C/L/H/V/Z, absolute or relative; `S`/`Q`/`A` arcs aren't supported). Stop and **ASK**. Don't rewrite the SVG |
| `3MF validation FAIL` (any count, e.g. `degenerate_triangles=88`) | Stop and report. Repair is its own task: SVG Cup Repair workflow |
| Shell renders black / inside-out in Bambu | Shouldn't happen (the Blender step flips negative-volume shells). Check the nonmanifold counts and re-run |

## Lessons learned

- Wrap with a dense mesh: `cup_decal_blender.py` re-cuts every 0.6 mm before bending, or long triangles cut through the curve.
- Sinking 0.2 mm into the wall makes the shells fuse with the cup when sliced; overlapping shells in one part slice as a union in Bambu.
- Lid art is inlaid flush, never raised: the face prints on the bed. Seen from above the bed (+z) it is mirrored; the preview camera looks from below so it shows the real reading direction.
- Cut the lid pocket with the union outline of all colors: per-color prisms that touch leave inner walls and the Exact boolean returns an empty mesh.
- Read cup dimensions from the 3MF, not `NewSTL\cup.stl`: the 3MF part is shifted by `source_offset_z` (58.42).

## Log

| Date | Art | Output | Result |
|---|---|---|---|
| 2026-11-01 | `Projects\SVG\Providence\Drafts\Providence_v1` | `NewCupProject\Final\Providence Cooler Cup - Final.3mf` | 48.7×70 mm, centered (37.9–107.9 mm from bottom), White 0.8 / Pink, Navy 0.6. Done by hand (`NewCupProject\ProvidenceCup\Scripts`) before this tool; tool reproduces it |
| 2026-11-08 | `Projects\Cup\Stitch\SVGs\Drafts\Stitch_v1` | `NewCupProject\Happy Blue Creature\Happy Blue Creature Cup.3mf` | 55.1×70 mm, centered (37.9–107.9 mm from bottom), Black 0.8 / 8 others 0.6, nonmanifold 0. Folder laid out flat like `GrinchCup` (user request) |
| 2026-11-09 | `Projects\Cup\Stitch\SVGs\Drafts\Stitch_v2` (Santa hat) | `NewCupProject\Happy Blue Creature\Happy Blue Creature Cup.3mf` (overwritten in place) | 59.5×59.15 mm (70.4 wide too wide for grips), centered (43.3–102.5 mm from bottom), outline DarkBlue 0.8 / 6 others 0.6, nonmanifold 0. v1 STLs/previews → `work\v1\`, run files `work\v2\` |
| 2026-11-10 | `Stitch_v2` (re-done SVGs, black outline) | `NewCupProject\Happy Blue Creature\Happy Blue Creature Cup.3mf` (overwritten; src = that 3MF, plain cup + painted cap; run files `work\v2b\`) | 59.5×59.15 mm, 43.3–102.45 mm from bottom, Black 0.8 / 6 others 0.6, nonmanifold 0, cap paint kept |
| 2026-11-26 | `Projects\Capibara\Final` | `NewCupProject\Final\Capibara Cooler Cup - Final.3mf` | 60.74×70.0 mm, centered (37.87–107.87 mm from bottom), Brown2 0.8 / Tan, Belly, Brown, Skin 0.6, nonmanifold 0. Made before the 60 mm cap; today it would be scaled to 60 mm |
| 2026-11-26 | `Projects\Spurs\Final\Spurs_BW` | `NewCupProject\Final\Spurs BW Cooler Cup - Final.3mf` | 60.0×32.13 mm, centered (56.81–88.94 mm from bottom), White 0.8 / Black 0.6, nonmanifold 0, previews `NewCupProject\Spurs_BWCup\Images` (front + angle) |
| 2026-11-26 | `Projects\Spurs\Final\Spurs` (Spurs_v3, 6 colors) | `NewCupProject\Final\Spurs Color Cooler Cup - Final.3mf` + `- Repaired.3mf` (use Repaired) | 60.0×30.43 mm, centered (57.66–88.09 mm from bottom), White 0.8 / Teal, Pink, Orange, Black, Grey 0.6, relief r 41.71–42.71. Default cleanup dropped spur rowel, pink counters, thin black edges, grey shaft → rerun with `--clean-px 0.5 --min-area-px 10` (all restored; only ~1 px grey hairlines on letter edges lost). Final had 55 welded 4-face seam edges → `split_nm.py` (pattern `Spurs_v3 - *.stl`, offset 0) → Repaired: 0 bad edges, 0 flipped, 0 neg-vol. Bambu GUI check pending. Previews `NewCupProject\Spurs_v3Cup\Images` |

| 2026-11-26 | `Projects\Spurs\Final\SpursV2` | `Projects\Spurs\Final\Spurs V2 Cooler Cup - Final.3mf` | 56.49×70.00 mm, centered (37.87–107.87 mm from bottom), Black 0.8 / White 0.6, relief radii 41.710–42.710 mm. Split welded color-seam vertices in the exported cup. Verified zero non-manifold edges, same-direction duplicate edges, and negative-volume components in the repaired 3MF. Visual Bambu Studio check pending. |
| 2026-11-27 | `Projects\Spurs\Drafts\Spurs_v4` (6 colors) | `NewCupProject\Final\Spurs Color Cooler Cup - Final.3mf` (old v3 Final + Repaired deleted first) | 60.00×30.30 mm, 57.72–88.02 mm from bottom, White 0.8 / Teal, Pink, Orange, Black, Grey 0.6, relief r 41.710–42.710, nonmanifold 0 per decal. `--outline White` (white keylines in v4), `--clean-px 0.5 --min-area-px 10` (v3 lesson). 60.0 mm is exactly the grip limit (allowed). Previews `NewCupProject\Spurs_v4Cup\Images`. Post-Bambu: expect welded seam edges → re-check + `split_nm.py` if needed |

Add a row per cup.
