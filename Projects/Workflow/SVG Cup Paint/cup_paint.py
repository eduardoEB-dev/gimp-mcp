"""Paint the appended art on a cup 3MF (cup front and/or lid) to match the SVG colors (Bambu Studio paint).

  python -I cup_paint.py "<cup.3mf>" [--work "<append work folder>" ...] [--out "<out.3mf>"]
                         [--slots "White=2,Black=3"] [--body "#FFFFFF"] [--force]

Finds the append runs that made the art by itself: every NewCupProject\\*\\ folder with a cup run
(Work\\<Name>_tris.json + STL\\<Name> - <Color>.stl) or a lid run (Work\\<Name>_lid_tris.json +
STL\\<Name> Lid - <Color>.stl) whose triangles are in the 3MF. Cup art and lid art may come from different runs.
Every matching triangle gets its color's filament slot; the cup and lid bodies keep theirs. Geometry is not
changed: only triangle paint_color attributes and the filament colors.

Default out: "<cup name> - Painted.3mf" next to the cup. Slots: each SVG color uses the filament already in
the 3MF with the same or a close color (any order); colors with no match need new filaments, and it stops and
prints a table of what to add. Handles parts Bambu re-centered on save.
Exit 0 = written, 1 = stopped (the ERROR line says why).
"""

import argparse
import glob
import json
import os
import re
import sys
import zipfile
from tempfile import NamedTemporaryFile

import numpy as np
from scipy.spatial import cKDTree

PROJECTS = r"G:\Blender\blender-mcp\Projects\NewCupProject"
TRI_RE = re.compile(r"<triangle\b([^>]*?)/>")
VERT_RE = re.compile(r'<vertex\s+x="([^"]+)"\s+y="([^"]+)"\s+z="([^"]+)"')
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')
TOL = 0.002  # mm, centroid match
NEAR = 60    # RGB distance: an existing filament this close counts as the SVG color (e.g. #000000 for #111111)
# (kind, tris.json suffix, per-color STL name, source part STL the art was added to)
KINDS = [
    ("cup", "_tris.json", lambda n, c: f"{n} - {(n + '_' + c).split('_', 1)[1]}.stl", "cup_preview.stl"),
    ("lid", "_lid_tris.json", lambda n, c: f"{n} Lid - {c}.stl", "lid_src.stl"),
]


def die(msg):
    sys.stdout.flush()
    sys.exit("ERROR: " + msg)


def paint_code(slot):
    """Bambu/Prusa whole-triangle paint state for filament slot 1..18."""
    if slot == 1: return "4"
    if slot == 2: return "8"
    return f"{slot - 3:X}C"


def paint_states(code):
    """Filament slots used in one paint_color string (handles subdivided triangles)."""
    nib = [int(ch, 16) for ch in reversed(code)]
    out, i = set(), 0

    def node():
        nonlocal i
        if i >= len(nib): return
        n = nib[i]; i += 1
        if n & 3:  # split: (n & 3) + 1 children
            for _ in range((n & 3) + 1): node()
        else:
            s = n >> 2
            if s == 3 and i < len(nib): s = 3 + nib[i]; i += 1
            if s: out.add(s)
    while i < len(nib): node()
    return out


def read_stl(path):
    b = open(path, "rb").read()
    n = int.from_bytes(b[80:84], "little")
    dt = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("x", "<u2")])
    return np.frombuffer(b, dtype=dt, count=n, offset=84)["v"].astype(np.float64)


def cent_norm(P):
    c = P.mean(axis=1)
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    ln = np.linalg.norm(n, axis=1)
    return c, n / np.where(ln > 0, ln, 1)[:, None]


