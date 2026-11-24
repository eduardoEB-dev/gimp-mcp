"""Blender side of the learning manual: builds a small demo scene per concept panel and renders it (Eevee).
usage: blender -b --python demos.py -- <raw_dir> [only_demo1,only_demo2]
Writes <raw_dir>/<demo>__<i>.png and <raw_dir>/<demo>.json (captions)."""
import bpy, bmesh, sys, os, math, json, random
from mathutils import Vector, Matrix, noise

ARGS = sys.argv[sys.argv.index("--") + 1:]
RAW = ARGS[0]; ONLY = set(ARGS[1].split(",")) if len(ARGS) > 1 and ARGS[1] else None
os.makedirs(RAW, exist_ok=True)
RES = (1000, 750)

COL = dict(main="#6C9BD2", gold="#F2B544", red="#E06C5A", green="#62B58F", grey="#B8BCC2", sel="#FF8C1A",
           seam="#E0302A", cut="#3D7BE0", wire="#1E2328", floor="#E9EBEE")
_mats = {}

def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)

def mat(key, alpha=1.0, rough=0.5, emit=0.0):
    k = (key, alpha, rough, emit)
    if k in _mats: return _mats[k]
    m = bpy.data.materials.new(f"{key}_{alpha}"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(COL.get(key, key)), 1); b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*lin(COL.get(key, key)), 1); b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"): m.surface_render_method = 'BLENDED'
        else: m.blend_method = 'BLEND'
        if hasattr(m, "use_transparency_overlap"): m.use_transparency_overlap = False
    _mats[k] = m; return m

def face_orient_mat():
    m = bpy.data.materials.new("FaceOrient"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    g = nt.nodes.new("ShaderNodeNewGeometry"); mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs["A"].default_value = (0.08, 0.25, 0.9, 1); mix.inputs["B"].default_value = (0.9, 0.08, 0.08, 1)
    nt.links.new(g.outputs["Backfacing"], mix.inputs["Factor"]); nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    return m

def bump_mat():
    m = bpy.data.materials.new("Bump"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(COL["gold"]), 1)
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 4; nz.inputs["Detail"].default_value = 4
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 1.0; bp.inputs["Distance"].default_value = 0.6
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m

# ---------- scene ----------
def reset():
    global _mats; _mats = {}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try: sc.render.engine = eng; break
        except TypeError: pass
    sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.resolution_percentage = 100
    try: sc.eevee.taa_render_samples = 48
    except Exception: pass
    sc.render.film_transparent = True; sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (*lin(COL["floor"]), 1); bg.inputs[1].default_value = 0.9
    sun = bpy.data.lights.new("Sun", 'SUN'); sun.energy = 2.6; sun.angle = math.radians(12)
    so = bpy.data.objects.new("Sun", sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(40), math.radians(-10), math.radians(-35))
    fl = bpy.data.lights.new("Fill", 'SUN'); fl.energy = 0.8; fl.angle = math.radians(40)
    fo = bpy.data.objects.new("Fill", fl); sc.collection.objects.link(fo); fo.rotation_euler = (math.radians(60), 0, math.radians(140))
    return sc

def link(o): bpy.context.scene.collection.objects.link(o); return o

def mk(name, bm, m="main", smooth=False, extra=()):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me))
    me.materials.append(mat(m) if isinstance(m, str) else m)
    for e in extra: me.materials.append(mat(e) if isinstance(e, str) else e)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    return o

def cube(size=2, loc=(0, 0, 0), scale=(1, 1, 1)):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=size)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ Matrix.Diagonal((*scale, 1)), verts=bm.verts); return bm

def cyl(r=1, d=2, seg=32, loc=(0, 0, 0), r2=None):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=d)
    bmesh.ops.translate(bm, vec=Vector(loc), verts=bm.verts); return bm

def sphere(r=1, u=32, v=16, loc=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    bmesh.ops.translate(bm, vec=Vector(loc), verts=bm.verts); return bm

def monkey():
    bm = bmesh.new(); bmesh.ops.create_monkey(bm); return bm

def grid(nx, ny, sx=2, sy=2, loc=(0, 0, 0)):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=1)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(loc) @ Matrix.Diagonal((sx / 2, sy / 2, 1, 1)), verts=bm.verts); return bm

def star_pts(n=5, r1=1, r2=0.45, z=0):
    return [Vector(((r1 if i % 2 == 0 else r2) * math.cos(math.pi / 2 + i * math.pi / n), (r1 if i % 2 == 0 else r2) * math.sin(math.pi / 2 + i * math.pi / n), z)) for i in range(2 * n)]

def prism(pts, z0, z1):
    bm = bmesh.new(); vs = [bm.verts.new((p.x, p.y, z0)) for p in pts]; f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f]); top = [v for v in r["geom"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, z1 - z0), verts=top); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); return bm

def evaluated(o):
    bpy.context.view_layer.update(); return o.evaluated_get(bpy.context.evaluated_depsgraph_get())

def wire(o, t=0.012, m="wire"):
    me = bpy.data.meshes.new_from_object(evaluated(o)); w = link(bpy.data.objects.new(o.name + "_wire", me))
    w.matrix_world = o.matrix_world.copy(); me.materials.clear(); me.materials.append(mat(m, rough=0.8))
    md = w.modifiers.new("W", 'WIREFRAME'); md.thickness = t; md.use_even_offset = True; md.use_replace = True; md.use_boundary = True
    return w

