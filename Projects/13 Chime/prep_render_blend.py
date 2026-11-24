"""13 Chime: build an assembled render .blend whose parts carry the 3MF colors.

13Chime.blend has the clock/nameplates as plain single meshes; the 3MF adds SVG relief parts (gold/purple),
the 13 fill/outline, painted borders and the name text. This takes those 3MF meshes (paint decoded, split per
extruder), moves them into the blend's assembled pose and swaps the name text for NAME.
Output objects are named <Piece>_e<extruder> so spec "assign" can map them.

usage: blender -b 13Chime.blend --python prep_render_blend.py -- <file.3mf> <out.blend> <name>
"""
import bpy, sys, re, zipfile, json, math
import numpy as np
from mathutils import Matrix

SRC, OUT, NAME = sys.argv[sys.argv.index("--") + 1:][:3]
FONT = r"C:\Windows\Fonts\CALIST.TTF"  # Calisto MT, as the 3MF text part
z = zipfile.ZipFile(SRC)
ms = z.read("Metadata/model_settings.config").decode("utf8")
model = z.read("3D/3dmodel.model").decode("utf8")


def decode_paint(s):  # same decoder as Workflow/Renders/extract_3mf.py
    nib = [int(c, 16) for c in reversed(s)]; i = 0; out = []
    def rec(b):
        nonlocal i
        n = nib[i]; i += 1; split = n & 3; hi = n >> 2
        if split == 0:
            st = hi
            if st == 3: st = nib[i] + 3; i += 1
            out.append((b, st)); return
        r = [b[(j + hi) % 3] for j in range(3)]
        if split == 1:
            m = (r[1] + r[2]) / 2; ch = [(r[0], r[1], m), (m, r[2], r[0])]
        elif split == 2:
            m1, m2 = (r[0] + r[1]) / 2, (r[0] + r[2]) / 2; ch = [(r[0], m1, m2), (m1, r[1], r[2]), (r[2], m2, m1)]
        else:
            a, c, d = (r[0] + r[1]) / 2, (r[1] + r[2]) / 2, (r[2] + r[0]) / 2
            ch = [(r[0], a, d), (a, r[1], c), (d, c, r[2]), (a, c, d)]
        for k in range(len(ch) - 1, -1, -1): rec(np.array(ch[k]))
    rec(np.eye(3)); return out


def parts(oid):
    """3MF object -> {part name: (verts (object coords), [(tri verts 3x3, extruder)])}."""
    body = re.search(rf'<object id="{oid}">(.*?)</object>', ms, re.S).group(1)
    oext = int(re.search(r'<metadata key="extruder" value="(\d+)"', body).group(1))
    pinfo = {}
    for pid, pb in re.findall(r'<part id="(\d+)"(.*?)</part>', body, re.S):
        e = re.search(r'key="extruder" value="(\d+)"', pb)
        pinfo[pid] = (re.search(r'key="name" value="([^"]+)"', pb).group(1), int(e.group(1)) if e else oext)
    comps = re.search(rf'<object id="{oid}"[^>]*>\s*<components>(.*?)</components>', model, re.S).group(1)
    res = {}
    for path, cid, tr in re.findall(r'p:path="([^"]+)" objectid="(\d+)"[^>]*?transform="([^"]+)"', comps):
        t = z.read(path.lstrip("/")).decode("utf8")
        ob = re.search(rf'<object id="{cid}"[^>]*>(.*?)</object>', t, re.S).group(1)
        v = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', ob), float)
        m = np.array(tr.split(), float).reshape(4, 3); v = v @ m[:3] + m[3]
        name, ext = pinfo[cid]
        tris = []
        for a, b, c, s in re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"(?: paint_color="([0-9A-F]+)")?', ob):
            P = v[[int(a), int(b), int(c)]]
            if not s: tris.append((P, ext)); continue
            for bc, st in decode_paint(s): tris.append((bc @ P, st or ext))
        res[name] = (v, tris)
    return res


def bbox(v): v = np.asarray(v); return v.min(0), v.max(0)


def world_verts(names):
    return np.vstack([np.array([o.matrix_world @ x.co for x in o.data.vertices]) for o in (bpy.data.objects[n] for n in names)])


