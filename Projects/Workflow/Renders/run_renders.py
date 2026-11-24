"""TryCatch ad renders from a 3MF, end to end.

usage: python -I run_renders.py <file.3mf> <output_dir> [--spec spec.json] [--test] [--only shot1,shot2]
  --test   quick 400px / 24-sample pass into Renders/test + contact sheet (check framing first)
  --spec   optional JSON overrides (see Render_Workflow.md)

Creates under <output_dir>:
  Work/            manifest.json, shots.json, extracted meshes (npz)
  Renders/layers/  fg (sharp product) + bg (blurred set) per shot
  Renders/no_logo/ composited renders
  Renders/test/    quick test renders + contact_sheet.png
  Drafts/          final images with the logo card  (+ contact_sheet.png)
"""
import sys, os, json, subprocess, argparse
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--spec"); ap.add_argument("--test", action="store_true")
ap.add_argument("--only")
a = ap.parse_args()
spec = json.load(open(a.spec)) if a.spec else {}
D = {k: os.path.join(a.out, *k.split("/")) for k in ("Work", "Renders/layers", "Renders/no_logo", "Renders/test", "Drafts")}
for p in D.values(): os.makedirs(p, exist_ok=True)

# 1. extract
subprocess.run([sys.executable, "-I", os.path.join(HERE, "extract_3mf.py"), a.src, D["Work"]], check=True)
man = json.load(open(os.path.join(D["Work"], "manifest.json")))
objs = man["objects"]

# 2. choose cups / caps
def ncolors(o): return len(o["painted"]) + 1
if spec.get("cups"): cups = spec["cups"]
else:  # one per distinct object name; prefer the variant with the most colors (e.g. "5 Color" plates)
    best = {}
    for o in (o for o in objs if o["role"] == "cup"):
        if o["name"] not in best or ncolors(o) > ncolors(best[o["name"]]): best[o["name"]] = o
    cups = [o["label"] for o in best.values()]
SHORT = {}  # label -> short name for file names (drops the _2 suffix of duplicate variants)
for c in cups:
    s = next(o for o in objs if o["label"] == c)["label"].rsplit("_", 1)
    s = s[0] if len(s) == 2 and s[1].isdigit() else c
    SHORT[c] = s if s not in SHORT.values() else c
caps = spec.get("caps") or [o["label"] for o in objs if o["role"] == "cap"]
if not cups: sys.exit("no cup found in 3MF")
cap_for = spec.get("cap_for", {})
def cap_of(i, cup): return cap_for.get(cup) or (caps[i % len(caps)] if caps else None)

# 3. plan shots (framing tuned on the Grinch/Snoopy releases)
X = 0.052
# items taller than the ~130 mm cooler cup (e.g. popcorn bucket) -> pull camera back proportionally
H = max(o["bbox"][1][2] - o["bbox"][0][2] for o in objs if o["label"] in cups)
K = spec.get("frame_scale", max(1.0, H / 130.0))
def rig(cup, cap, x=0, rot=0, handle=0): return {"cup": cup, "cap": cap, "x": x, "rot": rot, "handle": handle}
shots = []
def add(name, rigs, az, el, dist, tz): shots.append({"name": name, "rigs": rigs, "az": az, "el": el, "dist": dist * K, "tz": tz * K})
if len(cups) >= 2:
    c0, c1 = cups[0], cups[1]
    add("pair_hero", [rig(c0, cap_of(0, c0), -X, 10, 88), rig(c1, cap_of(1, c1), X, -10, 88)], 0, 20, 0.62, 0.064)
    add("pair_front", [rig(c0, cap_of(0, c0), -X), rig(c1, cap_of(1, c1), X)], 0, 8, 0.74, 0.090)
    heroes = [(c, cap_of(i, c), SHORT[c]) for i, c in enumerate(cups)]
else:
    c0 = cups[0]
    heroes = [(c0, cp, cp) for cp in caps] if len(caps) > 1 else [(c0, cap_of(0, c0), SHORT[c0])]
