# Stitch Santa Onesie

Started 2026-11-08. Workflow: D:\gimp-mcp\Projects\Workflow\SVG Creation\SVG_Creation_Workflow.md

## Goal
- What it's for: cup art (to be appended to a cup 3MF next, SVG Cup Append workflow)
- Size: 70 mm tall (55.1 x 70)
- Colors (9, user-named; >5 AMS, pause to swap): Green, Blue, LightBlue, Pink, Red, White, Black, Yellow, DarkBlue
- Keep / drop: character only, no ground shadow. Mouth: tongue = Red, rest of mouth shading = Black. Gap between hat pompom and brim = transparent (user, 2026-11-08)

## Versions

| Version | Date | What changed | Command |
|---|---|---|---|
| v1 | 2026-11-08 | 9 colors; pale cyan face edges -> LightBlue; hat pompom/brim gap cut transparent | `python image_to_layers.py "Images\Happy Blue Creature in Santa Monster Onesie.png" Drafts\Stitch_v1 --name Stitch --force --height-mm 70 --colors "Green=#72DB52,Blue=#2563C0,LightBlue=#4FA8E6,Pink=#F28EC3,Red=#E0100C,White=#F6F4F2,Black=#080C14,Yellow=#FBF3A0,DarkBlue=#182D63" --map "#FD7380=Red,#F9808E=Red,#4B0811=Black,#5F0F17=Black,#AC0100=Red,#2D8E2E=Green,#88D8F8=LightBlue,#98E8F8=LightBlue,#A8ECFC=LightBlue,#B8F0FF=LightBlue" --island 80 --cut-hole "337,325"` |
| v2 | 2026-11-09 | Festive Blue Monster with Santa Hat.png; 7 colors, 70.4x70 mm; flat basics; outline = Black like v1, pads/nose DarkBlue | `python image_to_layers.py "Images\Festive Blue Monster with Santa Hat.png" Drafts\Stitch_v2 --name Stitch --force --height-mm 70 --colors "Blue=#2563C0,LightBlue=#4FA8E6,Pink=#F28EC3,Red=#E0100C,White=#F6F4F2,Black=#080C14,DarkBlue=#182D63" --map "#246AC4=Blue,#0D1A3A=Black,#33476D=Black,#233462=Black,#C285BB=Pink,#7CCEF5=LightBlue,#479AD5=LightBlue,#EB616B=Red,#F3221F=Red,#BA0506=Red,#B23444=Red,#35070B=Black,#5F0F16=Black,#8D2E36=Black,#6A1525=Black,#0E234D=DarkBlue,#0D2149=DarkBlue,#0E2576=DarkBlue" --grow Black=1 --flat 7 --flat-skip Black --split-thick Black=DarkBlue:6 --island 3500 --island-skip White` |

## Final


Cup: v1 appended 2026-11-08 -> `D:\Blender\blender-mcp\Projects\NewCupProject\Happy Blue Creature\Happy Blue Creature Cup.3mf`
