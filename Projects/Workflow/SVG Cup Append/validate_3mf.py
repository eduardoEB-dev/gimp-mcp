"""Check stored 3MF mesh topology without importing or welding the geometry."""

import argparse
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np


CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"


def shell_volumes(vertices, triangles, edges):
    parents = list(range(len(vertices)))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    # Two edges per triangle connect all three vertices.
    for start, end in edges[:2 * len(triangles)].tolist():
        parents[root(start)] = root(end)
    roots = np.fromiter((root(i) for i in range(len(vertices))), dtype=np.intp)
    shell = roots[triangles[:, 0]]
    # Use a local origin for each shell to reduce cancellation.
    points = vertices[triangles] - vertices[shell, None]
    terms = np.einsum("ij,ij->i", points[:, 0], np.cross(points[:, 1], points[:, 2]))
    return np.bincount(shell, weights=terms)[np.unique(shell)] / 6


def check_mesh(mesh):
    vertices = np.array([
        [float(v.attrib[axis]) for axis in "xyz"]
        for v in mesh.findall(f"{CORE}vertices/{CORE}vertex")
    ])
    triangles = np.array([
        [int(t.attrib[key]) for key in ("v1", "v2", "v3")]
        for t in mesh.findall(f"{CORE}triangles/{CORE}triangle")
    ], dtype=np.int64)
    if not len(vertices) or not len(triangles):
        raise ValueError("empty mesh")
    if not np.isfinite(vertices).all():
        raise ValueError("nonfinite vertex coordinates")
    if triangles.min() < 0 or triangles.max() >= len(vertices):
        raise ValueError("triangle index out of range")

    edges = np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]])
    order = np.lexsort((edges.max(axis=1), edges.min(axis=1)))
    undirected = np.sort(edges[order], axis=1)
    starts = np.r_[0, np.flatnonzero(np.any(undirected[1:] != undirected[:-1], axis=1)) + 1]
    counts = np.diff(np.r_[starts, len(edges)])
    forward = edges[:, 0] < edges[:, 1]
    directions = np.add.reduceat(forward[order], starts)
    points = vertices[triangles]
    area_vectors = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
    defects = {
        "open_edges": np.count_nonzero(counts == 1),
        "edges_with_3plus_faces": np.count_nonzero(counts > 2),
        "edges_with_repeated_direction": np.count_nonzero((directions > 1) | (counts - directions > 1)),
        "degenerate_triangles": np.count_nonzero(~np.any(area_vectors, axis=1)),
    }
    if not any(defects.values()):
        volumes = shell_volumes(vertices, triangles, edges)
        defects["nonpositive_volume_shells"] = np.count_nonzero(volumes <= 0)
    return len(triangles), defects


def validate(path, members=None):
    """Print a compact verdict. Return 0 for pass, 1 for defects, 2 for check errors."""
    status = 0
    checked = 0
    try:
        with zipfile.ZipFile(path) as archive:
            selected = members or sorted(name for name in archive.namelist() if name.lower().endswith(".model"))
            for member in selected:
                model = ET.fromstring(archive.read(member))
                if model.tag != f"{CORE}model":
                    raise ValueError(f"{member}: unsupported model XML")
                objects = model.findall(f"{CORE}resources/{CORE}object")
                mesh_count = 0
                for obj in objects:
                    mesh = obj.find(f"{CORE}mesh")
                    if mesh is None:
                        continue
                    mesh_count += 1
                    checked += 1
                    label = f"{member} object={obj.get('id', '?')}"
                    try:
                        triangles, defects = check_mesh(mesh)
                    except (ValueError, KeyError, OverflowError) as exc:
                        print(f"ERROR {label}: {exc}")
                        status = 2
                        continue
                    if any(defects.values()):
                        status = max(status, 1)
                    counts = " ".join(f"{name}={count}" for name, count in defects.items())
                    print(f"{label}: triangles={triangles} {counts}")
                if members and not mesh_count:
                    raise ValueError(f"{member}: no meshes found")
            if not checked:
                raise ValueError("no meshes found")
    except (OSError, ValueError, KeyError, ET.ParseError, zipfile.BadZipFile, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        status = 2
    print(f"3MF validation {('PASS', 'FAIL', 'ERROR')[status]}: {checked} mesh(es)")
    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="3MF file")
    parser.add_argument("--member", action="append", help="model member to check (repeatable, default: all)")
    args = parser.parse_args()
    sys.exit(validate(args.path, args.member))