def tubes(segs, r=0.025, m="sel", name="Tubes"):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 3; cu.use_fill_caps = True
    for seg in segs:
        sp = cu.splines.new('POLY'); sp.points.add(len(seg) - 1)
        for p, c in zip(sp.points, seg): p.co = (*c, 1)
    o = link(bpy.data.objects.new(name, cu)); cu.materials.append(mat(m, rough=0.4)); return o

def edges_of(o, pred=lambda e: True):
    me = o.data; M = o.matrix_world
    return [[M @ me.vertices[e.vertices[0]].co, M @ me.vertices[e.vertices[1]].co] for e in me.edges if pred(e)]

def dot(p, r=0.06, m="sel"):
    o = mk("Dot", sphere(r, 16, 8, p), m, smooth=True); return o

def faces(o): return len(evaluated(o).data.polygons)

def shoot(path, az=-30, el=25, zoom=1.0, ortho=False, target=None, floor=True):
    sc = bpy.context.scene; bpy.context.view_layer.update()
    pts = []
    for o in sc.objects:
        if o.type not in ('MESH', 'CURVE') or o.hide_render: continue
        e = evaluated(o)
        if o.type == 'CURVE':
            me = e.to_mesh(); pts += [o.matrix_world @ v.co for v in me.vertices]; e.to_mesh_clear()
        else: pts += [o.matrix_world @ Vector(c) for c in e.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    tgt = Vector(target) if target else (lo + hi) / 2
    if floor and el >= 15 and not ortho:
        f = mk("Floor", grid(1, 1, 400, 400, (0, 0, lo.z - 0.002)), "floor"); f.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    a, e = math.radians(az), math.radians(el)
    fwd = -Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    right = fwd.cross(Vector((0, 0, 1))); right = right.normalized() if right.length > 1e-6 else Vector((1, 0, 0))
    up = right.cross(fwd).normalized()
    asp = RES[0] / RES[1]; cam = bpy.data.cameras.new("Cam"); cam.lens = 50; cam.sensor_width = 36; cam.sensor_fit = 'HORIZONTAL'
    th = 18 / 50; tv = th / asp
    rel = [p - tgt for p in pts]
    if ortho:
        cam.type = 'ORTHO'
        wx = max(abs(r.dot(right)) for r in rel) * 2; wy = max(abs(r.dot(up)) for r in rel) * 2
        cam.ortho_scale = max(wx, wy * asp) * 1.18 / zoom; d = 30
    else:
        d = max(max(abs(r.dot(right)) / th + r.dot(-fwd), abs(r.dot(up)) / tv + r.dot(-fwd)) for r in rel) * 1.14 / zoom
    co = link(bpy.data.objects.new("Cam", cam)); co.location = tgt - fwd * d
    co.rotation_euler = fwd.to_track_quat('-Z', 'Y').to_euler(); cam.clip_end = 1000; sc.camera = co
    sc.render.filepath = path; bpy.ops.render.render(write_still=True)

# ---------- demos: each panel = (caption, builder) ; builder returns dict of shoot kwargs and may set "count" ----------
D = {}
def demo(name, *panels, **kw): D[name] = (panels, kw)

# --- edges & corners
def p_sharp():
    mk("C", cube()); return {}
def p_chamfer():
    o = mk("C", cube()); m = o.modifiers.new("B", 'BEVEL'); m.width = 0.3; m.segments = 1; wire(o, 0.008); return {}
def p_round():
    o = mk("C", cube(), smooth=True); m = o.modifiers.new("B", 'BEVEL'); m.width = 0.3; m.segments = 6; m.harden_normals = False
    o.data.set_sharp_from_angle(angle=math.radians(30)) if hasattr(o.data, "set_sharp_from_angle") else None; return {}
demo("bevel", ("Sharp edges", p_sharp), ("Chamfer = flat cut (1 segment)", p_chamfer), ("Bevel / fillet = rounded (6 segments)", p_round))

def L_block(fillet=False):
    pts = [Vector(p) for p in [(-1.2, 0, 0), (1.2, 0, 0), (1.2, 0, 0.6), (-0.6, 0, 0.6), (-0.6, 0, 2), (-1.2, 0, 2)]]
    bm = bmesh.new(); vs = [bm.verts.new((p.x, -0.8, p.z)) for p in pts]; f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f]); bmesh.ops.translate(bm, vec=(0, 1.6, 0), verts=[v for v in r["geom"] if isinstance(v, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if fillet:
        inner = [e for e in bm.edges if all(abs(v.co.x + 0.6) < 1e-4 and abs(v.co.z - 0.6) < 1e-4 for v in e.verts)]
        bmesh.ops.bevel(bm, geom=inner + list({v for e in inner for v in e.verts}), offset=0.45, offset_type='OFFSET', segments=10, profile=0.5, affect='EDGES')
    o = mk("L", bm, smooth=True)
    if hasattr(o.data, "set_sharp_from_angle"): o.data.set_sharp_from_angle(angle=math.radians(30))
    return o
def p_L(): L_block(); return {"az": -35, "el": 18}
def p_Lf(): o = L_block(True); return {"az": -35, "el": 18}
demo("fillet", ("Hard inside corner", p_L), ("Fillet: smooth curved blend", p_Lf))

def top_face_bm(op):
    bm = cube(2, scale=(1, 1, 0.5)); top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    for f in bm.faces: f.material_index = 0
    if op == "sel": top.material_index = 1
    else:
        r = bmesh.ops.inset_region(bm, faces=[top], thickness=0.3, depth=0)
        top.material_index = 1
        if op == "recess":
            ex = bmesh.ops.extrude_face_region(bm, geom=[top]); vs = [v for v in ex["geom"] if isinstance(v, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, vec=(0, 0, -0.35), verts=vs); bmesh.ops.delete(bm, geom=[top], context='FACES') if False else None
    return bm
def p_in(op):
    def f():
        o = mk("S", top_face_bm(op), "main", extra=["sel"]); wire(o, 0.01); return {"el": 40}
    return f
demo("inset", ("Top face selected", p_in("sel")), ("Inset (I): new border, smaller face", p_in("inset")), ("Inset + extrude down = recess", p_in("recess")))

def p_outset():
    bm = grid(6, 6, 3, 3); fs = [f for f in bm.faces if abs(f.calc_center_median().x) < 0.6 and abs(f.calc_center_median().y) < 0.6]
    r = bmesh.ops.inset_region(bm, faces=fs, thickness=0.25, depth=0, use_outset=True)
    for f in fs: f.material_index = 1
    o = mk("G", bm, "main", extra=["sel"]); wire(o, 0.01); return {"el": 55}
def p_outset0():
    bm = grid(6, 6, 3, 3)
    for f in bm.faces:
        if abs(f.calc_center_median().x) < 0.6 and abs(f.calc_center_median().y) < 0.6: f.material_index = 1
    o = mk("G", bm, "main", extra=["sel"]); wire(o, 0.01); return {"el": 55}
demo("outset", ("Faces selected", p_outset0), ("Outset: border grows outward", p_outset))

# --- taper / apex
def pencil(tip):
    bm = cyl(0.4, 2.4, 6, (0, 0, 1.2))
    if tip:
        top = max(bm.faces, key=lambda f: f.calc_center_median().z)
        ex = bmesh.ops.extrude_face_region(bm, geom=[top]); vs = [v for v in ex["geom"] if isinstance(v, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=(0, 0, 1.0), verts=vs); bmesh.ops.pointmerge(bm, verts=vs, merge_co=Vector((0, 0, 3.4)))
    return bm
def p_pencil0(): mk("P", pencil(False), "gold"); return {"el": 15}
def p_pencil1(): mk("P", pencil(True), "gold"); dot((0, 0, 3.4), 0.07); return {"el": 15}
demo("taper", ("Straight prism", p_pencil0), ("Taper: narrows along its length to an apex (orange dot)", p_pencil1))

# --- loft
def loops():
    c = [Vector((math.cos(t), math.sin(t), 0)) for t in [i * 2 * math.pi / 32 for i in range(32)]]
    s = []
    for t in [i * 2 * math.pi / 32 for i in range(32)]:
        v = Vector((math.cos(t), math.sin(t), 0)); k = 0.8 / max(abs(v.x), abs(v.y)); s.append(Vector((v.x * k, v.y * k, 2.2)))
    return c, s
def p_loft0():
    c, s = loops(); tubes([c + [c[0]], s + [s[0]]], 0.03, "sel"); return {"el": 25}
def p_loft1():
    c, s = loops(); bm = bmesh.new(); a = [bm.verts.new(p) for p in c]; b = [bm.verts.new(p) for p in s]
    es = [bm.edges.new((a[i], a[(i + 1) % 32])) for i in range(32)] + [bm.edges.new((b[i], b[(i + 1) % 32])) for i in range(32)]
    bmesh.ops.bridge_loops(bm, edges=es, use_merge=False); bmesh.ops.subdivide_edgering(bm, edges=[e for e in bm.edges if e.verts[0].co.z != e.verts[1].co.z], cuts=8, profile_shape='SMOOTH') if False else None
    o = mk("Loft", bm, "main", smooth=True); tubes([c + [c[0]], s + [s[0]]], 0.03, "sel"); return {"el": 25}
demo("loft", ("Two profiles: circle + square", p_loft0), ("Loft: surface blended between them", p_loft1))

# --- extrude
def p_ext0():
    bm = bmesh.new(); bm.faces.new([bm.verts.new(p) for p in star_pts()]); o = mk("Star", bm, "red"); wire(o, 0.012); return {"el": 40}
def p_ext1():
    o = mk("Star", prism(star_pts(), 0, 0.6), "red"); wire(o, 0.012); return {"el": 40}
demo("extrude", ("Flat outline (one face)", p_ext0), ("Extrude (E): pulled up into a solid", p_ext1))

# --- planarize
def p_plan(flat):
    def f():
        random.seed(3); bm = grid(10, 10, 3, 3)
        for v in bm.verts: v.co.z = 0 if flat else noise.noise(v.co * 1.7) * 0.25
        o = mk("G", bm, "green"); wire(o, 0.01); return {"el": 22}
    return f
demo("planarize", ("Wavy, noisy surface", p_plan(False)), ("Planarized: every point on one flat plane", p_plan(True)))

# --- boolean
def bool_scene(op):
    o = mk("Cube", cube(2)); s = mk("Cutter", sphere(1.32, 48, 24), "cut", smooth=True)
    if op is None:
        s.data.materials[0] = mat("cut", alpha=0.35); return {}
    m = o.modifiers.new("B", 'BOOLEAN'); m.operation = op; m.object = s
    try: m.solver = 'EXACT'
    except TypeError: pass
    s.hide_render = True; return {}
def bp(op): return lambda: bool_scene(op)
demo("boolean", ("Object + cutter (blue)", bp(None)), ("Difference: cutter subtracted", bp('DIFFERENCE')),
     ("Union: merged into one", bp('UNION')), ("Intersect: only the overlap", bp('INTERSECT')))

# --- bisect / slice
def egg(): bm = sphere(1, 32, 16); bmesh.ops.scale(bm, vec=(1, 1, 1.3), verts=bm.verts); return bm
def cut_bm(keep):  # keep: "lower"/"upper"
    bm = egg(); n = Vector((0.25, 0, 1)).normalized()
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0.2), plane_no=n, clear_inner=keep == "upper", clear_outer=keep == "lower")
    bnd = [e for e in bm.edges if e.is_boundary]; fr = bmesh.ops.holes_fill(bm, edges=bnd, sides=0)
    for f in fr["faces"]: f.material_index = 1
    return bm
def p_bis0():
    mk("Egg", egg(), "main", smooth=True); pl = mk("Plane", grid(1, 1, 3.4, 3.4), "cut")
    pl.data.materials[0] = mat("cut", alpha=0.4); pl.rotation_euler = (0, math.atan2(0.25, 1), 0); pl.location = (0, 0, 0.2); return {}
def p_bis1(): mk("Egg", cut_bm("lower"), "main", smooth=True, extra=["sel"]); return {"el": 35}
def p_bis2():
    a = mk("A", cut_bm("lower"), "main", smooth=True, extra=["sel"]); b = mk("B", cut_bm("upper"), "gold", smooth=True, extra=["sel"])
    b.location = (0.25, 0, 0.9); return {"el": 15}
demo("bisect", ("Cutting plane through the mesh", p_bis0), ("Bisect: keep one side, Fill caps the hole", p_bis1), ("Slice: keep both pieces", p_bis2))

# --- separate
def two_parts(sep):
    bm = cube(1.4, (-1, 0, 0)); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.75, matrix=Matrix.Translation((0.9, 0, 0)))
    o = mk("One", bm, "main", smooth=False)
    if sep:
        bpy.data.objects.remove(o)
        mk("Cube", cube(1.4, (-1.6, 0, 0)), "main"); mk("Ball", sphere(0.75, 32, 16, (1.5, 0, 0)), "gold", smooth=True)
    return {"el": 20}
demo("separate", ("One object with two loose parts", lambda: two_parts(False)), ("Separate (P) → By Loose Parts: two objects", lambda: two_parts(True)))

# --- seam
def p_seam0():
    o = mk("Cyl", cyl(1, 2.4, 32), "main", smooth=False); ring = [Vector((math.cos(t), math.sin(t), 0)) * 1.005 for t in [i * 2 * math.pi / 32 for i in range(33)]]
    bm = cyl(1, 2.4, 32); bm.free()
    tubes([ring], 0.035, "seam"); return {"el": 25}
def p_seam1():
    a = mk("A", cyl(1, 1.2, 32, (0, 0, -0.6))); b = mk("B", cyl(1, 1.2, 32, (0, 0, 0.9)), "gold"); return {"el": 25}
demo("seam", ("Mark Seam: red edge loop = boundary", p_seam0), ("Split along the seam", p_seam1))

# --- knife project
def p_kp(cut):
    def f():
        mk("Block", cube(2, scale=(1.3, 1.3, 0.4)))
        st = [p * 0.85 for p in star_pts()]
        if not cut:
            hi = [Vector((p.x, p.y, 1.4)) for p in st]; tubes([hi + [hi[0]]], 0.025, "sel")
            tubes([[Vector((p.x, p.y, 1.4)), Vector((p.x, p.y, 0.41))] for p in st[::2]], 0.006, "wire")
        else:
            bm = bmesh.new(); bm.faces.new([bm.verts.new((p.x, p.y, 0.402)) for p in st]); mk("StarFace", bm, "sel")
            lo = [Vector((p.x, p.y, 0.405)) for p in st]; tubes([lo + [lo[0]]], 0.015, "wire")
        return {"el": 40}
    return f
demo("knife", ("Template shape above, viewed from the top", p_kp(False)), ("Knife Project: outline cut into the surface", p_kp(True)))

# --- decimate / remesh
def noisy_sphere():
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=5, radius=1)
    for v in bm.verts: v.co += v.co.normalized() * (noise.noise(v.co * 3) * 0.08 + random.uniform(-0.012, 0.012))
    return bm
def p_dec(ratio):
    def f():
        random.seed(1); o = mk("N", noisy_sphere(), "grey")
        if ratio: m = o.modifiers.new("D", 'DECIMATE'); m.ratio = ratio
        wire(o, 0.0022 if not ratio else 0.006); return {"el": 15, "count": faces(o)}
    return f
demo("decimate", ("Dense noisy mesh: {count} faces", p_dec(None)), ("Decimate Collapse 0.05: {count} faces", p_dec(0.05)))

def p_planar(on):
    def f():
        random.seed(2); bm = cube(2); bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=11, use_grid_fill=True)
        for v in bm.verts: v.co += Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))) * 0.004
        o = mk("Box", bm, "grey")
        if on: m = o.modifiers.new("D", 'DECIMATE'); m.decimate_type = 'DISSOLVE'; m.angle_limit = math.radians(5)
        wire(o, 0.008); return {"count": faces(o)}
    return f
