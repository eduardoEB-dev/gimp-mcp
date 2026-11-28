"""Render-only accessory on a cup rig (render_3mf.py), from prop_3mf.py output.

rig key "prop": {"mode": "lid" | "hang", ...}  (all mm, rig/cup frame: front = -Y, up = +Z)
  lid : "x", "y" (position on lid), "yaw" (deg), "lift" (mm above cap top, default 0)
  hang: "side" (+1 = +X arm, -1 = -X arm), "along" (mm from pivot along handle arm, default 24),
        "links" (chain links, default 6), "yaw" (deg, opener face turn about vertical; 0 = face outward),
        "out" (extra mm pushed outward from the arm)
  Chain = keyring around the handle arm -> small chain -> jump ring through the prop's hole.
"""
import bpy, bmesh, math, os, json
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

S = None  # set by render_3mf (scene_env module)

def _metal(env):
    m = bpy.data.materials.get("Keychain steel")
    if m: return m
    return env.plain("Keychain steel", (0.62, 0.62, 0.64), 0.28, 1.0)

def _torus(name, R, r, M, mat, parent, segs=(32, 10)):
    """torus in local XZ plane (axis = local Y), transformed by M (rig mm)"""
    bm = bmesh.new()
    U, Vn = segs
    verts = []
    for i in range(U):
        a = math.tau * i / U
        c = Vector((math.cos(a), 0, math.sin(a)))
        for j in range(Vn):
            b = math.tau * j / Vn
            p = c * (R + r * math.cos(b)) + Vector((0, r * math.sin(b), 0))
            verts.append(bm.verts.new(M @ p))
    for i in range(U):
        for j in range(Vn):
            a, b = i * Vn + j, i * Vn + (j + 1) % Vn
            c, d = ((i + 1) % U) * Vn + (j + 1) % Vn, ((i + 1) % U) * Vn + j
            bm.faces.new((verts[a], verts[b], verts[c], verts[d]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); o.parent = parent
    return o

def _oval_link(name, L, Wd, r, M, mat, parent):
    """chain link: torus stretched along local Z to outer length L, outer width Wd"""
    R = (Wd - 2 * r) / 2
    sz = (L - 2 * r) / (2 * R)
    return _torus(name, R, r, M @ Matrix.Diagonal((1, 1, sz, 1)), mat, parent, (28, 8))

def _frame(z_dir, y_dir):
    """rotation whose local Z -> z_dir, local Y -> y_dir (orthogonalized)"""
    zz = z_dir.normalized(); xx = y_dir.cross(zz).normalized(); yy = zz.cross(xx)
    return Matrix((xx, yy, zz)).transposed().to_4x4()

def add(rig, cfg, work, env, mesh_obj, pla, lin, cap_top, pivot, handle_obj, cup_obj):
    pdir = os.path.join(work, "prop")
    d = np.load(os.path.join(pdir, "prop.npz")); info = json.load(open(os.path.join(pdir, "prop.json")))
    mats = [pla(f"Prop F{i + 1}", lin(h)) for i, h in enumerate(info["filaments"])]
    v = d["v"].copy(); mode = cfg.get("mode", "lid")
    if mode == "lid":
        M = (Matrix.Translation((cfg.get("x", 0), cfg.get("y", 0), cap_top + cfg.get("lift", 0))) @
             Matrix.Rotation(math.radians(cfg.get("yaw", 0)), 4, 'Z'))
        o = mesh_obj("Prop", v, d["f"], mats, d["p"] - 1, rig); o.matrix_parent_inverse = Matrix(); o.matrix_basis = M
        return o
    # ---- hang from handle arm ----
    steel = _metal(env); side = cfg.get("side", 1)
    bpy.context.view_layer.update()
    HM = handle_obj.parent.matrix_local @ handle_obj.matrix_local
    lv = np.array([tuple(p.co) for p in handle_obj.data.vertices])  # handle local: pivot-centred, arm = +Z
    hp = handle_obj.parent  # pivot empty
    arm = (hp.matrix_local.to_3x3() @ Vector((0, 0, 1))).normalized()
    al = cfg.get("along", 24)
    # arm is a straight prism with few verts: use a wide band (skip hub z<8) and take bbox centre of the section
    sec = lv[(np.sign(lv[:, 0]) == side) & (lv[:, 2] > 8) & (np.abs(lv[:, 2] - al) < 16)]
    if not len(sec): raise SystemExit("prop hang: no handle section found; change 'along'")
    lo, hi = sec.min(0), sec.max(0); ext = hi - lo
    c = HM @ Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, al))
    rad = 0.5 * max(np.hypot(ext[0], ext[1]), 1.0)
    c.x += side * cfg.get("out", 0)
    yaw = math.radians(cfg.get("yaw", 0))
    face = Matrix.Rotation(yaw, 3, 'Z') @ Vector((side, 0, 0))  # opener outward normal
    # ball chain loop (plane = face normal + vertical): over the arm, down both faces of the opener, through the hole
    br, pitch = cfg.get("ball_mm", 2.4) / 2, cfg.get("ball_pitch", 3.1)
    Rt = rad + br + 0.3; s = info["size"][2] / 2 + br + 0.2; wb = -cfg.get("drop", 24)
    pts = [(Rt * math.cos(a), Rt * math.sin(a)) for a in np.linspace(math.pi, 0, 15)]
    pts += [(Rt, -4), (s, wb + 5), (s, wb), (-s, wb), (-s, wb + 5), (-Rt, -4)]
    for _ in range(3):  # Chaikin smoothing (closed loop) -> natural hanging curve
        q = []
        for i in range(len(pts)):
            a, b = np.array(pts[i]), np.array(pts[(i + 1) % len(pts)])
            q += [tuple(0.75 * a + 0.25 * b), tuple(0.25 * a + 0.75 * b)]
        pts = q
    P = np.array(pts); seg = np.linalg.norm(np.roll(P, -1, 0) - P, axis=1); cum = np.r_[0, np.cumsum(seg)]
    n = int(cum[-1] // pitch); ts = np.linspace(0, cum[-1], n, endpoint=False)
    uv = np.c_[np.interp(ts, cum, np.r_[P[:, 0], P[0, 0]]), np.interp(ts, cum, np.r_[P[:, 1], P[0, 1]])]
    Zv = Vector((0, 0, 1))
    W3 = [c + face * u + Zv * w for u, w in uv]
    bm = bmesh.new()
    for i, p in enumerate(W3):
        bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=br, matrix=Matrix.Translation(p))
        q = W3[(i + 1) % len(W3)]; dv = q - p
        if i == len(W3) // 3: continue  # clasp sits here instead of a wire
        bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=0.32, radius2=0.32, depth=dv.length,
                              matrix=Matrix.Translation((p + q) / 2) @ Zv.rotation_difference(dv).to_matrix().to_4x4())
    # connector clasp: small capsule over the joint
    k = len(W3) // 3; p, q = W3[k], W3[(k + 1) % len(W3)]; dv = q - p; cm_ = (p + q) / 2
    Mr = Matrix.Translation(cm_) @ Zv.rotation_difference(dv).to_matrix().to_4x4()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=br * 1.15, radius2=br * 1.15, depth=6.0, matrix=Mr)
    for e in (-3.0, 3.0):
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=br * 1.15, matrix=Mr @ Matrix.Translation((0, 0, e)))
    me = bpy.data.meshes.new("BallChain"); bm.to_mesh(me); bm.free()
    for poly in me.polygons: poly.use_smooth = True
    me.materials.append(steel)
    ch = bpy.data.objects.new("BallChain", me); bpy.context.scene.collection.objects.link(ch); ch.parent = rig
    jb = c + Zv * wb  # bottom run of balls: hole top edge rests on top of these balls
    rj = br
    hx, hy, hr = info["hole"]
    hole = Vector((hx, hy, info["size"][2] / 2))
    g = Vector(info["centroid"]); u = Vector((g.x - hx, g.y - hy, 0)).normalized()  # hole -> centroid (local)
    # local basis (u, w, n) -> world (down, side_dir, face)
    down = Vector((0, 0, -1)); sdir = face.cross(down)
    w = Vector((0, 0, 1)).cross(u)
    Rm = Matrix((down, sdir, face)).transposed() @ Matrix((u, w, Vector((0, 0, 1))))
    target = jb + Vector((0, 0, rj - hr))  # hole centre
    M = Matrix.Translation(target) @ Rm.to_4x4() @ Matrix.Translation(-hole)
    o = mesh_obj("Prop", v, d["f"], mats, d["p"] - 1, rig); o.matrix_parent_inverse = Matrix(); o.matrix_basis = M
    # clearance check vs cup
    bpy.context.view_layer.update()
    cm = cup_obj.matrix_local; pts = [M @ Vector(p) for p in v[::7]]
    bvh = BVHTree.FromPolygons([cm @ x.co for x in cup_obj.data.vertices], [tuple(p.vertices) for p in cup_obj.data.polygons])
    inside = 0; gap = 1e9
    for p in pts:
        loc, nrm, _, dist = bvh.find_nearest(p)
        if loc is None: continue
        gap = min(gap, dist)
        if (p - loc).dot(nrm) < 0: inside += 1
    print(f"PROP hang: arm centre {tuple(round(x, 1) for x in c)} min gap {gap:.1f} mm, inside pts {inside}")
    return o
