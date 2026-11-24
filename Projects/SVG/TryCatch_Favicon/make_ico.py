"""Build a multi-size favicon.ico (16-256px) from the hi-res transparent logo mark.
usage: python -I make_ico.py <logo_mark.png> <out.ico>"""
import sys
from PIL import Image
src, out = sys.argv[1:3]
im = Image.open(src).convert("RGBA"); im = im.crop(im.getbbox())
s = max(im.size); sq = Image.new("RGBA", (s, s), (0, 0, 0, 0))
sq.paste(im, ((s - im.width) // 2, (s - im.height) // 2))
sq.resize((256, 256), Image.LANCZOS).save(out, sizes=[(n, n) for n in (16, 32, 48, 64, 128, 256)])