demo("decimate_planar", ("Slightly wrinkled flat sides: {count} faces", p_planar(False)), ("Decimate Planar (5°): {count} faces", p_planar(True)))

def messy_monkey():
    o = mk("M", monkey(), "grey", smooth=True); m = o.modifiers.new("S", 'SUBSURF'); m.levels = 1
    t = o.modifiers.new("T", 'TRIANGULATE'); d = o.modifiers.new("D", 'DECIMATE'); d.ratio = 0.35
    me = bpy.data.meshes.new_from_object(evaluated(o)); bpy.data.objects.remove(o)
    o = link(bpy.data.objects.new("Messy", me)); me.materials.clear(); me.materials.append(mat("grey"))
    for p in me.polygons: p.use_smooth = True
    return o
def p_rm0(): o = messy_monkey(); wire(o, 0.004); return {"az": -25, "el": 10}
def p_rm1():
    o = messy_monkey(); m = o.modifiers.new("R", 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = 0.035
    o.data.materials[0] = mat("main"); wire(o, 0.003); return {"az": -25, "el": 10}
def p_rm2():
    o = messy_monkey(); m = o.modifiers.new("R", 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = 0.03
    me = bpy.data.meshes.new_from_object(evaluated(o)); bpy.data.objects.remove(o)
    o = link(bpy.data.objects.new("Q", me)); me.materials.clear(); me.materials.append(mat("green"))
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.quadriflow_remesh(target_faces=1800, use_mesh_symmetry=False, seed=0)
    for p in o.data.polygons: p.use_smooth = True
    wire(o, 0.005); return {"az": -25, "el": 10}
demo("remesh", ("Messy AI-style triangles", p_rm0), ("Remesh Voxel: even, rebuilt surface", p_rm1), ("QuadriFlow (quad) remesh: clean quads", p_rm2))

# --- weld / merge
def p_weld(merged):
    def f():
        bm = sphere(1, 12, 8)
        es = [e for e in bm.edges if abs(e.verts[0].co.x) < 1e-4 and abs(e.verts[1].co.x) < 1e-4 and e.verts[0].co.y + e.verts[1].co.y < 0]
        es += [e for e in bm.edges if abs(e.verts[0].co.z) < 1e-4 and abs(e.verts[1].co.z) < 1e-4]
        bmesh.ops.split_edges(bm, edges=es)
        nv = len(bm.verts)
        if merged: bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0001)
        o = mk("S", bm, "gold", smooth=True); return {"az": -20, "el": 20, "count": len(o.data.vertices)}
    return f
_weld = ( ("Duplicate verts along seams: {count} verts, visible creases", p_weld(False)), ("Merge by Distance / Weld: {count} verts, smooth", p_weld(True)))

# --- normals
def p_norm(fixed):
    def f():
        random.seed(5); bm = sphere(1, 24, 12)
        if not fixed: bmesh.ops.reverse_faces(bm, faces=[f for f in bm.faces if random.random() < 0.25])
        o = mk("S", bm, face_orient_mat(), smooth=False); return {"el": 20}
    return f
demo("normals", ("Face Orientation overlay: red = flipped faces", p_norm(False)), ("After Recalculate Outside: all blue", p_norm(True)))

# --- shading
def p_shade(mode):
    def f():
        o = mk("C", cyl(1, 2, 20), "main", smooth=mode != "flat")
        if mode == "auto" and hasattr(o.data, "set_sharp_from_angle"): o.data.set_sharp_from_angle(angle=math.radians(30))
        return {"el": 30}
    return f
demo("shading", ("Shade Flat: facets", p_shade("flat")), ("Shade Smooth: caps go dark/smudged", p_shade("smooth")), ("Shade Auto Smooth: smooth sides, crisp rims", p_shade("auto")))

# --- recess / pocket / relief
def slab_op(kind):
    def f():
        o = mk("Slab", cube(2, scale=(1.4, 1.4, 0.35))); top = 0.35
        if kind == "recess": t = mk("T", prism([p * 0.9 for p in star_pts()], top - 0.12, top + 0.2)); op = 'DIFFERENCE'
        elif kind == "pocket": t = mk("T", cyl(0.75, 1, 48, (0, 0, top + 0.5 - 0.55))); op = 'DIFFERENCE'
        else: t = mk("T", prism([p * 0.9 for p in star_pts()], top - 0.1, top + 0.18)); op = 'UNION'
        m = o.modifiers.new("B", 'BOOLEAN'); m.operation = op; m.object = t
        try: m.solver = 'EXACT'
        except TypeError: pass
        t.hide_render = True; return {"el": 45}
    return f
demo("recess", ("Recess: shallow sunken area", slab_op("recess")), ("Pocket: deeper, enclosed", slab_op("pocket")), ("Relief: raised detail", slab_op("relief")))

# --- alignment
def p_pins():
    b = mk("Bottom", cube(2, (0, 0, 0.4), (1.4, 0.8, 0.4)))
    h = [mk(f"H{i}", cyl(0.2, 0.8, 32, (x, 0, 0.8))) for i, x in enumerate((-0.8, 0.8))]
    for c in h:
        m = b.modifiers.new("B", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = c; c.hide_render = True
    mk("Top", cube(2, (0, 0, 2.0), (1.4, 0.8, 0.4)), "gold")
    for x in (-0.8, 0.8): mk("Pin", cyl(0.18, 0.5, 32, (x, 0, 1.4)), "gold", smooth=False)
    return {"az": -25, "el": 30}
def p_biscuit():
    def oval(z0=-0.06, z1=0.06, s=1.0):
        pts = [Vector((0.75 * s * math.cos(t), 0.35 * s * math.sin(t), 0)) for t in [i * 2 * math.pi / 40 for i in range(40)]]
        return prism(pts, z0, z1)
    a = mk("A", cube(2, (-1.6, 0, 0), (1, 1, 0.5))); b = mk("B", cube(2, (1.6, 0, 0), (1, 1, 0.5)), "main")
    for o, x in ((a, -0.6), (b, 0.6)):
        c = mk("Slot", oval(-0.08, 0.08, 1.06)); c.location = (x, 0, 0.0)
        m = o.modifiers.new("B", 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = c; c.hide_render = True
        try: m.solver = 'EXACT'
        except TypeError: pass
    mk("Biscuit", oval(), "red").location = (0, 0, 0.0)
    return {"az": -40, "el": 22}
demo("align", ("Pins + sockets (dowels): mate one way only", p_pins), ("Biscuit in matching slots (contrast color)", p_biscuit))

# --- extrusion options
def p_tap():
    bm = cube(2, (0, 0, 1)); top = [v for v in bm.verts if v.co.z > 1.5]; bmesh.ops.scale(bm, vec=(0.45, 0.45, 1), verts=top, space=Matrix.Translation((0, 0, 0)))
    mk("T", bm, "gold"); return {}
def p_twist():
    bm = cube(2, (0, 0, 0), (0.6, 0.6, 1.6)); bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1], cuts=24, use_grid_fill=True)
    o = mk("Tw", bm, "red", smooth=True); m = o.modifiers.new("T", 'SIMPLE_DEFORM'); m.deform_method = 'TWIST'; m.angle = math.radians(180); m.deform_axis = 'Z'
    if hasattr(o.data, "set_sharp_from_angle"): o.data.set_sharp_from_angle(angle=math.radians(40))
    return {}
def p_screw():
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=False, segments=16, radius=0.18)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'), verts=bm.verts); bmesh.ops.translate(bm, vec=(0.9, 0, 0), verts=bm.verts)
    o = mk("Sp", bm, "green", smooth=True); m = o.modifiers.new("S", 'SCREW'); m.screw_offset = 0.55; m.iterations = 5; m.steps = 32; m.render_steps = 32
    return {}
