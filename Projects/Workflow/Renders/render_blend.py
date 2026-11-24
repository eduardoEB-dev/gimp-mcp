"""Blender side of run_blend.py: renders an already-assembled multi-part model straight from its .blend
(parts in mm, no materials needed) in a scene_env.py set. Part colors come from the 3MF via blend_shots.json.
One call = one shot, one layer (fg | bg | full), same as render_3mf.py.

usage: blender -b --python render_blend.py -- <work_dir> --inspect                       -> <work_dir>/blend_parts.json
       blender -b --python render_blend.py -- <work_dir> <shot> <out.png> <samples> <res> <fg|bg|full>
"""
import bpy, sys, os, json
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:]
WORK = ARGS[0]
HERE = os.path.dirname(os.path.abspath(__file__))
S = 0.001  # mm -> m

if ARGS[1] == "--inspect":  # run with the .blend opened: list renderable mesh parts + bounds
    parts = []
    for o in bpy.data.objects:
        if o.type != 'MESH': continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        parts.append({"name": o.name, "collections": [c.name for c in o.users_collection], "hide_render": o.hide_render,
                      "polys": len(o.data.polygons), "min": [min(v[i] for v in bb) for i in range(3)], "max": [max(v[i] for v in bb) for i in range(3)]})
    json.dump({"unit_scale": bpy.context.scene.unit_settings.scale_length, "parts": parts}, open(os.path.join(WORK, "blend_parts.json"), "w"), indent=1)
    print("DONE inspect"); sys.exit()

SHOT, OUT, SAMPLES, RES, LAYER = ARGS[1:6]
SAMPLES, RES = int(SAMPLES), int(RES)
cfg = json.load(open(os.path.join(WORK, "blend_shots.json")))
shot = next(s for s in cfg["shots"] if s["name"] == SHOT)

bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, HERE)
import scene_env as env
cfg = {**cfg, **{k: shot[k] for k in ("layer_lines", "exposure") if k in shot}}  # per-shot overrides (close-ups want lighter lines)
env.LINES = cfg.get("layer_lines", 1.0)
sc = env.sc

FIL = [env.pla(f"F{i + 1}", env.lin(h), rough=0.35 if max(env.lin(h)) < 0.02 else 0.42) for i, h in enumerate(cfg["filaments"])]
W = bpy.data.objects.new("World", None); sc.collection.objects.link(W)
rig = bpy.data.objects.new("Rig", None); sc.collection.objects.link(rig); rig.parent = W; rig.scale = (S, S, S)
rig.location = cfg["offset"]  # bbox center over the turntable axis, base on the table
if "center_mm" in shot: rig.location.x, rig.location.y = (-c * S for c in shot["center_mm"])  # close-ups: detail on the axis = in focus

names = list(cfg["parts"])
with bpy.data.libraries.load(cfg["blend"], link=False) as (src, dst): dst.objects = [n for n in src.objects if n in names]
for o in dst.objects: sc.collection.objects.link(o)
bpy.context.view_layer.update()  # appended objects' matrix_world is stale until evaluated (Snoopy candle bowl landed at z=0)
for o in dst.objects:
    o.data = o.data.copy(); o.data.transform(o.matrix_world); o.matrix_world.identity()  # bake: object coords = assembled mm (layer lines run along world Z)
    e = cfg["parts"][o.name]; fz = any(o.name.startswith(p) for p in cfg.get("fuzzy") or [])
    if fz and f"Fuzzy{e}" not in bpy.data.materials: env.fuzzy(f"Fuzzy{e}", env.lin(cfg["filaments"][e - 1]), cfg.get("fuzzy_strength", 1.0))
    o.parent = rig; o.data.materials.clear(); o.data.materials.append(bpy.data.materials[f"Fuzzy{e}"] if fz else FIL[e - 1])
    for p in o.data.polygons: p.use_smooth = True
    if hasattr(o.data, "set_sharp_from_angle"): o.data.set_sharp_from_angle(angle=0.61)  # ~35 deg, as render_3mf

