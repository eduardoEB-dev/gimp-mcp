import sys, base64, io
from PIL import Image, ImageChops
src, out, prev = sys.argv[1:4]
im = Image.open(src).convert("RGB")
im = im.crop((0, 0, 940, im.height))                       # mark only, drop wordmark
m = ImageChops.difference(im, Image.new("RGB", im.size, "white")).convert("L").point(lambda v: 255 if v > 24 else 0)
im = im.crop(m.getbbox()).convert("RGBA")
px = im.load()
for y in range(im.height):                                  # white -> transparent (soft key)
    for x in range(im.width):
        r, g, b, _ = px[x, y]; d = 255 - min(r, g, b)
        px[x, y] = (r, g, b, max(0, min(255, int((d - 8) * 255 / 40))))
s = max(im.size); sq = Image.new("RGBA", (s, s), (0, 0, 0, 0))
sq.paste(im, ((s - im.width) // 2, (s - im.height) // 2))
sq = sq.resize((128, 128), Image.LANCZOS)
buf = io.BytesIO(); sq.save(buf, "PNG", optimize=True)
b64 = base64.b64encode(buf.getvalue()).decode()
open(out, "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 128 128"><image width="128" height="128" xlink:href="data:image/png;base64,{b64}"/></svg>\n')
sq.save(out.replace(".svg", ".png"))
pv = Image.new("RGBA", (300, 140), "white")
for i, sz in enumerate((128, 32, 16)):
    pv.alpha_composite(sq.resize((sz, sz), Image.LANCZOS), ([0, 140, 190][i], 4))
dk = Image.new("RGBA", (40, 40), (32, 33, 36, 255)); dk.alpha_composite(sq.resize((16, 16), Image.LANCZOS), (12, 12))
pv.alpha_composite(dk, (220, 4)); pv.save(prev)
print(len(buf.getvalue()))
