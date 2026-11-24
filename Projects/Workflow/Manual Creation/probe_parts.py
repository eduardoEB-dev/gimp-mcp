"""Part positions for placing labels and arrows, in assembly mm. Run with the .blend open.

usage: blender -b <model.blend> --python probe_parts.py -- <out.json> <blend_shots.json>            bounds, center, top/bottom of every part
       blender -b <model.blend> --python probe_parts.py -- --query <part> "<test on v>" [...]        centroid of the matching vertices

Examples: --query BaseCloud "v.z > 70"  finds a nub on top; --query Brim_White "v.z > 125.8 and v.y > 35"  finds a key block.
For a rod or string, "top"/"bottom" are its two end points.
"""
import bpy, sys, json, math
from mathutils import Vector

A = sys.argv[sys.argv.index("--") + 1:]

def verts(name):
    o = bpy.data.objects[name]; return [o.matrix_world @ v.co for v in o.data.vertices]

def mean(vs): return [round(sum(v[i] for v in vs) / len(vs), 1) for i in range(3)]

if A[0] == "--query":
    for i in range(1, len(A), 2):
        vs = [v for v in verts(A[i]) if eval(A[i + 1], {"math": math}, {"v": v, "r": math.hypot(v.x, v.y)})]
        print(A[i], A[i + 1], "->", mean(vs) if vs else None, "n", len(vs))
else:
    out = {}
    for n in json.load(open(A[1]))["parts"]:
        vs = verts(n); z = sorted(vs, key=lambda v: v.z)
        out[n] = {"min": [round(min(v[i] for v in vs), 1) for i in range(3)], "max": [round(max(v[i] for v in vs), 1) for i in range(3)],
                  "center": mean(vs), "top": mean(z[-8:]), "bottom": mean(z[:8])}
    json.dump(out, open(A[0], "w"), indent=1)
print("DONE")
