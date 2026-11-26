# ChristmasOhana

Started 2026-11-09. Workflow: G:\gimp-mcp\Projects\Workflow\SVG Creation\SVG_Creation_Workflow.md

## Goal
- What it's for: cup art (Christmas Ohana lettering); copy also in XmasOhana\Drafts
- Size: 70 mm tall (88.1 x 70)
- Colors: Red, Green (flat)
- Keep / drop: all; flattened from Glossy Christmas Ohana Typography.png

## Versions

| Version | Date | What changed | Command |
|---|---|---|---|
| v1 | 2026-11-09 | original "Christmas" text, flat Red/Green, 88.1x70 mm (`make_xmas_image.py --keep-text`) | `python image_to_layers.py "Images\Christmas Ohana Typography Flat.png" Drafts\ChristmasOhana_v1 --name ChristmasOhana --colors "Red=#DE1010,Green=#188C28" --height-mm 70 --bg alpha --keep all --min-blob 400` |
| MerryStitchmas v1 | 2026-11-10 | "Merry Stitchmas" retro lettering + snowflake/swashes, flat Red/Green, 70 mm tall | `python image_to_layers.py "Images\Merry Stitchmas Retro Holiday Lettering.png" Drafts\MerryStitchmas_v1 --name MerryStitchmas --colors "Red=#E00808,Green=#03911D" --height-mm 70 --bg color --keep all --min-blob 400 --cut-white 30 --debug Drafts\MerryStitchmas_v1\_labels.png` (first run filled letter counters green -> added `--cut-white`) |

## Final

