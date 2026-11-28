# TryCatch Designs: 3MF Release Workflow

**For Claude:** the user will give you this file, a Bambu Studio `.3mf`, and render images. Do every step below without being asked. Stop and ask only where a step says **ASK**.

## Brand details (use exactly)

| Field | Value |
|---|---|
| Designer | **TryCatch Designs** |
| Catchphrase | **From Code to 3D Models** |
| Logo | `G:\gimp-mcp\Projects\Cup\Ad Images\TryCatch Designs_ From Code to Creation.png` |
| Etsy | https://www.etsy.com/shop/TryCatchDesignsShop |
| Cults3D | https://cults3d.com/en/users/trycatchdesigns |
| Patreon | https://www.patreon.com/TryCatchDesigns |
| MakerWorld | https://makerworld.com/en/@TryCatchDesigns |
| Facebook | https://www.facebook.com/profile.php?id=61595400764100 |

If any of these change, update this table **and** `OUR_URLS` / `DESIGNER` at the top of `clean_3mf.py`.

## Inputs from the user

1. The `.3mf` file (any path, e.g. `M:\Custom3D\...` or `G:\Blender\blender-mcp\Projects\...`).
2. Render images (PNG/JPG, any size). **The first image is the hero.** It becomes the cover and thumbnails. If the user doesn't say which one is the hero, **ASK**.
   - **No renders supplied?** Make them first with `G:\gimp-mcp\Projects\Workflow\Renders\Render_Workflow.md`, which needs the 3MF and an output path. Then use the `<output>\Drafts\*_logo.png` images here, with the hero first (`pair_hero` or `hero_*`).
3. Optional: title, description notes, output folder.

## Tool

`G:\gimp-mcp\Projects\Workflow\3MF_Release\clean_3mf.py`. Run it with `python -I` (Python 3.11 with Pillow).

