import bpy, math, sys, random
from mathutils import Matrix, Vector, Euler

args = sys.argv[sys.argv.index("--") + 1:]
SHOT, OUT = args[0], args[1]
SAMPLES = int(args[2]) if len(args) > 2 else 256
RES = int(args[3]) if len(args) > 3 else 2000

P = r"G:\Blender\blender-mcp\Projects\NewCupProject"
G = P + r"\GrinchCup"
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
M_GREEN_LINES_OFF = pla("GreenTop", srgb("#00AE42"), lines=False)
M_RED_TOP = pla("RedTop", srgb("#C12E1F"), lines=False)

root = bpy.data.objects.new("CupRig", None); sc.collection.objects.link(root)
root.scale = (S, S, S)

def imp(path, mat, M=Matrix.Identity(4), parent=root):
    bpy.ops.wm.stl_import(filepath=path)
    o = bpy.context.selected_objects[0]
    o.data.transform(M); o.data.materials.clear(); o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = False
    o.parent = parent
    return o

def shade_auto(o, ang=35):
    o.data.set_sharp_from_angle(angle=math.radians(ang)) if hasattr(o.data, "set_sharp_from_angle") else None
    for p in o.data.polygons: p.use_smooth = True

# ---------- cup ----------
cup = imp(G + r"\Grinch Cup - Cup.stl", M_WHITE); shade_auto(cup)

def paint_ribs(o, mat):
    import numpy as np
    me = o.data; me.materials.append(mat); n = len(me.polygons)
    c = np.zeros(n * 3, np.float32); me.polygons.foreach_get("center", c); c = c.reshape(-1, 3)
    x, y, z = c.T; r = np.hypot(x, y); ab = (np.degrees(np.arctan2(y, x)).round().astype(int)) % 360
    idx = np.zeros(n, np.int32)
    for zc in (37.8, 65.3, 92.7):  # every other rib red (candy cane)
        near = ((np.abs(z - zc) > 2.0) & (np.abs(z - zc) < 3.5)) & (r < 41.4) & (r > 38)
        bins = np.zeros(360, bool); bins[ab[near]] = True
        bins = bins | np.roll(bins, 1) | np.roll(bins, -1)
        floor = np.median(r[near])
        idx[(np.abs(z - zc) < 1.9) & (r > floor + 0.2) & bins[ab]] = 1
    me.polygons.foreach_set("material_index", idx); me.update()
    print("RIBS faces", int(idx.sum()))
paint_ribs(cup, M_RED)
for part, mat in [("Black", M_BLACK), ("Green", M_GREEN), ("Red", M_RED), ("Text", M_RED), ("White", M_WHITE)]:
    imp(G + rf"\Grinch Cup - Grinch_{part}.stl", mat)

# ---------- parts from assembly blend ----------
with bpy.data.libraries.load(BLU) as (src, dst):
    dst.objects = [n for n in src.objects if n in ("Handle", "HandlePin", "Spigot", "Cap")]
shift = Matrix.Translation((0, -CY, 0))
parts = {}
for o in dst.objects:
    if o.name.startswith("Cap"): continue
    sc.collection.objects.link(o)
    o.data = o.data.copy(); o.data.transform(shift @ o.matrix_world); o.matrix_world = Matrix.Identity(4)
    o.data.materials.clear(); o.data.materials.append(M_RED if o.name.startswith("HandlePin") else M_GREEN)
    shade_auto(o); o.parent = root; parts[o.name.split(".")[0]] = o
pin = parts["HandlePin"]
pin2 = pin.copy(); pin2.data = pin.data.copy(); pin2.data.transform(Matrix.Scale(-1, 4, (1, 0, 0))); pin2.data.flip_normals(); sc.collection.objects.link(pin2)

# handle pivot = pin center
pv = sum((v.co for v in pin.data.vertices), Vector()) / len(pin.data.vertices)
PIVOT = Vector((0, pv.y, pv.z))
handle = parts["Handle"]
hp = bpy.data.objects.new("HandlePivot", None); sc.collection.objects.link(hp)
hp.parent = root; hp.location = PIVOT
handle.data.transform(Matrix.Translation(-PIVOT)); handle.parent = hp

def set_handle(deg):  # positive = tilt toward back (+Y)
    hp.rotation_euler = (math.radians(-deg), 0, 0)

