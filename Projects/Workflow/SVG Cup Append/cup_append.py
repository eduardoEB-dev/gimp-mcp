"""Add a multi-color SVG layer set to a cooler cup 3MF: raised relief on the cup front and/or inlay on the lid.

Input: a layer set from the SVG Creation workflow (<Name>_<Color>.svg + layers.json) and a cup 3MF.
cup: each color = own closed shell wrapped onto the cup wall (sunk EMBED into it), appended to the cup
     part's mesh (one part, overlapping shells, like the Grinch/Snoopy finals). Outline stands taller.
lid: the lid prints face-down, so colors are inlaid flush (LID_DEPTH pocket, own shells joined into the
     cap mesh, like the Grinch caps). Art reads upright with the straw hole at 12 o'clock; by default it
     sits below the hole or wherever misses it. The hole cuts the art only with --lid-place through.
Separate shells -> Bambu's paint bucket stops at each color. Other objects, plates, settings untouched.

Run: python -I cup_append.py <layer_set_dir> <src.3mf> <out.3mf> [options]   (see SVG_Cup_Append_Workflow.md)
"""
import argparse, glob, json, math, os, re, subprocess, sys, zipfile
import numpy as np
import shapely
from shapely import make_valid
from shapely.affinity import affine_transform
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

HERE = os.path.dirname(os.path.abspath(__file__))
# cooler cup base (NewSTL/cup.stl, 116.84 tall): mm measured from the cup bottom
RECESS_TOP = 31.5         # spigot recess edge (wall leaves R below this)
RECESS_GAP = 1.0          # art bottom stays this far above it
TOP_GAP = 3.592           # art top stays this far below the cup rim
W_MAX = 60.0              # arc width limit: grip panels start ~50deg = +-36.6mm
EMBED = 0.2               # cup bodies sink into wall
R_PLAIN = 41.91           # plain cup front wall radius
# lid (cap.stl): flat top face prints on the bed
LID_DEPTH = 0.6           # inlay depth (3 layers @ 0.2)
LID_EDGE = 1.0            # art stays this far inside the flat face edge
LID_HOLE_GAP = 1.0        # art stays this far from the straw hole (through mode: 0.5 rim kept)

ap = argparse.ArgumentParser()
ap.add_argument("layers", help="layer set folder (has layers.json)")
ap.add_argument("src", help="cup 3MF (never modified)")
ap.add_argument("out", help="output 3MF")
ap.add_argument("--target", choices=("cup", "lid", "both"), default="cup", help="where the art goes")
g = ap.add_mutually_exclusive_group()
g.add_argument("--height-mm", type=float, help="cup art height (default: layers.json size)")
g.add_argument("--width-mm", type=float, help="cup art arc width")
ap.add_argument("--align", choices=("center", "top"), default="center", help="cup: center in free band, or top at rim gap")
ap.add_argument("--z-shift", type=float, default=0.0, help="cup: move art up (+) / down (-) mm after aligning")
ap.add_argument("--u-shift", type=float, default=0.0, help="cup: move art around the cup (+ = right, arc mm)")
ap.add_argument("--outline", help="color that wins overlaps, fills hairline gaps, stands taller on the cup (default: Black/White if present)")
ap.add_argument("--heights", default="", help='cup raise per color, e.g. "White=0.8,Pink=0.6" (default outline 0.8, others 0.6)')
ap.add_argument("--fill-holes", action="store_true", help="fill holes inside the art with the outline color (default: keep open, e.g. P counter)")
ap.add_argument("--lid-place", choices=("below", "miss", "through"), default="below",
                help="lid: below the straw hole (default), biggest spot that misses it, or centered with the hole cut through the art")
ap.add_argument("--lid-height-mm", type=float, help="lid art height (default: largest that fits)")
ap.add_argument("--lid-shift", default="0,0", help='lid: nudge "right,up" mm (hole = up)')
ap.add_argument("--object", default="cup", help="name (substring) of the cup object in the 3MF")
ap.add_argument("--lid-object", default="cap", help="name (substring) or object id of the lid in the 3MF")
ap.add_argument("--work", help=r"work folder (default: G:\Blender\blender-mcp\Projects\NewCupProject\<Name>Cup)")
ap.add_argument("--blender", help="blender.exe (default: newest under Program Files\\Blender Foundation)")
ap.add_argument("--dry-run", action="store_true", help="layout + previews only, no 3MF written")
ap.add_argument("--force", action="store_true", help="allow overwriting out, or adding to a cup/lid that already has art")
a = ap.parse_args()
DO_CUP, DO_LID = a.target in ("cup", "both"), a.target in ("lid", "both")

