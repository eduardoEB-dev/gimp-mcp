"""Clean copy of a Bambu 3MF: drop the original designer's MakerWorld metadata + listing pictures,
set our title/designer, and embed our ad images as model/profile pictures + thumbnails.
usage: python clean_3mf.py <src.3mf> <dst.3mf> "<title>" <description.html> <hero.png> [more ad images...]
"""
import sys, io, re, zipfile
from PIL import Image

src, dst, title, desc_file, imgs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:]
DROP_META = {"Designer", "DesignerUserId", "DesignerCover", "DesignModelId", "DesignProfileId", "DesignRegion",
             "ProfileCover", "ProfileUserId", "ProfileUserName", "ProfileDescription", "ProfileTitle",
             "Origin", "License", "Description", "Title"}
def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# Bambu stores the description as HTML escaped twice (quotes as &#34;); pre-escape once so the XML write below makes it twice
html = " ".join(open(desc_file, encoding="utf8").read().split())
SET_META = {"Title": title, "Designer": "TryCatch Designs", "Description": esc(html.replace('"', "&#34;"))}

def enc(im, size, fmt, crop=None):
    im = im.convert("RGB")
    if crop:  # center-crop to aspect w/h
        w, h = im.size; a = crop
        if w / h > a: nw = int(h * a); im = im.crop(((w - nw) // 2, 0, (w + nw) // 2, h))
        else: nh = int(w / a); im = im.crop((0, (h - nh) // 2, w, (h + nh) // 2))
    im = im.resize(size, Image.LANCZOS); b = io.BytesIO()
    im.save(b, fmt, **({"quality": 90} if fmt == "WEBP" else {})); return b.getvalue()

pics = [Image.open(p) for p in imgs]
zin = zipfile.ZipFile(src)
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
    for i in zin.infolist():
        n = i.filename
        if n.startswith("Auxiliaries/Model Pictures/") or n.startswith("Auxiliaries/Profile Pictures/"):
            continue
        d = zin.read(n)
        if n == "3D/3dmodel.model":
            t = d.decode("utf8")
            t = re.sub(r'\s*<metadata name="([^"]+)">[^<]*</metadata>',
                       lambda m: "" if m.group(1) in DROP_META else m.group(0), t)
            add = "".join(f'\n <metadata name="{k}">{esc(v)}</metadata>' for k, v in SET_META.items())
            t = t.replace('<metadata name="Application">', add.lstrip("\n ") + '\n <metadata name="Application">', 1)
            d = t.encode("utf8")
        elif n == "Auxiliaries/.thumbnails/thumbnail_3mf.png": d = enc(pics[0], (240, 180), "PNG", 4 / 3)
        elif n == "Auxiliaries/.thumbnails/thumbnail_middle.png": d = enc(pics[0], (680, 510), "PNG", 4 / 3)
        elif n == "Auxiliaries/.thumbnails/thumbnail_small.png": d = enc(pics[0], (251, 188), "PNG", 4 / 3)
        zout.writestr(i, d)
    for k, im in enumerate(pics):
        zout.writestr(f"Auxiliaries/Model Pictures/TryCatch_{k + 1:02d}.webp", enc(im, (1080, 1080), "WEBP"))
    zout.writestr("Auxiliaries/Profile Pictures/TryCatch_cover.webp", enc(pics[0], (1440, 1080), "WEBP", 4 / 3))

# verify
z = zipfile.ZipFile(dst); bad = [n for n in z.namelist() if re.search(rb"animul", z.read(n), re.I)]
print("WROTE", dst, "| leftover refs:", bad or "none", "| pictures:", len(pics))
