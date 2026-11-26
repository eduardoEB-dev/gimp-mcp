import bpy, math, sys, random
from mathutils import Matrix, Vector, Euler

args = sys.argv[sys.argv.index("--") + 1:]
SHOT, OUT = args[0], args[1]
SAMPLES = int(args[2]) if len(args) > 2 else 256
RES = int(args[3]) if len(args) > 3 else 2000

P = r"G:\Blender\blender-mcp\Projects\NewCupProject"
MESH = r"G:\gimp-mcp\Projects\Cup\Ad Images\Snoopy\Mesh"  # npz from extract.py (SnoopyCupProject.3mf, paint kept)
BLU = P + r"\BlenderFiles\New_Cup_Solid_Half_BLU.blend"
CY = 41.91
S = 0.001  # mm -> m

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ---------- materials ----------
def pla(name, rgb, rough=0.42, lines=True):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.45
    if lines:  # subtle FDM layer lines (0.2 mm) in object Z
        tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 2 * math.pi / 0.2
        sn = nt.nodes.new("ShaderNodeMath"); sn.operation = 'SINE'
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.08; bump.inputs["Distance"].default_value = 0.00005
        nt.links.new(tc.outputs["Object"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], mul.inputs[0])
        nt.links.new(mul.outputs[0], sn.inputs[0]); nt.links.new(sn.outputs[0], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

M_WHITE = pla("White", (0.82, 0.82, 0.80))
M_RED = pla("Red", srgb("#C12E1F"))
M_GREEN = pla("Green", srgb("#00AE42"))
M_BLACK = pla("Black", (0.012, 0.012, 0.012), rough=0.35)
M_YELLOW = pla("Yellow", srgb("#FFFF00"))
M_BLACK_TOP = pla("BlackTop", (0.012, 0.012, 0.012), rough=0.35, lines=False)

import numpy as np
W = bpy.data.objects.new("World", None); sc.collection.objects.link(W)

def shade_auto(o, ang=35):
    if hasattr(o.data, "set_sharp_from_angle"): o.data.set_sharp_from_angle(angle=math.radians(ang))
    for p in o.data.polygons: p.use_smooth = True

def npz_obj(name, oid, M, mats, parent):
    d = np.load(f"{MESH}/obj{oid}.npz"); v = d["v"]; f = d["f"]; p = d["p"]
    v = (np.c_[v, np.ones(len(v))] @ np.array(M).T)[:, :3]
    me = bpy.data.meshes.new(name); me.from_pydata(v.tolist(), [], f.tolist())
    for m in mats: me.materials.append(m)
    me.polygons.foreach_set("material_index", p.astype(np.int32)); me.update()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o); o.parent = parent; shade_auto(o); return o

# 3MF object frames -> cup frame (cup axis at x=y=0, base z=0)
CUP_M = Matrix.Translation((0, -0.4, 58.42))
CAP_TOP = 130.2
CAP_M = Matrix.Translation((0, 0, CAP_TOP)) @ Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Rotation(math.pi, 4, 'X') @ Matrix.Translation((0, 0, 11.5))
CUPS = {"christmas": 36, "xmas": 39}   # 36 = MERRY CHRISTMAS (yellow eyes), 39 = MERRY X-MAS
# paint index -> extruder: 0 default, 1 black, 2 white, 3 red, 4 green, 5 yellow
CUP_MATS = [M_WHITE, M_BLACK, M_WHITE, M_RED, M_GREEN, M_YELLOW]
CAP_MATS = [M_RED, M_BLACK_TOP, M_WHITE, M_RED, M_GREEN, M_YELLOW]

with bpy.data.libraries.load(BLU) as (src, dst):
    dst.objects = [n for n in src.objects if n in ("Handle", "HandlePin", "Spigot")]
shift = Matrix.Translation((0, -CY, 0))
LIB = {}
for o in dst.objects:
    me = o.data.copy(); me.transform(shift @ o.matrix_world); LIB[o.name] = me
