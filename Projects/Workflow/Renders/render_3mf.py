"""Blender scene for TryCatch ad renders: cooler cup(s) from an extracted 3MF on a wood table with
Christmas bokeh. One call = one shot, one layer.
Layers: fg = product only, no DOF (sharp, transparent bg); bg = set with DOF, product invisible to camera
but still casting shadows/reflections. comp.py stacks fg over bg -> sharp product, blurred background.

usage: blender -b --python render_3mf.py -- <work_dir> <shot_name> <out.png> <samples> <res> <fg|bg|full>
reads <work_dir>/manifest.json (extract_3mf.py) and <work_dir>/shots.json (run_renders.py)
"""
import bpy, math, sys, os, json, random
import numpy as np
from mathutils import Matrix, Vector

WORK, SHOT, OUT, SAMPLES, RES, LAYER = sys.argv[sys.argv.index("--") + 1:][:6]
SAMPLES, RES = int(SAMPLES), int(RES)
HERE = os.path.dirname(os.path.abspath(__file__))
S = 0.001  # mm -> m
man = json.load(open(os.path.join(WORK, "manifest.json")))
cfg = json.load(open(os.path.join(WORK, "shots.json")))
shot = next(s for s in cfg["shots"] if s["name"] == SHOT)
OBJ = {o["label"]: o for o in man["objects"]}
ROLE = {}
for o in man["objects"]: ROLE.setdefault(o["role"], o)
asset = np.load(os.path.join(HERE, "assets", "cooler_parts.npz")); ainfo = json.load(open(os.path.join(HERE, "assets", "cooler_parts.json")))
PIVOT, CAP_TOP = Vector(ainfo["pivot"]), ainfo["cap_top"]
LINES = cfg.get("layer_lines", 1.0)  # FDM layer-line strength (renders must read as real 3D prints)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

sys.path.insert(0, HERE)
import scene_env as env
env.LINES = LINES
pla, lin, sc = env.pla, env.lin, env.sc


FIL = [pla(f"F{i + 1}", lin(h), rough=0.35 if max(lin(h)) < 0.02 else 0.42) for i, h in enumerate(man["filaments"])]
FIL_FLAT = [pla(f"F{i + 1}flat", lin(h), lines=False) for i, h in enumerate(man["filaments"])]
def fil(e, flat=False): return (FIL_FLAT if flat else FIL)[max(1, min(e, len(FIL))) - 1]

W = bpy.data.objects.new("World", None); sc.collection.objects.link(W)

def shade_auto(o, ang=35):
    if hasattr(o.data, "set_sharp_from_angle"): o.data.set_sharp_from_angle(angle=math.radians(ang))
    for p in o.data.polygons: p.use_smooth = True

def mesh_obj(name, v, f, mats, idx, parent):
    me = bpy.data.meshes.new(name); me.from_pydata(v.tolist(), [], f.tolist())
    for m in mats: me.materials.append(m)
    if idx is not None: me.polygons.foreach_set("material_index", idx.astype(np.int32))
    me.update(); o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); o.parent = parent; shade_auto(o); return o

def tf(v, M): return (np.c_[v, np.ones(len(v))] @ np.array(M).T)[:, :3]

def from_3mf(rec, M, parent, flat_paint=False):
    d = np.load(os.path.join(WORK, f"obj{rec['id']}.npz"))
    mats = [fil(rec["extruder"])] + [fil(i + 1, flat_paint) for i in range(len(FIL))]
    return mesh_obj(rec["label"], tf(d["v"], M), d["f"], mats, d["p"], parent)

def cup_matrix(rec):  # 3MF object frame -> cup frame: axis from top ring, base at z=0, front = -Y
    v = np.load(os.path.join(WORK, f"obj{rec['id']}.npz"))["v"]
    top = v[np.abs(v[:, 2] - (v[:, 2].max() - 1.3)) < 0.4]
    cx, cy = (top[:, 0].min() + top[:, 0].max()) / 2, (top[:, 1].min() + top[:, 1].max()) / 2
    return Matrix.Rotation(math.radians(cfg.get("cup_rot_deg", 0)), 4, 'Z') @ Matrix.Translation((-cx, -cy, -v[:, 2].min()))

def cap_matrix(rec, rot_deg):  # printed face-down -> on cup, face up
    v = np.load(os.path.join(WORK, f"obj{rec['id']}.npz"))["v"]
    c = (v.min(0) + v.max(0)) / 2
    flip = 0 if cfg.get("cap_face_up") else math.pi
    reference_z = v[:, 2].max() if cfg.get("cap_face_up") else v[:, 2].min()
    return (Matrix.Translation((0, 0, CAP_TOP)) @ Matrix.Rotation(math.radians(rot_deg), 4, 'Z') @
            Matrix.Scale(cfg.get("cap_scale", 1.0), 4) @ Matrix.Rotation(flip, 4, 'X') @
            Matrix.Translation((-c[0], -c[1], -reference_z)))

def hw(name, key, role, parent):
    if name in cfg.get("source_hardware", {}):
        part = cfg["source_hardware"][name]
        transform = (Matrix.Translation(part["offset"]) @
                     Matrix.Rotation(math.radians(part.get("rot", 0)), 4, 'Z') @
                     Matrix.Scale(part.get("scale", 1.0), 4))
        return from_3mf(OBJ[part["object"]], transform, parent)
    rec = ROLE.get(role)
    return mesh_obj(name, asset[key + "_v"], asset[key + "_f"], [fil(rec["extruder"] if rec else 1)], None, parent)

def make_rig(r):
    rig = bpy.data.objects.new("Rig", None); sc.collection.objects.link(rig)
    rig.parent = W; rig.scale = (S, S, S); rig.location = (r.get("x", 0), 0, 0); rig.rotation_euler = (0, 0, math.radians(r.get("rot", 0)))
    if r.get("cup"):
        rec = OBJ[r["cup"]]; cup_o = from_3mf(rec, cup_matrix(rec), rig)
        if "spigot" in ROLE or "Spigot" in cfg.get("source_hardware", {}):
            hw("Spigot", "Spigot", "spigot", rig)
        if "pin" in ROLE:
            hw("Pin", "HandlePin", "pin", rig)
            p2 = hw("Pin2", "HandlePin", "pin", rig)
            if "Pin2" not in cfg.get("source_hardware", {}):
                p2.scale = (-1, 1, 1)
        if "handle" in ROLE:
            hp = bpy.data.objects.new("HandlePivot", None); sc.collection.objects.link(hp)
            hp.parent = rig; hp.location = PIVOT; hp.rotation_euler = (math.radians(-r.get("handle", 0)), 0, 0)
            handle_o = hw("Handle", "Handle", "handle", hp)
    if r.get("cap"):
        rec = OBJ[r["cap"]]; M = cap_matrix(rec, cfg.get("cap_rot_deg", 180))
        if not r.get("cup"): M = Matrix.Translation((0, 0, -(CAP_TOP - 23.0))) @ M  # loose cap: sit on table
        from_3mf(rec, M, rig, flat_paint=True)
    return rig

FSTOP = env.build(cfg)

# ---------- shot ----------
for r in shot["rigs"]: make_rig(r)
env.shoot({**shot, "world": W}, [o for o in W.children_recursive if o.type == 'MESH'], LAYER, OUT, SAMPLES, RES, FSTOP)
