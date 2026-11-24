"""Assembly-instruction renders for the Cat in the Hat balloon: part subsets, exploded offsets, clean studio set.
Geometry/pose from the .blend, colors from Work/blend_shots.json, PLA + layer lines from Workflow/Renders/scene_env.py.
Writes <out>.png plus <out>.json (2D pixel positions of the shot's anchors/arrows, for annotate.py).

usage: blender -b --python render_steps.py -- <steps.json> <shot> <out.png> <samples> <res>
"""
import bpy, sys, os, json, math
from mathutils import Vector, Matrix, Euler
from bpy_extras.object_utils import world_to_camera_view

ARGS = sys.argv[sys.argv.index("--") + 1:]
STEPS, SHOT, OUT, SAMPLES, RES = ARGS[0], ARGS[1], ARGS[2], int(ARGS[3]), int(ARGS[4])
cfg = json.load(open(STEPS))
shot = next(s for s in cfg["shots"] if s["name"] == SHOT)
bs = json.load(open(cfg["blend_shots"]))
S = 0.001

bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, cfg["workflow_dir"])
import scene_env as env
env.LINES = shot.get("layer_lines", cfg.get("layer_lines", 1.0))
sc = env.sc

FIL = [env.pla(f"F{i + 1}", env.lin(h), rough=0.35 if max(env.lin(h)) < 0.02 else 0.42) for i, h in enumerate(bs["filaments"])]
colors = {**bs["parts"], **cfg.get("assign", {})}

# ---------- parts ----------
def pick(pats):  # name prefixes -> part names
    return [n for n in colors if any(n.startswith(p) for p in pats)]
names = pick(shot.get("parts", cfg["all_parts"]))
names = [n for n in names if not any(n.startswith(p) for p in shot.get("drop", []))]
moves = {n: Vector(v) for pre, v in shot.get("move", {}).items() for n in pick([pre])}

W = bpy.data.objects.new("World", None); sc.collection.objects.link(W)
rig = bpy.data.objects.new("Rig", None); sc.collection.objects.link(rig); rig.parent = W
with bpy.data.libraries.load(cfg["blend"], link=False) as (src, dst): dst.objects = [n for n in src.objects if n in names]
prod = []
for o in dst.objects:
    sc.collection.objects.link(o)
    o.data = o.data.copy(); o.data.transform(o.matrix_world); o.matrix_world.identity()
    if o.name in moves: o.data.transform(Matrix.Translation(moves[o.name]))
    o.parent = rig; o.data.materials.clear(); o.data.materials.append(FIL[colors[o.name] - 1])
    for p in o.data.polygons: p.use_smooth = True
    if hasattr(o.data, "set_sharp_from_angle"): o.data.set_sharp_from_angle(angle=0.61)
    prod.append(o)

def rod(name, a, b, ext=3, r=0.875):  # extra filament string a->b (mm, assembly coords)
    a, b = Vector(a), Vector(b); d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, vertices=16, location=(a + b) / 2)
    o = bpy.context.object; o.name = name; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    bpy.ops.object.transform_apply(location=True, rotation=True)
    o.parent = rig; o.data.materials.append(FIL[ext - 1]); prod.append(o)
for i, (a, b) in enumerate(shot.get("rods", [])): rod(f"XRod{i}", a, b)

# whole-model pose (mm-space rotation, e.g. lying on its back), then units + floor/centering
pose = Euler([math.radians(x) for x in shot.get("rot", [0, 0, 0])]).to_matrix().to_4x4()
rig.matrix_basis = Matrix.Scale(S, 4) @ pose
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in prod for c in o.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
if "center_mm" in shot: cx, cy = (pose @ Vector((*shot["center_mm"], 0))).xy * S
else: cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
rig.matrix_basis = Matrix.Translation((-cx, -cy, -lo.z)) @ rig.matrix_basis
bpy.context.view_layer.update()
H = hi.z - lo.z
def world(p): return rig.matrix_world @ Vector(p)  # assembly mm -> world (before turntable spin)

