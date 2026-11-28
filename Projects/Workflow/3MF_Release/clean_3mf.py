"""Clean copy of a Bambu Studio 3MF for TryCatch Designs.

- drops a previous designer's MakerWorld metadata (Designer/IDs/License/Origin/Profile*/covers)
- sets Title, Designer, Description (HTML, stored the way Bambu stores it: escaped twice)
- replaces Auxiliaries model/profile pictures + thumbnails with the supplied renders
- leaves geometry, plates, paint and print settings byte-identical
- prints a discrepancy report

usage: python -I clean_3mf.py <src.3mf> <dst.3mf> "<title>" <description.html> <render1> [render2 ...]
render1 = hero image (cover + thumbnails). Renders can be any size/aspect; center-cropped, or fitted over a blurred fill when aspect is far off (portrait photos).
"""
import sys, io, re, zipfile
from PIL import Image, ImageFilter

DESIGNER = "TryCatch Designs"
OUR_URLS = ("etsy.com/shop/TryCatchDesignsShop", "cults3d.com/en/users/trycatchdesigns", "patreon.com/TryCatchDesigns",
            "makerworld.com/en/@TryCatchDesigns", "facebook.com/profile.php?id=61595400764100")
KNOWN_FOREIGN = (rb"animul",)          # names seen in past source files; add more as found
DROP_META = {"Designer", "DesignerUserId", "DesignerCover", "DesignModelId", "DesignProfileId", "DesignRegion",
             "ProfileCover", "ProfileUserId", "ProfileUserName", "ProfileDescription", "ProfileTitle",
             "Origin", "License", "Description", "Title"}
EXPECTED_META = {"Title", "Designer", "Description", "Application", "BambuStudio:3mfVersion", "CopyRight", "Copyright",
                 "CreationDate", "ModificationDate", "Thumbnail_Middle", "Thumbnail_Small"}

THUMBS = {"3mf": ("Auxiliaries/.thumbnails/thumbnail_3mf.png", (240, 180)),
          "middle": ("Auxiliaries/.thumbnails/thumbnail_middle.png", (680, 510)),
          "small": ("Auxiliaries/.thumbnails/thumbnail_small.png", (251, 188))}
THUMB_RELS = {"metadata/thumbnail": "3mf", "cover-thumbnail-middle": "middle", "cover-thumbnail-small": "small"}
THUMB_META = {"Thumbnail_Middle": "middle", "Thumbnail_Small": "small"}

src, dst, title, desc_file, imgs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:]
if not imgs: sys.exit("need at least one render")
import os
if os.path.exists(dst): sys.exit(f"REFUSED: {dst} exists; never overwrite (pick a new name)")

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
html = " ".join(open(desc_file, encoding="utf8").read().split())
SET_META = {"Title": title, "Designer": DESIGNER, "Description": esc(html.replace('"', "&#34;"))}

