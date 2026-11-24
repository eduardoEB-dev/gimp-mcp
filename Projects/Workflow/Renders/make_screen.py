"""Dark-theme code editor screenshot (generic, no app branding) for the desk theme's monitor.
Two editor panes of real, syntax-colored Python next to a file tree.

usage: python -I make_screen.py <a.py[,b.py]> <out.png> [width height]   (one file per pane; one file = split in halves)
"""
import sys, os, io, tokenize, keyword
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
W, H = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (3440, 1440)
FONT = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 22)
BG, SIDE, TABS, GUTTER = "#1e1e1e", "#252526", "#2d2d2d", "#858585"
COL = {"kw": "#569cd6", "str": "#ce9178", "com": "#6a9955", "num": "#b5cea8", "name": "#9cdcfe", "call": "#dcdcaa", "op": "#d4d4d4"}
SRCS = src.split(",")
FILES = [open(s, encoding="utf8").read().splitlines() for s in SRCS]

def spans(line):  # (col, text, color) per token; falls back to plain text on tokenizer errors
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(line + "\n").readline))
    except Exception:
        return [(0, line, COL["op"])]
    out = []
    for k, t in enumerate(toks):
        if t.type in (tokenize.NEWLINE, tokenize.NL, tokenize.ENDMARKER, tokenize.INDENT, tokenize.DEDENT): continue
        c = (COL["com"] if t.type == tokenize.COMMENT else COL["str"] if t.type == tokenize.STRING else COL["num"] if t.type == tokenize.NUMBER
             else COL["kw"] if t.type == tokenize.NAME and keyword.iskeyword(t.string)
             else COL["call"] if t.type == tokenize.NAME and k + 1 < len(toks) and toks[k + 1].string == "("
             else COL["name"] if t.type == tokenize.NAME else COL["op"])
        out.append((t.start[1], t.string, c))
    return out

im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
side_w, tab_h, lh, cw = 300, 44, 30, FONT.getlength("m")
d.rectangle((0, 0, side_w, H), fill=SIDE)
proj = os.path.dirname(os.path.abspath(SRCS[0]))  # file tree = the shown files' folder
tree = ["PROJECTS", "  " + os.path.basename(os.path.dirname(proj)), "    " + os.path.basename(proj)]
tree += ["      " + n for n in sorted(os.listdir(proj)) if n.endswith(".py")][:30]
sel = next((i for i, n in enumerate(tree) if n.strip() == os.path.basename(SRCS[0])), 0)
d.rectangle((0, 20 + sel * lh - 4, side_w, 20 + (sel + 1) * lh - 4), fill="#37373d")  # selected file
for i, n in enumerate(tree):
    d.text((16, 20 + i * lh), n, font=FONT, fill="#cccccc" if i else "#bbbbbb")
panes = [(side_w, (W + side_w) // 2), ((W + side_w) // 2, W)]
for p, (x0, x1) in enumerate(panes):
    d.rectangle((x0, 0, x1, tab_h), fill=TABS); d.rectangle((x0, 0, x0 + 220, tab_h), fill=BG)
    code = FILES[p % len(FILES)]
    d.text((x0 + 20, 10), os.path.basename(SRCS[p % len(SRCS)]), font=FONT, fill="#ffffff")
    d.line((x0, 0, x0, H), fill="#444444", width=2)
    start = len(code) // 2 if (p == 1 and len(FILES) == 1) else 0
    for r in range((H - tab_h - 20) // lh):
        n = start + r
        if n >= len(code): break
        y = tab_h + 10 + r * lh
        d.text((x0 + 60 - FONT.getlength(str(n + 1)), y), str(n + 1), font=FONT, fill=GUTTER)
        for col, txt, c in spans(code[n]):
            x = x0 + 90 + col * cw
            if x < x1 - 10: d.text((x, y), txt, font=FONT, fill=c)
im.save(out); print("SCREEN", out)
