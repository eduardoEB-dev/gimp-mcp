# Capibara

Workflow: [SVG Creation](../Workflow/SVG%20Creation/SVG_Creation_Workflow.md)

## Goal

- What it's for: Standard cup front (`NewCupProject` cooler cup).
- Size: Fit the visible artwork proportionally inside the standard 54 × 72 mm artwork box. Record the resulting dimensions with the sample.
- Colors: Follow the workflow's flat basics rule and preserve distinct intentional feature colors.
- Keep / drop: Keep the character artwork and flatten lighting effects into each feature's base color.

## Versions

| Version | Date | What changed | Command |
|---|---|---|---|
| 1 | 2026-11-26 | Initial SVG build from `Images/Adorable Baby Capybara.png`. 4 colors (Tan, Brown, Brown2, Skin); width-limited to 54 mm → 54.0 × 73.9 mm. | `image_to_layers.py Images/Adorable Baby Capybara.png Drafts --name Capibara --width-mm 54 --bg alpha` |
| 2 | 2026-11-26 | Restored belly cream as its own flat color (Belly `#FCCF9D`), splitting it from Tan; 5 colors; 60.7 × 70.0 mm (width-limited; user accepted size regression vs v1). | `image_to_layers.py "Images/Adorable Baby Capybara.png" Drafts --name Capibara --colors "Tan=#F8B37A,Belly=#FCCF9D,Brown=#BD785F,Brown2=#793B1C,Skin=#FA9872"` |

## Final

- Files: `Final/Capibara_Tan.svg`, `Final/Capibara_Belly.svg`, `Final/Capibara_Brown.svg`, `Final/Capibara_Brown2.svg`, `Final/Capibara_Skin.svg`, `Final/Capibara_AllColors_preview.svg`
- Manifest: `Final/layers.json`
- Dimensions: 60.74 × 70.0 mm (6.74 mm wider than the default cup-front artwork box)
- Colors: 5 — Tan `#F8B37A`, Belly `#FCCF9D`, Brown `#BD785F`, Brown2 `#793B1C`, Skin `#FA9872`
