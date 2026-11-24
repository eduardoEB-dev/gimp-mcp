# TryCatch Designs: SVG Cup Append Workflow (art on the cooler cup and lid)

**For Claude:** the user will give you this file (or its folder), an **SVG layer set** and a **cup 3MF**. Add the art to the **cup front** (raised relief) and/or the **lid** (flush inlay), one shell per color, merged into the part the way the Grinch and Snoopy finals were done. Cup only unless the user asks for the lid. The user paints it in Bambu afterwards. Do every step below without being asked. Stop and ask only where a step says **ASK**.

## Tools

Everything is in `D:\gimp-mcp\Projects\Workflow\SVG Cup Append\`. Run with `python -I` (3.11; needs `shapely>=2 numpy`). Blender 5.x is found automatically under `C:\Program Files\Blender Foundation\`.

| Tool | Use |
|---|---|
| `cup_append.py` | The whole job: lays out the layer set on the cup and/or lid, calls Blender, merges the result into the 3MF parts, writes a new 3MF |
| `cup_decal_blender.py` | Blender half for the cup (called by `cup_append.py`, not run by hand): wrap + extrude, STLs, previews |
| `lid_inlay_blender.py` | Blender half for the lid (called by `cup_append.py`): flush inlay pocketed into the lid, STLs, preview |

```
python -I cup_append.py "<layer set>" "<src.3mf>" "<out.3mf>" [--target cup|lid|both] [options]
```

## Inputs from the user

1. **Layer set**: a folder from the SVG Creation workflow (`D:\gimp-mcp\Projects\Workflow\SVG Creation\`) holding `<Name>_<Color>.svg` + `layers.json`. Prefer `<project>\Final\<Name>\`; a `Drafts\<Name>_vN\` is fine if the user points at it. No layer set yet → make one first with the SVG Creation workflow.
2. **Cup 3MF**: normally `D:\Blender\blender-mcp\Projects\NewCupProject\Final\Cooler Coozie Cup Base - Final.3mf` (plain cup, all plates and settings). If the user names a copy of the base (e.g. `<Name> Coozie Cup - Final.3mf`) that is byte-identical to it, use the base as src and the copy as out.
3. **Output**: default `D:\Blender\blender-mcp\Projects\NewCupProject\Final\<Name> Coozie Cup - Final.3mf`. If the user names a cup's own 3MF (e.g. `NewCupProject\<Name>\<Name> Cup.3mf`, plain cup), overwrite it in place: src = out + `--force`, no backup (user, 2026-11-09). Otherwise don't overwrite the base. If the user gives a folder (e.g. `NewCupProject\<Name>\`), lay it out flat like `GrinchCup`: `<Name> Cup.3mf`, `<Name> Cup - <Art>_<Color>.stl`, `preview.png` + `preview angle.png` at the top, `work\` for the rest. The script doesn't do this, so move and rename the files after the write.

## What it does (cup, `--target cup`, default)

- **Colors tile.** The outline color (`--outline`, default Black, else White) wins overlaps; every other color is cut by the ones before it; hairline gaps go to the outline. Holes inside the art stay open (cup wall shows, e.g. the P counter) unless `--fill-holes`.
- **Placement.** Cup front (-Y, above the spigot). Size = `layers.json` size unless `--height-mm` / `--width-mm`. Centered in the free band between the spigot recess (+1 mm) and 3.592 mm below the rim (`--align top` puts it at the rim gap instead, like Grinch/Snoopy, which had text below). Too tall → scaled down with a warning. Wider than 60 mm arc → warning (runs onto the grip panels).
- **Relief.** Each color is its own closed shell, sunk 0.2 mm into the wall. Outline stands 0.8 mm, others 0.6 mm (`--heights "White=0.8,Pink=0.6"`). The step edges stop Bambu's paint bucket from bleeding between colors.
- **3MF.** Appends the shells to the cup part's mesh (one part, overlapping shells, same as Grinch final) and updates its face count. Other objects, plates, paint, settings and pictures are copied unchanged. Cup geometry (wall radius, rim, recess) is read from the 3MF itself.
- **Guards.** Stops if the cup front wall isn't the plain 41.91 mm radius (already has relief, or a different cup) or if out exists. `--force` overrides both.
## What it does (lid, `--target lid` or `both`)

The lid prints **face-down** on the bed, so the art is **inlaid flush**, not raised: each color is a 0.6 mm deep prism level with the face, pocketed into the lid (one Exact boolean cut by the union outline), then lid + colors are joined into one mesh. Colors stay separate shells, so the face stays flat for the bed and the paint bucket stops at each color (same as the Grinch caps).

- **Orientation.** Art reads upright from outside with the **straw hole at 12 o'clock** (as on the Grinch "Merry Grinchmas" cap). The tool finds the hole from the lid's flat face (Ø79.2 face, Ø9.5 hole 13 mm off center on the base lid).
- **Placement** (`--lid-place`). **Never put art over the straw hole unless the user explicitly says the hole may go through the art.**
  - `below` (default): centered left-right, in the space below the hole, as big as fits. Providence P: 28×41 mm.
  - `miss`: the biggest spot anywhere that misses the hole (can sit beside it). Providence P: 33×48 mm, right of the hole.
  - `through`: **only when the user asks.** Centered on the lid; the hole cuts the art (0.5 mm lid rim kept around the hole). Providence P: 44×63 mm.
  - Clearance: 1 mm to the face edge and to the hole. Holes inside the art are filled when checking, so the hole never sits inside a letter counter unless `through`.
  - `--lid-height-mm` fixes the size (stops if it doesn't fit); `--lid-shift "right,up"` nudges (mm, hole = up).
- **Guard.** Stops if the lid face is already made of several shells (has inlay). `--force` overrides.

## Shared

- **Work folder** (default `D:\Blender\blender-mcp\Projects\NewCupProject\<Name>Cup\`, `--work` to change):
  - `STL\<Name> - <Color>.stl` per color + `<Name> - Logo.stl` (all colors), in 3MF local coords: for users who want separate parts instead of painting
  - `Images\preview.png` (front, ortho) + `preview_angle.png`; lid: `preview_lid.png` (face from outside, hole up)
  - `STL\<Name> Lid - <Color>.stl` + `<Name> Lid.stl` (lid with inlay joined)
  - `Work\` tris json + cup preview STL

## Steps

1. **Check the inputs.** Read `layers.json` (name, colors, size). Look at the layer set's `_check.png`. Confirm the src 3MF is the plain base (or identical to it: `cmp`).
2. **Target.** Cup only, unless the user asks for the lid (`--target lid` / `both`). For the lid, use `--lid-place below` unless they ask otherwise; `through` only if they say the hole can go through the art.
3. **Pick the outline color.** The color that separates the others (black linework, a white keyline). If it isn't obvious, **ASK**.
4. **Dry run.** `python -I cup_append.py "<layers>" "<src>" "<out>" --dry-run`. Read the printed size and z range, then **look at the previews**: cup art between the grips, clear of the spigot recess and rim; lid art reading upright with the hole on top, clear of the hole (unless `through`); colors right, nothing missing.
5. **Adjust** with `--height-mm`, `--width-mm`, `--align`, `--z-shift`, `--u-shift`, `--heights`, `--lid-place`, `--lid-height-mm`, `--lid-shift`, and dry-run again. If the user gave no size, use the layer-set size and say so.
6. **Write it.** Same command without `--dry-run` (add `--force` only when replacing an earlier output of the same art).
7. **Report back.** Output path; cup: art size and position (mm from cup bottom), heights per color, the `relief r` line (should be wall −0.2 to wall +max height); lid: mode, size, position; nonmanifold counts (must be 0); the previews. Note: plate thumbnails still show the plain cup until the file is re-saved in Bambu.
8. **Log** a row below.

## Options

| Option | Effect |
|---|---|
| `--height-mm 70` / `--width-mm 50` | Art size (one of the two; aspect is kept) |
| `--align center\|top` | Center in free band (default) or top at the rim gap |
| `--z-shift 5` / `--u-shift -3` | Nudge up/down, or around the cup (arc mm, + = right when facing the front) |
| `--outline White` | Color that wins overlaps, fills gaps, stands taller |
| `--heights "White=0.8,Navy=0.6"` | Raise per color, mm above the wall |
| `--fill-holes` | Fill holes in the art with the outline color |
| `--target cup\|lid\|both` | Where the art goes (default cup) |
| `--lid-place below\|miss\|through` | Lid placement (default below; through only on request) |
| `--lid-height-mm 35` | Lid art height (default: largest that fits) |
| `--lid-shift "2,-3"` | Nudge lid art right/up (mm, hole = up) |
| `--lid-object cap` | Name substring or object id of the lid (largest single-part match wins) |
| `--object cup` | Name substring of the cup object in the 3MF (largest single-part match wins) |
| `--work DIR` / `--blender EXE` | Work folder, Blender path |
| `--dry-run` | Layout, STLs, previews only |
| `--force` | Overwrite out / add to a cup or lid that already has art |

## Fixing problems

| Problem | Fix |
|---|---|
| "front wall R ... != 41.91" | src already has art (use the base 3MF), or it's a different cup (`--force` only if you're sure; the wrap uses the measured radius) |
| Art runs onto the grip panels | `--width-mm 55` or smaller `--height-mm` |
| Art too close to the spigot / rim | Smaller size, or `--z-shift` |
| A color piece missing or speck-sized | It was under 200 svg px² or thinner than ~3 svg px and got cleaned out. Fix the layer set (SVG Creation `--grow`) |
| Paint bucket bleeds between two colors | Give them different `--heights` (only matters where they touch) |
| "lid face already has inlaid art" | src lid already has art: use the base 3MF |
| Lid art too small below the hole | `--lid-place miss`, or ask the user if the hole may go through the art (`through`) |
| Lid boolean leaves an empty lid | Cutter must be one clean outline (the tool unions all colors); check the art has no zero-width slivers |
| Bambu: "N non-manifold edges" + "reversed faces" on the cup (after painting) | Bambu welds the coincident vertices where two same-height color shells touch, so those edges get 4 faces. Fix without losing paint: `python -I <work>\split_nm.py "<painted>.3mf" "<out>.3mf" 3D/Objects/object_21.model "<folder with per-color STLs>"`. It gives each shell its own copy of those vertices; triangles, order and paint stay the same. Bambu re-centers the mesh on save, so set the STL y offset in the script (base vs painted first vertex; Stitch: +0.4001). Check with `mesh_check.py`. Example in `NewCupProject\Happy Blue Creature\work\` |
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
| 2026-11-01 | `Projects\SVG\Providence\Drafts\Providence_v1` | `NewCupProject\Final\Providence Coozie Cup - Final.3mf` | 48.7×70 mm, centered (37.9–107.9 mm from bottom), White 0.8 / Pink, Navy 0.6. Done by hand (`NewCupProject\ProvidenceCup\Scripts`) before this tool; tool reproduces it |
| 2026-11-08 | `Projects\Cup\Stitch\SVGs\Drafts\Stitch_v1` | `NewCupProject\Happy Blue Creature\Happy Blue Creature Cup.3mf` | 55.1×70 mm, centered (37.9–107.9 mm from bottom), Black 0.8 / 8 others 0.6, nonmanifold 0. Folder laid out flat like `GrinchCup` (user request) |
| 2026-11-09 | `Projects\Cup\Stitch\SVGs\Drafts\Stitch_v2` (Santa hat) | `NewCupProject\Happy Blue Creature\Happy Blue Creature Cup.3mf` (overwritten in place) | 59.5×59.15 mm (70.4 wide too wide for grips), centered (43.3–102.5 mm from bottom), outline DarkBlue 0.8 / 6 others 0.6, nonmanifold 0. v1 STLs/previews → `work\v1\`, run files `work\v2\` |
| 2026-11-10 | `Stitch_v2` (re-done SVGs, black outline) | `NewCupProject\Happy Blue Creature\Happy Blue Creature Cup.3mf` (overwritten; src = that 3MF, plain cup + painted cap; run files `work\v2b\`) | 59.5×59.15 mm, 43.3–102.45 mm from bottom, Black 0.8 / 6 others 0.6, nonmanifold 0, cap paint kept |

Add a row per cup.