def p_curve():
    cu = bpy.data.curves.new("Hose", 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.16; cu.bevel_resolution = 6; cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER'); pts = [(-2, 0, 0.2), (-0.8, 1.2, 1.4), (0.6, -0.6, 0.4), (2, 0.6, 1.6)]; sp.bezier_points.add(len(pts) - 1)
    for bp_, p in zip(sp.bezier_points, pts): bp_.co = p; bp_.handle_left_type = bp_.handle_right_type = 'AUTO'
    o = link(bpy.data.objects.new("Hose", cu)); cu.materials.append(mat("main")); return {"el": 30}
demo("extrude_opts", ("Taper", p_tap), ("Twist (Simple Deform)", p_twist), ("Screw: circle spun into a spring", p_screw), ("Extrude along a curve: hose", p_curve), cols=4)

def p_solid(on):
    def f():
        bm = grid(20, 12, 3, 1.8)
        for v in bm.verts: v.co.z = 0.35 * math.sin(v.co.x * 1.6)
        o = mk("Sh", bm, "gold", smooth=True)
        if on: m = o.modifiers.new("S", 'SOLIDIFY'); m.thickness = 0.18; m.offset = 0
        return {"az": -30, "el": 15}
    return f
demo("solidify", ("Zero-thickness surface (can't print)", p_solid(False)), ("Solidify: real wall thickness", p_solid(True)))

# --- topology
def p_topo(kind):
    def f():
        if kind == "quad": bm = grid(6, 6, 2.4, 2.4)
        elif kind == "tri": bm = grid(6, 6, 2.4, 2.4); bmesh.ops.triangulate(bm, faces=bm.faces[:])
        else: bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=1.3)
        o = mk("P", bm, {"quad": "green", "tri": "gold", "ngon": "red"}[kind]); wire(o, 0.02); return {"el": 60}
    return f
