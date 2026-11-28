# TryCatch Designs: Ad Render Workflow

**For Claude:** the user will give you this file, a Bambu Studio `.3mf`, an **output path**, and any specifics. Generate the ad renders (with the logo) without being asked. Stop and ask only where a step says **ASK**. Afterwards, the renders usually go into the 3MF through `..\3MF_Release\3MF_Release_Workflow.md`.

## Core rule: it must look like a real 3D print

These are ads for 3D-printed models. Every render must read as a physical FDM print, not a smooth CG model: visible 0.2 mm layer lines (slightly uneven), matte PLA finish, real filament colors. `render_3mf.py` does this by default (layer-line bump + per-layer roughness). Check a full-size crop every run; if lines aren't visible, raise `"layer_lines"` in the spec (default 1.0).

## Inputs from the user

1. The `.3mf` file.
2. **Output path.** If it isn't given, **ASK**. The past convention was `G:\gimp-mcp\Projects\Cup\Ad Images\<Name>\`.
3. Optional specifics: which cups or caps to show, which shots to skip, and whether to include a straight-back shot.

## What gets created under the output path

```
<output>\
  Work\              manifest.json (what was found in the 3MF), shots.json (shot plan), meshes (npz)
  Renders\test\      quick 400px previews + contact_sheet.png
  Renders\layers\    <shot>_fg.png (sharp product) + <shot>_bg.png (blurred set)
  Renders\no_logo\   final renders without the logo
  Drafts\            final renders WITH the logo card (<shot>_logo.png) + contact_sheet.png
  Drafts\stale\      drafts from older runs whose shot is no longer planned (moved, never deleted)
```

## Tools (all in `G:\gimp-mcp\Projects\Workflow\Renders\`)

