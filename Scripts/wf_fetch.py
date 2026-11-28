"""Copy files OUT of a workflow folder into a project/work folder (never into a workflow folder).
Usage: python -I G:/gimp-mcp/Scripts/wf_fetch.py --why "<reason>" "<dest folder>" "<workflow file>" ["<workflow file>" ...]
Sources must be inside G:\gimp-mcp\Projects\Workflow or G:\Blender\blender-mcp\Projects\Workflows.
Dest must be outside both, under G:\Blender\blender-mcp\Projects or G:\gimp-mcp\Projects. Prints OK <name> <sha256[:12]> per file."""
import hashlib, os, shutil, sys

WF = [os.path.normcase(os.path.realpath(p)) for p in (r"G:\gimp-mcp\Projects\Workflow", r"G:\Blender\blender-mcp\Projects\Workflows")]
OK_DEST = [os.path.normcase(os.path.realpath(p)) for p in (r"G:\Blender\blender-mcp\Projects", r"G:\gimp-mcp\Projects")]

def inside(p, roots): return any(p == r or p.startswith(r + os.sep) for r in roots)
def sha(p):
    with open(p, "rb") as f: return hashlib.sha256(f.read()).hexdigest()[:12]

args = sys.argv[1:]
if len(args) < 4 or args[0] != "--why" or not args[1].strip():
    sys.exit('ERROR: --why "<reason>" is required first. ' + __doc__)
why, args = args[1].strip(), args[2:]
dest = os.path.realpath(args[0]); nd = os.path.normcase(dest)
if inside(nd, WF): sys.exit(f"ERROR: dest {dest} is inside a workflow folder")
if not inside(nd, OK_DEST): sys.exit(f"ERROR: dest {dest} is not under a Projects folder")
os.makedirs(dest, exist_ok=True)
print(f"COPY {len(args) - 1} file(s) -> {dest}  WHY: {why}")
for s in args[1:]:
    src = os.path.realpath(s)
    if not inside(os.path.normcase(src), WF): sys.exit(f"ERROR: {src} is not inside a workflow folder")
    if not os.path.isfile(src): sys.exit(f"ERROR: {src} is not a file")
    out = os.path.join(dest, os.path.basename(src))
    shutil.copyfile(src, out)
    a, b = sha(src), sha(out)
    print(f"{'OK' if a == b else 'MISMATCH'} {os.path.basename(src)} {b}")
