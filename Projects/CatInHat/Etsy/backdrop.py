"""Bright storybook backdrop for compositing real product photos: sky-blue wall with outlined cartoon clouds,
red/white striped tablecloth, fuzzy pom-poms, book stack. No product; the camera focuses where the product will stand.

usage: blender -b --python backdrop.py -- <out.png> <width> <height> <samples> [closeup]
"""
import bpy, sys, math, random
from mathutils import Vector

A = sys.argv[sys.argv.index("--") + 1:]
OUT, RW, RH, SAMPLES = A[0], int(A[1]), int(A[2]), int(A[3])
CLOSE = len(A) > 4 and A[4] == "closeup"
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
random.seed(11)

def mat(name, rgb, rough=0.5, sheen=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    if sheen: b.inputs["Sheen Weight"].default_value = sheen
    return m

def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

# ---------- wall: sky gradient ----------
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.75, 1.0), rotation=(math.radians(90), 0, 0))
wall = bpy.context.object; wall.scale = (4, 2.4, 1)
m = bpy.data.materials.new("Sky"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.42; ramp.color_ramp.elements[0].color = (*srgb("8FD3F5"), 1)
ramp.color_ramp.elements[1].position = 0.62; ramp.color_ramp.elements[1].color = (*srgb("2E9BE6"), 1)
nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs["Y"], ramp.inputs[0])
nt.links.new(ramp.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
em = nt.nodes["Principled BSDF"]; nt.links.new(ramp.outputs[0], em.inputs["Emission Color"]); em.inputs["Emission Strength"].default_value = 0.0
wall.data.materials.append(m)

# ---------- cartoon clouds on the wall (white puffs with a navy outline) ----------
white = mat("CloudW", srgb("FFFFFF"), 0.8); white.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1, 1, 1, 1)
white.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 0.05
navy = mat("Outline", srgb("1B3A6B"), 0.8)
def cloud(cx, cz, s):
    puffs = [(-0.9, 0, 0.55), (-0.35, 0.25, 0.7), (0.3, 0.3, 0.75), (0.85, 0.05, 0.55), (0.0, -0.15, 0.6), (-0.6, -0.2, 0.45), (0.6, -0.2, 0.45)]
    for (dx, dz, r) in puffs:
        for rr, y, mm in ((r * s, 0.72, white), (r * s + 0.006, 0.725, navy)):
            bpy.ops.mesh.primitive_cylinder_add(radius=rr, depth=0.004, vertices=64, location=(cx + dx * s, y, cz + dz * s), rotation=(math.radians(90), 0, 0))
            bpy.context.object.data.materials.append(mm)
for (cx, cz, s) in [(-0.42, 0.62, 0.085), (0.05, 0.78, 0.07), (0.46, 0.55, 0.09), (-0.2, 0.38, 0.05), (0.3, 0.30, 0.045), (-0.62, 0.30, 0.06), (0.75, 0.80, 0.07), (-0.75, 0.85, 0.06), (0.62, 0.15, 0.04)]:
    cloud(cx, cz, s)