| File | Role |
|---|---|
| `run_renders.py` | **Entry point.** Extracts the 3MF, plans the shots, renders, composites and adds the logo. |
| `extract_3mf.py` | Reads the 3MF: meshes, object extruders, painted triangles and filament colors. Classifies each object as cup, cap, handle, pin, spigot or other. |
| `render_3mf.py` | Builds the cup rigs from the extracted 3MF and renders one shot and one layer per call. |
| `scene_env.py` | Shared set: PLA material with layer lines, the `christmas` / `seuss` / `desk` themes, camera and fg/bg layer render. Used by `render_3mf.py` and `render_blend.py`. |
| `run_blend.py` + `render_blend.py` | **Entry point for assembled multi-part models** (see below): geometry and pose from a `.blend`, colors from the 3MF. |
| `comp.py` | Puts the sharp product layer over the blurred background, so the product is never blurry. |
| `make_screen.py` | Code-editor image for the `desk` theme's monitor (dark theme, syntax colors, no app branding). |
| `brand.py` | Adds the logo card at the bottom right. Logo path and size are at the top of the file. `--pos tr\|tl\|bl` moves it, `--frac` resizes it (e.g. `--pos tr --frac 0.21` keeps it off a tall product). Photos get EXIF-rotated. |
| `sharpen.py` | Real photos: sharpens a soft-focus bottom (e.g. couch under the Cat in the Hat balloon), feathered so the top is untouched. Run before `brand.py`. |
| `make_assets.py` + `assets\` | Handle, pin and spigot geometry already assembled in the cup frame, taken from `New_Cup_Solid_Half_BLU.blend`. Re-run only if that hardware's design changes. |

Requirements: Blender 5.1 at `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe` (NVIDIA OptiX GPU), and Python 3.11 with numpy and Pillow. Always run the Python scripts with `python -I`.

## Steps

1. **Test pass** (about 1–2 minutes):
   ```
   python -I run_renders.py "<file.3mf>" "<output>" --test
   ```
   Read the printed `cups:` / `caps:` / `shots:` lines, then **look at** `Renders\test\contact_sheet.png`. Check:
   - Colors match the 3MF. Paint and filament colors are read from the file, so ribs, text and art should already be right.
   - Cap text reads the right way up from the front. If it's upside down, set `"cap_rot_deg": 0` in a spec file.
   - Nothing is cropped, and the right cups and caps are in each shot.

   Show the user the contact sheet and the shot list. If anything looks wrong, or the cup/cap choice is ambiguous, **ASK**.
2. **Final pass** (about 30–45 s per shot at 64–96 samples: 6 shots ≈ 3 min, 8 shots with pairs ≈ 5.5 min; give the command a 600000 ms timeout or run it in the background):
   ```
   python -I run_renders.py "<file.3mf>" "<output>" [--spec spec.json]
   ```
3. **Verify.** Look at `Drafts\contact_sheet.png` and at least one full-size crop. The product must be sharp. If it's blurry, the fg/bg composite was skipped.
4. **Report.** Give the paths, the list of shots, and anything odd you noticed.
5. **Hand off.** If the user wants the renders in the 3MF, follow `..\3MF_Release\3MF_Release_Workflow.md` and pass the `Drafts\*_logo.png` images with the hero first: `pair_hero`, or `hero_*` when there's only one cup.

## Automatic shot plan

| Situation | Shots |
|---|---|
| 2 or more distinct cups | `pair_hero` (side by side, handles folded back), `pair_front`, plus `hero_<cup>` for each cup |
| 1 cup, several caps | `hero_<cap>` for each cap on that cup, plus `front` |
| 1 cup, 1 cap | `hero_<cup>`, plus `front` |
| Always | `left`, `right`, `back_three_q` (angled back), `caps_top` (all caps on the table) |
| Optional | `back` (straight back, handle folded forward), only with `"back": true` |

How it decides:
- **Duplicate cups:** objects with the same name, such as the standard and 5-color plates, count as one cup. The variant with the most colors wins.
  - **Pitfall:** two cups with the same mesh name but different body filaments (Spurs Color Painted: `cup` pink + `cup_2` navy, both `cup.stl`) also merge, so `cups:` shows one cup and there are no `pair_*` shots. If the extract lists `cup` and `cup_2` but `cups:` shows one, set `"cups": ["cup", "cup_2"]` in the spec.
- **Cap per cup:** cup *i* gets cap *i* in rotation.

The framing (camera distance and angles) was tuned on the Grinch and Snoopy releases.

## Optional spec file (JSON)

Pass any of these keys with `--spec`:

```json
{
  "cups": ["snoopy_cup", "snoopy_cup_x_mas_2"],
  "caps": ["cap"],
  "cap_for": {"snoopy_cup": "cap"},
  "skip": ["back_three_q"],
  "back": true,
  "cap_rot_deg": 180,
  "caps_top_rot": 30,
  "samples": 256,
  "res": 2000,
  "theme": "christmas",
  "layer_lines": 1.0,
  "frame_scale": 1.3,
  "extra_shots": []
}
```

- `theme`: scene set. `christmas` (default: green wall, dark wood, gold/red bokeh, red ornaments) or `seuss` (sky-blue wall, light wood, candy-colored bokeh, book stack, popcorn spilled on the table), or `desk` (maker's desk modeled on the user's setup: clean grey desk, curved ultrawide monitor showing real syntax-colored code, sage wall; fits "From Code to 3D Models"; used for the popcorn bucket). For `desk`, `"screen_code": ["a.py", "b.py"]` picks the files shown on the monitor (one per editor pane; default `render_3mf.py`), rendered by `make_screen.py`. Use `"frame_scale"` about 1.2 for desk shots so the product is big in frame and the blurred code still shows. No keyboard or mouse: the user rejected simple box/blob versions as fake-looking. Keep the product big in every shot. Match it to the product, and **ASK** if unsure. Never use Christmas for non-holiday items.
- `basketball` theme: maple boards, painted court markings, a hoop and arena seating.
- `tabletop` theme: warm wood table, muted green wall, and soft window lighting.
- `layer_lines`: layer-line strength multiplier (realism).
- `post_extract`: path of a render-only recolor/decal script, run as `python -I <script> <Work>` right after extraction. It may rewrite `manifest.json` filaments/extruders and the `obj<id>.npz` meshes (`v`, `f`, per-tri `p`). Use it when the 3MF isn't colored yet. Example: `G:\gimp-mcp\Projects\Spurs\Render\recolor_spurs.py`, which fits an SVG's colors onto the cup relief and subdivides the region so color edges stay smooth.
- `logo_pos` and `logo_frac`: optional logo card corner (`br`, `bl`, `tr`, `tl`) and width fraction for the full 3MF render set.
- `frame_scale`: camera distance multiplier. Default is automatic: item height / 130 mm (cooler cup), never below 1.
- `extra_shots` are not scaled; give `dist`/`tz` in meters. Example (popcorn bucket, looking inside):
  `{"name":"top_inside","rigs":[{"cup":"<label>","cap":null}],"az":-20,"el":48,"dist":0.85,"tz":0.08}`

Labels come from `Work\manifest.json`, which the test pass prints. Cups are named after the object, caps after their plate (or just `cap` when there's only one). Use `--only shot1,shot2` to re-render particular shots.

**Re-running a product from a new 3MF** (e.g. `... - Final - Painted.3mf`):
- The old `spec.json` in the output folder was made for the old 3MF. Its labels (`woodstock_cup`, `pin1`, `spout`), `source_hardware`, `cup_rot_deg`/`cap_face_up` and `post_extract` may not fit. Never overwrite it: write a new spec next to it (e.g. `spec_painted.json`) with only the keys that still apply, and check every label against the extract's printed object list.
- A painted 3MF already holds its colors: drop `post_extract` (a recolor script would paint over the real paint).
- `cap_rot_deg` can change between 3MFs of the same product (Woodstock: old lid -90, Painted lid 0). Check the lid art in the test pass every time.
- Re-running into the same output folder replaces drafts with the same shot names. A full final run (no `--only`) moves drafts whose shot is no longer planned (e.g. `hero_woodstock_cup_logo.png` after the shot became `hero_cup`) into `Drafts\stale\` and prints `STALE <file>` for each, so expect those lines in the final-pass output. `--only` moves nothing. For a folder rendered before this change, run `python -I G:\gimp-mcp\Scripts\move_stale_drafts.py "<output>"`. Hand off only `Drafts\*_logo.png`, never `stale\`.

- `cup_rot_deg` aligns a cup's front with the rig. For lids stored upright in the 3MF, use `cap_face_up: true`. `cap_rot_deg` controls the artwork direction and `cap_scale` applies a uniform scale.
- `source_hardware` can use the model's own meshes for `Handle`, `Pin`, `Pin2`, and `Spigot`. Each entry specifies an `object` label from the manifest, `offset` in millimeters, optional Z `rot` in degrees, and optional uniform `scale`. Handle offsets are relative to its pivot. The other offsets are in the cup rig frame.

## Assembled models from a .blend

A multi-part model is laid out in the 3MF as plates, not as the assembled model. When the user has a `.blend` with the parts assembled (in mm), render from that instead:

```
python -I run_blend.py "<model.blend>" "<file.3mf>" "<output>" --spec spec.json [--test] [--only shot1,shot2]
```

`--plan` stops after writing `Work\blend_shots.json` (part colors), with no renders. `..\Manual Creation\run_manual.py` uses it.

- **Parts:** every mesh except hidden-from-render objects, names containing `Proxy`, and `"exclude_collections"` / `"exclude"` in the spec. The blend needs no materials.
- **Colors:** each part is matched by name to a 3MF object, which gives its extruder and filament. Match on the name minus the number prefix and `upsidedown`/`bottom`, so `Ring1_TopCap_Red` matches `10_TopCap_Red_upsidedown.stl`. Next comes the trailing color word, then `"assign"` (`{"name prefix": extruder}`, which takes priority). The run prints the mapping, so check it. If a part has no match, the run stops: **ASK** which filament it uses. The 3MF decides the color, not the blend's name (for example, the "Silver" knobs print in brass).
- **Shots:** `hero`, `front`, `left`, `right` and `back_three_q`, all framed to the assembled height. Close-ups go in `"extra_shots"` as `{"name","az","el","frame_mm","tz_mm","center_mm"?,"fstop"?,"layer_lines"?,"exposure"?}` (last two override the spec per shot; close-ups look right at about 1.0 / -0.2):
  - `frame_mm` is the framed height and `tz_mm` is the aim height.
  - `center_mm` is the `[x, y]` of the detail in blend mm. It moves that detail onto the turntable axis so it's in focus. Without it, a close-up of a part away from the center comes out soft.
- Extra spec keys:
  - `"exposure"`: AgX exposure (default 0.1). Tall white/red models blew out at 0.1, and the Cat in the Hat uses -0.6.
  - `"fstop"`: default aperture. Tall models put the camera farther back, so the set barely blurs at f/4.5. Open up (f/1.8) to match the popcorn's blurred code.
  - `"popcorn": 0` turns off the seuss popcorn.
  - `"logo"`: `{"<shot>": ["tr", 0.26]}` sets the logo corner/size per shot (default `br`, 0.34). The default card covers the base of tall models; top corners are usually empty bokeh. Check that it clears the product.
  - `"candle"`: render-only 3-wick jar candle (no label) on the product, e.g. a candle holder: `{"center_mm":[x,y],"z_mm":215,"d_mm":102,"h_mm":95,"jar":"#FFE11A","wax":"#FFF0A0","jar_glow":0.35,"lit":true,"flame":22,"flame_r":3.8,"light_w":0.6}`. It is added to the framed height. Example: `G:\gimp-mcp\Projects\SnoopyCandle\spec_candle.json`.
  - `"light_tz"`: the height the lights aim at (default 0.45 × the model's height).
  - `"extra_filaments"`: render-only colors not in the 3MF, e.g. `["#2E9E3F"]`. Assign them in `"assign"` as the next extruder (a 3-filament 3MF's first extra is 4).
  - `"fuzzy"`: part-name prefixes printed with Bambu fuzzy skin, e.g. `["PlushDog", "PlushArm", "PlushFeet", "HatCuff"]`. They get a grainy, more matte material (`scene_env.fuzzy`). `"fuzzy_strength"` scales the bump (default 1.0; Olaf used 1.3). **ASK** which parts are fuzzy if the print notes mention fuzzy skin.
  - Name matching uses 3MF **object** names. When the blend names match the 3MF **part** (volume) names instead (e.g. `PlushDog` inside object `Body`), set `"assign"` from the part extruders.
  - `desk` + `"screen_code"` work as in `run_renders.py`. The monitor's file tree lists the folder of the first code file.
- Same output layout as `run_renders.py`. Example: `G:\gimp-mcp\Projects\CatInHat\spec.json`.
- Give `<output>` as an **absolute** path. A relative one breaks the `desk` monitor image (Blender can't find `Work\code_screen.png`).
- **3MF-only parts (SVG relief, text, paint):** the blend gives each part one color, so Bambu SVG/text parts and painted borders added in the 3MF are lost. Build a render blend first: take the 3MF object's parts (paint decoded), split them per extruder into `<Piece>_e<n>` meshes, fit each into the blend pose (known print rotation + bbox center of the base part), then map them with `"assign"`. Example: `G:\gimp-mcp\Projects\13 Chime\prep_render_blend.py` (also swaps the name text for a new name in the same font/size).

## Limits and known behavior

- The assembly is built for the **cooler-cup family**: the cup, the cap on top, and the BLU-blend handle, pins and spigot. Hardware is only added if the 3MF has handle/pin/spigot objects, so any single tall object (>90 mm) without caps renders as a lone "cup" (worked for the popcorn bucket). For multi-part products, use **Assembled models from a .blend** above. If there's no assembled blend, **ASK** before improvising.
- Pure white filament renders as a light grey, and pure black as a near-black, so neither clips.
- The black base model renders entirely black because that's what the 3MF says. If it's meant to show a different color, the user has to change the filament in the 3MF.
- Scene themes live in the environment section of `render_3mf.py` (`THEME` branches). For a new theme, add a branch there and list it under `theme` above.
- Painted colors are decoded from Bambu's full paint subdivision tree, so band edges are smooth. The old shortcut (one color per whole triangle) made sawtooth edges on big triangles, which showed inside the popcorn bucket.

## Release log

| Date | 3MF | Output |
|---|---|---|
| 2026-10-21 | Grinch Cup | `G:\gimp-mcp\Projects\Cup\Ad Images\Drafts\` (built by hand, before this workflow existed) |
| 2026-10-22 | Snoopy Cup Project | `G:\gimp-mcp\Projects\Cup\Ad Images\Snoopy\` (built by hand, before this workflow existed) |
| 2026-10-27 | Workflow verified on Grinch, Snoopy and Cooler Cup base (test pass) | scratch only |
| 2026-10-27 | Cat in Hat Popcorn Bucket (`PopcornBucket_A1mini_Optimized.3mf`); added layer-line realism, auto frame scale, `top_inside` shot, `seuss` + `desk` themes (final: `desk`), full paint decoding | `G:\gimp-mcp\Projects\PopCorn\` (spec.json there) |
| 2026-10-29 | Cat in the Hat Hot Air Balloon (`... - Final_flatbrim.3mf` + `CanInHatCouch.blend`); added `run_blend.py`/`render_blend.py`, split the set into `scene_env.py` (regression-checked: identical popcorn render) | `G:\gimp-mcp\Projects\CatInHat\` (spec.json there) |
| 2026-10-30 | 13 Chime trophy (`13Chime_Clock_x2d.3mf` + `13Chime.blend`); 3MF SVG/text/paint parts mapped onto blend via `prep_render_blend.py`, name "David", desk theme, close-ups, `layer_lines` 0 (user rejected the ridges) | `G:\gimp-mcp\Projects\13 Chime\` (spec.json there) |
| 2026-11-01 | Snoopy Candle Holder (`SnoopyCandleHolder_A1Mini_optimized.3mf` + `SnoopyCandle_V3.blend`); christmas theme, `bowl_top` + `face_detail` close-ups; fixed `render_blend.py` stale `matrix_world` on appended parts (bowl rendered at z=0) | `G:\gimp-mcp\Projects\SnoopyCandle\` (spec.json there) |
| 2026-11-01 | Snoopy Candle Holder, candle version (`spec_candle.json`, `candle` prop: lit 3-wick jar in bowl pocket, `candle_top` + `upper_detail` close-ups) | `G:\gimp-mcp\Projects\SnoopyCandle\Candle\` |
| 2026-11-03 | Snoopy Candle Holder, grass base mockup (`prep_grass_blend.py` builds render-only base + render blend, `extra_filaments`, `base_detail` close-up) | `G:\gimp-mcp\Projects\SnoopyCandle\GrassBase\` |
| 2026-11-03 | Snoopy Candle Holder, printable grass base (`SnoopyCandleHolder_A1Mini_optimized.3mf` + `SnoopyCandle_V3.blend`, `GrassBase` from the user's blend, plate 6 green) | `G:\gimp-mcp\Projects\SnoopyCandle\GrassBlades\` (spec_blades.json there) |
| 2026-11-10 | Snoopy Candle, snowy base: real photos cut out (birefnet onnx in `~\.rembg\models`) + regraded onto christmas `hero_bg.png`, via `SnoopyCandle\Snowy\photo_comp.py` | `G:\gimp-mcp\Projects\SnoopyCandle\Drafts\snowy_*_logo.png` |
| 2026-11-10 | Snoopy Candle, snow base renders (`SnoopyCandle_V4.blend` + original `SnoopyCandleHolder_A1Mini_optimized.3mf`; SnowBase 3MF only holds the base). V4 parts assigned: `EyeL_p/EyeR_p/Mouth_bent_preview`=3, `SnowBase`=1, exclude `Mouth_p` (flat print copy) | `G:\gimp-mcp\Projects\SnoopyCandle\SnowBase\` (spec_snow.json there) |
| 2026-11-10 | Happy Blue Creature Cup + Grinch variant (two separate sets, same 2 caps), christmas theme, `layer_lines` 0 | `G:\gimp-mcp\Projects\Cup\Ad Images\Happy Blue Creature\Standard\` + `\Grinch\` (spec.json in parent) |
| 2026-11-15 | Olaf candle holder (`OlafCandleHolder_X2D_optimized.3mf` + `SnoopyCandle_V4.blend`); christmas theme, `fuzzy` option added (body/arms/feet/hat cuff), `extract_3mf.py` now reads inline meshes (no `p:path`); hat = `_SC_Rest`, brim = `_SC_Piece`, ref collections excluded. Candle version: pocket center found by circle-fitting raycast hits on the pocket wall (r 53 mm at (234.3, 2.7)); a bbox/floor-span guess was 9 mm off and the jar poked through the hat front | `G:\gimp-mcp\Projects\SnoopyCandle\Olaf\` (spec_olaf.json) + `\Olaf\Candle\` (spec_olaf_candle.json) |

Add a row after each run.