def die(msg): sys.exit("ERROR: " + msg)

# ---------- layer set ----------
meta = json.load(open(os.path.join(a.layers, "layers.json")))
NAME = meta["name"]
COLORS = [l["color"] for l in meta["layers"]]
HEX = {l["color"]: l.get("hex", "#888888") for l in meta["layers"]}
OUTLINE = a.outline or next((c for c in ("Black", "White") if c in COLORS), None)
if OUTLINE and OUTLINE not in COLORS: die(f"--outline {OUTLINE} not in layers {COLORS}")
H = {c: (0.8 if c == OUTLINE else 0.6) for c in COLORS}
for kv in filter(None, a.heights.split(",")):
    k, v = kv.split("="); H[k.strip()] = float(v)
WORK = a.work or rf"G:\Blender\blender-mcp\Projects\NewCupProject\{NAME}Cup"
if os.path.abspath(a.out) == os.path.abspath(a.src) and not a.force and not a.dry_run:
    die("out == src: pass --force to overwrite the src in place")
if os.path.exists(a.out) and not a.force and not a.dry_run: die(f"{a.out} exists (--force to overwrite)")

def bez(p0, p1, p2, p3, n=8):
    t = np.linspace(0, 1, n + 1)[1:, None]
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3

def load_svg(path):  # M/C/L/Z paths (layer-set output), evenodd -> shapely
    rings = []
    for d in re.findall(r'\sd="([^"]+)"', open(path).read()):
        toks = re.findall(r'[MCLZ]|-?[\d.]+(?:e-?\d+)?', d)
        i = 0; cur = None; ring = []
        while i < len(toks):
            c = toks[i]; i += 1
            if c == "M":
                if len(ring) > 2: rings.append(np.array(ring))
                cur = np.array([float(toks[i]), float(toks[i + 1])]); i += 2; ring = [cur]
            elif c == "C":
                while i < len(toks) and toks[i] not in "MCLZ":
                    p = [np.array([float(toks[i + 2 * k]), float(toks[i + 2 * k + 1])]) for k in range(3)]; i += 6
                    ring.extend(bez(cur, *p)); cur = p[2]
            elif c == "L":
                while i < len(toks) and toks[i] not in "MCLZ":
                    cur = np.array([float(toks[i]), float(toks[i + 1])]); i += 2; ring.append(cur)
            elif c == "Z":
                if len(ring) > 2: rings.append(np.array(ring))
                ring = []
        if len(ring) > 2: rings.append(np.array(ring))
    g = None
    for r in rings:
        p = make_valid(Polygon(r))
        g = p if g is None else g.symmetric_difference(p)
    return g.buffer(0)

def clean(g, r=1.5):  # drop slivers / specks (svg px)
    g = g.buffer(-r).buffer(r)
    return unary_union([p for p in getattr(g, "geoms", [g]) if p.area > 200])

def filled(g): return unary_union([Polygon(p.exterior) for p in getattr(g, "geoms", [g])])

L = {l["color"]: load_svg(os.path.join(a.layers, l["file"])) for l in meta["layers"]}
sil = unary_union(list(L.values())).buffer(2).buffer(-2)   # closes hairline gaps, keeps holes
if a.fill_holes: sil = filled(sil)
art = {}
if OUTLINE:  # outline wins overlaps; others cut by everything placed before them; leftovers -> outline
    taken = L[OUTLINE]
    for c in COLORS:
        if c == OUTLINE: continue
        art[c] = clean(L[c].difference(taken)); taken = taken.union(art[c])
    art[OUTLINE] = clean(sil.difference(unary_union([art[c] for c in art])), 0.5)
else:
    taken = None
    for c in COLORS:
        art[c] = clean(L[c] if taken is None else L[c].difference(taken)); taken = art[c] if taken is None else taken.union(art[c])
art = {c: g for c, g in art.items() if not g.is_empty}
X0, Y0, X1, Y1 = sil.bounds; CX, CY = (X0 + X1) / 2, (Y0 + Y1) / 2

def triangulate(g, seg):
    g = shapely.segmentize(g.simplify(0.012), seg)
    return [list(t.exterior.coords)[:3] for t in shapely.constrained_delaunay_triangles(g).geoms]

# ---------- 3MF objects ----------
zin = zipfile.ZipFile(a.src)
cfg = zin.read("Metadata/model_settings.config").decode()
root = zin.read("3D/3dmodel.model").decode()
paths = dict(re.findall(r'<object id="(\d+)"[^>]*>\s*<components>\s*<component p:path="([^"]+)"', root))
OBJS = []
for oid, blk in re.findall(r'<object id="(\d+)">(.*?)</object>', cfg, re.S):
    nm = re.search(r'key="name" value="([^"]*)"', blk).group(1)
    if oid in paths and blk.count("<part ") == 1:
        OBJS.append((oid, nm, paths[oid].lstrip("/")))

