# Laces

Started 2026-11-04. Workflow: D:\gimp-mcp\Projects\Workflow\SVG Creation\SVG_Creation_Workflow.md

## Goal
- What it's for: lace shapes per view, for building laces in Blender (D:\Blenderlender-mcp\Projects\Glove)
- Size: 101.6 mm tall canvas, loop included (Project.md). Width follows each view
- Colors: Black (laces). Outline = glove reference only, same canvas
- Keep / drop: keep black laces. Drop finger slots, pocket lip, web gap shadows + voids, wrist hole, floor shadow, stitching
- Source: 1536 px copies in Images/ (same renders as Blender Images/, higher res)

## Versions

| Version | Date | What changed | Command |
|---|---|---|---|
| Laces_Front/Back/Left/Right_v1 | 2026-11-04 | First pass: laces + outline, 4 views | `python Scripts\lace_layers.py all` |

## Final

2026-11-04: Laces_Front, Laces_Back, Laces_Left, Laces_Right from their `_v1` drafts -> `Final\`. Kept: index-side black strip, tab under loop. Removed: dark areas behind webbing (gaps).
