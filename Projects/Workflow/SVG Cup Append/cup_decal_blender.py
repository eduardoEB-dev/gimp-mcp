"""Blender half of cup_append.py: wrap triangulated color regions onto the cup wall, extrude, export, preview.

tris.json: {name, R, embed, heights{color: mm}, hex{color: #rgb}, tris{color: [[(u, z) x3], ...]}} in 3MF local mm.
Out: <work>/STL/<Name> - <Color>.stl + <Name> - Logo.stl, <work>/Images/preview.png + preview_angle.png.

Run: blender -b --factory-startup --python cup_decal_blender.py -- <tris.json> <work> <cup_preview.stl>
"""
import bpy, bmesh, json, math, sys, os
from mathutils import Vector

TRIS, WORK, CUP = map(os.path.abspath, sys.argv[sys.argv.index("--") + 1:][:3])
STEP = 0.6           # bisect spacing for smooth bend
d = json.load(open(TRIS))
NAME, R, EMBED = d["name"], d["R"], d["embed"]

bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(n, hx):
    m = bpy.data.materials.new(n); hx = hx.lstrip("#")
    m.diffuse_color = [(int(hx[i:i + 2], 16) / 255) ** 2.2 for i in (0, 2, 4)] + [1]; return m

def wrap(co):  # (u arc mm, z mm, w height) -> cylinder, front = -Y
    th = co.x / R; r = R - EMBED + co.z
    return Vector((r * math.sin(th), -r * math.cos(th), co.y))

objs = []
for name, tris in d["tris"].items():
    h = d["heights"][name] + EMBED
    bm = bmesh.new()
    for t in tris:
        bm.faces.new([bm.verts.new((u, z, 0)) for u, z in t])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.dissolve_limit(bm, angle_limit=0.01, verts=bm.verts, edges=bm.edges)  # merge into ngons, re-cut evenly
    for ax in (0, 1):
        lo = min(v.co[ax] for v in bm.verts); hi = max(v.co[ax] for v in bm.verts)
        k = math.floor(lo / STEP) + 1
        no = Vector((1, 0, 0)) if ax == 0 else Vector((0, 1, 0))
        while k * STEP < hi:
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=no * (k * STEP), plane_no=no)
            k += 1
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
    for f in bm.faces:
        if f.normal.z < 0: f.normal_flip()
    ext = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    for v in [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]: v.co.z = h
    for v in bm.verts: v.co = wrap(v.co)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    seen = set()  # recalc can leave whole shells inside-out (render black in Bambu): flip any shell with -volume
    for f0 in bm.faces:
        if f0 in seen: continue
        isl, st = [], [f0]; seen.add(f0)
        while st:
            f = st.pop(); isl.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g not in seen: seen.add(g); st.append(g)
        if sum(f.verts[0].co.dot(f.verts[1].co.cross(f.verts[2].co)) for f in isl) < 0:
            for f in isl: f.normal_flip()
    nm = sum(not e.is_manifold for e in bm.edges)
    me = bpy.data.meshes.new(f"{NAME}_{name}"); bm.to_mesh(me)
    print(f"  decal {name}: tris {len(bm.faces)} vol {bm.calc_volume():.0f} nonmanifold {nm}")
    bm.free()
    o = bpy.data.objects.new(f"{NAME}_{name}", me); o.data.materials.append(mat(name, d["hex"][name]))
    bpy.context.scene.collection.objects.link(o); objs.append(o)

def sel(os_):
    bpy.ops.object.select_all(action='DESELECT')
    for o in os_: o.select_set(True)
    bpy.context.view_layer.objects.active = os_[0]

stl = os.path.join(WORK, "STL")
for o in objs:
    sel([o]); bpy.ops.wm.stl_export(filepath=os.path.join(stl, f"{NAME} - {o.name.split('_', 1)[1]}.stl"), export_selected_objects=True)
sel(objs); bpy.ops.wm.stl_export(filepath=os.path.join(stl, f"{NAME} - Logo.stl"), export_selected_objects=True)

bpy.ops.wm.stl_import(filepath=CUP)
cup = bpy.context.selected_objects[0]; cup.data.materials.append(mat("Cup", "#E6E6E6"))
zc = (cup.bound_box[0][2] + cup.bound_box[1][2]) / 2

scn = bpy.context.scene
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scn.collection.objects.link(cam)
cam.data.type = 'ORTHO'; scn.camera = cam
scn.render.engine = 'BLENDER_WORKBENCH'; scn.display.shading.color_type = 'MATERIAL'
scn.display.shading.light = 'STUDIO'; scn.render.resolution_x = scn.render.resolution_y = 1000
img = os.path.join(WORK, "Images")
for fn, loc, rot, sc in (("preview.png", (0, -200, zc + 13.6), (90, 0, 0), 92),
                         ("preview_angle.png", (-140, -140, zc + 51.6), (70, 0, -45), 120)):
    cam.location = loc; cam.rotation_euler = [math.radians(x) for x in rot]; cam.data.ortho_scale = sc
    scn.render.filepath = os.path.join(img, fn); bpy.ops.render.render(write_still=True)
