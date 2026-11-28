"""Extract a small multi-part Bambu 3MF accessory (e.g. can opener keychain) as ONE colored prop for ad renders.

Per-part extruders (model_settings <part>) become per-triangle colors (extract_3mf.py only reads object extruders).
Also finds the keyring hole (enclosed gap in the top-view footprint) so props.py can thread a ring through it.

Output <out_dir>/prop.npz (v mm, f, p = extruder per tri; frame: bbox center xy = 0, z min = 0, art up +Z)
       <out_dir>/prop.json (filaments, size, hole [x, y, r] or null, centroid)
usage: python -I prop_3mf.py <file.3mf> <out_dir>
"""
import sys, os, re, json, zipfile
import numpy as np
from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
z = zipfile.ZipFile(src)
ms = z.read("Metadata/model_settings.config").decode("utf8")
fil = json.loads(z.read("Metadata/project_settings.config")).get("filament_colour", ["#FFFFFF"])
model = z.read("3D/3dmodel.model").decode("utf8")

part_ext = {pid: int(e) for pid, e in re.findall(
    r'<part id="(\d+)"[^>]*>.*?key="extruder" value="(\d+)"', ms, re.S)}
obj_ext = re.search(r'<object id="\d+">.*?key="extruder" value="(\d+)"', ms, re.S)
obj_ext = int(obj_ext.group(1)) if obj_ext else 1

meshes = {}  # (path, objectid) -> (v, f)
def load(path):
    s = z.read(path.lstrip("/")).decode("utf8")
    for oid, body in re.findall(r'<object id="(\d+)"[^>]*>(.*?)</object>', s, re.S):
        if "<mesh" not in body: continue
        v = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', body), float)
        f = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', body), int)
        meshes[(path, oid)] = (v, f)

V, F, P = [], [], []; n = 0
comps = re.findall(r'<component (?:p:path="([^"]+)" )?objectid="(\d+)"[^>]*?transform="([^"]+)"', model)
if not comps: sys.exit("no components: single-mesh 3MF, use extract_3mf.py")
for path, oid, t in comps:
    path = path or "/3D/3dmodel.model"
    if (path, oid) not in meshes: load(path)
    v, f = meshes[(path, oid)]
    m = np.array(t.split(), float).reshape(4, 3)  # 3MF: 3x3 rows then translation
    v = v @ m[:3] + m[3]
    V.append(v); F.append(f + n); P.append(np.full(len(f), part_ext.get(oid, obj_ext))); n += len(v)
    print(f"part {oid}: ext {part_ext.get(oid, obj_ext)} tris {len(f)}")
v, f, p = np.vstack(V), np.vstack(F), np.concatenate(P)
lo, hi = v.min(0), v.max(0)
v = v - [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]
lo, hi = v.min(0), v.max(0)

# keyring hole: top-view footprint, flood-fill outside, enclosed empty regions = holes
PX = 10  # px per mm
Wd, Ht = int((hi[0] - lo[0]) * PX) + 20, int((hi[1] - lo[1]) * PX) + 20
img = Image.new("L", (Wd, Ht), 0); d = ImageDraw.Draw(img)
xy = (v[:, :2] - lo[:2]) * PX + 10
for t in f: d.polygon([tuple(xy[i]) for i in t], fill=255)
ImageDraw.floodfill(img, (0, 0), 128)
a = np.array(img); holes = []
while True:
    ys, xs = np.nonzero(a == 0)
    if not len(ys): break
    lab = 10 + len(holes)
    ImageDraw.floodfill(img, (int(xs[0]), int(ys[0])), lab); a = np.array(img)
    yy, xx = np.nonzero(a == lab)
    area = len(yy) / PX ** 2
    cx, cy = (xx.mean() - 10) / PX + lo[0], (yy.mean() - 10) / PX + lo[1]
    holes.append({"x": float(cx), "y": float(cy), "r": float(np.sqrt(area / np.pi)), "area": float(area)})
holes = [h for h in holes if h["area"] > 3]
print("holes:", [(round(h["x"], 1), round(h["y"], 1), round(h["r"], 2)) for h in holes])
hole = max(holes, key=lambda h: h["area"]) if holes else None

# centroid of the solid (area-weighted top footprint is fine for hanging direction)
tri = v[f]; ar = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
cen = (tri.mean(1) * ar[:, None]).sum(0) / ar.sum()
np.savez(os.path.join(out, "prop.npz"), v=v, f=f, p=p)
json.dump({"filaments": fil, "size": (hi - lo).tolist(), "centroid": cen.tolist(),
           "hole": [hole["x"], hole["y"], hole["r"]] if hole else None, "src": src},
          open(os.path.join(out, "prop.json"), "w"), indent=1)
print("prop size", np.round(hi - lo, 1), "hole", hole and [round(hole[k], 2) for k in ("x", "y", "r")])
