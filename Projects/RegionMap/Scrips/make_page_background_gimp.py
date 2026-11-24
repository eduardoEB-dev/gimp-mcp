"""GIMP 3 script: put the SharePoint screenshot on a 2000x1200 presentation background.

Steps: subtle light-grey gradient, screenshot centered, drop shadow
(blur 30, offset Y 12, opacity 0.15) and a 1px #E5E7EB border.
Writes RegionMap/WPImages/PageAppBackgroundIMG.png (+ .xcf with layers).

Run headless (from the repo root):
  "C:/Program Files/GIMP 3/bin/gimp-console-3.exe" -i --batch-interpreter python-fu-eval
      -b "exec(open(r'RegionMap/Scrips/make_page_background_gimp.py').read())" -b "Gimp.quit()"
"""

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl, Gio
from pathlib import Path

ROOT = Path(r"D:\gimp-mcp\RegionMap\WPImages")
SHOT = ROOT / "FullPageWPView_anon.png"
OUT = ROOT / "PageAppBackgroundIMG.png"

W, H = 2000, 1200
TOP, BOTTOM = "#F8F9FB", "#ECEEF2"   # very subtle light-grey gradient
BORDER = "#E5E7EB"

img = Gimp.Image.new(W, H, Gimp.ImageBaseType.RGB)

# 1. Background gradient (top -> bottom), dithered to avoid banding.
bg = Gimp.Layer.new(img, "Background", W, H, Gimp.ImageType.RGB_IMAGE, 100, Gimp.LayerMode.NORMAL)
img.insert_layer(bg, None, 0)
Gimp.context_push()
Gimp.context_set_foreground(Gegl.Color.new(TOP))
Gimp.context_set_background(Gegl.Color.new(BOTTOM))
Gimp.context_set_gradient_fg_bg_rgb()
bg.edit_gradient_fill(Gimp.GradientType.LINEAR, 0, False, 1, 0, True, 0, 0, 0, H)

# 2. Screenshot centered.
shot = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, img, Gio.File.new_for_path(str(SHOT)))
shot.set_name("Screenshot")
sw, sh = shot.get_width(), shot.get_height()
x, y = (W - sw) // 2, (H - sh) // 2

# 3. Card layer: 1px border ring (screenshot covers its inside) + drop shadow.
card = Gimp.Layer.new(img, "Border + Shadow", W, H, Gimp.ImageType.RGBA_IMAGE, 100, Gimp.LayerMode.NORMAL)
img.insert_layer(card, None, 0)
card.fill(Gimp.FillType.TRANSPARENT)
img.select_rectangle(Gimp.ChannelOps.REPLACE, x - 1, y - 1, sw + 2, sh + 2)
Gimp.context_set_foreground(Gegl.Color.new(BORDER))
card.edit_fill(Gimp.FillType.FOREGROUND)
Gimp.Selection.none(img)

shadow = Gimp.DrawableFilter.new(card, "gegl:dropshadow", "Drop Shadow")
cfg = shadow.get_config()
cfg.set_property("x", 0.0)
cfg.set_property("y", 12.0)
cfg.set_property("radius", 30.0)
cfg.set_property("opacity", 0.15)
cfg.set_property("color", Gegl.Color.new("black"))
shadow.update()
card.merge_filter(shadow)
Gimp.context_pop()

img.insert_layer(shot, None, 0)
shot.set_offsets(x, y)

# 4. Save layered .xcf and flattened .png.
Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, Gio.File.new_for_path(str(OUT.with_suffix(".xcf"))), None)
Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, img, Gio.File.new_for_path(str(OUT)), None)
print(f"wrote {OUT}")
img.delete()
