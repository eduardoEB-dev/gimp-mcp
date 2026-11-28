"""Shared Blender set for TryCatch ad renders: PLA material with FDM layer lines, scene themes, camera + fg/bg layer render.
Used by render_3mf.py (3MF cooler cups) and render_blend.py (assembled .blend models). Import after bpy factory reset."""
import bpy, math, random
from mathutils import Vector

sc = bpy.context.scene
LINES = 1.0  # FDM layer-line strength multiplier (set by caller)
cfg_light_tz = 0.07  # height the set lights aim at (m); build() reads cfg "light_tz"
cfg_exposure = 0.1  # AgX exposure; build() reads cfg "exposure"

# ---------- materials ----------
def pla(name, rgb, rough=0.42, lines=True):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.45
    if lines:  # FDM layer lines (0.2 mm) in object Z, slightly uneven like a real print; strength from shots.json
        tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 2 * math.pi / 0.2
        sn = nt.nodes.new("ShaderNodeMath"); sn.operation = 'SINE'
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.4; nz.inputs["Detail"].default_value = 2
        amp = nt.nodes.new("ShaderNodeMath"); amp.operation = 'MULTIPLY_ADD'; amp.inputs[2].default_value = 0.6
        h = nt.nodes.new("ShaderNodeMath"); h.operation = 'MULTIPLY'
        bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.55 * LINES; bump.inputs["Distance"].default_value = 0.0001
        nt.links.new(tc.outputs["Object"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], mul.inputs[0])
        nt.links.new(mul.outputs[0], sn.inputs[0])
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"]); nt.links.new(nz.outputs["Fac"], amp.inputs[0]); amp.inputs[1].default_value = 0.8
        nt.links.new(sn.outputs[0], h.inputs[0]); nt.links.new(amp.outputs[0], h.inputs[1])
        nt.links.new(h.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
        # layer lines also catch light unevenly: tiny roughness variation per layer
        rr = nt.nodes.new("ShaderNodeMath"); rr.operation = 'MULTIPLY_ADD'; rr.inputs[1].default_value = 0.05 * LINES; rr.inputs[2].default_value = rough
        nt.links.new(sn.outputs[0], rr.inputs[0]); nt.links.new(rr.outputs[0], b.inputs["Roughness"])
    return m

def fuzzy(name, rgb, strength=1.0):
    """Bambu fuzzy skin (0.2 mm jitter, 0.6 mm point distance): fine grainy bump in object mm coords, stretched along
    layers (0.2 mm tall cells), more matte. Object coords must be mm (render_blend bakes parts in mm)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = 0.62
    b.inputs["Specular IOR Level"].default_value = 0.35
    tc = nt.nodes.new("ShaderNodeTexCoord"); sc_ = nt.nodes.new("ShaderNodeVectorMath"); sc_.operation = 'MULTIPLY'
    sc_.inputs[1].default_value = (1 / 0.6, 1 / 0.6, 1 / 0.2)  # cells: 0.6 mm around, one per 0.2 mm layer
    vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 1.0; vo.inputs["Randomness"].default_value = 1.0
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 1
    mix = nt.nodes.new("ShaderNodeMath"); mix.operation = 'MULTIPLY_ADD'; mix.inputs[1].default_value = 0.5
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.9 * strength; bump.inputs["Distance"].default_value = 0.0002
    nt.links.new(tc.outputs["Object"], sc_.inputs[0]); nt.links.new(sc_.outputs[0], vo.inputs["Vector"]); nt.links.new(sc_.outputs[0], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], mix.inputs[0]); nt.links.new(vo.outputs["Distance"], mix.inputs[2])
    nt.links.new(mix.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m

def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    if min(c) > 0.95: return (0.82, 0.82, 0.80)          # pure white blows out; PLA white reads as light grey
    if max(c) < 0.05: return (0.012, 0.012, 0.012)
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

# ---------- environment ----------
def mat_emit(name, rgb, st):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (*rgb, 1); e.inputs[1].default_value = st
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs[0]); return m


def wood_mat(dark, light):
    m = bpy.data.materials.new("Wood"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (40, 4, 40)
    wv = nt.nodes.new("ShaderNodeTexNoise"); wv.inputs["Scale"].default_value = 3; wv.inputs["Detail"].default_value = 8; wv.inputs["Distortion"].default_value = 2.5
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*dark, 1); ramp.color_ramp.elements[1].color = (*light, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs[0]); nt.links.new(mp.outputs[0], wv.inputs[0])
    nt.links.new(wv.outputs["Fac"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.7
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15
    nt.links.new(wv.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs[0], b.inputs["Normal"])
    return m

def plain(name, rgb, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    return m

def area(name, loc, size, energy, color=(1, 1, 1), target=None):
    target = target or (0, 0, cfg_light_tz)
    l = bpy.data.lights.new(name, 'AREA'); l.size = size; l.energy = energy; l.color = color
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()

def bokeh(n, cols, weights):
    for i in range(n):
        x = random.uniform(-0.7, 0.7); y = random.uniform(0.55, 1.05); z = random.uniform(0.03, 0.7)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(0.004, 0.008), location=(x, y, z), segments=12, ring_count=6)
        bpy.context.object.data.materials.append(random.choices(cols, weights)[0])

def wall_and_table(wall_rgb, wood_dark, wood_light, world_rgb):
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0)); bpy.context.object.data.materials.append(wood_mat(wood_dark, wood_light))
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 1.1, 1.5), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(plain("Wall", wall_rgb, 0.9))
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (*world_rgb, 1)


def basketball_court(hoop=True):
    maple = wood_mat((0.15, 0.068, 0.026), (0.53, 0.30, 0.125))
    wood_nodes = maple.node_tree
    surface = next(n for n in wood_nodes.nodes if n.type == 'BSDF_PRINCIPLED')
    grain = surface.inputs["Base Color"].links[0].from_socket
    position = wood_nodes.nodes.new("ShaderNodeNewGeometry")
    planks = wood_nodes.nodes.new("ShaderNodeTexBrick")
    planks.inputs["Scale"].default_value = 1
    planks.inputs["Brick Width"].default_value = 0.26
    planks.inputs["Row Height"].default_value = 0.042
    planks.inputs["Mortar Size"].default_value = 0.00045
    planks.inputs["Color1"].default_value = (0.64, 0.56, 0.48, 1)
    planks.inputs["Color2"].default_value = (0.97, 0.94, 0.91, 1)
    planks.inputs["Mortar"].default_value = (0.24, 0.20, 0.16, 1)
    combine = wood_nodes.nodes.new("ShaderNodeMixRGB")
    combine.blend_type = 'MULTIPLY'
    combine.inputs[0].default_value = 0.72
    wood_nodes.links.new(position.outputs["Position"], planks.inputs["Vector"])
    wood_nodes.links.new(grain, combine.inputs[1])
    wood_nodes.links.new(planks.outputs["Color"], combine.inputs[2])
    wood_nodes.links.new(combine.outputs[0], surface.inputs["Base Color"])
    graphite = plain("Graphite court paint", (0.027, 0.039, 0.049), 0.52)
    white = plain("Court markings", (0.74, 0.73, 0.66), 0.56)
    black = plain("Backboard padding", (0.014, 0.019, 0.024))
    board = plain("Backboard", (0.36, 0.43, 0.46), 0.24)
    orange = plain("Rim enamel", (0.69, 0.13, 0.031), 0.32)

    def box(name, xyz, size, material):
        bpy.ops.mesh.primitive_cube_add(size=1, location=xyz)
        obj = bpy.context.object
        obj.name = name
        obj.dimensions = size
        obj.data.materials.append(material)

    def stroke(name, points, radius, material, closed=False):
        curve = bpy.data.curves.new(name, 'CURVE')
        curve.dimensions = '3D'
        curve.bevel_depth = radius
        curve.bevel_resolution = 3
        spline = curve.splines.new('POLY')
        spline.points.add(len(points) - 1)
        for point, xyz in zip(spline.points, points):
            point.co = (*xyz, 1)
        spline.use_cyclic_u = closed
        obj = bpy.data.objects.new(name, curve)
        sc.collection.objects.link(obj)
        obj.data.materials.append(material)

    def circle(x, y, z, radius, start=0, sweep=math.tau, steps=64):
        angles = [start + sweep * i / steps for i in range(steps + 1)]
        return [(x + radius * math.cos(a), y + radius * math.sin(a), z) for a in angles]

    box("Maple courtside platform", (0, -0.18, -0.015), (1.60, 0.79, 0.03), maple)
    arc = circle(-0.185, 0.105, 0.0002, 0.12, -1.25, 2.27)
    inside = circle(-0.185, 0.105, 0.0002, 0.113, -1.25, 2.27)
    paint = bpy.data.meshes.new("Court arc paint")
    paint.from_pydata(inside + arc, [], [(i, i + len(inside), i + len(inside) + 1, i + 1)
                                         for i in range(len(inside) - 1)])
    paint.materials.append(graphite)
    sc.collection.objects.link(bpy.data.objects.new("Court arc paint", paint))
    box("Maple court", (0, 0.73, -0.561), (3.0, 2.35, 0.02), maple)
    box("Painted key", (0.32, 0.91, -0.550), (0.85, 0.97, 0.002), graphite)
    stroke("Key outline", [(-0.105, 1.395, -0.547), (-0.105, 0.425, -0.547),
                           (0.745, 0.425, -0.547), (0.745, 1.395, -0.547)], 0.005, white)
    stroke("Free-throw arc", circle(0.32, 0.425, -0.547, 0.31, math.pi, math.pi), 0.005, white)
    stroke("Center-circle arc", circle(-0.45, -0.09, -0.547, 0.34, 0, math.pi), 0.005, white)
    box("Arena wall", (0, 1.54, -0.05), (4, 0.05, 1), black)
    for row in range(4):
        box("Bleacher row", (0, 1.48 - row * 0.035, -0.09 - row * 0.065),
            (4, 0.06, 0.03), graphite)

    if hoop:
        x, y, z = 0.195, 0.86, 0.023
        box("Hoop support", (x, y + 0.20, -0.234), (0.034, 0.034, 0.63), black)
        box("Hoop bracket", (x, y + 0.09, z + 0.027), (0.035, 0.22, 0.024), black)
        box("Backboard surround", (x, y, z + 0.066), (0.232, 0.018, 0.140), black)
        box("Backboard panel", (x, y - 0.011, z + 0.069), (0.219, 0.009, 0.126), board)
        stroke("Backboard target", [(x - 0.047, y - 0.017, z + 0.023),
                                    (x + 0.047, y - 0.017, z + 0.023),
                                    (x + 0.047, y - 0.017, z + 0.091),
                                    (x - 0.047, y - 0.017, z + 0.091)], 0.003, white, True)
        cy = y - 0.063
        stroke("Basketball rim", circle(x, cy, z, 0.043)[:-1], 0.0035, orange, True)
        rings = [circle(x, cy, z - depth, radius, start, steps=12)[:-1]
                 for depth, radius, start in [(0.003, 0.042, 0), (0.032, 0.033, math.pi / 12), (0.067, 0.024, 0)]]
        for i in range(12):
            j = (i + 1) % 12
            stroke("Basket net", [rings[0][i], rings[1][i], rings[2][i]], 0.00075, white)
            stroke("Basket net", [rings[0][j], rings[1][i], rings[2][j]], 0.00075, white)

    world = bpy.data.worlds.new("Arena ambient")
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.12, 0.14, 0.19, 1)
    area("Key softbox", (-0.31, -0.32, 0.42), 0.28, 12, (1, 0.95, 0.88))
    area("Fill softbox", (0.45, -0.24, 0.18), 0.38, 5, (0.87, 0.94, 1))
    area("Grazing rim light", (-0.25, 0.24, 0.20), 0.19, 8, (0.80, 0.89, 1))
    area("Top softbox", (0.09, 0.11, 0.47), 0.23, 5)
    area("Arena lights", (0.22, 0.52, 0.67), 0.75, 63, (1, 0.94, 0.82), (0.25, 0.92, -0.37))
    return 7.1


def build(cfg):
    """Build the requested set and return the camera f-stop."""
    global cfg_light_tz, cfg_exposure
    cfg_light_tz = cfg.get("light_tz", 0.07); cfg_exposure = cfg.get("exposure", 0.1)
    THEME = cfg.get("theme", "christmas")
    random.seed(7)
    FSTOP = 3.2
    if THEME == "basketball":
        return basketball_court(cfg.get("court_hoop", True))
    if THEME == "tabletop":
        wall_and_table((0.145, 0.198, 0.174), (0.17, 0.080, 0.031),
                       (0.37, 0.210, 0.102), (0.15, 0.17, 0.19))
        sc.cycles.use_auto_tile = True
        sc.cycles.tile_size = 512
        area("Window key", (-0.55, -0.20, 0.57), 0.58, 28, (1, 0.97, 0.91))
        area("Bounce fill", (0.45, -0.30, 0.33), 0.65, 12, (0.89, 0.95, 1))
        area("Edge light", (0.32, 0.33, 0.46), 0.34, 16, (1, 0.95, 0.88))
        area("Wall wash", (-0.43, 0.56, 0.44), 0.58, 19, (0.88, 0.97, 1), (0.0, 1.1, 0.22))
        return 5.0
    if THEME == "desk":
        # maker's desk: clean grey desk, curved monitor with code behind, sage wall (keyboard/mouse removed: looked fake)
        wall_and_table((0.045, 0.06, 0.045), (0.09, 0.085, 0.08), (0.13, 0.125, 0.115), (0.02, 0.022, 0.025))
        FSTOP = 4.5  # keep the code on screen recognizable
        def curved(name, w, h, y, zc, R=1.8, sub=96):  # vertical panel bent around the viewer (ultrawide curve)
            bpy.ops.mesh.primitive_grid_add(x_subdivisions=sub, y_subdivisions=2, size=1)
            o = bpy.context.object; o.name = name
            for v in o.data.vertices:
                x, zz = v.co.x * w, v.co.y * h
                v.co = Vector((x, y - x * x / (2 * R), zc + zz))
            return o
        scr = curved("Screen", 1.00, 0.42, 0.45, 0.25)
        sm = bpy.data.materials.new("ScreenImg"); sm.use_nodes = True; nt = sm.node_tree
        nt.nodes.remove(nt.nodes["Principled BSDF"])
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(cfg["screen"])
        em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 4.0
        nt.links.new(tex.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs[0])
        for p in scr.data.polygons: p.use_smooth = True
        scr.data.materials.append(sm)
        bez = curved("Bezel", 1.014, 0.434, 0.454, 0.25)  # thin border just behind the screen (camera always faces it)
        blk = plain("MonitorBlack", (0.012, 0.012, 0.013), 0.4); bez.data.materials.append(blk)
        bpy.ops.mesh.primitive_cube_add(location=(0, 0.50, 0.03)); nk = bpy.context.object; nk.scale = (0.035, 0.012, 0.03); nk.data.materials.append(blk)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.11, depth=0.008, location=(0, 0.50, 0.004)); bpy.context.object.scale = (1.4, 0.7, 1)
        bpy.context.object.data.materials.append(blk)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.008, depth=0.5, location=(0, 0.45, 0.485), rotation=(0, math.radians(90), 0))
        bpy.context.object.data.materials.append(plain("BarAlu", (0.05, 0.05, 0.055), 0.3, 0.8))  # monitor light bar
        area("Key", (-0.45, -0.45, 0.55), 0.5, 13, (1, 0.94, 0.86)); area("Fill", (0.55, -0.35, 0.25), 0.6, 5, (0.9, 0.95, 1))
        area("RimL", (-0.35, 0.30, 0.35), 0.25, 8, (0.75, 0.85, 1)); area("RimR", (0.35, 0.30, 0.35), 0.25, 8, (0.75, 0.85, 1))
        area("Top", (0, 0, 0.7), 0.3, 3)
    elif THEME == "seuss":
        # bright, playful, storybook: sky-blue wall, light wood, candy-colored bokeh, books + spilled popcorn
        wall_and_table((0.10, 0.32, 0.55), (0.20, 0.10, 0.04), (0.45, 0.25, 0.11), (0.25, 0.3, 0.38))
        bokeh(140, [mat_emit("Wht", (1, 0.95, 0.85), 18), mat_emit("Yel", (1, 0.8, 0.15), 14), mat_emit("Tea", (0.1, 0.85, 0.8), 10),
                    mat_emit("Cor", (1, 0.35, 0.3), 10)], [0.4, 0.25, 0.2, 0.15])
        for i, (rgb, sx, sy, sz, rz) in enumerate([((0.02, 0.35, 0.40), 0.20, 0.15, 0.030, 8), ((0.80, 0.55, 0.02), 0.18, 0.13, 0.025, -6),
                                                   ((0.03, 0.10, 0.45), 0.16, 0.12, 0.022, 14)]):
            z = sum(b[3] for b in [(0, 0, 0, 0.030), (0, 0, 0, 0.025), (0, 0, 0, 0.022)][:i])
            bpy.ops.mesh.primitive_cube_add(location=(-0.20, 0.33, z + sz / 2), rotation=(0, 0, math.radians(20 + rz)))
            bk = bpy.context.object; bk.scale = (sx / 2, sy / 2, sz / 2); bpy.ops.object.transform_apply(scale=True)
            bv = bk.modifiers.new("b", 'BEVEL'); bv.width = 0.002; bv.segments = 3
            bk.data.materials.append(plain(f"Book{i}", rgb, 0.55))
            bpy.ops.mesh.primitive_cube_add(location=(-0.20, 0.33, z + sz / 2), rotation=(0, 0, math.radians(20 + rz)))
            pg = bpy.context.object; pg.scale = (sx / 2 - 0.003, sy / 2 + 0.0005, sz / 2 - 0.003)  # page block peeking out
            pg.data.materials.append(plain(f"Pages{i}", (0.85, 0.82, 0.72), 0.8))
        corn = bpy.data.materials.new("Popcorn"); corn.use_nodes = True; cb = corn.node_tree.nodes["Principled BSDF"]
        cb.inputs["Base Color"].default_value = (0.92, 0.80, 0.55, 1); cb.inputs["Roughness"].default_value = 0.65
        cb.inputs["Subsurface Weight"].default_value = 0.3; cb.inputs["Subsurface Radius"].default_value = (0.004, 0.003, 0.002)
        from mathutils import noise
        placed = []
        while len(placed) < cfg.get("popcorn", 16):  # spilled popcorn count (0 = none)
            x, y = random.uniform(-0.32, 0.32), random.uniform(-0.12, 0.25)
            if math.hypot(x, y) < 0.13 or (math.hypot(x + 0.20, y - 0.33) < 0.14) or any(math.hypot(x - a, y - b) < 0.04 for a, b in placed): continue
            placed.append((x, y)); r = random.uniform(0.011, 0.015)
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=(x, y, r * 0.8))
            pc = bpy.context.object; seed = Vector((random.random() * 100, random.random() * 100, 0))
            for v in pc.data.vertices:  # lumpy "butterfly" popcorn
                d = v.co.normalized(); v.co = d * r * (0.75 + 0.55 * max(0, noise.noise(d * 2.2 + seed)))
            pc.rotation_euler = [random.uniform(0, 6.3) for _ in range(3)]
            bpy.ops.object.shade_smooth(); pc.data.materials.append(corn)
        area("Key", (-0.45, -0.45, 0.55), 0.5, 16, (1, 0.97, 0.92)); area("Fill", (0.55, -0.35, 0.25), 0.6, 7, (0.95, 0.97, 1))
        area("RimL", (-0.35, 0.40, 0.35), 0.25, 10, (1, 0.95, 0.85)); area("RimR", (0.35, 0.40, 0.35), 0.25, 10, (0.85, 0.95, 1))
        area("Top", (0, 0, 0.7), 0.3, 4)
    else:  # christmas: green wall, dark wood, gold/red/green bokeh, red ornaments
        wall_and_table((0.006, 0.03, 0.012), (0.035, 0.014, 0.005), (0.13, 0.055, 0.02), (0.02, 0.025, 0.03))
        bokeh(160, [mat_emit("Gold", (1.0, 0.62, 0.25), 30), mat_emit("RedL", (1.0, 0.12, 0.08), 10), mat_emit("GrnL", (0.2, 1.0, 0.3), 6)],
              [0.75, 0.17, 0.08])
        orn = plain("Orn", (0.5, 0.01, 0.01), 0.15, 0.9)
        for (x, y, r) in [(-0.22, 0.18, 0.035), (0.26, 0.30, 0.045), (0.17, 0.12, 0.022), (-0.35, 0.45, 0.05)]:
            bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, y, r), segments=48, ring_count=24)
            bpy.ops.object.shade_smooth(); bpy.context.object.data.materials.append(orn)
        area("Key", (-0.45, -0.45, 0.55), 0.45, 14, (1, 0.93, 0.85)); area("Fill", (0.55, -0.35, 0.25), 0.6, 5, (0.85, 0.92, 1))
        area("RimL", (-0.35, 0.40, 0.35), 0.25, 12, (1, 0.8, 0.6)); area("RimR", (0.35, 0.40, 0.35), 0.25, 10, (0.8, 1, 0.85))
        area("Top", (0, 0, 0.7), 0.3, 3)

    return FSTOP


# ---------- shot + render ----------
def shoot(shot, prod, layer, out, samples, res, fstop):
    """Camera orbit around world empty W (product spins, set stays). prod = product mesh objects.
    layer: fg = product only, no DOF, transparent; bg = set with DOF, product invisible to camera; full = both."""
    W = shot["world"]
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 85; cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = fstop
    a, e = math.radians(shot["az"]), math.radians(shot["el"])
    W.rotation_euler = (0, 0, -a)                       # spin product; camera + backdrop stay fixed
    t = Vector((0, 0, shot["tz"])); loc = t + Vector((0, -shot["dist"] * math.cos(e), shot["dist"] * math.sin(e)))
    cam.location = loc; cam.rotation_euler = (t - loc).to_track_quat('-Z', 'Y').to_euler(); cam.data.dof.focus_distance = (t - loc).length
    env = [o for o in sc.objects if o.type in {'MESH', 'CURVE'} and o not in prod]
    if layer == "fg":
        for o in env: o.is_holdout = True
        sc.render.film_transparent = True; cam.data.dof.use_dof = False
        sc.render.image_settings.color_mode = 'RGBA'
    elif layer == "bg":
        for o in prod: o.visible_camera = False
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dev in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = dev; prefs.get_devices()
            if any(d.type == dev for d in prefs.devices):
                for d in prefs.devices: d.use = d.type == dev
                sc.cycles.device = 'GPU'; break
        except Exception: pass
    sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Punchy'; sc.view_settings.exposure = cfg_exposure
    sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("DONE", out)