def find_obj(key, what):
    c = [o for o in OBJS if o[0] == key] or [o for o in OBJS if key.lower() in o[1].lower()]
    if not c: die(f'no single-part {what} object matching "{key}" (objects: {[(o[0], o[1]) for o in OBJS]})')
    return max(c, key=lambda o: zin.getinfo(o[2]).file_size)

def read_mesh(model):
    m = zin.read(model).decode()
    V = np.array(re.findall(r'<vertex x="([-\d.e]+)" y="([-\d.e]+)" z="([-\d.e]+)"', m), float)
    T = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', m), int)
    return m, V, T

STL_DT = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("x", "<u2")])
def write_stl(path, V, T):
    rec = np.zeros(len(T), dtype=STL_DT); rec["v"] = V[T].astype("<f4")
    with open(path, "wb") as f: f.write(b"\0" * 80 + np.uint32(len(T)).tobytes() + rec.tobytes())
def read_stl(path):
    b = open(path, "rb").read(); n = int.from_bytes(b[80:84], "little")
    v, idx = np.unique(np.frombuffer(b, dtype=STL_DT, count=n, offset=84)["v"].reshape(-1, 3), axis=0, return_inverse=True)
    return v.astype(np.float64), idx.reshape(-1, 3)
def vxml(V): return "".join(f'     <vertex x="{p:.6g}" y="{q:.6g}" z="{t:.6g}"/>\n' for p, q, t in V)
def txml(T): return "".join(f'     <triangle v1="{p}" v2="{q}" v3="{t}"/>\n' for p, q, t in T)