demo("topology", ("Quads: 4-sided, subdivide cleanly", p_topo("quad")), ("Tris: 3-sided", p_topo("tri")), ("Ngon: one face, 24 sides", p_topo("ngon")))

def p_subd(lv):
    def f():
        o = mk("C", cube(2), "main", smooth=True)
        if lv: m = o.modifiers.new("S", 'SUBSURF'); m.levels = m.render_levels = lv
        tubes(edges_of(o), 0.012, "wire"); return {"count": faces(o)}
    return f
demo("subsurf", ("Cube cage: {count} faces", p_subd(0)), ("Subdivision level 1: {count}", p_subd(1)), ("Level 3: {count}, smooth blob", p_subd(3)))

def p_support(on):
    def f():
        bm = cube(2)
        if on: bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=0.12, offset_type='OFFSET', segments=1, profile=0.5, affect='EDGES')
        o = mk("C", bm, "main", smooth=True); tubes(edges_of(o), 0.012, "wire")
        m = o.modifiers.new("S", 'SUBSURF'); m.levels = m.render_levels = 3; return {}
    return f
demo("support", ("Subdivision, no support loops: blob", p_support(False)), ("Extra edge loops near the edges: crisp", p_support(True)))

def p_loopcut():
    bm = cube(2); bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1], cuts=1, use_grid_fill=True)
    o = mk("C", bm); tubes(edges_of(o, lambda e: not (abs(o.data.vertices[e.vertices[0]].co.z) < 1e-4 and abs(o.data.vertices[e.vertices[1]].co.z) < 1e-4)), 0.012, "wire")
    tubes(edges_of(o, lambda e: abs(o.data.vertices[e.vertices[0]].co.z) < 1e-4 and abs(o.data.vertices[e.vertices[1]].co.z) < 1e-4), 0.03, "sel")
    return {}
