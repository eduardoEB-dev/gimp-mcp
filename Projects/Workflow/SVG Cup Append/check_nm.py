"""Headless non-manifold geometry check for 3MF/STL/OBJ/GLB inputs.

Usage:
  blender -b --python check_nm.py -- <file.3mf>

Prints per-mesh non-manifold stats and an overall verdict.
Exit code 0 if manifold, 1 if non-manifold, 2 on error.
"""
import sys
import os
import argparse
import bpy
import bmesh


def parse_args():
    argv = sys.argv if isinstance(sys.argv, (list, tuple)) else list(sys.argv)
    i = argv.index("--") if "--" in argv else -1
    rest = list(argv[i + 1:]) if i >= 0 else []
    p = argparse.ArgumentParser()
    p.add_argument("path")
    return p.parse_args(rest)


def load(path):
    p = os.path.abspath(path)
    ext = os.path.splitext(p)[1].lower()
    if ext == ".3mf":
        bpy.ops.wm.aseptif_3mf_read(filepath=p)
    elif ext == ".stl":
        if hasattr(bpy.ops.wm, "stl_read"):
            bpy.ops.wm.stl_read(filepath=p)
        else:
            bpy.ops.import_scene.stl(filepath=p)
    elif ext == ".obj":
        bpy.ops.import_scene.obj(filepath=p)
    elif ext == ".glb":
        bpy.ops.import_scene.gltf(filepath=p)
    else:
        raise SystemExit(f"unsupported ext {ext}")


def main():
    args = parse_args()
    if not os.path.isfile(args.path):
        print(f"ERROR: file not found: {args.path}")
        sys.exit(2)
    load(args.path)
    objects = [o for o in bpy.data.objects if o.type == "MESH"]
    print(f"objects: {len(objects)}")
    total_nm_verts = 0
    total_nm_edges = 0
    total_weld_4f = 0
    for o in objects:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        nm_verts = sum(1 for v in bm.verts if v.is_non_manifold)
        nm_edges = sum(1 for e in bm.edges if e.is_non_manifold)
        welded = sum(1 for e in bm.edges if len(e.link_faces) == 4)
        print(f"  {o.name}: verts={len(bm.verts)} faces={len(bm.faces)} "
              f"nm_verts={nm_verts} nm_edges={nm_edges} welded_4face={welded}")
        total_nm_verts += nm_verts
        total_nm_edges += nm_edges
        total_weld_4f += welded
        bm.free()
    print(f"TOTAL: nm_verts={total_nm_verts} nm_edges={total_nm_edges} welded_4face={total_weld_4f}")
    if total_nm_verts == 0 and total_nm_edges == 0:
        print("VERDICT: MANIFOLD")
        rc = 0
    else:
        print("VERDICT: NON-MANIFOLD")
        rc = 1
    if total_weld_4f > 0:
        print(f"NOTE: {total_weld_4f} welded 4-face edges (likely 3D-print seam edges; slicer handles these)")
    sys.exit(rc)


if __name__ == "__main__":
    main()
