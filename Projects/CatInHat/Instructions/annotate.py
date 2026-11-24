"""Draw labels (leader + dot) and motion arrows on renders using the <shot>.json pixel anchors from render_steps.py.
usage: python -I annotate.py <render_dir> <out_dir>"""
import sys, os, json, glob, math
from PIL import Image, ImageDraw, ImageFont
src, dst = sys.argv[1], sys.argv[2]; os.makedirs(dst, exist_ok=True)
INK, ACC, BOX = (24, 33, 45), (28, 126, 214), (255, 255, 255)
for f in sorted(glob.glob(os.path.join(src, "*.png"))):
    im = Image.open(f).convert("RGB"); W = im.width; k = W / 1000
    ann = json.load(open(os.path.splitext(f)[0] + ".json"))
    d = ImageDraw.Draw(im, "RGBA"); font = ImageFont.truetype(r"C:\Windows\Fonts\seguisb.ttf", int(30 * k))
    for r in ann["arrows"]:
        (ax, ay), (bx, by) = r["a_px"], r["b_px"]
        if math.hypot(bx - ax, by - ay) < 10 * k: continue
        ang = math.atan2(by - ay, bx - ax); hl = 26 * k
        ex, ey = bx - hl * 0.8 * math.cos(ang), by - hl * 0.8 * math.sin(ang)
        d.line([(ax, ay), (ex, ey)], fill=ACC, width=int(9 * k))
        d.polygon([(bx, by), (bx - hl * math.cos(ang - 0.45), by - hl * math.sin(ang - 0.45)),
                   (bx - hl * math.cos(ang + 0.45), by - hl * math.sin(ang + 0.45))], fill=ACC)
    for l in ann["labels"]:
        x, y = l["px"]; tx, ty = x + l.get("dx", 0.2) * W, y + l.get("dy", 0) * W
        bb = d.textbbox((0, 0), l["text"], font=font); tw, th = bb[2] - bb[0], bb[3] - bb[1]; p = 12 * k
        bx0 = min(max(tx - tw / 2 - p, 8 * k), W - tw - 2 * p - 8 * k); by0 = min(max(ty - th / 2 - p, 8 * k), W - th - 2 * p - 8 * k)
        box = (bx0, by0, bx0 + tw + 2 * p, by0 + th + 2 * p)
        cx = min(max(x, box[0]), box[2]); cy = min(max(y, box[1]), box[3])  # leader to nearest box edge point
        d.line([(x, y), (cx, cy)], fill=INK, width=int(4 * k))
        rr = 9 * k; d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=ACC, outline=BOX, width=int(3 * k))
        d.rounded_rectangle(box, radius=10 * k, fill=(*BOX, 235), outline=INK, width=int(3 * k))
        d.text((box[0] + p - bb[0], box[1] + p - bb[1]), l["text"], font=font, fill=INK)
    im.save(os.path.join(dst, os.path.basename(f)), quality=92); print("ANN", os.path.basename(f))