# ---------- caps ----------
CAP_TOP = 130.2
FLIP = Matrix.Translation((0, 0, CAP_TOP)) @ Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Rotation(math.pi, 4, 'X')
def make_cap(kind, M=FLIP, parent=root):
    grp = bpy.data.objects.new("Cap_" + kind, None); sc.collection.objects.link(grp); grp.parent = parent
    name = "Merry Grinchmas" if kind == "merry" else "Mean One"
    c = imp(G + rf"\Grinch Cap {name} - Cap.stl", M_WHITE, M, grp); shade_auto(c)
    if kind == "merry":
        imp(G + rf"\Grinch Cap {name} - Text_Green.stl", M_GREEN_LINES_OFF, M, grp)
        imp(G + rf"\Grinch Cap {name} - Text_Red.stl", M_RED_TOP, M, grp)
    else:
        imp(G + rf"\Grinch Cap {name} - Text_Red.stl", M_RED_TOP, M, grp)
    return grp

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
    # az 0 = front (camera on -Y), positive = rotate toward +X (cup's right side seen from front)
    a, e = math.radians(az_deg), math.radians(el_deg)
    root.rotation_euler = (0, 0, -a)  # spin product, keep camera + backdrop fixed
    t = Vector(target)
    loc = t + Vector((0, -dist * math.cos(e), dist * math.sin(e)))
    look(loc, t, **kw)
    return 0

def lights_for(az):
    rot = Matrix.Rotation(az, 3, 'Z')
    area("Key", rot @ Vector((-0.45, -0.45, 0.55)), 0.45, 14, (1, 0.93, 0.85))
    area("Fill", rot @ Vector((0.55, -0.35, 0.25)), 0.6, 5, (0.85, 0.92, 1))
    area("RimL", rot @ Vector((-0.35, 0.40, 0.35)), 0.25, 12, (1, 0.8, 0.6))
    area("RimR", rot @ Vector((0.35, 0.40, 0.35)), 0.25, 10, (0.8, 1, 0.85))
    area("Top", (0, 0, 0.7), 0.3, 3)

# ---------- shots ----------
if SHOT == "merry_hero":
    make_cap("merry"); set_handle(88); a = orbit(-25, 20, 0.50, target=(0, 0, 0.068)); lights_for(a)
elif SHOT == "mean_hero":
    make_cap("mean"); set_handle(88); a = orbit(25, 20, 0.50, target=(0, 0, 0.068)); lights_for(a)
elif SHOT == "front":
    make_cap("merry"); set_handle(0); a = orbit(0, 8, 0.62, target=(0, 0, 0.090)); lights_for(a)
elif SHOT == "left":
    make_cap("merry"); set_handle(0); a = orbit(-90, 10, 0.62, target=(0, 0, 0.090)); lights_for(a)
elif SHOT == "right":
    make_cap("mean"); set_handle(0); a = orbit(90, 10, 0.62, target=(0, 0, 0.090)); lights_for(a)
elif SHOT == "back_three_q":
    make_cap("merry"); set_handle(0); a = orbit(140, 16, 0.62, target=(0, 0, 0.090)); lights_for(a)
elif SHOT == "back":
    make_cap("mean"); set_handle(-88); a = orbit(180, 18, 0.50, target=(0, 0, 0.068)); lights_for(a)
elif SHOT == "caps_top":
    # cup hidden; two caps upright on table, overhead
    for o in list(root.children):
        if o.name != "HandlePivot": o.hide_render = True
    for o in [hp, handle]: o.hide_render = True
    for o in root.children_recursive: o.hide_render = True
    zoff = Matrix.Translation((0, 0, 23.0)) @ Matrix.Rotation(math.pi, 4, 'X')
    for kind, x in (("merry", -47), ("mean", 47)):
        g = make_cap(kind, M=zoff); g.location = (x, 0, 0)
        g.rotation_euler = (0, 0, math.radians(-150))
    a = orbit(0, 30, 0.46, target=(0, 0, 0.016)); lights_for(a)
else:
    raise SystemExit("unknown shot")

# ---------- render ----------
LAYER = args[4] if len(args) > 4 else "full"
prod = [o for o in root.children_recursive if o.type == 'MESH']
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
