"""List the connected shells that fail validation, with color, size and edge checks.

Read-only. Same shell grouping and signed volume as SVG Cup Append\validate_3mf.py.

  python -I diagnose_shells.py "<work>\\Work\\<Name>_cup_mesh.json"        # decal only, colors known
  python -I diagnose_shells.py "<file.3mf>" --member 3D/Objects/object_21.model   # stored 3MF mesh
  add --all to list every shell, --json OUT to save the table

Columns: shell, color (JSON input only), tris, first tri index, signed volume mm^3,
open / 3+ face / repeated-direction edges in that shell, bbox, verdict.
Verdicts:
  FLIP-OK    closed, consistently wound, volume < 0: reversing the whole shell's winding is valid
  ZERO-VOL   closed and consistent but volume == 0: degenerate, do not flip
  TOPOLOGY   has open, 3+ face or repeated-direction edges: winding flip will not fix it
  ok         passes
Exit 0 = no bad shells, 1 = bad shells listed, 2 = input error.
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np

CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"


def shell_ids(vertices, triangles, edges):
    """Connected-shell id per triangle (same grouping as validate_3mf.shell_volumes)."""
    parents = list(range(len(vertices)))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for start, end in edges[:2 * len(triangles)].tolist():
        parents[root(start)] = root(end)
    roots = np.fromiter((root(i) for i in range(len(vertices))), dtype=np.intp)
    return roots[triangles[:, 0]]


def triangle_volume_terms(vertices, triangles, shell):
    points = vertices[triangles] - vertices[shell, None]  # local origin per shell
    return np.einsum("ij,ij->i", points[:, 0], np.cross(points[:, 1], points[:, 2]))


def load_json(path):
    with open(path, encoding="utf-8") as stream:
        mesh = json.load(stream)
    V = np.asarray(mesh["vertices"], dtype=float)
    T = np.asarray(mesh["triangles"], dtype=np.int64)
    owner = np.full(len(T), "?", dtype=object)
    for obj in mesh.get("objects", []):
        owner[obj["tri_start"]:obj["tri_end"]] = obj["name"]
    return [("json", V, T, owner)]


def load_3mf(path, members):
    out = []
    with zipfile.ZipFile(path) as archive:
        names = members or sorted(n for n in archive.namelist() if n.lower().endswith(".model"))
        for member in names:
            model = ET.fromstring(archive.read(member))
            for obj in model.findall(f"{CORE}resources/{CORE}object"):
                mesh = obj.find(f"{CORE}mesh")
                if mesh is None:
                    continue
                V = np.array([[float(v.attrib[k]) for k in "xyz"] for v in mesh.findall(f"{CORE}vertices/{CORE}vertex")])
                T = np.array([[int(t.attrib[k]) for k in ("v1", "v2", "v3")]
                              for t in mesh.findall(f"{CORE}triangles/{CORE}triangle")], dtype=np.int64)
                if len(V) and len(T):
                    painted = sum(1 for t in mesh.iter(f"{CORE}triangle") if "paint_color" in t.attrib)
                    out.append((f"{member} object={obj.get('id', '?')} painted_tris={painted}", V, T,
                                np.full(len(T), "", dtype=object)))
    return out


def shells(V, T, owner):
    edges = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]])
    shell = shell_ids(V, T, edges)
    vol = np.bincount(shell, weights=triangle_volume_terms(V, T, shell), minlength=len(V)) / 6
    # per undirected edge: incident count and direction balance, charged to the edge's shell
    edge_shell = np.concatenate([shell, shell, shell])
    order = np.lexsort((edges.max(axis=1), edges.min(axis=1)))
    und = np.sort(edges[order], axis=1)
    starts = np.r_[0, np.flatnonzero(np.any(und[1:] != und[:-1], axis=1)) + 1]
    counts = np.diff(np.r_[starts, len(edges)])
    fwd = np.add.reduceat((edges[:, 0] < edges[:, 1])[order], starts)
    es = edge_shell[order][starts]
    n = len(V)
    open_e = np.bincount(es[counts == 1], minlength=n)
    many_e = np.bincount(es[counts > 2], minlength=n)
    rep_e = np.bincount(es[(fwd > 1) | (counts - fwd > 1)], minlength=n)
    rows = []
    for s in np.unique(shell):
        idx = np.flatnonzero(shell == s)
        pts = V[np.unique(T[idx])]
        topo = open_e[s] or many_e[s] or rep_e[s]
        verdict = "TOPOLOGY" if topo else ("FLIP-OK" if vol[s] < 0 else "ZERO-VOL" if vol[s] == 0 else "ok")
        colors = sorted(set(owner[idx]) - {""})
        rows.append({
            "shell": int(s), "color": ",".join(colors), "tris": int(len(idx)), "first_tri": int(idx[0]),
            "volume": float(vol[s]), "open": int(open_e[s]), "3plus": int(many_e[s]), "repeated": int(rep_e[s]),
            "bbox_min": [round(float(x), 2) for x in pts.min(axis=0)],
            "bbox_max": [round(float(x), 2) for x in pts.max(axis=0)], "verdict": verdict,
        })
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="<Name>_cup_mesh.json / _lid_mesh.json, or a .3mf")
    ap.add_argument("--member", action="append", help="3MF model member (repeatable, default all)")
    ap.add_argument("--all", action="store_true", help="list passing shells too")
    ap.add_argument("--json", help="also write the rows to this JSON file")
    a = ap.parse_args()
    try:
        meshes = load_3mf(a.path, a.member) if a.path.lower().endswith(".3mf") else load_json(a.path)
    except (OSError, ValueError, KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}")
        return 2
    bad_total, report = 0, {}
    for label, V, T, owner in meshes:
        rows = shells(V, T, owner)
        bad = [r for r in rows if r["verdict"] != "ok"]
        bad_total += len(bad)
        report[label] = rows if a.all else bad
        print(f"{label}: {len(T)} tris, {len(rows)} shells, {len(bad)} bad")
        for r in report[label]:
            print(f"  shell {r['shell']} {r['color'] or '-'} tris={r['tris']} first_tri={r['first_tri']} "
                  f"vol={r['volume']:.4f} open={r['open']} 3plus={r['3plus']} repeated={r['repeated']} "
                  f"bbox={r['bbox_min']}..{r['bbox_max']} {r['verdict']}")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as stream:
            json.dump(report, stream, indent=1)
    print(f"diagnose: {bad_total} bad shell(s)")
    return 1 if bad_total else 0


if __name__ == "__main__":
    sys.exit(main())