def p_sel(mode):
    def f():
        o = mk("C", cube(2), "grey", extra=["sel"]); tubes(edges_of(o), 0.012 if mode != "edge" else 0.016, "wire")
        if mode == "vert":
            for i, v in enumerate(o.data.vertices): dot(o.matrix_world @ v.co, 0.07, "sel" if i in (1, 3) else "wire")
        elif mode == "edge":
            e = max(o.data.edges, key=lambda e: sum((o.data.vertices[i].co.z - o.data.vertices[i].co.y) for i in e.vertices))
            tubes([[o.data.vertices[i].co for i in e.vertices]], 0.035, "sel")
        else:
            f_ = max(o.data.polygons, key=lambda p: p.center.z); f_.material_index = 1
        return {}
    return f
demo("select_modes", ("1 = Vertex select", p_sel("vert")), ("2 = Edge select", p_sel("edge")), ("3 = Face select", p_sel("face")))
demo("loopcut", ("Loop Cut (Ctrl R): new ring of edges", p_loopcut))

def holey(fill):
    bm = sphere(1, 24, 12); bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().z > 0.75 or (f.calc_center_median().x > 0.85 and abs(f.calc_center_median().z) < 0.3)], context='FACES')
    if fill:
        r = bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
        for f in r["faces"]: f.material_index = 1
    o = mk("S", bm, "main", extra=["sel"])
    if not fill:
        me = o.data; cnt = {}
        for p in me.polygons:
            for k in p.edge_keys: cnt[k] = cnt.get(k, 0) + 1
        tubes([[me.vertices[a].co, me.vertices[b].co] for (a, b), n in cnt.items() if n == 1], 0.025, "sel")
    return {"az": 20, "el": 40}
