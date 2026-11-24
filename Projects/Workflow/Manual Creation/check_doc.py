"""Check a built manual: opens it in Word, exports PDF, makes a page contact sheet, and reports size, near-empty pages and any
number in the source notes that didn't reach the document (a dropped cut length means a buyer's print goes wrong).

usage: .venv\\Scripts\\python -I check_doc.py <manual.docx> <renders_dir> [--source notes.txt]
"""
import sys, os, re, html, zipfile, subprocess
import pymupdf
from PIL import Image

args = sys.argv[1:]; source = None
if "--source" in args: i = args.index("--source"); source = args[i + 1]; del args[i:i + 2]
docx, rend = os.path.abspath(args[0]), os.path.abspath(args[1])
pdf = os.path.join(rend, "check.pdf")

# Word, not LibreOffice: this is what the buyer opens, and it decides the page breaks
ps = "$w=New-Object -ComObject Word.Application;$w.Visible=$false;try{$d=$w.Documents.Open($env:DOCX,$false,$true);$d.SaveAs2($env:PDF,17);$d.Close($false)}finally{$w.Quit()}"
subprocess.run(["pwsh", "-NoProfile", "-Command", ps], check=True, env={**os.environ, "DOCX": docx, "PDF": pdf})  # pwsh: Windows PowerShell 5 can't load Word's type library here

mb = os.path.getsize(docx) / 1e6
d = pymupdf.open(pdf); ims, sparse = [], []
for n, p in enumerate(d, 1):
    x = p.get_pixmap(dpi=40); im = Image.frombytes("RGB", (x.width, x.height), x.samples); ims.append(im)
    ink = sum(1 for v in im.convert("L").tobytes() if v < 235) / (x.width * x.height)
    if ink < 0.05: sparse.append(f"{n} ({ink:.0%})")  # a full text page is about 11%, a stray heading or caption under 3%
w, h = ims[0].size; c = 5; S = Image.new("RGB", (c * w, ((len(ims) + c - 1) // c) * h), "grey")
for i, im in enumerate(ims): S.paste(im, ((i % c) * w, (i // c) * h))
sheet = os.path.join(rend, "pages.png"); S.save(sheet)
print(f"PAGES {len(ims)} | {mb:.1f} MB" + ("  WARNING: over Etsy's 20 MB limit" if mb > 20 else ""))
print("SHEET", sheet)
print("near-empty pages (orphans?):", ", ".join(sparse) or "none")

if source:
    xml = zipfile.ZipFile(docx).read("word/document.xml").decode("utf-8")
    text = html.unescape(re.sub(r"<[^>]+>", " ", xml))
    num = r"(?<![\d.])\d+(?:\.\d+)?(?![\d])"
    have = set(re.findall(num, text))
    miss = sorted({n for n in re.findall(num, open(source, encoding="utf-8", errors="replace").read()) if n not in have}, key=float)
    print("numbers in the notes but not in the document:", ", ".join(miss) or "none")