# ---------- studio set: seamless cyclorama, soft lights ----------
bg = env.plain("Cyc", tuple(cfg.get("cyc_rgb", (0.42, 0.47, 0.52))), 0.85)
R, Y0 = 0.6, 0.7
prof = [(y, 0) for y in (-4, Y0)] + [(Y0 + R * math.sin(t * math.pi / 32), R - R * math.cos(t * math.pi / 32)) for t in range(1, 17)] + [(Y0 + R, 4)]
me = bpy.data.meshes.new("Cyc"); vs = [(x, y, z) for (y, z) in prof for x in (-4, 4)]
me.from_pydata(vs, [], [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(len(prof) - 1)])
cyc = bpy.data.objects.new("Cyc", me); sc.collection.objects.link(cyc); me.materials.append(bg)
for p in me.polygons: p.use_smooth = True
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.55, 0.6, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.35

fr = shot.get("frame_mm", max(H, hi.x - lo.x, hi.y - lo.y) * 1000 * 1.2 * shot.get("zoom", 1)) * S  # framed size (m)
tz = shot["tz_mm"] * S if "tz_mm" in shot else H / 2
if "target_mm" in shot: tgt = world(shot["target_mm"]); tz = tgt.z; rig.matrix_basis = Matrix.Translation((-tgt.x, -tgt.y, 0)) @ rig.matrix_basis
bpy.context.view_layer.update()
L = max(fr, 0.12)
env.cfg_light_tz = tz
for nm, loc, size, en, col in [("Key", (-1.0, -1.1, 1.2), 0.9, 40, (1, 0.96, 0.9)), ("Fill", (1.2, -0.9, 0.5), 1.2, 16, (0.92, 0.96, 1)),
                               ("RimL", (-0.8, 0.8, 0.9), 0.5, 18, (0.9, 0.95, 1)), ("RimR", (0.8, 0.8, 0.9), 0.5, 18, (1, 0.97, 0.92)),
                               ("Top", (0, 0, 1.6), 0.8, 10, (1, 1, 1))]:
    env.area(nm, tuple(c * L for c in loc[:2]) + (tz + loc[2] * L,), size * L, en * L * L, col, target=(0, 0, tz))

# ---------- camera (turntable: product spins, camera/set/lights fixed) ----------
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 85
dist = fr / (2 * 18 / 85)
a, e = math.radians(shot.get("az", -30)), math.radians(shot.get("el", 15))
W.rotation_euler = (0, 0, -a)
t = Vector((0, 0, tz)); loc = t + Vector((0, -dist * math.cos(e), dist * math.sin(e)))
cam.location = loc; cam.rotation_euler = (t - loc).to_track_quat('-Z', 'Y').to_euler()
cam.data.dof.use_dof = False
sc.render.resolution_x = sc.render.resolution_y = RES  # before projecting anchors (aspect)
bpy.context.view_layer.update()

# 2D anchors for annotate.py: points given in assembly mm (+ the moved part's offset)
def px(p, part=None):
    v = Vector(p) + (moves.get(part, Vector()) if part else Vector())
    c = world_to_camera_view(sc, cam, rig.matrix_world @ v)
    return [round(c.x * RES), round((1 - c.y) * RES)]
ann = {"labels": [{**l, "px": px(l["p"], l.get("part"))} for l in shot.get("labels", [])],
       "arrows": [{**r, "a_px": px(r["a"], r.get("part_a")), "b_px": px(r["b"], r.get("part_b"))} for r in shot.get("arrows", [])]}
json.dump(ann, open(os.path.splitext(OUT)[0] + ".json", "w"), indent=1)

sc.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons["cycles"].preferences
for dev in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = dev; prefs.get_devices()
        if any(d.type == dev for d in prefs.devices):
            for d in prefs.devices: d.use = d.type == dev
            sc.cycles.device = 'GPU'; break
    except Exception: pass
sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = RES
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Base Contrast'
sc.view_settings.exposure = shot.get("exposure", cfg.get("exposure", 0.0))
sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("DONE", OUT)
