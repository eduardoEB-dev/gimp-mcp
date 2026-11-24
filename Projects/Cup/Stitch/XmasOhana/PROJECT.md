# XmasOhana

Started 2026-11-09. Workflow: D:\gimp-mcp\Projects\Workflow\SVG Creation\SVG_Creation_Workflow.md

## Goal
- What it's for: cup art (X-mas Ohana lettering)
- Size: 70 mm tall (85.3 x 70), default
- Colors: Red, Green (flat, no gloss shading per user)
- Keep / drop: all lettering + swash + snowflake. Source = `Glossy Christmas Ohana Typography.png`, 'Christ' replaced by Script MT Bold X + hyphen, 'mas' reused (`Scripts\make_xmas_image.py` -> `Images\Xmas Ohana Typography.png`)

## Versions

| Version | Date | What changed | Command |
|---|---|---|---|
| ChristmasOhana_v1 | 2026-11-09 | original "Christmas" text, flat Red/Green, 88.1x70 mm (`make_xmas_image.py --keep-text`) | `python image_to_layers.py "Images\Christmas Ohana Typography Flat.png" Drafts\ChristmasOhana_v1 --name ChristmasOhana --colors "Red=#DE1010,Green=#188C28" --height-mm 70 --bg alpha --keep all --min-blob 400` |
| v1 | 2026-11-09 | 2 flat colors | `python image_to_layers.py "Images\Xmas Ohana Typography.png" Drafts\XmasOhana_v1 --name XmasOhana --colors "Red=#DE1010,Green=#188C28" --height-mm 70 --bg alpha --keep all --min-blob 400` |

## Final

