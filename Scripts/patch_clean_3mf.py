"""Patch the COPY of clean_3mf.py: refuse to write over an existing file (or the source).
usage: python -I patch_clean_3mf.py "<copy of clean_3mf.py>"
Refuses files inside the workflow folder or with an unexpected sha256[:12]. Prints PATCHED <new sha256[:12]>."""
import hashlib, os, sys

EXPECT = "5c4ec021a678"
WF = os.path.normcase(os.path.realpath(r"G:\gimp-mcp\Projects\Workflow"))
p = os.path.realpath(sys.argv[1])
if os.path.normcase(p).startswith(WF + os.sep): sys.exit(f"ERROR: {p} is inside the workflow folder; patch a copy")
b = open(p, "rb").read()
h = hashlib.sha256(b).hexdigest()[:12]
if h != EXPECT: sys.exit(f"HASH MISMATCH {h} (expected {EXPECT})")
s = b.decode("utf8")
NL = "\r\n" if "\r\n" in s else "\n"
a = 'if not imgs: sys.exit("need at least one render")'
if s.count(a) != 1: sys.exit(f"ERROR: anchor found {s.count(a)}x")
s = s.replace(a, a + NL + 'import os' + NL +
              'if os.path.exists(dst): sys.exit(f"REFUSED: {dst} exists; never overwrite (pick a new name)")')
nb = s.encode("utf8"); open(p, "wb").write(nb)
print("PATCHED", hashlib.sha256(nb).hexdigest()[:12])
