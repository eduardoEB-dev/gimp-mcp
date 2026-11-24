"""Read a Bambu Studio 3MF -> <work>/manifest.json + one npz per unique object (verts, tris, per-tri extruder).

Colors: object extruder from Metadata/model_settings.config, painted triangles (paint_color) decoded to
their extruder, filament hex colors from Metadata/project_settings.config.
Roles (cooler-cup family): pin / handle / spigot / cap / cup / other, by object name then size.

usage: python -I extract_3mf.py <file.3mf> <work_dir>
"""
import sys, os, re, json, zipfile, hashlib, collections, html
import numpy as np

src, work = sys.argv[1], sys.argv[2]
os.makedirs(work, exist_ok=True)
z = zipfile.ZipFile(src)
ms = z.read("Metadata/model_settings.config").decode("utf8")
filaments = json.loads(z.read("Metadata/project_settings.config")).get("filament_colour", ["#FFFFFF"])
model = z.read("3D/3dmodel.model").decode("utf8")

REV = True  # children are serialized last-first (verified on popcorn bucket: other order gives jagged bands)

def decode_paint(s, cache={}):
    """Bambu TriangleSelector string -> [(3x3 barycentric corners, extruder)] leaf sub-triangles (0 = object default).
    Keeps the full subdivision so color boundaries stay smooth instead of following whole (large) triangles."""
    if s in cache: return cache[s]
    nib = [int(c, 16) for c in reversed(s)]; i = 0; out = []
    def rec(b):
        nonlocal i
        n = nib[i]; i += 1; split = n & 3; hi = n >> 2
        if split == 0:
            st = hi
            if st == 3: st = nib[i] + 3; i += 1
            out.append((b, st)); return
        r = [b[(j + hi) % 3] for j in range(3)]  # rotate so the special side comes first
        if split == 1:
            m = (r[1] + r[2]) / 2; ch = [(r[0], r[1], m), (m, r[2], r[0])]
        elif split == 2:
            m1, m2 = (r[0] + r[1]) / 2, (r[0] + r[2]) / 2; ch = [(r[0], m1, m2), (m1, r[1], r[2]), (r[2], m2, m1)]
        else:
            a, c, d = (r[0] + r[1]) / 2, (r[1] + r[2]) / 2, (r[2] + r[0]) / 2
            ch = [(r[0], a, d), (a, r[1], c), (d, c, r[2]), (a, c, d)]
        for k in (range(len(ch) - 1, -1, -1) if REV else range(len(ch))): rec(np.array(ch[k]))
    try:
        rec(np.eye(3))
    except Exception:
        out = [(np.eye(3), 0)]
    cache[s] = out; return out

# object id -> (name, extruder)  [model_settings]
objs = {}
for oid, body in re.findall(r'<object id="(\d+)">(.*?)</object>', ms, re.S):
    name = re.search(r'key="name" value="([^"]+)"', body).group(1)
    ext = re.search(r'key="extruder" value="(\d+)"', body)
    objs[oid] = {"name": name, "extruder": int(ext.group(1)) if ext else 1}
plates = []
for p in re.findall(r"<plate>(.*?)</plate>", ms, re.S):
    plates.append({"name": html.unescape(re.search(r'plater_name" value="([^"]*)', p).group(1)),
                   "objects": re.findall(r'object_id" value="(\d+)"', p)})
# object id -> component model files  [3dmodel.model]
comps = dict(re.findall(r'<object id="(\d+)"[^>]*>\s*<components>(.*?)</components>', model, re.S))

out, seen = [], {}
for oid, info in objs.items():
    if oid not in comps: continue
    V, F, P, off = [], [], [], 0
    for attrs in re.findall(r'<component\b([^>]*)/?>', comps[oid]):  # mesh in sub-file (p:path) or inline in main model
        path = re.search(r'p:path="([^"]+)"', attrs); cid = re.search(r'objectid="(\d+)"', attrs).group(1)
        tr = (re.search(r'transform="([^"]+)"', attrs) or [0, "1 0 0 0 1 0 0 0 1 0 0 0"])[1]
        t = z.read(path.group(1).lstrip("/")).decode("utf8") if path else model
        body = re.search(rf'<object id="{cid}"[^>]*>(.*?)</object>', t, re.S).group(1)
        v = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', body), float)
        m = np.array(tr.split(), float).reshape(4, 3); v = v @ m[:3] + m[3]
        tri = re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"(?: paint_color="([0-9A-F]+)")?', body)
        nv, ff, pp, mid = [], [], [], {}
        def vid(x):  # dedupe split midpoints so shading stays smooth across sub-triangles
            k = tuple(np.round(x, 4))
            if k not in mid: mid[k] = len(v) + len(nv); nv.append(x)
            return mid[k]
        for a_, b_, c_, s in tri:
            ids = [int(a_), int(b_), int(c_)]
            if not s: ff.append(ids); pp.append(0); continue
            P3 = v[ids]
            for bc, st in decode_paint(s):
                ff.append([ids[int(np.argmax(w))] if w.max() == 1 else vid(w @ P3) for w in bc]); pp.append(st)
        v = np.vstack([v, np.array(nv).reshape(-1, 3)])
        V.append(v); F.append(np.array(ff) + off); P.append(np.array(pp, np.int8)); off += len(v)
    v, f, p = np.vstack(V), np.vstack(F), np.concatenate(P)
    h = hashlib.md5(v.tobytes() + p.tobytes()).hexdigest()[:10]
    plate = next((pl["name"] for pl in plates if oid in pl["objects"]), "")
    if h in seen:  # exact duplicate instance (e.g. two pins) -> just count it
        seen[h]["count"] += 1; continue
    lo, hi = v.min(0), v.max(0); nm = info["name"].lower()
    role = ("pin" if "pin" in nm else "handle" if "handle" in nm else "spigot" if ("spigot" in nm or "valve" in nm)
            else "cap" if ("cap" in nm or "lid" in nm) else "cup" if hi[2] - lo[2] > 90 else "other")
    np.savez(os.path.join(work, f"obj{oid}.npz"), v=v.astype(np.float32), f=f.astype(np.int32), p=p)
    rec = {"id": oid, "name": info["name"], "plate": plate, "role": role, "extruder": info["extruder"],
           "painted": {int(k): int(c) for k, c in zip(*np.unique(p, return_counts=True)) if k},
           "bbox": [lo.round(2).tolist(), hi.round(2).tolist()], "tris": int(len(f)), "count": 1, "hash": h}
    seen[h] = rec; out.append(rec)

def slug(s): return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "x"
used = set(); ncaps = sum(r["role"] == "cap" for r in out)
for r in out:  # readable unique labels: cups by object name, caps by plate name (just "cap" if only one)
    nm = re.sub(r"\.stl$", "", r["name"], flags=re.I)
    base = slug(("cap" if ncaps == 1 else r["plate"] or "cap") if r["role"] == "cap" else nm)
    lab, k = base, 2
    while lab in used: lab, k = f"{base}_{k}", k + 1
    used.add(lab); r["label"] = lab
man = {"source": os.path.abspath(src), "filaments": filaments, "plates": plates, "objects": out}
json.dump(man, open(os.path.join(work, "manifest.json"), "w"), indent=1)
print("filaments:", filaments)
for r in out:
    print(f"  {r['role']:7} {r['label']:28} id={r['id']:>3} ext={r['extruder']} painted={r['painted']} x{r['count']}  plate='{r['plate']}'")
