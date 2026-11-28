"""Patch the COPY of 3MF_Release_Workflow.md: generic titles, Etsy output folder/names, no overwrite, log table blank line.
usage: python -I patch_release_doc.py "<copy of 3MF_Release_Workflow.md>"
Refuses files inside the workflow folder or with an unexpected sha256[:12]. Prints PATCHED <new sha256[:12]>."""
import hashlib, os, sys

EXPECT = "b1d8ccbfc69c"
WF = os.path.normcase(os.path.realpath(r"G:\gimp-mcp\Projects\Workflow"))
p = os.path.realpath(sys.argv[1])
if os.path.normcase(p).startswith(WF + os.sep): sys.exit(f"ERROR: {p} is inside the workflow folder; patch a copy")
b = open(p, "rb").read()
h = hashlib.sha256(b).hexdigest()[:12]
if h != EXPECT: sys.exit(f"HASH MISMATCH {h} (expected {EXPECT})")
s = b.decode("utf8"); NL = "\r\n"

def rep(a, c):
    global s
    if s.count(a) != 1: sys.exit(f"ERROR: anchor found {s.count(a)}x: {a[:60]!r}")
    s = s.replace(a, c)

rep("3. **Title.** Use the user's title if given. Otherwise draft one from the plate and object names, and say what you picked.",
    "3. **Title.** Use the user's title if given. Otherwise draft one from the plate and object names, and say what you picked. "
    "Titles, file names and descriptions are **always generic**: no character, team or brand names (copyright), "
    "e.g. \"Happy Blue Creature Cooler Cup\", \"Texas Basketball Team Cooler Cup\". Plate names that carry such names don't go in the "
    "description either. The cup product is \"Cooler Cup\", never \"Coozie\". If no title is given, **ASK** with 3 generic options.")
rep("5. **Run `clean_3mf.py`.** Never overwrite the source. Default output is `<source folder>\\Final\\<Title> - Final.3mf`, or the folder the user names.",
    "5. **Run `clean_3mf.py`.** Never overwrite the source or any existing file (the cleaner refuses an existing output). "
    "Default output for printer-optimized sources (`*_a1mini_optimized.3mf`, `*_x2d_optimized.3mf`) is "
    "`<source folder>\\Etsy <Name>\\<Title> A1 mini - Etsy.3mf` / `<Title> X2D - Etsy.3mf` (like `Etsy Snoopy\\`); "
    "otherwise `<source folder>\\Etsy <Name>\\<Title> - Etsy.3mf`. `<source folder>\\Final\\<Title> - Final.3mf` collides with the "
    "existing finals, so don't use it. The user may name another folder.")
rep("SnowBase_X2D.3mf` (snow base only) | 2 ad renders from `SnowBase\\Drafts` (hero: hero_logo) |" + NL + NL,
    "SnowBase_X2D.3mf` (snow base only) | 2 ad renders from `SnowBase\\Drafts` (hero: hero_logo) |" + NL)
rep("Add a row after each release.", "Add a row after each release, directly under the last row (a blank line splits the table).")
nb = s.encode("utf8"); open(p, "wb").write(nb)
print("PATCHED", hashlib.sha256(nb).hexdigest()[:12])
