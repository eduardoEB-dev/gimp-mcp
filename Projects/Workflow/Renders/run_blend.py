"""TryCatch ad renders for an assembled multi-part model: geometry/pose from the .blend, colors from the 3MF.

usage: python -I run_blend.py <model.blend> <file.3mf> <output_dir> [--spec spec.json] [--test] [--only shot1,shot2] [--plan]
--plan stops after Work/blend_shots.json (part colors), no renders; Manual Creation uses it.
Same output layout and flags as run_renders.py (see Render_Workflow.md, "Assembled models from a .blend").
"""
import sys, os, re, json, math, difflib, subprocess, argparse
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

ap = argparse.ArgumentParser()
ap.add_argument("blend"); ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--spec"); ap.add_argument("--test", action="store_true")
ap.add_argument("--only"); ap.add_argument("--plan", action="store_true")
a = ap.parse_args()
spec = json.load(open(a.spec)) if a.spec else {}
D = {k: os.path.join(a.out, *k.split("/")) for k in ("Work", "Renders/layers", "Renders/no_logo", "Renders/test", "Drafts")}
for p in D.values(): os.makedirs(p, exist_ok=True)

# 1. colors from the 3MF, parts from the blend
subprocess.run([sys.executable, "-I", os.path.join(HERE, "extract_3mf.py"), a.src, D["Work"]], check=True, capture_output=True)
man = json.load(open(os.path.join(D["Work"], "manifest.json")))
r = subprocess.run([BLENDER, "-b", a.blend, "--python", os.path.join(HERE, "render_blend.py"), "--", D["Work"], "--inspect"], capture_output=True, text=True)
if "DONE" not in r.stdout: sys.exit(f"blend inspect failed\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
bp = json.load(open(os.path.join(D["Work"], "blend_parts.json")))
excl = set(spec.get("exclude_collections", []))
parts = [p for p in bp["parts"] if not p["hide_render"] and "proxy" not in p["name"].lower()
         and not excl & set(p["collections"]) and p["name"] not in spec.get("exclude", [])]

# 2. part -> extruder: best name match against the 3MF objects; spec "assign" (name prefix -> extruder) wins
def norm(n): return re.sub(r"[^a-z0-9]", "", re.sub(r"(\.stl$|^\d+_|_?(upside_?down|bottom))", "", n.lower()))
mf = {norm(o["name"]): o["extruder"] for o in man["objects"]}
word = {o["name"].lower().removesuffix(".stl").split("_")[-1]: o["extruder"] for o in man["objects"]}  # color word -> extruder
assign, unmatched = {}, []
for p in parts:
    pre = next((k for k in spec.get("assign", {}) if p["name"].startswith(k)), None)
    best = max(mf, key=lambda k: difflib.SequenceMatcher(None, norm(p["name"]), k).ratio())
    score = difflib.SequenceMatcher(None, norm(p["name"]), best).ratio()
    if pre: assign[p["name"]] = (spec["assign"][pre], "spec")
    elif score >= 0.75: assign[p["name"]] = (mf[best], best)
    elif p["name"].lower().split("_")[-1] in word: assign[p["name"]] = (word[p["name"].lower().split("_")[-1]], "color word")
    else: unmatched.append(p["name"])
if unmatched: sys.exit(f"no color for {unmatched}: add them to spec \"assign\" (ASK the user which filament)")
filaments = man["filaments"] + spec.get("extra_filaments", [])  # render-only colors not in the 3MF (assign them as extruder n + 1, ...)
for n, (e, why) in assign.items(): print(f"  {n:24} ext={e} {filaments[e - 1]}  <- {why}")

# 3. shot plan: camera fits the assembled height; product centered on the turntable
lo = [min(p["min"][i] for p in parts) for i in range(3)]; hi = [max(p["max"][i] for p in parts) for i in range(3)]
if spec.get("candle"):  # render-only jar candle on top: include it (+ flames) in the framed height
    c = spec["candle"]; hi[2] = max(hi[2], c.get("z_mm", 0) + c.get("h_mm", 95) + (14 if c.get("lit", True) else 0))
H = (hi[2] - lo[2]) / 1000
FIT = 1 / (2 * math.tan(math.atan(18 / 85)))  # 85 mm lens, square frame: distance per meter of framed height
F = spec.get("frame_scale", 1.0)
def shot(name, az, el, frame_h, tz, **k):  # spec "fstop" sets the default aperture (tall models sit farther back: open up to blur the set)
    return {"name": name, "az": az, "el": el, "dist": frame_h * FIT * F, "tz": tz, **({"fstop": spec["fstop"]} if "fstop" in spec else {}), **k}
shots = [shot("hero", -30, 12, H * 1.25, H * 0.5), shot("front", 0, 6, H * 1.22, H * 0.5), shot("left", -90, 8, H * 1.22, H * 0.5),
         shot("right", 90, 8, H * 1.22, H * 0.5), shot("back_three_q", 145, 14, H * 1.25, H * 0.5)]
shots += [shot(s["name"], s["az"], s["el"], s["frame_mm"] / 1000, s["tz_mm"] / 1000, **{k: v for k, v in s.items() if k in ("fstop", "center_mm", "layer_lines", "exposure")})
          for s in spec.get("extra_shots", [])]
shots = [s for s in shots if s["name"] not in set(spec.get("skip", []))]
screen = None
if spec.get("theme", "seuss") == "desk":  # monitor shows real code: spec "screen_code" = list of .py files (default: this script)
    screen = os.path.join(D["Work"], "code_screen.png")
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "make_screen.py"), ",".join(spec.get("screen_code") or [os.path.abspath(__file__)]), screen], check=True)
json.dump({"blend": os.path.abspath(a.blend), "filaments": filaments, "parts": {n: e for n, (e, _) in assign.items()},
           "offset": [-(lo[0] + hi[0]) / 2000, -(lo[1] + hi[1]) / 2000, -lo[2] / 1000], "shots": shots,
           "theme": spec.get("theme", "seuss"), "layer_lines": spec.get("layer_lines", 1.0), "popcorn": spec.get("popcorn", 16),
           "light_tz": spec.get("light_tz", H * 0.45), "exposure": spec.get("exposure", 0.1), "screen": screen, "candle": spec.get("candle"),
           "fuzzy": spec.get("fuzzy", []), "fuzzy_strength": spec.get("fuzzy_strength", 1.0)}, open(os.path.join(D["Work"], "blend_shots.json"), "w"), indent=1)
names = [s["name"] for s in shots if not a.only or s["name"] in a.only.split(",")]
print(f"parts: {len(parts)} | height {H * 1000:.0f} mm | shots: {names}")
if a.plan: sys.exit()

# 4. render (same layer/composite/logo flow as run_renders.py)
def blender(name, out, samples, res, layer):
    r = subprocess.run([BLENDER, "-b", "--python", os.path.join(HERE, "render_blend.py"), "--",
                        D["Work"], name, out, str(samples), str(res), layer], capture_output=True, text=True)
    if "DONE" not in r.stdout: sys.exit(f"render failed: {name} {layer}\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}")

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
for f in finals:  # spec "logo": {"<shot>": ["tr", 0.26]} moves/resizes the card off the product
    pos, frac = spec.get("logo", {}).get(os.path.splitext(os.path.basename(f))[0], ["br", 0.34])
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "brand.py"), "--pos", pos, "--frac", str(frac), D["Drafts"], f], check=True)
sheet([os.path.join(D["Drafts"], os.path.splitext(os.path.basename(f))[0] + "_logo.png") for f in finals],
      os.path.join(D["Drafts"], "contact_sheet.png"))