pv = sum((v.co for v in LIB["HandlePin"].vertices), Vector()) / len(LIB["HandlePin"].vertices)
PIVOT = Vector((0, pv.y, pv.z))
LIB["Handle"].transform(Matrix.Translation(-PIVOT))
pin2 = LIB["HandlePin"].copy(); pin2.transform(Matrix.Scale(-1, 4, (1, 0, 0))); pin2.flip_normals(); LIB["HandlePin2"] = pin2

def lib_obj(name, mat, parent):
    o = bpy.data.objects.new(name, LIB[name].copy()); sc.collection.objects.link(o)
    o.data.materials.clear(); o.data.materials.append(mat); o.parent = parent; shade_auto(o); return o

def make_rig(kind, x=0.0, rot=0.0, handle=0, cup=True, cap=True):
    rig = bpy.data.objects.new("Rig_" + kind, None); sc.collection.objects.link(rig)
    rig.parent = W; rig.scale = (S, S, S); rig.location = (x, 0, 0); rig.rotation_euler = (0, 0, math.radians(rot))
    if cup:
        npz_obj("Cup_" + kind, CUPS[kind], CUP_M, CUP_MATS, rig)
        lib_obj("Spigot", M_RED, rig); lib_obj("HandlePin", M_RED, rig); lib_obj("HandlePin2", M_RED, rig)
        hp = bpy.data.objects.new("HandlePivot", None); sc.collection.objects.link(hp)
        hp.parent = rig; hp.location = PIVOT; hp.rotation_euler = (math.radians(-handle), 0, 0)
        lib_obj("Handle", M_GREEN, hp)
    if cap:
        npz_obj("Cap", 37, CAP_M, CAP_MATS, rig)
    return rig

# ---------- environment ----------
def mat_emit(name, rgb, st):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*rgb, 1); e.inputs[1].default_value = st
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs[0]); return m

def wood_mat():
    m = bpy.data.materials.new("Wood"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (40, 4, 40)
    wv = nt.nodes.new("ShaderNodeTexNoise"); wv.inputs["Scale"].default_value = 3; wv.inputs["Detail"].default_value = 8; wv.inputs["Distortion"].default_value = 2.5
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.035, 0.014, 0.005, 1); ramp.color_ramp.elements[1].color = (0.13, 0.055, 0.02, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs[0]); nt.links.new(mp.outputs[0], wv.inputs[0])
    nt.links.new(wv.outputs["Fac"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.7
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15
    nt.links.new(wv.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs[0], b.inputs["Normal"])
    return m

bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0)); floor = bpy.context.object
floor.data.materials.append(wood_mat())

# backdrop: dark evergreen gradient wall
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 1.1, 1.5), rotation=(math.radians(90), 0, 0)); wall = bpy.context.object
wm = bpy.data.materials.new("Wall"); wm.use_nodes = True; wm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.006, 0.03, 0.012, 1)
wm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
wall.data.materials.append(wm)

# bokeh fairy lights + ornaments in background
random.seed(7)
gold = mat_emit("Gold", (1.0, 0.62, 0.25), 30); redl = mat_emit("RedL", (1.0, 0.12, 0.08), 10); grn = mat_emit("GrnL", (0.2, 1.0, 0.3), 6)
for i in range(160):
    x = random.uniform(-0.7, 0.7); y = random.uniform(0.55, 1.05); z = random.uniform(0.03, 0.7)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(0.004, 0.008), location=(x, y, z), segments=12, ring_count=6)
    r = random.random(); bpy.context.object.data.materials.append(gold if r < 0.75 else (redl if r < 0.92 else grn))
orn = bpy.data.materials.new("Orn"); orn.use_nodes = True; ob = orn.node_tree.nodes["Principled BSDF"]
ob.inputs["Base Color"].default_value = (0.5, 0.01, 0.01, 1); ob.inputs["Metallic"].default_value = 0.9; ob.inputs["Roughness"].default_value = 0.15
for (x, y, r) in [(-0.22, 0.18, 0.035), (0.26, 0.30, 0.045), (0.17, 0.12, 0.022), (-0.35, 0.45, 0.05)]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, y, r), segments=48, ring_count=24)
    bpy.ops.object.shade_smooth(); bpy.context.object.data.materials.append(orn)