Folder layout (`G:\gimp-mcp\Projects\Workflow\3MF_Release\`):
- `3MF_Release_Workflow.md`: this file.
- `clean_3mf.py`: the cleaner.
- `descriptions\`: one `<name>.html` per release. Save each new description here.

```
python -I clean_3mf.py <src.3mf> <dst.3mf> "<Title>" <description.html> <hero> [more renders...]
```

What it does:
- Removes metadata left by a previous designer: Designer, DesignerUserId, DesignerCover, DesignModelId, DesignProfileId, DesignRegion, ProfileCover, ProfileUserId, ProfileUserName, ProfileDescription, ProfileTitle, Origin, License, and the old Title and Description.
- Sets Title, Designer (TryCatch Designs) and Description. The description is HTML, stored double-escaped the way Bambu Studio stores it, so the links can be clicked.
- Replaces `Auxiliaries/Model Pictures/*` with the renders (1080×1080 webp) and `Auxiliaries/Profile Pictures/*` with the hero (1440×1080). Images are center-cropped; if the aspect is far off (portrait phone photos) the whole image is fitted over a blurred fill instead.
- Writes the three `Auxiliaries/.thumbnails/*.png` files from the hero (4:3), even if the source has none, and points `_rels/.rels` + `Thumbnail_Middle/Small` at them (sources often point at `Metadata/plate_1.png`, the plate preview).
- Leaves geometry, paint, plates and print settings byte-for-byte unchanged.
- Prints a **discrepancy report**: what it removed, unexpected metadata, foreign names or URLs, files that changed when they shouldn't have, and the object and plate lists.

## Steps

1. **Inspect the source.** List its metadata, `Auxiliaries/` contents, plates and objects (the cleaner prints these too). Note any author name, URL or ID that isn't ours.
2. **Inspect the renders.** Look at every image. Check that they match the model in the 3MF: same design, text and colors as the plates. Flag any mismatch (wrong text, missing parts, colors not in the 3MF's filaments) and **ASK** before continuing.
3. **Title.** Use the user's title if given. Otherwise draft one from the plate and object names, and say what you picked. Titles, file names and descriptions are **always generic**: no character, team or brand names (copyright), e.g. "Happy Blue Creature Cooler Cup", "Texas Basketball Team Cooler Cup". Plate names that carry such names don't go in the description either. The cup product is "Cooler Cup", never "Coozie". If no title is given, **ASK** with 3 generic options.
4. **Description.** Write `descriptions\<short-name>.html`, using the template below. Describe only what is actually in the file: the plates, what's printed in which color, and what the variants are. Don't claim "no supports" or "no AMS" unless the user confirms it. Show the user the text.
5. **Run `clean_3mf.py`.** Never overwrite the source or any existing file (the cleaner refuses an existing output). Default output for printer-optimized sources (`*_a1mini_optimized.3mf`, `*_x2d_optimized.3mf`) is `<source folder>\Etsy <Name>\<Title> A1 mini - Etsy.3mf` / `<Title> X2D - Etsy.3mf` (like `Etsy Snoopy\`); otherwise `<source folder>\Etsy <Name>\<Title> - Etsy.3mf`. `<source folder>\Final\<Title> - Final.3mf` collides with the existing finals, so don't use it. The user may name another folder.
6. **Check against previous data.** Read `G:\Blender\blender-mcp\Projects\NewCupProject\Final\*.3mf`, the earlier releases, and compare:
   - Designer and links are identical to the brand table.
   - No leftover foreign names. `animuL67` came in from the base project's print settings, so look for it specifically, and for any new name you find.
   - The plate and object structure looks like a complete project, for example not missing a cap or pins plate that earlier releases had.
   
   Report every difference you find.
7. **Report back.** Give the output path, the title, the description text, the number of pictures, and the discrepancy list (or "none").

## Description template

```html
<p><strong>{Title}</strong></p>
<p>{One or two sentences: what it is, its key design, its colors.}</p>
<p>{Variants, caps or lids, special parts.}</p>
<p>Plates: {plate list}.</p>
<p><strong>TryCatch Designs</strong> &#8212; From Code to 3D Models</p>
<ul>
<li>Etsy: <a href="https://www.etsy.com/shop/TryCatchDesignsShop">etsy.com/shop/TryCatchDesignsShop</a></li>
<li>Cults3D: <a href="https://cults3d.com/en/users/trycatchdesigns">cults3d.com/en/users/trycatchdesigns</a></li>
<li>Patreon: <a href="https://www.patreon.com/TryCatchDesigns">patreon.com/TryCatchDesigns</a></li>
<li>MakerWorld: <a href="https://makerworld.com/en/@TryCatchDesigns">makerworld.com/en/@TryCatchDesigns</a></li>
<li>Facebook: <a href="https://www.facebook.com/profile.php?id=61595400764100">facebook.com/TryCatchDesigns</a></li>
</ul>
```

Past examples: `descriptions\` in this folder (grinch, snoopy, base).

## Notes

- **MakerWorld IDs** (DesignModelId and similar) are left blank on purpose. MakerWorld assigns them when the model is published, so never copy them from another file.
- **Logo-on-bottom versions** are just another 3MF. Run them through the same process and add a line to the description if the user asks.
- **Print settings** in the 3MF stay unchanged, including the ones that came from the base project. Only the metadata and pictures change.
- **Ad renders:** see `G:\gimp-mcp\Projects\Workflow\Renders\Render_Workflow.md`. It's a reusable pipeline that takes a 3MF and an output path and produces `Drafts\` images with the logo.

## Release log

| Date | File | Pictures |
|---|---|---|
| 2026-10-27 | `NewCupProject\Final\Grinch Cooler Cup - Final.3mf` | 8 ad renders |
| 2026-10-27 | `NewCupProject\Final\Snoopy Cooler Cup - Final.3mf` | 8 ad renders |
| 2026-10-27 | `NewCupProject\Final\Cooler Cup Base - Final.3mf` | Bambu plate preview (needs real renders) |
| 2026-10-27 | `Cat In Hat\Pop Corn Bucket\STL\FinalSTL\Cat in the Hat Popcorn Bucket (A1 mini) - Final.3mf` | 4 ad renders (hero: top_inside) |
| 2026-10-27 | `Cat In Hat\Pop Corn Bucket\STL\FinalSTL\Cat in the Hat Popcorn Bucket (X2D) - Final.3mf` | 4 ad renders (hero: top_inside) |
| 2026-10-29 | `Cat In Hat\STL\FinalSTL\Final\Cat in the Hat Hot Air Balloon (A1 mini) - Final.3mf` (from `_flatbrim`) | 5 real photos (hero: 105739) |
| 2026-11-03 | `SnoopyCandle\STL\Final\Beagle Dog Bowl Candle Holder (A1 mini) - Final.3mf` | 7 ad renders (hero: hero_logo) |
| 2026-11-03 | `SnoopyCandle\STL\Final\Beagle Dog Bowl Candle Holder (X2D) - Final.3mf` | 7 ad renders (hero: hero_logo) |
| 2026-11-03 | `SnoopyCandle\STL\Final\Beagle Dog Bowl Candle Holder (A1 mini) - Final.3mf` (rebuilt: optional grass base on plate 6) | 8 ad renders from `GrassBlades\Drafts` (hero: hero_logo) |
| 2026-11-03 | `SnoopyCandle\STL\Final\Beagle Dog Bowl Candle Holder (X2D) - Final.3mf` (rebuilt: optional grass base on plate 6) | 8 ad renders from `GrassBlades\Drafts` (hero: hero_logo) |
| 2026-11-10 | `SnoopyCandle\STL\Final -Etsy\SnoopyCandleHolderSnowBase_A1Mini.3mf` (snow base only) | 2 ad renders from `SnowBase\Drafts` (hero: hero_logo) |
| 2026-11-10 | `SnoopyCandle\STL\Final -Etsy\SnoopyCandleHolderSnowBase_X2D.3mf` (snow base only) | 2 ad renders from `SnowBase\Drafts` (hero: hero_logo) |
| 2026-11-10 | `NewCupProject\Final\EtsyStitch\Happy Blue Creature Cooler Cup X2D - Etsy.3mf` | 1 ad render (hero: Standard front_logo) |
| 2026-11-10 | `NewCupProject\Final\EtsyStitch\Happy Blue Creature Grinch Cooler Cup X2D - Etsy.3mf` | 1 ad render (hero: Grinch front_logo) |
| 2026-11-28 | `NewCupProject\Final\Etsy Woodstock\Little Yellow Bird Cooler Cup A1 mini - Etsy.3mf` (from `Woodstock Cooler Cup - Final - Painted_a1mini_optimized.3mf`) | 6 ad renders from `Cup\Ad Images\Woodstock\Drafts` (hero: hero_cup_logo) |
| 2026-11-28 | `NewCupProject\Final\Etsy Woodstock\Little Yellow Bird Cooler Cup X2D - Etsy.3mf` (from `Woodstock Cooler Cup - Final - Painted_x2d_optimized.3mf`) | 6 ad renders from `Cup\Ad Images\Woodstock\Drafts` (hero: hero_cup_logo) |

Add a row after each release, directly under the last row (a blank line splits the table).