def pose(R, ref_part_verts, target_names):
    """3MF object coords -> blend: rotate by R, then shift so the reference part's bbox center lands on the target's."""
    R3 = np.array(R.to_3x3())
    lo, hi = bbox(ref_part_verts @ R3.T); tlo, thi = bbox(world_verts(target_names))
    t = (tlo + thi) / 2 - (lo + hi) / 2
    print(f"  fit {target_names}: size 3mf {np.round(hi - lo, 2)} blend {np.round(thi - tlo, 2)}")
    return lambda P: P @ R3.T + t


def add_mesh(name, tris):
    V = np.vstack([P for P, _ in tris]); F = np.arange(len(V)).reshape(-1, 3)
    me = bpy.data.meshes.new(name); me.from_pydata(V.tolist(), [], F.tolist()); me.validate()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    for x in bpy.context.selected_objects: x.select_set(False)
    o.select_set(True); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0005); bpy.ops.object.mode_set(mode="OBJECT")
    return o


def emit(piece, tris, fn):
    by = {}
    for P, e in tris: by.setdefault(e, []).append(fn(P))
    for e, ts in sorted(by.items()):
        o = add_mesh(f"{piece}_e{e}", [(P, e) for P in ts]); print(f"  {o.name}: {len(ts)} tris")


def text_tris(text, size):
    cu = bpy.data.curves.new("txt", "FONT"); cu.body = text; cu.font = bpy.data.fonts.load(FONT)
    cu.size = size; cu.align_x = "CENTER"; cu.align_y = "CENTER"; cu.extrude = 0.5
    o = bpy.data.objects.new("txt", cu); bpy.context.scene.collection.objects.link(o)
    dg = bpy.context.evaluated_depsgraph_get(); me = o.evaluated_get(dg).to_mesh()
    me.calc_loop_triangles()
    V = np.array([x.co for x in me.vertices]); T = [V[list(t.vertices)] for t in me.loop_triangles]
    o.to_mesh_clear(); bpy.data.objects.remove(o)
    return T


# --- clock: base + SVG relief + 13, printed face-up -> assembled (export used Rx(-90))
clock = parts(8)
fn = pose(Matrix.Rotation(math.radians(90), 4, "X"), clock["13Chime_Clock.stl"][0], ["Clock"])
emit("Clock", [t for _, (_, ts) in clock.items() for t in ts], fn)

# --- play nameplate (painted single mesh)
play = parts(17)
v, ts = play["13Chime_PlayNamePlate_All.stl"]
fn = pose(Matrix.Rotation(math.radians(90), 4, "X"), v, ["PlayNamePlate", "PlayNamePlate_Lines", "PlayNamePlate_Text"])
emit("PlayNamePlate", ts, fn)

# --- name plate: painted plate + new name, stood up like NamePlate_Preview
plate = parts(11)
fn = pose(Matrix.Rotation(math.radians(90), 4, "X"), plate["13Chime_NamePlate.stl"][0], ["NamePlate_Preview"])
old_v = plate["name"][0]; olo, ohi = bbox(old_v)
ref = np.vstack(text_tris("Mini Toddler", 10.0)); rlo, rhi = bbox(ref)
k = (ohi[1] - olo[1]) / (rhi[1] - rlo[1]) * 10.0  # font size that matches the 3MF text height
new = text_tris(NAME, k); nlo, nhi = bbox(np.vstack(new))
c_old = (olo + ohi) / 2; c_new = (nlo + nhi) / 2
zs = lambda P: np.column_stack([P[:, 0] - c_new[0] + c_old[0], P[:, 1] - c_new[1] + c_old[1],
                                olo[2] + (P[:, 2] - nlo[2]) / (nhi[2] - nlo[2]) * (ohi[2] - olo[2])])
print(f"  name '{NAME}': size {k:.2f}, width {nhi[0] - nlo[0]:.1f} mm (was {ohi[0] - olo[0]:.1f})")
name_ext = plate["name"][1][0][1]
emit("NamePlate", plate["13Chime_NamePlate.stl"][1] + [(zs(P), name_ext) for P in new], fn)

for n in ["Clock", "NamePlate", "NamePlate_Preview", "PlayNamePlate", "PlayNamePlate_Lines", "PlayNamePlate_Text"]:
    bpy.data.objects.remove(bpy.data.objects[n])
for o in bpy.data.objects: o.hide_render = False
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True)
print("DONE", OUT)