demo("holes", ("Non-manifold: open holes (orange boundary)", lambda: holey(False)), ("Fill Holes: closed, printable", lambda: holey(True)))

# --- mirror
def half_monkey():
    bm = monkey(); bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(1, 0, 0), clear_inner=True)
    return bm
def p_mir(on):
    def f():
        o = mk("M", half_monkey(), "main", smooth=True)
        if on: m = o.modifiers.new("M", 'MIRROR'); m.use_clip = True
        else:
            pl = mk("Pl", grid(1, 1, 2.2, 2.0), "cut"); pl.data.materials[0] = mat("cut", alpha=0.3); pl.rotation_euler = (0, math.pi / 2, 0)
        return {"az": -40, "el": 18}
    return f
demo("mirror", ("Model only one half (+X)", p_mir(False)), ("Mirror modifier (X): other half generated", p_mir(True)))

# --- shrinkwrap
def p_sw(on):
    def f():
        s = mk("Ball", sphere(1, 48, 24), "grey", smooth=True); bm = grid(24, 24, 1.3, 1.3, (0, 0, 1.4)); g = mk("Lace", bm, "red", smooth=True)
        if on:
            m = g.modifiers.new("SW", 'SHRINKWRAP'); m.target = s; m.wrap_method = 'PROJECT'; m.use_negative_direction = True; m.offset = 0.01
            sd = g.modifiers.new("So", 'SOLIDIFY'); sd.thickness = 0.04
        wire(g, 0.004); return {"el": 25}
    return f
demo("shrinkwrap", ("Flat patch above a curved surface", p_sw(False)), ("Shrinkwrap: patch conforms to the surface", p_sw(True)))

# --- array / proportional / displace
def p_arr(on):
    def f():
        o = mk("C", cube(0.6), "gold")
        if on: m = o.modifiers.new("A", 'ARRAY'); m.count = 6; m.relative_offset_displace = (1.5, 0, 0)
        return {"el": 25, "zoom": 0.5 if not on else 1}
    return f
demo("array", ("One object", p_arr(False)), ("Array ×6: repeated in a pattern", p_arr(True)))

def p_prop(on):
    def f():
        bm = grid(30, 30, 3, 3)
        for v in bm.verts:
            r = v.co.xy.length
            if on: v.co.z = 0.9 * math.exp(-(r / 0.6) ** 2)
            elif r < 1e-4: v.co.z = 0.9
        o = mk("G", bm, "green", smooth=True); wire(o, 0.004); return {"el": 25}
    return f
demo("proportional", ("Move one vertex: a spike", p_prop(False)), ("Proportional editing (O): neighbors follow", p_prop(True)))

def p_disp():
    o = mk("G", grid(160, 160, 3, 3), "gold", smooth=True); tx = bpy.data.textures.new("Cl", 'CLOUDS'); tx.noise_scale = 0.35
    m = o.modifiers.new("D", 'DISPLACE'); m.texture = tx; m.strength = 0.35; m.mid_level = 0.5; return {"el": 30}