for i, (cup, cap, lab) in enumerate(heroes):
    add(f"hero_{lab}", [rig(cup, cap, handle=88)], -25 if i % 2 == 0 else 25, 20, 0.50, 0.068)
if len(cups) == 1: add("front", [rig(cups[0], cap_of(0, cups[0]))], 0, 8, 0.62, 0.090)
add("left", [rig(cups[0], cap_of(0, cups[0]))], -90, 10, 0.62, 0.090)
add("right", [rig(cups[-1], cap_of(len(cups) - 1, cups[-1]) if len(cups) > 1 else (caps[-1] if caps else None))], 90, 10, 0.62, 0.090)
add("back_three_q", [rig(cups[0], cap_of(0, cups[0]))], 140, 16, 0.62, 0.090)
if spec.get("back"): add("back", [rig(cups[0], caps[-1] if caps else None, handle=-88)], 180, 18, 0.50, 0.068)
if caps:
    n = len(caps); step = 0.094
    rr = [{"cup": None, "cap": cp, "x": (k - (n - 1) / 2) * step, "rot": spec.get("caps_top_rot", 30)} for k, cp in enumerate(caps)]
    add("caps_top", rr, 0, 32 if n == 1 else 30, 0.36 if n == 1 else 0.46 + 0.05 * max(0, n - 2), 0.012 if n == 1 else 0.016)
for s in spec.get("extra_shots", []): shots.append(s)
skip = set(spec.get("skip", []))
shots = [s for s in shots if s["name"] not in skip]
screen = None
if spec.get("theme") == "desk":  # monitor shows real code: spec "screen_code" = list of .py files (default: this pipeline)
    screen = os.path.join(D["Work"], "code_screen.png")
    code = spec.get("screen_code") or [os.path.join(HERE, "render_3mf.py")]
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "make_screen.py"), ",".join(code), screen], check=True)
json.dump({"shots": shots, "cap_rot_deg": spec.get("cap_rot_deg", 180), "layer_lines": spec.get("layer_lines", 1.0),
           "theme": spec.get("theme", "christmas"), "screen": screen}, open(os.path.join(D["Work"], "shots.json"), "w"), indent=1)
names = [s["name"] for s in shots if not a.only or s["name"] in a.only.split(",")]
print("cups:", cups, "| caps:", caps); print("shots:", names)

# 4. render
def blender(shot, out, samples, res, layer):
    r = subprocess.run([BLENDER, "-b", "--python", os.path.join(HERE, "render_3mf.py"), "--",
                        D["Work"], shot, out, str(samples), str(res), layer], capture_output=True, text=True)
    if "DONE" not in r.stdout: sys.exit(f"render failed: {shot} {layer}\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}")

def sheet(files, path, cell=400):
    cols = 4; rows = (len(files) + cols - 1) // cols; W = Image.new("RGB", (cols * cell, rows * cell), "white")
    for i, f in enumerate(files): W.paste(Image.open(f).convert("RGB").resize((cell, cell)), (cell * (i % cols), cell * (i // cols)))
    W.save(path); print("SHEET", path)

if a.test:
    outs = []
    for n in names:
        o = os.path.join(D["Renders/test"], f"{n}.png"); blender(n, o, 24, 400, "full"); outs.append(o); print("TEST", n)
    sheet(outs, os.path.join(D["Renders/test"], "contact_sheet.png")); sys.exit()

samples, res = spec.get("samples", 256), spec.get("res", 2000)
finals = []
for n in names:
    fg, bg = (os.path.join(D["Renders/layers"], f"{n}_{l}.png") for l in ("fg", "bg"))
    blender(n, fg, samples, res, "fg"); blender(n, bg, samples, res, "bg")
    out = os.path.join(D["Renders/no_logo"], f"{n}.png")
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "comp.py"), fg, bg, out], check=True); finals.append(out); print("RENDERED", n)
subprocess.run([sys.executable, "-I", os.path.join(HERE, "brand.py"), D["Drafts"], *finals], check=True)
sheet([os.path.join(D["Drafts"], os.path.splitext(os.path.basename(f))[0] + "_logo.png") for f in finals],
      os.path.join(D["Drafts"], "contact_sheet.png"))
