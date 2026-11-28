# TryCatch Designs: SVG Cup Paint Workflow (color the appended art in Bambu)

**For Qwen and other agents:** the user gives you a **cup 3MF** (made by the SVG Cup Append workflow: art on the cup front, the lid, or both) and this folder. Paint each color of the art with its own filament so it matches the SVG, ready to print in Bambu Studio. Do every step below without being asked. Stop and ask only where a step says **ASK**.

**Never create, edit, move or delete anything in a workflow folder** (`G:\gimp-mcp\Projects\Workflow\` or `G:\Blender\blender-mcp\Projects\Workflows\`). Only run the scripts. If a script prints `ERROR`, report that line and follow the table below; don't patch code. Don't read the `.py` files: this doc says everything they print.

## Tool

Run from `G:\gimp-mcp\Projects\Workflow\SVG Cup Paint\` with `python -I` (3.11; needs `numpy scipy`). No Blender.

```
python -I cup_paint.py "<cup.3mf>" [--slots "White=2,Black=3"] [--body "#FFFFFF"] [--out "<out.3mf>"] [--force]
```

- Finds the append runs that made the art by itself (any folder under `G:\Blender\blender-mcp\Projects\NewCupProject\`, newest first, e.g. `WoodstockCup_v2`; an old failed run of the same art doesn't match, so it's skipped) and prints `cup art: …` / `lid art: …`. Cup and lid art may come from different runs; both are painted in one go.
- **Finds each SVG color among the filaments already in the 3MF, by color, in any order** (exact or close, e.g. `#000000` counts as `#111111`). A white cup body (slot 1) also serves White art. Colors with no match reuse spare filaments nothing else uses (recolored), then need new ones: it stops and prints a table of what to add. The same color on cup and lid shares one slot.
- Paints every art triangle with its color's slot. Geometry is not changed. Handles a cup Bambu re-centered when saving.
- Writes `<cup name> - Painted.3mf` next to the cup. Never overwrites the cup unless the user asks (`--out` = cup + `--force`).
- About 5 s.

## Printer

Decide from the **SVG colors** (the `<Color>` lines the script prints / `layers.json`), not from how many filaments the 3MF already has: a 3MF can carry extra filaments used by other parts (a lid, other plates).

Slots for this cup = SVG colors + 1 for the cup body, or just the SVG colors when the body shares one of them (a white cup body automatically serves White art).

| Slots for this cup | Printer |
|---|---|
| 4 or fewer | X2D or A1 mini |
| more than 4 | **X2D only** (A1 mini holds 4) |

The script prints `WARNING: … needs N filaments but the 3MF is set to … A1 mini` when the printer is wrong: pass that on to the user. It never recolors a slot something else already uses. If a slot it wants is taken (another object's filament or other paint), it stops with `already used by other parts`.

## Steps

1. **Paint.** `python -I cup_paint.py "<cup.3mf>"`. Expect `cup art:` and/or `lid art:`, then one line per color, `<Color>: N/N triangles -> slot S (#hex, existing filament|recolored spare slot|new)` (both numbers equal), then `painted …` and `wrote <path>`. After the user added filaments in Bambu, `recolored spare slot` is normal (the added filament's color wasn't close, so the script set it to the SVG hex), and so is `(re-centered by Bambu, shift …)`.
2. **On `ERROR`**, use this table, then stop:

| ERROR says | Do |
|---|---|
| `needs N (add the **ADD** rows)` | Copy the **Filaments for this cup** table the script printed above the ERROR into your message unchanged (slot, color, hex, RGB, status; keep the `|` and `**ADD**` marks), then **ASK** the user to open the cup 3MF in Bambu Studio, pick the printer (N > 4: X2D; N ≤ 4: X2D or A1 mini, see **Printer**), add a filament for each **ADD** row in any slot order with that hex/RGB color, save, and tell you when done. Then run step 1 again. If they want the A1 mini but N > 4, **ASK** which colors may share a slot and pass `--slots` (e.g. `--slots "Grey=5"` puts Grey on Black's slot 5) |
| `slot(s) [...] are already used by other parts` | **ASK** the user which free slots to use (add more filaments in Bambu if needed), then pass `--slots` |
| `no append work folder … matches` | **ASK** the user for the append work folder (pass `--work "<folder>"`), or whether to re-run the SVG Cup Append workflow |
| `some art triangles not found` | The cup was changed after the append (re-meshed, or a different run). Report it; **ASK** the user |
| `… exists (--force to overwrite)` | **ASK** before replacing it |

3. **Check.** `python -I "..\SVG Cup Append\validate_3mf.py" "<painted.3mf>"`. Expect one line per mesh, then `3MF validation PASS: N mesh(es)` (exit 0; don't run extra commands to check the exit code) (painting doesn't change geometry; a FAIL means the input already had it, so report it).
4. **Report back:** painted file path, the color → slot lines, any WARNING, validator verdict. Tell the user to open it in Bambu Studio and map each filament slot to the spool loaded in the AMS.

## Options

| Option | Effect |
|---|---|
| `--slots "Grey=5,White=2"` | Force slots per color (several colors may share one). Unlisted colors are matched by color |
| `--body "#000000"` | Also set slot 1 (cup body) color |
| `--work "<folder>"` | Append work folder, when it can't be found automatically (repeat for cup + lid runs) |
| `--out "<path>"` / `--force` | Output path / allow replacing an existing file |

## Notes

- The paint is Bambu's per-triangle `paint_color` (slot 1 = `4`, 2 = `8`, 3 = `0C`, 4 = `1C`…). Re-running on an already painted cup repaints the art; the body's paint is left alone.
- Works on a cup Bambu has re-saved: triangles are matched by position, not by order.
- Uses the append runs' `STL\<Name> - <Color>.stl` + `Work\<Name>_tris.json` (cup) and `STL\<Name> Lid - <Color>.stl` + `Work\<Name>_lid_tris.json` (lid). Don't delete an append work folder while its cup may still need painting.
- Art must be geometry made by the append workflow. A Bambu SVG modifier/part added by hand is not painted (Bambu may also ignore its filament when merged into the cap); put lid art on with SVG Cup Append `--target lid` instead.

## Log

| Date | Cup | Result |
|---|---|---|

Write the row in your report; the user adds it.
