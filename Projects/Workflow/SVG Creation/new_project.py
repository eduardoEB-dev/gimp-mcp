"""Create (or reuse) a project folder for the SVG Creation workflow.

  <project>/
    Images/    source images / SVGs (copied in)
    Scripts/   project-specific scripts (one-off tweaks, lettering builders)
    Drafts/    <Name>_vN/ layer sets, one SVG per color + preview + _check.png
    Final/     <Name>/ approved layer sets, ready for Bambu Studio
    PROJECT.md goal, colors, size, version log

usage:
  python new_project.py <project_dir> [source files ...]
  python new_project.py <project_dir> --finalize <Drafts/Name_vN>   # copy approved draft to Final/Name
  python new_project.py <project_dir> --next <Name>                 # print next free Drafts/<Name>_vN path
"""
import argparse
import datetime
import os
import re
import shutil

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("sources", nargs="*")
ap.add_argument("--finalize")
ap.add_argument("--next")
args = ap.parse_args()

P = os.path.abspath(args.project)
DIRS = ["Images", "Scripts", "Drafts", "Final"]

if args.next:
    d = os.path.join(P, "Drafts")
    vs = [int(m.group(1)) for f in (os.listdir(d) if os.path.isdir(d) else [])
          if (m := re.fullmatch(re.escape(args.next) + r"_v(\d+)", f))]
    print(os.path.join(d, f"{args.next}_v{max(vs, default=0) + 1}"))
    raise SystemExit

if args.finalize:
    src = os.path.abspath(args.finalize if os.path.isabs(args.finalize) else os.path.join(P, args.finalize))
    name = re.sub(r"_v\d+$", "", os.path.basename(src.rstrip("\\/")))
    dst = os.path.join(P, "Final", name)
    if os.path.exists(dst):
        old = dst + "_old_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.rename(dst, old)
        print("previous final moved to", old)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("_check.png", "_labels.png"))
    print("final ->", dst)
    for f in sorted(os.listdir(dst)):
        print("  ", f)
    raise SystemExit

for d in DIRS:
    os.makedirs(os.path.join(P, d), exist_ok=True)
for s in args.sources:
    dst = os.path.join(P, "Images", os.path.basename(s))
    if os.path.abspath(s) != dst and not os.path.exists(dst):
        shutil.copy2(s, dst)
        print("copied", os.path.basename(s), "-> Images/")
md = os.path.join(P, "PROJECT.md")
if not os.path.exists(md):
    today = datetime.date.today().isoformat()
    open(md, "w", encoding="utf-8").write(f"""# {os.path.basename(P)}

Started {today}. Workflow: G:\\gimp-mcp\\Projects\\Workflow\\SVG Creation\\SVG_Creation_Workflow.md

## Goal
- What it's for:
- Size:
- Colors:
- Keep / drop:

## Versions

| Version | Date | What changed | Command |
|---|---|---|---|

## Final

""")
    print("created PROJECT.md")
print(P)
for d in DIRS:
    n = len(os.listdir(os.path.join(P, d)))
    print(f"  {d + '/':9s} {n} item(s)")