# ---------- table + striped tablecloth ----------
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -0.2, 0)); tab = bpy.context.object; tab.scale = (4, 1.9, 1)
m = bpy.data.materials.new("Cloth"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, math.radians(28))
sep = nt.nodes.new("ShaderNodeSeparateXYZ"); mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 1 / 0.032
fr = nt.nodes.new("ShaderNodeMath"); fr.operation = 'FRACT'; gt = nt.nodes.new("ShaderNodeMath"); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.5
mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'; mix.inputs[6].default_value = (*srgb("D7262E"), 1); mix.inputs[7].default_value = (*srgb("F4F1EC"), 1)
nt.links.new(tc.outputs["Object"], mp.inputs[0]); nt.links.new(mp.outputs[0], sep.inputs[0]); nt.links.new(sep.outputs["X"], mul.inputs[0])
nt.links.new(mul.outputs[0], fr.inputs[0]); nt.links.new(fr.outputs[0], gt.inputs[0]); nt.links.new(gt.outputs[0], mix.inputs[0])
nt.links.new(mix.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85; b.inputs["Sheen Weight"].default_value = 0.4
wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 600; wv.inputs["Distortion"].default_value = 2  # woven texture
nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 8; nz.inputs["Detail"].default_value = 4       # soft folds
ad = nt.nodes.new("ShaderNodeMath"); ad.operation = 'MULTIPLY_ADD'; ad.inputs[1].default_value = 0.15
bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25
nt.links.new(wv.outputs["Fac"], ad.inputs[0]); nt.links.new(nz.outputs["Fac"], ad.inputs[2]); nt.links.new(ad.outputs[0], bump.inputs["Height"])
nt.links.new(bump.outputs[0], b.inputs["Normal"])
tab.data.materials.append(m)

# ---------- pom-poms (hair particles) ----------
def pompom(loc, r, hexc):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=r * 0.55, location=loc); o = bpy.context.object
    hm = bpy.data.materials.new("Pom"); hm.use_nodes = True; nt = hm.node_tree; nt.nodes.remove(nt.nodes["Principled BSDF"])
    hb = nt.nodes.new("ShaderNodeBsdfHairPrincipled"); hb.parametrization = 'COLOR'; hb.inputs["Color"].default_value = (*srgb(hexc), 1)
    hb.inputs["Roughness"].default_value = 0.5; nt.links.new(hb.outputs[0], nt.nodes["Material Output"].inputs[0])
    o.data.materials.append(hm)
    ps = o.modifiers.new("hair", 'PARTICLE_SYSTEM').particle_system.settings
    ps.type = 'HAIR'; ps.count = 7000; ps.hair_length = r * 0.5; ps.use_advanced_hair = True; ps.normal_factor = 1.0
    ps.child_type = 'INTERPOLATED'; ps.child_percent = 6; ps.rendered_child_count = 6; ps.child_length = 1.0
    ps.root_radius = 0.0005; ps.tip_radius = 0.0002; ps.material = 1
for loc, r, c in [((-0.21, -0.12, 0.034), 0.042, "1E78D6"), ((0.24, 0.10, 0.036), 0.045, "E0262E"), ((-0.33, 0.28, 0.03), 0.036, "E0262E"), ((0.20, -0.20, 0.026), 0.032, "1E78D6")]:
    pompom(loc, r, c)

# ---------- book stack (right, behind) ----------
z = 0
for i, (hexc, sx, sy, sz, rz) in enumerate([("C8202A", 0.15, 0.11, 0.025, 6), ("1E5FB8", 0.14, 0.10, 0.022, -5), ("F2EFE8", 0.13, 0.095, 0.02, 9), ("C8202A", 0.12, 0.085, 0.02, -3)]):
    for (ex, ey, ez, mm) in ((0, 0, 0, mat(f"Book{i}", srgb(hexc), 0.5)), (-0.006, 0.003, -0.008, mat(f"Pg{i}", srgb("EDE6D3"), 0.8))):
        bpy.ops.mesh.primitive_cube_add(location=(0.40, 0.32, z + sz / 2), rotation=(0, 0, math.radians(-18 + rz)))
        bk = bpy.context.object; bk.scale = (sx / 2 + ex, sy / 2 + ey, sz / 2 + ez); bk.data.materials.append(mm)
        if mm.name.startswith("Book"): bv = bk.modifiers.new("b", 'BEVEL'); bv.width = 0.002; bv.segments = 3
    z += sz

# ---------- lights + camera ----------
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (*srgb("BFE6FF"), 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.25
def area(loc, size, e, col=(1, 1, 1), tgt=(0, 0.1, 0.15)):
    l = bpy.data.lights.new("A", 'AREA'); l.size = size; l.energy = e; l.color = col
    o = bpy.data.objects.new("A", l); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
area((-0.8, -0.9, 1.1), 1.0, 70, (1, 0.96, 0.9)); area((0.9, -0.6, 0.6), 1.0, 30, (0.92, 0.96, 1)); area((0, -0.2, 1.5), 1.5, 25)
sun = bpy.data.lights.new("Sun", 'SUN'); sun.energy = 0.6; sun.angle = math.radians(12)
so = bpy.data.objects.new("Sun", sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-30))

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 70 if CLOSE else 50; cam.data.sensor_fit = 'AUTO'
tgt = Vector((0, 0, 0.11 if CLOSE else 0.17)); loc = Vector((0, -0.45 if CLOSE else -0.62, 0.13 if CLOSE else 0.2))
cam.location = loc; cam.rotation_euler = (tgt - loc).to_track_quat('-Z', 'Y').to_euler()
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = (tgt - loc).length; cam.data.dof.aperture_fstop = 2.0 if CLOSE else 2.8

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
sc.render.resolution_x, sc.render.resolution_y = RW, RH
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'; sc.view_settings.exposure = -0.2
sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("DONE", OUT)