blender = a.blender or (sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender*\blender.exe")) or [None])[-1]
if not blender: die("blender.exe not found (--blender)")
def run_blender(script, *args):
    r = subprocess.run([blender, "-b", "--factory-startup", "--python", os.path.join(HERE, script), "--", *args], capture_output=True, text=True)
    for ln in r.stdout.splitlines():
        if ln.startswith(("  ", "Saved")) or "Error" in ln: print(ln)
    if r.returncode: die("blender failed:\n" + r.stdout[-3000:] + r.stderr[-3000:])

for d in ("Work", "STL", "Images"): os.makedirs(os.path.join(WORK, d), exist_ok=True)
edits = {}   # model path -> new text
faces = {}   # object id -> new face count

# ---------- cup: raised relief on the front wall ----------
if DO_CUP:
    OBJ, OBJ_NAME, MODEL = find_obj(a.object, "cup")
    m, V, T = read_mesh(MODEL)
    z0, z1 = V[:, 2].min(), V[:, 2].max()
    band = (V[:, 2] > z0 + RECESS_TOP + 2) & (V[:, 2] < z1 - TOP_GAP - 2) & (np.abs(V[:, 0]) < 15) & (V[:, 1] < 0)
    R = np.hypot(V[band, 0], V[band, 1]).max()
    print(f"cup: object {OBJ} '{OBJ_NAME}' ({MODEL}), {len(V)} verts {len(T)} tris, z {z0:.2f}..{z1:.2f}, front wall R {R:.3f}")
    if abs(R - R_PLAIN) > 0.05 and not a.force:
        die(f"front wall R {R:.3f} != {R_PLAIN}: cup already has relief, or not the cooler cup base (--force to continue)")
    if "paint_color" in m: print("note: cup has painted triangles; kept, new relief comes unpainted")
    # layout: u = arc mm from front, z = 3MF local z
    zmin, zmax = z0 + RECESS_TOP + RECESS_GAP, z1 - TOP_GAP
    s = a.width_mm / (X1 - X0) if a.width_mm else (a.height_mm or meta["size_mm"][1]) / (Y1 - Y0)
    w, h = (X1 - X0) * s, (Y1 - Y0) * s
    if h > zmax - zmin:
        print(f"WARNING: {h:.1f} mm tall > free band {zmax - zmin:.1f} mm -> scaled down"); s *= (zmax - zmin) / h; w, h = (X1 - X0) * s, (Y1 - Y0) * s
    if w > W_MAX: print(f"WARNING: {w:.1f} mm wide > {W_MAX} mm: art runs onto the grip panels")
    ztop = ((zmin + zmax + h) / 2 if a.align == "center" else zmax) + a.z_shift
    if ztop > zmax + 1e-6 or ztop - h < zmin - 1e-6: print(f"WARNING: art z {ztop - h:.2f}..{ztop:.2f} leaves free band {zmin:.2f}..{zmax:.2f}")
    tf = [s, 0, 0, -s, -CX * s + a.u_shift, ztop + Y0 * s]
    print(f"cup art: {w:.2f} x {h:.2f} mm, z {ztop - h:.2f}..{ztop:.2f} (local), {ztop - h - z0:.2f}..{ztop - z0:.2f} from cup bottom")
    tris = {}
    for c, g in art.items():
        tris[c] = triangulate(affine_transform(g, tf), 0.35)   # dense boundary for bending
        print(f"  {c}: raise {H[c]} mm")
    jt = os.path.join(WORK, "Work", f"{NAME}_tris.json")
    json.dump({"name": NAME, "R": R, "embed": EMBED, "heights": H, "hex": HEX, "tris": tris}, open(jt, "w"))
    cup_stl = os.path.join(WORK, "Work", "cup_preview.stl"); write_stl(cup_stl, V, T)
    run_blender("cup_decal_blender.py", jt, WORK, cup_stl)
    lv, lt = read_stl(os.path.join(WORK, "STL", f"{NAME} - Logo.stl"))
    lr = np.hypot(lv[:, 0], lv[:, 1])
    print(f"cup relief r {lr.min():.3f}..{lr.max():.3f} (wall {R:.3f})")
    i = m.rindex("\n", 0, m.index("</vertices>")) + 1; m = m[:i] + vxml(lv) + m[i:]
    i = m.rindex("\n", 0, m.index("</triangles>")) + 1; m = m[:i] + txml(lt + len(V)) + m[i:]
    edits[MODEL] = m; faces[OBJ] = len(T) + len(lt)

# ---------- lid: flush inlay on the top face ----------
if DO_LID:
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    LID, LID_NAME, LMODEL = find_obj(a.lid_object, "lid")
    m, V, T = read_mesh(LMODEL)
    z0 = V[:, 2].min()
    on = np.all(np.abs(V[T][:, :, 2] - z0) < 2e-3, axis=1)
    face = unary_union([Polygon(t[:, :2]).buffer(1e-4) for t in V[T[on]] if Polygon(t[:, :2]).area > 1e-9]).buffer(-1e-4)
    e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]]])
    _, lab = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(len(V), len(V))), directed=False)
    nshell = len(set(lab[T[on][:, 0]]))
    print(f"lid: object {LID} '{LID_NAME}' ({LMODEL}), {len(V)} verts {len(T)} tris, face z {z0:.2f}, face shells {nshell}")
    if nshell > 1 and not a.force: die("lid face already has inlaid art (--force to continue)")
    if nshell > 1: face = max(getattr(face, "geoms", [face]), key=lambda g: g.area)
    if face.geom_type != "Polygon" or not face.interiors: die(f"lid face at z {z0:.2f} is not one disc with a straw hole")
    disc = Polygon(face.exterior); hole = Polygon(max(face.interiors, key=lambda r: Polygon(r).area))
    Rf = math.sqrt(disc.area / math.pi); oc = np.array(disc.centroid.coords[0])
    hc = np.array(hole.centroid.coords[0]) - oc; rh = math.sqrt(hole.area / math.pi); dh = np.hypot(*hc)
    # frame (a right, b up) as read from outside (view x = -local x), hole straight up at (0, dh)
    bl = hc / dh                                   # up, in local xy
    al = np.array([-bl[1], bl[0]])                 # right, in local xy (mirrored view)
    print(f"  face R {Rf:.2f}, straw hole d {2 * rh:.2f} at {dh:.2f} mm from center")
    allowed = Point(0, 0).buffer(Rf - LID_EDGE, 256)
    if a.lid_place != "through": allowed = allowed.difference(Point(0, dh).buffer(rh + LID_HOLE_GAP, 128))
    pa = prep(allowed)
    shp = filled(sil).simplify(2)   # holes filled: art never straddles the straw hole
    def place(g, s, ta, tb): return affine_transform(g, [s, 0, 0, -s, ta - CX * s, tb + CY * s])
    sx, sy = a.lid_shift.split(",")
    ta0, tb0 = float(sx), float(sy)
    top = dh - rh - LID_HOLE_GAP
    def fits(s):  # -> (ta, tb) or None
        h = (Y1 - Y0) * s
        if a.lid_place == "below":
            tb = (top - (Rf - LID_EDGE)) / 2 + tb0   # centered in the span below the hole
            return (ta0, tb) if pa.contains(place(shp, s, ta0, tb)) else None
        if a.lid_place == "through":
            return (ta0, tb0) if pa.contains(place(shp, s, ta0, tb0)) else None
        st = 0.5; grid = np.arange(-Rf, Rf + st, st)
        ok = [(x, y) for x in grid for y in grid if pa.contains(place(shp, s, x, y))]
        if not ok: return None
        c = np.mean(ok, axis=0); best = min(ok, key=lambda p: np.hypot(p[0] - c[0], p[1] - c[1]))
        return (best[0] + ta0, best[1] + tb0)
    if a.lid_height_mm:
        s = a.lid_height_mm / (Y1 - Y0); pos = fits(s)
        if pos is None: die(f"--lid-height-mm {a.lid_height_mm} does not fit with --lid-place {a.lid_place}")
    else:
        lo, hi = 0.0, 2 * Rf / max(X1 - X0, Y1 - Y0)
        if a.lid_place == "miss": hi = min(hi, 2 * Rf / (Y1 - Y0))
        for _ in range(16 if a.lid_place != "miss" else 9):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if fits(mid) else (lo, mid)
        s = lo; pos = fits(s)
        if pos is None or s <= 0: die("art does not fit on the lid")
    ta, tb = pos
    lw, lh = (X1 - X0) * s, (Y1 - Y0) * s
    print(f"lid art ({a.lid_place}): {lw:.2f} x {lh:.2f} mm, center {ta:.2f},{tb:.2f} mm (right,up from lid center; hole up)")
    # frame -> local: p_local = oc + a*al + b*bl
    M = [al[0], bl[0], al[1], bl[1], oc[0], oc[1]]
    keep = face.buffer(-(0.5 if a.lid_place == "through" else 0.05))    # through: hole cuts the art, 0.5 rim stays
    ltris, lg = {}, []
    for c, g in art.items():
        gl = affine_transform(place(g, s, ta, tb), M).intersection(keep)
        gl = unary_union([p for p in getattr(gl, "geoms", [gl]) if p.geom_type == "Polygon" and p.area > 0.05])
        if gl.is_empty: print(f"  {c}: nothing left on the lid"); continue
        ltris[c] = triangulate(gl, 0.5); lg.append(gl)
        print(f"  {c}: {gl.area:.0f} mm2, {len(getattr(gl, 'geoms', [gl]))} pieces")
    cut = unary_union([g.buffer(1e-3, join_style="mitre") for g in lg])   # one clean outline: touching colors would leave inner walls
    jt = os.path.join(WORK, "Work", f"{NAME}_lid_tris.json")
    rz = math.atan2(bl[0], -bl[1])   # preview camera from below: hole up
    json.dump({"name": NAME, "z0": z0, "depth": LID_DEPTH, "hex": HEX, "tris": ltris, "cut": triangulate(cut, 0.5), "cam_rz": rz,
               "center": [float(oc[0]), float(oc[1])]}, open(jt, "w"))
    cap_stl = os.path.join(WORK, "Work", "lid_src.stl"); write_stl(cap_stl, V, T)
    run_blender("lid_inlay_blender.py", jt, WORK, cap_stl)
    nv, nt = read_stl(os.path.join(WORK, "STL", f"{NAME} Lid.stl"))
    i = m.index("<vertices>") + len("<vertices>\n"); j = m.rindex("\n", 0, m.index("</vertices>")) + 1; m = m[:i] + vxml(nv) + m[j:]
    i = m.index("<triangles>") + len("<triangles>\n"); j = m.rindex("\n", 0, m.index("</triangles>")) + 1; m = m[:i] + txml(nt) + m[j:]
    edits[LMODEL] = m; faces[LID] = len(nt)
    print(f"lid tris {len(T)} -> {len(nt)}")

if a.dry_run: sys.exit(f"dry run: previews in {os.path.join(WORK, 'Images')}")

# ---------- write 3MF ----------
for oid, n in faces.items():
    i = cfg.index(f'<object id="{oid}">'); j = cfg.index("</object>", i)
    cfg = cfg[:i] + re.sub(r'face_count="\d+"', f'face_count="{n}"', cfg[i:j]) + cfg[j:]
edits["Metadata/model_settings.config"] = cfg
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
tmp = a.out + ".tmp"  # write beside, then replace: out may be the src (in-place)
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
    for it in zin.infolist():
        data = edits[it.filename].encode() if it.filename in edits else zin.read(it)
        zo.writestr(it, data, compress_type=zipfile.ZIP_DEFLATED)
zin.close()
os.replace(tmp, a.out)
print(f"wrote {a.out}")
