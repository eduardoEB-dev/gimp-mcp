# TryCatch Designs: SVG Cup Repair Workflow

**For Qwen and other agents.** Use this workflow when either of these happens:
- **Bambu Studio** warns about a cup 3MF: *"N non-manifold edges"*, *"reversed faces detected"*, *"may affect rendering"*.
- **`cup_append.py`** stopped with `3MF validation FAIL`.

This is its own task, in its own session. You don't need the SVG Cup Append doc, the SVGs or the `.py` sources. Everything you need is below.

**Default: diagnose, plan, stop.** Run the read-only steps 1–4, report, propose a fix, then **stop for review**. Don't edit scripts, SVGs, layer sets or Final files, and don't write a repaired 3MF, unless the user approved that specific fix in this session.

## Inputs from the user

One of:
- **A 3MF that Bambu warns about** (usually a Final, often painted and re-saved). The work folder is optional.
- **A failed append:** its work folder. `<work>\Work\<Name>_cup_mesh.json` is the decal mesh that went into the 3MF. The failed 3MF itself isn't kept.

## Small-context rules

- **Checkpoint.** Keep `<repair>\CHECKPOINT.md`, where `<repair>` = `<work>\repair\` (or `<3MF folder>\repair_<file stem>\` when there's no work folder). Update it after every step. After a compaction, read it first and continue from **Next command**. Don't re-read files to rebuild your state.
- **Use the tools, don't write analysis scripts.** `validate_3mf.py` says *which mesh* is bad. `diagnose_shells.py` says *which shells* and *what kind*. Don't analyze STLs or SVGs.
- **Read verdict lines,** not full output. Keep each command's output short.

```markdown
# REPAIR CHECKPOINT (<file>, <date>)
Target: <3MF path>   Work: <work folder or none>   Painted: <n tris / no>
Validator: <member> <defect counts>
Diagnose: <n bad shells, verdicts, colors>
Case: <row from step 4>
Next command: <exact command or "report to user and stop">
```

## Tools

Run from this folder (`G:\gimp-mcp\Projects\Workflow\SVG Cup Repair\`) with `python -I` (3.11 + numpy). The validator lives in the append folder. No Blender needed for steps 1–4.

| Command | Output |
|---|---|
| `"..\SVG Cup Append\validate_3mf.py" "<file.3mf>"` | One line per mesh with defect counts, then `PASS` / `FAIL`. Exit 0 / 1 / 2 |
| `diagnose_shells.py "<file.3mf>" --member <member>` | Header with `painted_tris=N`, one line per bad shell (tris, volume, open / 3plus / repeated edges, bbox, verdict). About 5 s on a cup |
| `diagnose_shells.py "<work>\Work\<Name>_cup_mesh.json"` | Same, for the decal only (no cup body). Color shows `?` unless the JSON has color ranges |

## Steps

1. **Validate the target 3MF** (failed append: there's no 3MF, go to step 2 with the mesh JSON). Note the member(s) with defects. The cup is usually `3D/Objects/object_21.model`; Bambu may rename it. PASS while Bambu still warns → report that the stored mesh is clean, ask which object Bambu flags, stop.
2. **Diagnose that member** with `--member`. Note `painted_tris` and each bad shell's verdict.
3. **Find the matching append run** (needed for rebuilds):
   - The file's row in the **Log** table at the end of `G:\gimp-mcp\Projects\Workflow\SVG Cup Append\SVG_Cup_Append_Workflow.md` (layer set, options, work folder).
   - Else **ASK** the user.
   - Work folders are normally `G:\Blender\blender-mcp\Projects\NewCupProject\<Name>Cup\`. Colors: only if the report needs them, match each bad shell's bbox to the per-color STLs in that folder's `STL\`.
4. **Pick the case** from the table, report, propose, **stop**.

| # | Validator | Diagnose | Bambu shows | Meaning | Propose |
|---|---|---|---|---|---|
| A | `nonpositive_volume_shells=N`, rest 0 | all `FLIP-OK` | reversed faces | Closed, consistently wound shells that are inside-out | Exporter winding fix (§A) + fresh append. Painted file: reverse those shells' triangle winding in place, nothing else |
| B | `nonpositive_volume_shells=N` | `ZERO-VOL` | reversed faces | Degenerate speck/flat shell | Don't flip. Raise `--min-area-px` or fix that color in the layer set, then a fresh append |
| C | `edges_with_3plus_faces` (+ `repeated_direction`) > 0, file was **saved by Bambu** | `TOPOLOGY`, one big shell spanning 2+ colors | non-manifold edges | Bambu welded touching color shells at their seams | Unpainted: rebuild (§C1). Painted: seam split (§C2) |
| D | open / 3plus / repeated > 0 in a **fresh append** (mesh JSON) | `TOPOLOGY` | non-manifold edges | Exporter topology bug | Report shells + counts only. Stop |
| E | `degenerate_triangles` > 0 | `0 bad` is normal: diagnose doesn't count zero-area triangles | — | Zero-area triangles from the decal export. Base cup is clean (validates 0); don't blame it | Exporter fix (§E) + fresh append. A vertex split or `--force` can't fix these |
| F | `ERROR` / exit 2 | — | — | Unreadable/empty mesh | Report message; check the file is a complete 3MF. Stop |

**Report contents:**
- target file, member, validator line, `painted_tris`
- a table of bad shells: color, tris, volume, edge counts, bbox, verdict
- the case letter
- **measured vs hypothesis:** what the tools printed is measured; why it happened is a hypothesis
- the proposed fix and how it will be verified
- the work folder

## Fixes (only after approval)

Write every candidate into `<repair>\`, never over the target. Keep the target untouched until the final publish step.

### A. Inside-out shells (winding)

- **Exporter fix:** at the indexed export (end of `cup_decal_blender.py` / `indexed_mesh_blender.py`), on the exact triangles from `mesh.calc_loop_triangles()`:
  - Group triangles by shared vertex indices (`validate_3mf.shell_ids`).
  - Swap two indices of every triangle in a shell only if it's closed, consistently wound and strictly negative.
  - Print color, tris and volume before → after for each flipped shell.
  - Don't add a triangulation pass or edit STLs.
- **Hypothesis to confirm first:** `cup_decal_blender.py:60` takes the sign from the first 3 vertices of each face, but extrusion adds quads. Compare that estimate with the diagnose volume for the failing shells.
- **Then:** fresh append with the original options (Log row), a new `--work` and a candidate out.
- **Painted file instead:** reverse only the `first_tri`.. shell triangles' `v2`/`v3` in that member. Keep the order and all paint attributes.

### E. Zero-area triangles (exporter)

- **Hypothesis (Woodstock 2026-11-27, measured 88):** pixel-staircase SVGs (`M x,y L ... Z` 1-px rectangles) leave vertices in a line where `cup_decal_blender.py`'s 0.6 mm `bisect_plane` cuts land on straight edges. `triangulate(BEAUTY)` then makes zero-area triangles.
- **Exporter fix** in `cup_decal_blender.py`, right after `bmesh.ops.triangulate(...)`: loop up to 5×. Stop when no face has `calc_area() < 1e-12`. Otherwise run `bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])`, then re-triangulate the faces with more than 3 verts (BEAUTY). Print the count left (must be 0).
- **Test before the workflow copy:** copy `cup_decal_blender.py` + `indexed_mesh_blender.py` into `<repair>\`, patch the copy, and run it with Blender on `<work>\Work\<Name>_tris.json` + `cup_preview.stl` into `<repair>\t\`. Pass = each decal `nonmanifold 0`, zero-area left 0, and `diagnose_shells.py` on the new mesh JSON shows 0 bad.
- **Then:** the user approves the workflow edit, followed by a fresh append with the Log-row options and a new `--work`.
- **Status:** applied to `cup_decal_blender.py` on 2026-11-27 (prints `zero-area left 0` per color). If E shows up again with that line in the output, report it as a new case.
- **Copying workflow scripts into `<repair>\`:** use `python -I G:/gimp-mcp/Scripts/wf_fetch.py --why "<reason>" "<repair>\app" "<workflow file>" ...`. **Always tell the user which files you're copying and why, and report the `COPY ... WHY:` and `OK` lines.** Keep the reason free of the words *copy, move, del, ren* (e.g. "model", "current"): with "Workflow" in the same command they trip a deny rule. It prints `OK <name> <hash>` per file and refuses any destination inside a workflow folder. Never use `Copy-Item`/`copy` on workflow paths (denied), and don't copy by reading and rewriting with file tools (big files get truncated).

### C1. Welded seams, unpainted → rebuild

Rerun the original append (options from the Log row) with the clean base as src, a new `--work` and a candidate out. Compare previews, size, triangle counts and the `relief r` line with the original. If the user re-saves in Bambu, validate that save again (it may weld again; then go to C2 after painting).

### C2. Welded seams, painted → seam split

- Split welded seam vertices so each color shell gets its own vertices again. Map triangles back to color shells using the matching run's `*_cup_mesh.json` (exact positions + winding).
- Reference: `G:\Blender\blender-mcp\Projects\NewCupProject\Happy Blue Creature\work\split_nm.py` (glob/offset are job-specific; used for Spurs v3 and Spurs V2).
- Keep triangle order, winding and paint attributes. Add only new vertices and change only indices.
- An ambiguous match, poor coverage or any new defect means: discard the candidate, report, and **ASK** whether a rebuild + repaint is OK. Don't guess face pairs edge by edge along chained seams.

## Verify every candidate

- `validate_3mf.py "<candidate>"` exits 0 (all meshes).
- `diagnose_shells.py` on the repaired member reports 0 bad shells.
- Winding fix: same vertices, same triangle sets, order reversed only in the flagged shells. Seam split: same per-triangle positions, order, winding and paint.
- Other archive members byte-identical (compare from the ZIPs).
- New XML elements use the core namespace, with zero-based `v1`/`v2`/`v3`.
- Previews unchanged (rebuilds).

## Publish (only when the user asks)

- Back up the target and verify the backup matches by hash.
- Stage the candidate next to the target and replace it atomically.
- Validate the final path. The user reopens it in Bambu and checks the warning is gone, the paint and the slice (pending if unavailable).
- Add a row to the Log table in `G:\gimp-mcp\Projects\Workflow\SVG Cup Append\SVG_Cup_Append_Workflow.md`.

## Known cases

| Case | File | Result |
|---|---|---|
| A | Spurs v4 append (`NewCupProject\Spurs_v4Cup_fresh`, `Spurs_v4Cup`) | 3 FLIP-OK shells: Black 120, Black 60, White 8 tris. Exporter fix pending review |
| C2 | Spurs v3 Color Final, Spurs V2 Final | 55 / several welded seam edges → `split_nm.py` → 0 defects |
| E | Woodstock append (`NewCupProject\WoodstockCup`, fix tested in `WoodstockCup\repair\`) | 88 zero-area tris from a pixel-staircase SVG → §E exporter fix → fresh append `WoodstockCup_v2` PASS |
| C | Spurs BW Final (`NewCupProject\Final\Spurs BW Cooler Cup - Final.3mf`) | 290 3plus edges, 1 TOPOLOGY shell, painted 46,883 tris; repaired copies exist in that folder |
