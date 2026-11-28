"""Move drafts left by older runs (shot not in this run's Work/shots.json) into Drafts/stale. Never deletes or overwrites.
usage: python -I move_stale_drafts.py "<output dir>" ["<output dir>" ...]
Prints STALE <folder> <file> per moved file, then KEEP <folder> <n>."""
import json, os, sys

def move_stale(out, names):
    dr = os.path.join(out, "Drafts"); keep = {n + "_logo.png" for n in names}; moved = []
    for f in sorted(os.listdir(dr)):
        if f.endswith("_logo.png") and f not in keep:
            st = os.path.join(dr, "stale"); os.makedirs(st, exist_ok=True)
            base, ext = os.path.splitext(f); dst = os.path.join(st, f); k = 2
            while os.path.exists(dst): dst = os.path.join(st, f"{base}_{k}{ext}"); k += 1
            os.rename(os.path.join(dr, f), dst); moved.append(f)
    return moved

if __name__ == "__main__":
    for out in sys.argv[1:]:
        names = [s["name"] for s in json.load(open(os.path.join(out, "Work", "shots.json")))["shots"]]
        tag = os.path.basename(os.path.normpath(out))
        for f in move_stale(out, names): print("STALE", tag, f)
        print("KEEP", tag, sum(os.path.exists(os.path.join(out, "Drafts", n + "_logo.png")) for n in names))