def enc(im, size, fmt, aspect):
    src = im = im.convert("RGB"); w, h = im.size
    if w / h > aspect: nw = int(h * aspect); im = im.crop(((w - nw) // 2, 0, (w + nw) // 2, h))
    else: nh = int(w / aspect); im = im.crop((0, (h - nh) // 2, w, (h + nh) // 2))
    out = im.resize(size, Image.LANCZOS)
    if max(w / h, aspect) / min(w / h, aspect) > 1.15:  # aspect far off (e.g. portrait photo): fit whole image over a blurred fill, don't chop it
        out = out.filter(ImageFilter.GaussianBlur(size[0] / 30))
        s = min(size[0] / w, size[1] / h); fit = src.resize((round(w * s), round(h * s)), Image.LANCZOS)
        out.paste(fit, ((size[0] - fit.width) // 2, (size[1] - fit.height) // 2))
    b = io.BytesIO(); out.save(b, fmt, **({"quality": 90} if fmt == "WEBP" else {}))
    return b.getvalue()

pics = [Image.open(p) for p in imgs]
zin = zipfile.ZipFile(src)
old_meta = dict(re.findall(r'<metadata name="([^"]+)">([^<]{0,80})', zin.read("3D/3dmodel.model").decode("utf8")))
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
    for i in zin.infolist():
        n = i.filename
        if n.startswith(("Auxiliaries/Model Pictures/", "Auxiliaries/Profile Pictures/", "Auxiliaries/.thumbnails/")): continue
        d = zin.read(n)
        if n == "3D/3dmodel.model":
            t = d.decode("utf8")
            t = re.sub(r'\s*<metadata name="([^"]+)">[^<]*</metadata>', lambda m: "" if m.group(1) in DROP_META else m.group(0), t)
            add = "\n ".join(f'<metadata name="{k}">{esc(v)}</metadata>' for k, v in SET_META.items())
            t = t.replace('<metadata name="Application">', add + '\n <metadata name="Application">', 1)
            for k, f in THUMB_META.items(): t = re.sub(rf'(<metadata name="{k}">)[^<]*', rf"\g<1>/{THUMBS[f][0]}", t)
            d = t.encode("utf8")
        elif n == "_rels/.rels":  # point file-browser + Bambu cover thumbnails at the hero, not the plate preview
            t = d.decode("utf8")
            for typ, f in THUMB_RELS.items(): t = re.sub(rf'Target="[^"]*"(?=[^>]*Type="[^"]*{typ}")', f'Target="/{THUMBS[f][0]}"', t)
            d = t.encode("utf8")
        zi = zipfile.ZipInfo(n, i.date_time); zi.compress_type = zipfile.ZIP_DEFLATED
        zout.writestr(zi, d)  # fresh ZipInfo: writestr mutates the one it gets, which would break re-reading zin
    for k, im in enumerate(pics):
        zout.writestr(f"Auxiliaries/Model Pictures/TryCatch_{k + 1:02d}.webp", enc(im, (1080, 1080), "WEBP", 1))
    for path, size in THUMBS.values(): zout.writestr(path, enc(pics[0], size, "PNG", 4 / 3))
    zout.writestr("Auxiliaries/Profile Pictures/TryCatch_cover.webp", enc(pics[0], (1440, 1080), "WEBP", 4 / 3))

# ---------- discrepancy report ----------
z = zipfile.ZipFile(dst); issues = []
print(f"WROTE {dst}  ({len(pics)} pictures)")
print("removed from source:", {k: v for k, v in old_meta.items() if k in DROP_META} or "nothing")
meta = dict(re.findall(r'<metadata name="([^"]+)">([^<]*)', z.read("3D/3dmodel.model").decode("utf8")))
extra = set(meta) - EXPECTED_META
if extra: issues.append(f"unexpected metadata keys: {sorted(extra)}")
for n in z.namelist():
    if n.startswith(("Auxiliaries/", "Metadata/plate")) or n.endswith((".png", ".webp", ".jpg")): continue
    d = z.read(n)
    for p in KNOWN_FOREIGN:
        if re.search(p, d, re.I): issues.append(f"known foreign name {p!r} in {n}")
    for u in set(re.findall(rb"https?://[^\s\"'<&]+", d)):
        u = u.decode("utf8", "replace")
        if not any(o.lower() in u.lower() for o in OUR_URLS) and "schemas." not in u and "w3.org" not in u:
            issues.append(f"foreign URL in {n}: {u}")
untouched = [i.filename for i in zin.infolist() if not i.filename.startswith("Auxiliaries/") and i.filename not in ("3D/3dmodel.model", "_rels/.rels")]
changed = [n for n in untouched if zin.read(n) != z.read(n)]
if changed: issues.append(f"files changed that should be identical: {changed}")
obj = re.findall(r'<object id="\d+">\s*<metadata key="name" value="([^"]+)"', z.read("Metadata/model_settings.config").decode())
plates = re.findall(r'plater_name" value="([^"]*)', z.read("Metadata/model_settings.config").decode())
print("objects:", obj); print("plates:", plates)
print("DISCREPANCIES:" if issues else "DISCREPANCIES: none")
for s in issues: print("  -", s)
