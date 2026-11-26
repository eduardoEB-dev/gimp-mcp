# Providence

Started 2026-11-01. Workflow: G:\gimp-mcp\Projects\Workflow\SVG Creation\SVG_Creation_Workflow.md

## Goal
- What it's for: Providence "P" logo, multi-color Bambu print
- Size: 70 mm tall (default) -> 48.8 x 70 mm
- Colors: Pink, White, Navy
- Keep / drop: whole logo; drop white sticker halo baked into PNG (Scripts/strip_halo.py -> Images/Providence_clean.png); P counter left open (hole)

## Versions

| Version | Date | What changed | Command |
|---|---|---|---|
| v1 | 2026-11-01 | first build; halo stripped, White grown 1px for 0.4mm line | `python Scripts/strip_halo.py "Images/Providnce Logo.png" Images/Providence_clean.png` then `python image_to_layers.py Images/Providence_clean.png Drafts/Providence_v1 --name Providence --bg alpha --colors "Pink=#E266A6,White=#FFFFFF,Navy=#183668" --grow "White=1" --height-mm 70` |

## Final

