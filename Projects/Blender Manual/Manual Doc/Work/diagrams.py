"""Pillow diagrams for the shortcut chapters: mouse, numpad, keyboard map. usage: python -I diagrams.py <jpg_dir>"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont

JPG = sys.argv[1]; sizes_f = os.path.join(JPG, "sizes.json"); sizes = json.load(open(sizes_f))
F = lambda s, b=False: ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if b else "C:/Windows/Fonts/segoeui.ttf", s)
INK, MUTED, ACC, LINE = (31, 41, 51), (91, 102, 112), (232, 125, 13), (201, 206, 212)
CAT = {"nav": ((108, 155, 210), "Navigation / view"), "tf": ((232, 125, 13), "Transform"), "edit": ((98, 181, 143), "Editing"),
       "ui": ((242, 181, 68), "Interface"), "vis": ((224, 108, 90), "Visibility / select")}

def save(im, name):
    im.save(os.path.join(JPG, name + ".jpg"), quality=88, optimize=True); sizes[name] = im.size

def key(d, x, y, w, h, label, fill=(246, 247, 249), fg=INK, sub=None, r=14):
    d.rounded_rectangle([x, y + 6, x + w, y + h + 6], r, fill=(200, 205, 212))
    d.rounded_rectangle([x, y, x + w, y + h], r, fill=fill, outline=(170, 176, 184), width=2)
    d.text((x + w / 2, y + h / 2 - (12 if sub else 0)), label, font=F(34 if len(label) < 4 else 26, True), fill=fg, anchor="mm")
    if sub: d.text((x + w / 2, y + h / 2 + 24), sub, font=F(20), fill=fg, anchor="mm")

# ---- mouse
im = Image.new("RGB", (1800, 760), "white"); d = ImageDraw.Draw(im)
mx, my = 160, 90
d.rounded_rectangle([mx, my, mx + 300, my + 520], 150, fill=(238, 240, 243), outline=(150, 156, 164), width=4)
d.line([mx + 150, my + 10, mx + 150, my + 230], fill=(150, 156, 164), width=4); d.line([mx + 10, my + 230, mx + 290, my + 230], fill=(150, 156, 164), width=4)
d.rounded_rectangle([mx + 128, my + 70, mx + 172, my + 170], 22, fill=ACC, outline=(160, 80, 0), width=3)
d.text((mx + 70, my + 140), "L", font=F(40, True), fill=MUTED, anchor="mm"); d.text((mx + 230, my + 140), "R", font=F(40, True), fill=MUTED, anchor="mm")
d.text((mx + 150, my + 610), "Middle button / wheel", font=F(30, True), fill=ACC, anchor="mm")
rows = [("Drag middle button", "Orbit around the model"), ("Shift + drag middle", "Pan (slide the view)"), ("Ctrl + drag middle", "Zoom (or roll the wheel)"),
        ("Left click", "Select"), ("Right click", "Context menu")]
y = 110
for k, v in rows:
    d.rounded_rectangle([600, y, 1100, y + 90], 16, fill=(253, 240, 228) if "middle" in k else (244, 245, 247), outline=LINE, width=2)
    d.text((620, y + 45), k, font=F(34, True), fill=INK, anchor="lm"); d.text((1130, y + 45), v, font=F(34), fill=INK, anchor="lm"); y += 115
save(im, "dia_mouse")

# ---- numpad
im = Image.new("RGB", (1800, 900), "white"); d = ImageDraw.Draw(im)
K = 150; ox, oy = 110, 60
pad = [["Num", "/", "*", "-"], ["7", "8", "9", "+"], ["4", "5", "6", ""], ["1", "2", "3", "Ent"], ["0", "", ".", ""]]
info = {"7": "Top", "1": "Front", "3": "Right", "0": "Camera", ".": "Frame sel.", "5": "Persp/Ortho", "8": "Orbit", "2": "Orbit", "4": "Orbit", "6": "Orbit"}
for r, row in enumerate(pad):
    for c, lab in enumerate(row):
        if lab == "" or (r == 4 and c == 1): continue
        w = K * 2 - 14 if (r == 4 and c == 0) else K - 14; h = K * 2 - 14 if lab in ("+", "Ent") else K - 14
        hot = lab in ("7", "1", "3", "0", ".")
        fill = ACC if hot else ((222, 234, 248) if lab in info else (246, 247, 249)); fg = "white" if hot else INK
        key(d, ox + c * K, oy + r * K, w, h, lab, fill, fg, info.get(lab))
notes = [("7", "Top view", "Ctrl 7 = bottom"), ("1", "Front view", "Ctrl 1 = back"), ("3", "Right view", "Ctrl 3 = left"),
         ("0", "Camera view", "look through the scene camera"), (".", "Frame selected", "zoom to what's selected"), ("5", "Perspective / Ortho", "toggle"),
         ("`", "View pie menu", "backtick: all views in one pie")]
y = 70
for k, a, b in notes:
    key(d, 780, y, 90, 90, k, ACC if k in "7130." else (222, 234, 248), "white" if k in "7130." else INK, r=12)
    d.text((900, y + 26), a, font=F(34, True), fill=INK, anchor="lm"); d.text((900, y + 66), b, font=F(26), fill=MUTED, anchor="lm"); y += 112
save(im, "dia_numpad")

# ---- keyboard map
KM = {"Tab": "edit", "1": "edit", "2": "edit", "3": "edit", "E": "edit", "I": "edit", "O": "edit", "B": "edit", "R": "tf", "G": "tf", "S": "tf",
      "X": "tf", "Y": "tf", "Z": "ui", "D": "tf", "H": "vis", "L": "vis", "N": "ui", "T": "ui", "Q": "ui", "F3": "ui", "F9": "tf", "`": "nav", "P": "edit",
      "M": "edit", "A": "vis", "J": "edit", "K": "edit", "F": "edit", "C": "vis", "V": "edit", "W": "vis"}
LAB = {"Tab": "Edit mode", "1": "Vert", "2": "Edge", "3": "Face", "E": "Extrude", "I": "Inset", "O": "Prop.", "R": "Rotate", "G": "Grab", "S": "Scale",
       "X": "Axis", "Y": "Axis", "Z": "Shading", "D": "Dup*", "H": "Hide", "L": "Linked", "N": "Sidebar", "T": "Toolbar", "Q": "Favorites", "F3": "Search",
       "F9": "Redo", "`": "Views", "P": "Separate", "M": "Merge", "A": "All", "J": "Connect", "K": "Knife", "F": "Fill", "C": "Circle", "V": "Rip", "W": "Sel tool", "B": "Box"}
rows = [["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "F3", "F9"], ["Tab", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["Caps", "A", "S", "D", "F", "G", "H", "J", "K", "L"], ["Shift", "Z", "X", "C", "V", "B", "N", "M"], ["Ctrl", "Alt", "Space"]]
off = [0, 0.5, 0.75, 1.25, 0]; K = 128
im = Image.new("RGB", (int(K * 14.2) + 80, 5 * K + 200), "white"); d = ImageDraw.Draw(im)
for r, row in enumerate(rows):
    x = 40 + off[r] * K
    for lab in row:
        w = {"Tab": 1.5, "Caps": 1.75, "Shift": 2.25, "Ctrl": 1.5, "Alt": 1.5, "Space": 6}.get(lab, 1) * K - 12
        if lab in ("Tab",) and r == 1: x -= 0.5 * K
        if lab == "Caps": x -= 0.75 * K
        if lab == "Shift": x -= 1.25 * K
        cat = KM.get(lab); fill = CAT[cat][0] if cat else (246, 247, 249); fg = "white" if cat in ("tf", "nav", "edit", "vis") else INK
        if lab in ("Shift", "Ctrl", "Alt"): fill, fg = (90, 98, 108), "white"
        d.rounded_rectangle([x, 30 + r * K + 6, x + w, 30 + r * K + K - 12 + 6], 12, fill=(200, 205, 212))
        d.rounded_rectangle([x, 30 + r * K, x + w, 30 + r * K + K - 12], 12, fill=fill, outline=(150, 156, 164), width=2)
        d.text((x + w / 2, 30 + r * K + 40), lab, font=F(34 if len(lab) < 3 else 26, True), fill=fg, anchor="mm")
        if lab in LAB: d.text((x + w / 2, 30 + r * K + 82), LAB[lab], font=F(19), fill=fg, anchor="mm")
        x += w + 12
x = 40; y = 30 + 5 * K + 30
for c, (col, name) in CAT.items():
    d.rounded_rectangle([x, y, x + 40, y + 40], 8, fill=col); d.text((x + 52, y + 20), name, font=F(30), fill=INK, anchor="lm"); x += 52 + d.textlength(name, font=F(30)) + 50
d.text((x, y + 20), "*Shift D / Alt D", font=F(26), fill=MUTED, anchor="lm")
save(im, "dia_keyboard")
json.dump(sizes, open(sizes_f, "w"), indent=1); print("ok")
