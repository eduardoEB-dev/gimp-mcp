"""One-time: export the assembled cooler hardware (handle, pins, spigot) from the reference .blend
into assets/cooler_parts.npz in cup frame (cup axis at x=y=0, base z=0, front = -Y).
Re-run only if the handle/pin/spigot design changes.
Run: blender -b --python make_assets.py
"""
import bpy, bmesh, json, os, numpy as np
from mathutils import Matrix, Vector
BLU = r"G:\Blender\blender-mcp\Projects\NewCupProject\BlenderFiles\New_Cup_Solid_Half_BLU.blend"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
CY = 41.91
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(BLU) as (src, dst):
    dst.objects = [n for n in src.objects if n in ("Handle", "HandlePin", "Spigot", "Cap")]
arr = {}
for o in dst.objects:
    me = o.data.copy(); me.transform(Matrix.Translation((0, -CY, 0)) @ o.matrix_world)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    v = np.array([x.co[:] for x in me.vertices], np.float32); f = np.array([p.vertices[:] for p in me.polygons], np.int32)
    arr[o.name + "_v"], arr[o.name + "_f"] = v, f
pin = arr["HandlePin_v"]; pivot = [0.0, float(pin[:, 1].mean()), float(pin[:, 2].mean())]
arr["Handle_v"] = arr["Handle_v"] - np.array(pivot, np.float32)
cap_top = float(arr["Cap_v"][:, 2].max())
np.savez(os.path.join(OUT, "cooler_parts.npz"), **{k: v for k, v in arr.items() if not k.startswith("Cap")})
json.dump({"pivot": pivot, "cap_top": cap_top, "note": "cup frame mm; Handle_v is pivot-centred"},
          open(os.path.join(OUT, "cooler_parts.json"), "w"), indent=1)
print("ASSETS", pivot, cap_top, {k: v.shape for k, v in arr.items()})
