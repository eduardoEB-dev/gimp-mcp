"""Blender half of cup_append.py --target lid: inlay color regions flush into the lid's top face.

tris.json: {name, z0 (face z, on the bed), depth, hex{color}, tris{color: [[(x, y) x3], ...]}, cut (union outline tris), cam_rz, center} in 3MF local mm.
Each color = depth prism flush with the face, pocketed into the lid (Exact boolean, one cut for all colors),
then lid + prisms joined into one mesh (colors stay separate shells -> paint bucket stops at each).
Out: <work>/STL/<Name> Lid - <Color>.stl + <Name> Lid.stl (joined), <work>/Images/preview_lid.png.

Run: blender -b --factory-startup --python lid_inlay_blender.py -- <tris.json> <work> <lid.stl>
"""
import bpy, bmesh, json, math, sys, os

TRIS, WORK, LID = map(os.path.abspath, sys.argv[sys.argv.index("--") + 1:][:3])
d = json.load(open(TRIS))
NAME, Z0, DEPTH = d["name"], d["z0"], d["depth"]

bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(n, hx):
    m = bpy.data.materials.new(n); hx = hx.lstrip("#")
    m.diffuse_color = [(int(hx[i:i + 2], 16) / 255) ** 2.2 for i in (0, 2, 4)] + [1]; return m

def prism(name, tris, z0, z1):
    bm = bmesh.new()
    for t in tris:
        bm.faces.new([bm.verts.new((x, y, z0)) for x, y in t])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for f in bm.faces:
        if f.normal.z > 0: f.normal_flip()          # bottom faces point down (onto the bed)
    ext = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    for v in [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]: v.co.z = z1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

def report(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    print(f"  lid {o.name}: tris {len(o.data.polygons)} vol {bm.calc_volume():.1f} nonmanifold {sum(not e.is_manifold for e in bm.edges)}")
    bm.free()

def sel(os_):
    bpy.ops.object.select_all(action='DESELECT')
    for o in os_: o.select_set(True)
    bpy.context.view_layer.objects.active = os_[0]

parts = []
for c, tris in d["tris"].items():
    p = prism(c, tris, Z0, Z0 + DEPTH); p.data.materials.append(mat(c, d["hex"][c])); parts.append(p)
bpy.ops.wm.stl_import(filepath=LID)
lid = bpy.context.selected_objects[0]; lid.name = "Lid"; lid.data.materials.append(mat("Lid", "#E6E6E6"))
cut = prism("cut", d["cut"], Z0 - 0.1, Z0 + DEPTH)  # pokes past the face: no coplanar faces
md = lid.modifiers.new("b", 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = cut
bpy.context.view_layer.objects.active = lid; bpy.ops.object.modifier_apply(modifier="b")
bpy.data.objects.remove(cut)
objs = [lid] + parts
for o in objs: report(o)
stl = os.path.join(WORK, "STL")
for o in parts:
    sel([o]); bpy.ops.wm.stl_export(filepath=os.path.join(stl, f"{NAME} Lid - {o.name}.stl"), export_selected_objects=True)

# preview: top face as seen from outside (from below the bed), straw hole up
scn = bpy.context.scene
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); scn.collection.objects.link(cam)
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 88; scn.camera = cam
cam.location = (d["center"][0], d["center"][1], Z0 - 100); cam.rotation_euler = (math.pi, 0, d["cam_rz"])
scn.render.engine = 'BLENDER_WORKBENCH'; scn.display.shading.color_type = 'MATERIAL'
scn.display.shading.light = 'STUDIO'; scn.render.resolution_x = scn.render.resolution_y = 900
scn.render.filepath = os.path.join(WORK, "Images", "preview_lid.png"); bpy.ops.render.render(write_still=True)

sel(objs); bpy.ops.object.join()
sel([lid]); bpy.ops.wm.stl_export(filepath=os.path.join(stl, f"{NAME} Lid.stl"), export_selected_objects=True)
