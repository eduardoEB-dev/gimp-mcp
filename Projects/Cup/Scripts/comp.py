import sys
from PIL import Image
fg, bg, out = sys.argv[1:4]
b = Image.open(bg).convert("RGBA"); b.alpha_composite(Image.open(fg).convert("RGBA")); b.convert("RGB").save(out)
