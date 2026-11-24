"""Render-only blend: SnoopyCandle_V3 parts + a textured green grass base (not a print file).
Figure stays at its assembled coords; base top sits above z 0, so the figure looks seated in a recess.
usage: blender -b SnoopyCandle_V3.blend --python prep_grass_blend.py -- <out.blend>"""
import bpy, sys, math, numpy as np
OUT = sys.argv[sys.argv.index("--") + 1]
KEEP = ["ArmL", "ArmR", "Bowl", "Collar", "EarL_s", "EarR_s", "EyeL_c", "EyeR_c", "Nose", "Paw", "Remix", "RemixHead", "Smile_c", "Spot"]
A, B, CY, N = 88.0, 78.0, 9.0, 2.5        # superellipse semi-axes (176 x 156), center y, exponent
BOT, TOP, BLADE = -9.5, 2.0, 3.6          # base bottom z, soil level, blade height
RES = 0.2; X0, Y0 = -95.0, CY - 95.0; SZ = int(190 / RES)
rng = np.random.default_rng(11)
def rho(x, y): return (np.abs(x / B) ** N + np.abs((y - CY) / A) ** N) ** (1 / N)

# footprint of the figure near the table -> recess mask
d = bpy.data.objects["Remix"]; dg = d.data
co = np.empty(len(dg.vertices) * 3); dg.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
M = np.array(d.matrix_world); co = co @ M[:3, :3].T + M[:3, 3]
c = co[co[:, 2] < 7]
fp = np.zeros((SZ, SZ), bool); ix = ((c[:, 0] - X0) / RES).astype(int); iy = ((c[:, 1] - Y0) / RES).astype(int)
ok = (ix >= 0) & (ix < SZ) & (iy >= 0) & (iy < SZ); fp[iy[ok], ix[ok]] = True
print("footprint x", c[:, 0].min(), c[:, 0].max(), "y", c[:, 1].min(), c[:, 1].max(), "max rho", rho(c[:, 0], c[:, 1]).max())
def grow(m, it):
    for _ in range(it):
        m = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
    return m
def blur(a, it):
    for _ in range(it): a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    return a
fp = grow(fp, 3); fp = ~grow(~grow(fp, 12), 12)  # close small holes between verts
mask = np.clip(blur(fp.astype(float), 8) * 1.6, 0, 1)

# blades stamped into a height field (low relief, no overhangs)
H = np.zeros((SZ, SZ))
for _ in range(1100):
    while True:
        tx, ty = rng.uniform(-B, B), rng.uniform(CY - A, CY + A)
        if rho(tx, ty) < 0.97: break
    base = rng.uniform(0, 2 * math.pi)
    for k in range(rng.integers(5, 9)):
        ang = base + k * 2 * math.pi / 7 + rng.normal(0, 0.28)
        L, w0, hm, bend = rng.uniform(9, 16), rng.uniform(2.0, 2.9), BLADE * rng.uniform(0.75, 1.25), rng.uniform(-2.2, 2.2)
        rx, ry = tx + rng.normal(0, 0.7), ty + rng.normal(0, 0.7); dx, dy = math.cos(ang), math.sin(ang)
        R = L + 4; i0, i1 = max(int((rx - R - X0) / RES), 0), min(int((rx + R - X0) / RES), SZ); j0, j1 = max(int((ry - R - Y0) / RES), 0), min(int((ry + R - Y0) / RES), SZ)
        if i0 >= i1 or j0 >= j1: continue
        xx, yy = np.meshgrid(X0 + np.arange(i0, i1) * RES - rx, Y0 + np.arange(j0, j1) * RES - ry)
        u = xx * dx + yy * dy; v = -xx * dy + yy * dx; t = u / L
        s = v - bend * t * t; w = w0 * np.clip(1 - t, 0, 1) ** 0.75
        p = np.where((t >= 0) & (t <= 1) & (w > 0), np.clip(1 - np.abs(s) / np.maximum(w, 1e-3), 0, 1) ** 0.8 * hm * (0.45 + 0.55 * t), 0)
        H[j0:j1, i0:i1] = np.maximum(H[j0:j1, i0:i1], p)