# world
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.025, 0.03, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1

def area(name, loc, size, energy, color=(1, 1, 1), target=(0, 0, 0.07)):
    l = bpy.data.lights.new(name, 'AREA'); l.size = size; l.energy = energy; l.color = color
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    d = Vector(target) - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); return o

# ---------- camera ----------
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 85; cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = 3.2

def look(cam_loc, target, lens=85, fstop=3.2):
    cam.location = cam_loc; cam.data.lens = lens; cam.data.dof.aperture_fstop = fstop
    d = Vector(target) - Vector(cam_loc); cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.data.dof.focus_distance = d.length

def orbit(az_deg, el_deg, dist, target=(0, 0, 0.075), **kw):
    # az 0 = front (camera on -Y); spins the product, camera + backdrop stay fixed
    a, e = math.radians(az_deg), math.radians(el_deg)
    W.rotation_euler = (0, 0, -a)
    t = Vector(target)
    look(t + Vector((0, -dist * math.cos(e), dist * math.sin(e))), t, **kw)
    return 0

def lights_for(az):
    area("Key", (-0.45, -0.45, 0.55), 0.45, 14, (1, 0.93, 0.85))
    area("Fill", (0.55, -0.35, 0.25), 0.6, 5, (0.85, 0.92, 1))
    area("RimL", (-0.35, 0.40, 0.35), 0.25, 12, (1, 0.8, 0.6))
    area("RimR", (0.35, 0.40, 0.35), 0.25, 10, (0.8, 1, 0.85))
    area("Top", (0, 0, 0.7), 0.3, 3)

# ---------- shots ----------
X = 0.052  # pair half-spacing (m)
if SHOT == "pair_hero":
    make_rig("xmas", -X, 10, handle=88); make_rig("christmas", X, -10, handle=88); orbit(0, 20, 0.62, target=(0, 0, 0.064))
elif SHOT == "pair_front":
    make_rig("xmas", -X, handle=0); make_rig("christmas", X, handle=0); orbit(0, 8, 0.74, target=(0, 0, 0.090))
elif SHOT == "xmas_hero":
    make_rig("xmas", handle=88); orbit(-25, 20, 0.50, target=(0, 0, 0.068))
elif SHOT == "christmas_hero":
    make_rig("christmas", handle=88); orbit(25, 20, 0.50, target=(0, 0, 0.068))
elif SHOT == "left":
    make_rig("christmas", handle=0); orbit(-90, 10, 0.62, target=(0, 0, 0.090))
elif SHOT == "right":
    make_rig("xmas", handle=0); orbit(90, 10, 0.62, target=(0, 0, 0.090))
elif SHOT == "back_three_q":
    make_rig("christmas", handle=0); orbit(140, 16, 0.62, target=(0, 0, 0.090))
elif SHOT == "cap_top":
    g = make_rig("cap", cup=False); g.location = (0, 0, -(CAP_TOP - 23.0) * S)
    orbit(0, 32, 0.36, target=(0, 0, 0.012))
else:
    raise SystemExit("unknown shot")
lights_for(0)

# ---------- render ----------
LAYER = args[4] if len(args) > 4 else "full"
prod = [o for o in W.children_recursive if o.type == 'MESH']
env = [o for o in sc.objects if o.type == 'MESH' and o not in prod]
if LAYER == "fg":    # product only, tack sharp
    for o in env: o.is_holdout = True
    sc.render.film_transparent = True; cam.data.dof.use_dof = False
elif LAYER == "bg":  # blurred set, product invisible to camera but still casts shadows/reflections
    for o in prod: o.visible_camera = False
sc.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons["cycles"].preferences
for dev in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = dev; prefs.get_devices()
        if any(d.type == dev for d in prefs.devices):
            for d in prefs.devices: d.use = d.type == dev
            sc.cycles.device = 'GPU'; print("DEVICE", dev); break
    except Exception as ex: print("devfail", dev, ex)
sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = RES
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'; sc.view_settings.exposure = 0.1
sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("DONE", OUT)
