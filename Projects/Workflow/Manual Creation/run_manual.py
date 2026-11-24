"""TryCatch assembly manual: step renders from an assembled .blend + colors from the 3MF -> labeled images -> Word .docx.
Everything about the model lives in its manual.json (see Manual_Workflow.md).

usage: python -I run_manual.py prep  <manual.json> <output_dir>                 colors + part positions (Work/)
       python -I run_manual.py test  <manual.json> <output_dir> [--only a,b]    quick labeled previews + contact sheet
       python -I run_manual.py final <manual.json> <output_dir> [--only a,b]    full-size labeled renders + contact sheet
       python -I run_manual.py doc   <manual.json> <output_dir>                 JPEGs -> .docx -> Word/PDF check
"""
import sys, os, json, glob, shutil, subprocess, argparse
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
RUN_BLEND = os.path.join(HERE, "..", "Renders", "run_blend.py")
VENV_PY = os.path.join(HERE, ".venv", "Scripts", "python.exe")  # pymupdf for the page check

ap = argparse.ArgumentParser()
ap.add_argument("cmd", choices=["prep", "test", "final", "doc"]); ap.add_argument("manual"); ap.add_argument("out"); ap.add_argument("--only")
a = ap.parse_args()
manual, out = os.path.abspath(a.manual), os.path.abspath(a.out)  # Blender drops output when the path is relative
cfg = json.load(open(manual, encoding="utf-8")); shots = cfg["render"]["shots"]
work, rend = os.path.join(out, "Work"), os.path.join(out, "Renders")
blend_shots = os.path.join(work, "blend_shots.json")


def warn_unmatched():  # a typo in a part prefix or a shot name silently drops a part: catch it before spending render time
    parts = list(json.load(open(blend_shots))["parts"])
    prefixes = set(cfg["render"].get("all_parts", []))
    for s in shots:
        prefixes |= set(s.get("parts", [])) | set(s.get("drop", [])) | set(s.get("move", {}))
        for l in s.get("labels", []) + s.get("arrows", []):
            prefixes |= {l[k] for k in ("part", "part_a", "part_b") if k in l}
    for p in sorted(prefixes):
        if not any(n.startswith(p) for n in parts): print(f"WARNING: no part starts with '{p}'")
    names = {s["name"] for s in shots}
    for b in cfg["doc"]["blocks"]:
        refs = [b["img"]] if "img" in b else [c["shot"] for c in b.get("pair", [])]
        for r in refs:
            if r not in names: print(f"WARNING: doc uses shot '{r}', which isn't in render.shots")


def prep():
    os.makedirs(work, exist_ok=True)
    spec = os.path.join(work, "color_spec.json")
    json.dump({k: cfg[k] for k in ("exclude_collections", "exclude", "assign") if k in cfg}, open(spec, "w"), indent=1)
    subprocess.run([sys.executable, "-I", RUN_BLEND, cfg["blend"], cfg["3mf"], out, "--spec", spec, "--plan"], check=True)
    for d in ("Renders/layers", "Renders/no_logo", "Renders/test", "Drafts"):  # made by run_blend, unused here
        try: os.rmdir(os.path.join(out, *d.split("/")))
        except OSError: pass
    r = subprocess.run([BLENDER, "-b", cfg["blend"], "--python", os.path.join(HERE, "probe_parts.py"), "--", os.path.join(work, "part_points.json"), blend_shots],
                       capture_output=True, text=True)
    if "DONE" not in r.stdout: sys.exit(f"probe failed\n{r.stdout[-2000:]}\n{r.stderr[-1500:]}")
    print("part positions:", os.path.join(work, "part_points.json"))
    warn_unmatched()


def sheet(files, path, cell=400):
    cols = 4; rows = (len(files) + cols - 1) // cols; W = Image.new("RGB", (cols * cell, rows * cell), "white")
    for i, f in enumerate(files): W.paste(Image.open(f).convert("RGB").resize((cell, cell)), (cell * (i % cols), cell * (i // cols)))
    W.save(path); print("SHEET", path)


def render(name, samples, res):
    if not os.path.exists(blend_shots): sys.exit("run prep first")
    warn_unmatched()
    raw, ann = os.path.join(rend, name), os.path.join(rend, name + "_labeled"); os.makedirs(raw, exist_ok=True)
    only = a.only.split(",") if a.only else None
    for s in shots:
        if only and s["name"] not in only: continue
        o = os.path.join(raw, s["name"] + ".png")
        r = subprocess.run([BLENDER, "-b", "--python", os.path.join(HERE, "render_steps.py"), "--", manual, blend_shots, s["name"], o, str(samples), str(res)],
                           capture_output=True, text=True)
        if "DONE" not in r.stdout: sys.exit(f"render failed: {s['name']}\n{r.stdout[-2500:]}\n{r.stderr[-1500:]}")
        print("RENDERED", s["name"], flush=True)
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "annotate.py"), raw, ann], check=True)
    sheet(sorted(glob.glob(os.path.join(ann, "*.png"))), os.path.join(rend, name + "_contact_sheet.png"))


def doc():
    # JPEG, same pixels: the PNG build of the Cat in the Hat manual was 24.8 MB (Etsy limit 20 MB), this one 2.2 MB
    src, jpg = os.path.join(rend, "final_labeled"), os.path.join(rend, "jpg"); os.makedirs(jpg, exist_ok=True)
    sizes = {}
    def save(im, name):
        im.convert("RGB").save(os.path.join(jpg, name + ".jpg"), quality=85, optimize=True, progressive=True); sizes[name] = im.size
    for s in shots:
        f = os.path.join(src, s["name"] + ".png")
        if not os.path.exists(f): sys.exit(f"missing final render: {f}")
        save(Image.open(f), s["name"])
    cov = ImageOps.exif_transpose(Image.open(cfg["doc"]["cover"]["image"]))
    if cov.width > 1200: cov = cov.resize((1200, round(1200 * cov.height / cov.width)), Image.LANCZOS)
    save(cov, "cover")
    json.dump(sizes, open(os.path.join(jpg, "sizes.json"), "w"), indent=1)
    docx = os.path.join(out, cfg["name"] + " - Assembly Instructions.docx")
    subprocess.run(["node", os.path.join(HERE, "build_manual.js"), manual, jpg, docx], check=True)
    chk = [VENV_PY, "-I", os.path.join(HERE, "check_doc.py"), docx, rend]
    if cfg["doc"].get("source_notes"): chk += ["--source", cfg["doc"]["source_notes"]]
    subprocess.run(chk, check=True)


if a.cmd == "prep": prep()
elif a.cmd == "test": render("test", 24, 500)
elif a.cmd == "final": render("final", cfg["render"].get("samples", 128), cfg["render"].get("res", 1400))
else: doc()