def load_sets(work):
    """Art sets (cup and/or lid) an append work folder holds."""
    sets = []
    for kind, suffix, stl_name, base in KINDS:
        tj = [f for f in glob.glob(os.path.join(work, "Work", "*" + suffix))
              if kind == "lid" or not f.endswith("_lid_tris.json")]
        if len(tj) != 1: continue
        try:
            meta = json.load(open(tj[0], encoding="utf-8"))
            name, colors = meta["name"], list(meta["tris"].keys())
            stls = {c: read_stl(os.path.join(work, "STL", stl_name(name, c))) for c in colors}
        except (OSError, ValueError, KeyError):
            continue
        sets.append({"kind": kind, "work": work, "name": name, "colors": colors, "hex": meta["hex"], "stls": stls,
                     "base": os.path.join(work, "Work", base)})
    return sets


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cup", help="cup 3MF with the appended art")
    ap.add_argument("--work", action="append", help="append work folder (repeatable; default: found automatically)")
    ap.add_argument("--out", help='painted 3MF (default: "<cup name> - Painted.3mf" next to the cup)')
    ap.add_argument("--slots", default="", help='color=slot overrides, e.g. "White=2,Black=3"')
    ap.add_argument("--body", help="slot 1 filament color, e.g. #FFFFFF (default: keep)")
    ap.add_argument("--force", action="store_true", help="overwrite out (also allows out == cup)")
    a = ap.parse_args()
    out = a.out or os.path.splitext(a.cup)[0] + " - Painted.3mf"
    if os.path.exists(out) and not a.force: die(f"{out} exists (--force to overwrite)")

    # Every mesh in the 3MF: triangle centroids + normals + bbox center.
    zin = zipfile.ZipFile(a.cup)
    meshes = []
    for member in (m for m in zin.namelist() if m.lower().endswith(".model")):
        text = zin.read(member).decode("utf-8")
        V = np.array(VERT_RE.findall(text), dtype=float)
        tris = [dict(ATTR_RE.findall(t)) for t in TRI_RE.findall(text)]
        if not len(V) or not tris: continue
        T = np.array([[int(t["v1"]), int(t["v2"]), int(t["v3"])] for t in tris])
        c, n = cent_norm(V[T])
        meshes.append({"member": member, "text": text, "c": c, "n": n, "tree": cKDTree(c), "mid": (V.min(0) + V.max(0)) / 2})

    def coverage(s):
        """-> (share of sampled art triangles found, mesh index, shift). Bambu re-centers a part's mesh on its
        bounding box when it saves, so also try that shift (from the part the art was added to)."""
        P = np.concatenate(list(s["stls"].values()))
        pc, _ = cent_norm(P[np.linspace(0, len(P) - 1, min(200, len(P))).astype(int)])
        Q = P.reshape(-1, 3); lo, hi = Q.min(0), Q.max(0)
        if os.path.exists(s["base"]):
            B = read_stl(s["base"]).reshape(-1, 3); lo, hi = np.minimum(lo, B.min(0)), np.maximum(hi, B.max(0))
        best = (0, None, None)
        for i, m in enumerate(meshes):
            for sh in (np.zeros(3), m["mid"] - (lo + hi) / 2):
                cov = np.isfinite(m["tree"].query(pc + sh, distance_upper_bound=TOL)[0]).mean()
                if cov > best[0]: best = (cov, i, sh)
        return best

    # The append runs whose art is in this 3MF (newest first; one art set per part).
    works = a.work or sorted(glob.glob(os.path.join(PROJECTS, "*")), key=os.path.getmtime, reverse=True)
    chosen = {}
    for w in works:
        for s in load_sets(w):
            cov, mi, sh = coverage(s)
            if cov > 0.99 and mi not in chosen:
                s["mesh"], s["shift"] = mi, sh; chosen[mi] = s
    if not chosen:
        die(f"no append work folder {'given' if a.work else 'under ' + PROJECTS} matches this 3MF's art. Pass --work, or re-run the append")
    sets = list(chosen.values())

    # Match each part's triangles to its art colors (touching colors share walls facing opposite ways).
    for s in sets:
        m = meshes[s["mesh"]]
        C = np.concatenate([cent_norm(s["stls"][c])[0] for c in s["colors"]]) + s["shift"]
        N = np.concatenate([cent_norm(s["stls"][c])[1] for c in s["colors"]])
        owner = np.concatenate([np.full(len(s["stls"][c]), k) for k, c in enumerate(s["colors"])])
        d, idx = cKDTree(C).query(m["c"], k=4, distance_upper_bound=TOL)
        color = np.full(len(m["c"]), -1)
        for j in range(4):
            ok = (color < 0) & np.isfinite(d[:, j])
            ii = np.where(ok, idx[:, j], 0)
            ok &= np.einsum("ij,ij->i", m["n"], N[ii]) > 0.9
            color[ok] = owner[ii[ok]]
        s["color"] = color

    # Slots already used by other parts (their filament or other paint): shared only if the color matches.
    art_rows = {s["mesh"]: s["color"] for s in sets}
    used = {}
    for i, m in enumerate(meshes):
        rows = TRI_RE.findall(m["text"])
        if i in art_rows: rows = [t for t, k in zip(rows, art_rows[i]) if k < 0]
        for attrs in rows:
            pm = re.search(r'paint_color="([^"]*)"', attrs)
            if pm:
                for st in paint_states(pm.group(1)): used.setdefault(st, f"paint in {m['member']}")
    if "Metadata/model_settings.config" in zin.namelist():
        ms = zin.read("Metadata/model_settings.config").decode("utf-8")
        for v in re.findall(r'key="extruder"\s+value="(\d+)"', ms):
            if int(v) > 0: used.setdefault(int(v), "an object/part set to this filament")
    # Filament slots, per distinct SVG color (hex). Default: the filament already in the 3MF with the same or a
    # close color, in any order; colors with no match get new slots after the existing ones.
    settings = "Metadata/project_settings.config"
    cfg = zin.read(settings).decode("utf-8")
    cfg_json = json.loads(cfg)
    fil = cfg_json["filament_colour"]
    if a.body: fil[0] = a.body.upper()
    rgb = lambda h: np.array([int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)], float)
    label = {}  # hex -> color name(s)
    for s in sets:
        for c in s["colors"]:
            h = s["hex"][c].upper()
            if c not in label.get(h, []): label.setdefault(h, []).append(c)
    hexes = list(label)
    slots, matched = {}, set()
    for item in filter(None, a.slots.split(",")):
        c, sl = item.split("=")
        hit = [h for h in hexes if c.strip() in label[h] or c.strip().upper() == h]
        if not hit: die(f"--slots: unknown color {c!r}; colors are {sorted({n for v in label.values() for n in v})}")
        for h in hit: slots[h] = int(sl)
    pairs = sorted((float(np.linalg.norm(rgb(h) - rgb(f))), h, i + 1) for h in hexes if h not in slots for i, f in enumerate(fil))
    taken = set(slots.values())
    for dist, h, sl in pairs:
        if h in slots or sl in taken or dist > NEAR: continue
        slots[h] = sl; matched.add(h); taken.add(sl)
    # Colors with no match: first reuse existing slots nothing uses (e.g. filaments just added in Bambu with any
    # color; they get recolored), then new slots after the existing ones.
    free = [i + 1 for i in range(1, len(fil)) if i + 1 not in taken and i + 1 not in used]
    nxt = len(fil) + 1
    for h in hexes:
        if h not in slots:
            if free:
                slots[h] = free.pop(0)
            else:
                while nxt in taken: nxt += 1
                slots[h] = nxt
            taken.add(slots[h])

    short = {}
    for s in sets:
        print(f"{s['kind']} art: {s['name']} from {s['work']} -> {meshes[s['mesh']]['member']}"
              + (f" (re-centered by Bambu, shift {np.round(s['shift'], 3).tolist()} mm)" if np.any(np.abs(s["shift"]) > 1e-6) else ""))
        for k, c in enumerate(s["colors"]):
            h = s["hex"][c].upper()
            got = int((s["color"] == k).sum())
            print(f"  {c}: {got}/{len(s['stls'][c])} triangles -> slot {slots[h]} ({h}, {'existing filament' if h in matched else 'recolored spare slot' if slots[h] <= len(fil) else 'new'})")
            if got < len(s["stls"][c]): short[f"{s['kind']} {c}"] = (got, len(s["stls"][c]))
    if short: die(f"some art triangles not found: {short}. Nothing written")

    same = lambda h, sl: h in matched or (sl <= len(fil) and np.linalg.norm(rgb(fil[sl - 1]) - rgb(h)) <= NEAR)
    clash = {sl: used[sl] for h, sl in slots.items() if sl in used and not same(h, sl)}
    if clash:
        die(f"slot(s) {sorted(clash)} are already used by other parts in another color "
            f"({'; '.join(f'{k}: {w}' for k, w in sorted(clash.items()))}). Pick free slots with --slots, or ASK the user")

    need = max(slots.values())
    printer = cfg_json.get("printer_model", "")
    if need > 4 and "A1 mini" in printer:
        print(f"WARNING: this cup needs {need} filaments but the 3MF is set to {printer} (holds 4). Switch it to the X2D in Bambu Studio")
    if len(fil) < need:
        fmt = lambda h: ", ".join(str(int(x)) for x in rgb(h))
        print()
        print("Filaments for this cup (order doesn't matter: the script finds each one by its color):")
        print("| Slot | Color | Hex | RGB | Status |")
        print("|---|---|---|---|---|")
        print(f"| 1 | Body | {fil[0].upper()} | {fmt(fil[0])} | already in the 3MF |")
        for h in sorted(hexes, key=lambda h: slots[h]):
            if slots[h] == 1: continue
            print(f"| {slots[h]} | {' / '.join(label[h])} | {h} | {fmt(h)} | {'already in the 3MF' if slots[h] <= len(fil) else '**ADD**'} |")
        print()
        die(f"3MF has {len(fil)} filament slot(s), needs {need} (add the **ADD** rows). "
            f"The user must open it in Bambu Studio, pick the printer "
            f"({'X2D: more than 4 filaments' if need > 4 else 'X2D or A1 mini'}), add those filaments, save, then run this again")
    for h in hexes:
        if h not in matched: fil[slots[h] - 1] = h
    mm = re.search(r'("filament_colour":\s*)\[[^\]]*\]', cfg)
    nl = "\r\n" if "\r\n" in cfg else "\n"
    cfg = cfg[:mm.start()] + mm.group(1) + "[" + nl + ("," + nl).join(f'        "{x}"' for x in fil) + nl + "    ]" + cfg[mm.end():]

    # Repaint the art triangles; everything else stays byte-identical.
    new_texts, hits = {}, 0
    for s in sets:
        m = meshes[s["mesh"]]
        codes = [paint_code(slots[s["hex"][c].upper()]) for c in s["colors"]]
        it = iter(s["color"])

        def repaint(mt):
            k = next(it)
            if k < 0: return mt.group(0)
            attrs = re.sub(r'\s+paint_color="[^"]*"', "", mt.group(1))
            return f'<triangle{attrs} paint_color="{codes[k]}"/>'
        new_texts[m["member"]] = TRI_RE.sub(repaint, m["text"])
        hits += int((s["color"] >= 0).sum())

    with NamedTemporaryFile(dir=os.path.dirname(os.path.abspath(out)), suffix=".3mf", delete=False) as st:
        tmp = st.name
    try:
        with zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
            for info in zin.infolist():
                f = info.filename
                data = new_texts[f].encode() if f in new_texts else cfg.encode() if f == settings else zin.read(info)
                zo.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
        os.replace(tmp, out)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    print(f"painted {hits} triangles in {', '.join(new_texts)}; filaments: {', '.join(f'{i + 1}={x}' for i, x in enumerate(fil))}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
