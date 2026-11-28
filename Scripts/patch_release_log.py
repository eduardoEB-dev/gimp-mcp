"""Patch the COPY of 3MF_Release_Workflow.md (after patch_release_doc.py): add the Little Yellow Bird release log rows.
usage: python -I patch_release_log.py "<copy of 3MF_Release_Workflow.md>"
Refuses files inside the workflow folder or with an unexpected sha256[:12]. Prints PATCHED <new sha256[:12]>."""
import hashlib, os, sys

EXPECT = "cedafca9cc78"
WF = os.path.normcase(os.path.realpath(r"G:\gimp-mcp\Projects\Workflow"))
p = os.path.realpath(sys.argv[1])
if os.path.normcase(p).startswith(WF + os.sep): sys.exit(f"ERROR: {p} is inside the workflow folder; patch a copy")
b = open(p, "rb").read()
h = hashlib.sha256(b).hexdigest()[:12]
if h != EXPECT: sys.exit(f"HASH MISMATCH {h} (expected {EXPECT})")
s = b.decode("utf8"); NL = "\r\n"
a = "| 1 ad render (hero: Grinch front_logo) |" + NL
if s.count(a) != 1: sys.exit(f"ERROR: anchor found {s.count(a)}x")
row = ("| 2026-11-28 | `NewCupProject\\Final\\Etsy Woodstock\\Little Yellow Bird Cooler Cup {p} - Etsy.3mf` "
       "(from `Woodstock Cooler Cup - Final - Painted_{s}_optimized.3mf`) | 6 ad renders from `Cup\\Ad Images\\Woodstock\\Drafts` (hero: hero_cup_logo) |")
s = s.replace(a, a + row.format(p="A1 mini", s="a1mini") + NL + row.format(p="X2D", s="x2d") + NL)
nb = s.encode("utf8"); open(p, "wb").write(nb)
print("PATCHED", hashlib.sha256(nb).hexdigest()[:12])