def candle(c):  # spec "candle": generic 3-wick jar candle (render-only prop, no label) sitting in the product, e.g. a candle holder pocket
    import math
    cx, cy = c.get("center_mm", [0, 0]); z0, d, h = c.get("z_mm", 0), c.get("d_mm", 102), c.get("h_mm", 95)
    R, zt, rim = d / 2, z0 + h, c.get("rim_mm", 12)  # rim = clear glass band above the wax
    def cyl(name, r, za, zb, mat, bevel=0.0, verts=128, fill='NGON'):
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=zb - za, location=(cx, cy, (za + zb) / 2), end_fill_type=fill)
        o = bpy.context.active_object; o.name = name; o.data.materials.append(mat); o.parent = rig
        for p in o.data.polygons: p.use_smooth = True
        if bevel: m = o.modifiers.new("b", 'BEVEL'); m.width = bevel; m.segments = 4; m.limit_method = 'ANGLE'
        return o
    jar = env.plain("Jar", env.lin(c.get("jar", "#F2C72E")), rough=0.12); jb = jar.node_tree.nodes["Principled BSDF"]
    jb.inputs["Coat Weight"].default_value = 1.0; jb.inputs["Coat Roughness"].default_value = 0.03
    jb.inputs["Emission Color"].default_value = jb.inputs["Base Color"].default_value; jb.inputs["Emission Strength"].default_value = c.get("jar_glow", 0)  # printed-glass jars read brighter than plain diffuse
    glass = env.plain("Glass", (1, 1, 1), rough=0.02); gb = glass.node_tree.nodes["Principled BSDF"]
    gb.inputs["Transmission Weight"].default_value = 1.0; gb.inputs["IOR"].default_value = 1.5
    wax = env.plain("Wax", env.lin(c.get("wax", "#F6DE6A")), rough=0.45); wb = wax.node_tree.nodes["Principled BSDF"]
    wb.inputs["Subsurface Weight"].default_value = 0.3; wb.inputs["Subsurface Radius"].default_value = (4, 3, 1.5); wb.inputs["Subsurface Scale"].default_value = 1.0
    wick = env.plain("Wick", (0.02, 0.018, 0.015), rough=0.9)
    cyl("Candle_Jar", R, z0, zt - rim, jar, bevel=3)
    cyl("Candle_Wax", R - 3, zt - rim - 0.5, zt - rim + 0.6, wax)
    tube = cyl("Candle_Rim", R, zt - rim - 0.5, zt, glass, fill='NOTHING')  # open glass band, rounded lip
    m = tube.modifiers.new("s", 'SOLIDIFY'); m.thickness = 3; m.offset = -1; m.use_rim = True
    m = tube.modifiers.new("b", 'BEVEL'); m.width = 1.2; m.segments = 3
    flame = env.mat_emit("Flame", (1.0, 0.55, 0.15), c.get("flame", 12)) if c.get("lit", True) else None
    for i in range(3):
        a = math.radians(90 + 120 * i); wx, wy = cx + 0.45 * R * math.cos(a), cy + 0.45 * R * math.sin(a)
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.8, depth=8, location=(wx, wy, zt - rim + 4))
        w = bpy.context.active_object; w.name = f"Candle_Wick{i}"; w.data.materials.append(wick); w.parent = rig; w.rotation_euler = (0.08, 0.05 * (i - 1), 0)
        if flame:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=c.get("flame_r", 3.2), location=(wx, wy, zt - rim + 15))
            f = bpy.context.active_object; f.name = f"Candle_Flame{i}"; f.scale = (1, 1, 2.8); f.data.materials.append(flame); f.parent = rig
            for p in f.data.polygons: p.use_smooth = True
            for v in f.data.vertices: v.co.x *= 1 - 0.55 * max(0, v.co.z / 3.2); v.co.y *= 1 - 0.55 * max(0, v.co.z / 3.2)  # teardrop: taper the top
            L = bpy.data.lights.new(f"FlameL{i}", 'POINT'); L.energy = c.get("light_w", 0.35); L.color = (1.0, 0.62, 0.3); L.shadow_soft_size = 0.004
            lo = bpy.data.objects.new(f"FlameL{i}", L); sc.collection.objects.link(lo); lo.parent = rig; lo.location = (wx, wy, zt - rim + 16)

if cfg.get("candle"): candle(cfg["candle"])
FSTOP = env.build(cfg)
env.shoot({**shot, "world": W}, [o for o in W.children_recursive if o.type == 'MESH'], LAYER, OUT, SAMPLES, RES, shot.get("fstop", FSTOP))
