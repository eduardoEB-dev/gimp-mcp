"""Render instruction shots. usage: python -I run_steps.py <out_dir> <samples> <res> [shot,shot]"""
import sys, os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
out, samples, res = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3]
cfg = json.load(open(os.path.join(HERE, "steps.json")))
only = sys.argv[4].split(",") if len(sys.argv) > 4 else None
os.makedirs(out, exist_ok=True)
for s in cfg["shots"]:
    if only and s["name"] not in only: continue
    o = os.path.join(out, s["name"] + ".png")
    r = subprocess.run([BLENDER, "-b", "--python", os.path.join(HERE, "render_steps.py"), "--", os.path.join(HERE, "steps.json"), s["name"], o, samples, res],
                       capture_output=True, text=True)
    print(("OK  " if "DONE" in r.stdout else "FAIL") + " " + s["name"], flush=True)
    if "DONE" not in r.stdout: print(r.stdout[-2500:], r.stderr[-1500:])