gx, gy = np.meshgrid(X0 + np.arange(SZ) * RES, Y0 + np.arange(SZ) * RES)
soil = TOP + 0.35 * np.sin(gx / 13 + 1) * np.cos(gy / 17) + 0.25 * np.sin(gx / 7 + gy / 9)
Z = soil + blur(H, 1)
Z = Z * (1 - mask)                         # recess floor at z 0
def sample(x, y):
    fx, fy = np.clip((x - X0) / RES, 0, SZ - 2), np.clip((y - Y0) / RES, 0, SZ - 2); i, j = fx.astype(int), fy.astype(int); a, b = fx - i, fy - j
    return Z[j, i] * (1 - a) * (1 - b) + Z[j, i + 1] * a * (1 - b) + Z[j + 1, i] * (1 - a) * b + Z[j + 1, i + 1] * a * b

# superellipse rings: top field, rounded shoulder, side wall, bottom
NS, NR = 2000, 340
th = np.arange(NS) / NS * 2 * math.pi; ca, sa = np.cos(th), np.sin(th)
ux, uy = np.sign(ca) * np.abs(ca) ** (2 / N), np.sign(sa) * np.abs(sa) ** (2 / N)
rings = []
for r in (np.arange(1, NR + 1) / NR) ** 0.75:
    x, y = B * r * ux, CY + A * r * uy; z = sample(x, y)
    fade = np.clip((1.0 - r) / 0.035, 0, 1); fade = fade * fade * (3 - 2 * fade)    # blades die off into a rounded rim
    rings.append((x, y, TOP - 2.5 + (z - TOP + 2.5) * fade))
for k in range(1, 8):      # rounded shoulder down onto the wall
    a = k / 8 * math.pi / 2; r = 1 + 0.012 * math.sin(a); rings.append((B * r * ux, CY + A * r * uy, np.full(NS, TOP - 2.5 - 2.5 * (1 - math.cos(a)))))
for z, r in ((TOP - 5.0, 1.012), (BOT + 1.2, 1.022), (BOT + 0.35, 1.02), (BOT, 1.012)):
    rings.append((B * r * ux, CY + A * r * uy, np.full(NS, z)))
R = len(rings)
vt = np.empty((R * NS + 2, 3))
for i, (x, y, z) in enumerate(rings): vt[i * NS:(i + 1) * NS] = np.stack((x, y, z), 1)
vt[-2] = (0, CY, float(sample(np.array([0.0]), np.array([CY]))[0])); vt[-1] = (0, CY, BOT)
fa = []
for i in range(R - 1):
    a = i * NS + np.arange(NS); b = i * NS + (np.arange(NS) + 1) % NS
    fa.append(np.stack((a, b, b + NS, a + NS), 1))
fa = np.vstack(fa).tolist()
for j in range(NS):
    fa.append((R * NS, j, (j + 1) % NS))
    a, b = (R - 1) * NS + j, (R - 1) * NS + (j + 1) % NS; fa.append((R * NS + 1, b, a))
me = bpy.data.meshes.new("GrassBase"); me.from_pydata(vt.tolist(), [], fa); me.update()
ob = bpy.data.objects.new("GrassBase", me); bpy.context.scene.collection.objects.link(ob)
for o in list(bpy.data.objects):
    if o.name not in KEEP + ["GrassBase"]: bpy.data.objects.remove(o)
missing = [k for k in KEEP if k not in bpy.data.objects]
if missing: sys.exit(f"missing {missing}")
print("base", vt[:, 0].min(), vt[:, 0].max(), vt[:, 1].min(), vt[:, 1].max(), vt[:, 2].min(), vt[:, 2].max(), "faces", len(me.polygons))
bpy.ops.outliner.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True, relative_remap=False)
print("DONE")