def p_bump():
    o = mk("G", grid(1, 1, 3, 3), bump_mat()); wire(o, 0.012); return {"el": 30}
demo("displace", ("Displacement: real geometry moves", p_disp), ("Bump map: shading only, surface still flat", p_bump))

# --- origin
def p_orig(corner):
    def f():
        off = Vector((1, 1, 0)) if corner else Vector((0, 0, 0))
        for i, deg in enumerate((0, 25, 50)):
            bm = cube(1.6, (off.x * 0.8, off.y * 0.8, 0.8)); o = mk(f"C{i}", bm, "main" if i == 0 else mat("main", alpha=0.25 + 0.15 * i))
            o.rotation_euler = (0, 0, math.radians(deg))
        dot((0, 0, 1.65), 0.09); tubes([[Vector((0, 0, 0)), Vector((0, 0, 1.65))]], 0.015, "sel")
        return {"el": 55}
    return f
demo("origin", ("Origin at center: rotates in place", p_orig(False)), ("Origin at corner: swings around the corner", p_orig(True)))

# --- transforms
def p_tf(kind):
    def f():
        g = mk("Ghost", cube(1.2, (0, 0, 0.6)), mat("grey", alpha=0.35))
        o = mk("C", cube(1.2, (0, 0, 0.6)), "main")
        if kind == "G": o.location = (1.8, 0, 0)
        elif kind == "R": o.rotation_euler = (0, 0, math.radians(30))
        else: o.scale = (1.5, 1.5, 1.5)
        return {"el": 30}
    return f
demo("transform", ("G X 1.8: move along X", p_tf("G")), ("R Z 30: rotate around Z", p_tf("R")), ("S 1.5: scale up", p_tf("S")))

# --- views
def p_view(az, el):
    def f(): mk("M", monkey(), "main", smooth=True).modifiers.new("S", 'SUBSURF').levels = 2; return {"az": az, "el": el, "ortho": True}
    return f
demo("views", ("Numpad 1: Front", p_view(0, 0)), ("Numpad 3: Right", p_view(90, 0)), ("Numpad 7: Top", p_view(0, 90)))

def p_vs(kind):
    def f():
        o = mk("M", monkey(), "main", smooth=True); o.modifiers.new("S", 'SUBSURF').levels = 1
        if kind == "wire": wire(o, 0.004); o.hide_render = True
        elif kind == "xray": o.data.materials[0] = mat("main", alpha=0.3); wire(o, 0.003)
        return {"az": -25, "el": 10}
    return f
demo("viewshade", ("Solid", p_vs("solid")), ("Wireframe (Shift Z)", p_vs("wire")), ("X-ray (Alt Z): see through", p_vs("xray")))

# --- cover
def p_cover():
    o = mk("Bev", cube(1.4, (-2.2, 0.6, 0.7)), "main", smooth=True); m = o.modifiers.new("B", 'BEVEL'); m.width = 0.2; m.segments = 5
    if hasattr(o.data, "set_sharp_from_angle"): o.data.set_sharp_from_angle(angle=math.radians(30))
    bm = cube(2, (0, 0, 0), (0.45, 0.45, 1.1)); bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1], cuts=24, use_grid_fill=True)
    t = mk("Tw", bm, "red", smooth=True); md = t.modifiers.new("T", 'SIMPLE_DEFORM'); md.deform_method = 'TWIST'; md.angle = math.radians(180); md.deform_axis = 'Z'
    t.location = (-0.6, 1.6, 1.1)
    if hasattr(t.data, "set_sharp_from_angle"): t.data.set_sharp_from_angle(angle=math.radians(40))
    mo = mk("Mk", monkey(), "gold", smooth=True); mo.modifiers.new("S", 'SUBSURF').levels = 2; mo.location = (0.9, -0.2, 0.75); mo.rotation_euler = (0, 0, math.radians(-15))
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=False, segments=16, radius=0.14)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'), verts=bm.verts); bmesh.ops.translate(bm, vec=(0.55, 0, 0), verts=bm.verts)
    sp = mk("Sp", bm, "green", smooth=True); s = sp.modifiers.new("S", 'SCREW'); s.screw_offset = 0.4; s.iterations = 4; sp.location = (2.6, 1.0, 0.0)
    bp_ = mk("Star", prism([p * 0.7 for p in star_pts()], 0, 0.3), "main"); bp_.location = (-1.6, -1.3, 0)
    return {"az": -12, "el": 22}
demo("cover", ("", p_cover))

# ---------- run ----------
for name, (panels, kw) in D.items():
    if ONLY and name not in ONLY: continue
    caps = []
    for i, (cap, fn) in enumerate(panels):
        reset(); random.seed(0)
        try:
            k = fn() or {}
        except Exception as ex:
            print(f"DEMO FAIL {name}[{i}]: {ex!r}"); caps.append(None); continue
        cnt = k.pop("count", None); caps.append(cap.replace("{count}", f"{cnt:,}") if cnt is not None else cap)
        if name == "cover": RES_SAVE = RES; RES = (1400, 1000); bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = RES
        shoot(os.path.join(RAW, f"{name}__{i}.png"), **k)
        if name == "cover": RES = RES_SAVE
        print("RENDERED", name, i)
    json.dump({"captions": caps, **kw}, open(os.path.join(RAW, name + ".json"), "w"))
