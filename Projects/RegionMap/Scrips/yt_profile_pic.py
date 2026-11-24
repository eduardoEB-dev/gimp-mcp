"""Build YouTube profile pic (800x800) from logo mark in banner source.
usage: python yt_profile_pic.py <banner_src.png> <out.png>"""
import sys
import numpy as np
from PIL import Image, ImageFilter
src, out = sys.argv[1:3]
N = 800
LOGO = (598, 178, 920, 392)  # logo mark box in banner source px
im = Image.open(src).convert("RGB").crop(LOGO)
a = np.asarray(im, np.float32)
bg = np.median(np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3)]), axis=0)
# alpha from distance to dark backdrop
alpha = np.clip((np.abs(a - bg).max(axis=2) - 12) / 60, 0, 1)
# un-premultiply against backdrop so edges keep logo color
fg = np.clip(bg + (a - bg) / np.maximum(alpha, 0.05)[..., None], 0, 255)
logo = Image.fromarray(np.dstack([fg, alpha*255]).astype(np.uint8), "RGBA")
# scale logo to ~66% of canvas width
target_w = int(N * 0.66)
scale = target_w / logo.width
logo = logo.resize((target_w, round(logo.height*scale)), Image.LANCZOS)
logo = logo.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
# background: navy radial gradient + soft blue/purple glow
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
r = np.hypot(xx - N/2, yy - N/2) / (N/2)
inner, outer = np.array([20, 32, 62], np.float32), np.array([6, 10, 22], np.float32)
t = np.clip(r, 0, 1)[..., None]
bgimg = inner*(1-t) + outer*t
glow_l = np.exp(-(((xx-N*0.35)/(N*0.28))**2 + ((yy-N*0.5)/(N*0.28))**2))[..., None]
glow_r = np.exp(-(((xx-N*0.65)/(N*0.28))**2 + ((yy-N*0.5)/(N*0.28))**2))[..., None]
bgimg += glow_l*np.array([0, 70, 120]) * 0.35 + glow_r*np.array([90, 20, 140]) * 0.35
canvas = Image.fromarray(np.clip(bgimg, 0, 255).astype(np.uint8)).convert("RGBA")
# logo glow
glow = Image.new("RGBA", (N, N), (0, 0, 0, 0))
pos = ((N - logo.width)//2, (N - logo.height)//2)
glow.paste(logo, pos, logo)
glow = glow.filter(ImageFilter.GaussianBlur(28))
ga = np.asarray(glow).copy(); ga[..., 3] = (ga[..., 3] * 0.55).astype(np.uint8)
canvas = Image.alpha_composite(canvas, Image.fromarray(ga))
canvas.alpha_composite(logo, pos)
canvas.convert("RGB").save(out, optimize=True)
# circle preview
prev = canvas.convert("RGB").copy()
m = Image.new("L", (N, N), 0)
from PIL import ImageDraw
ImageDraw.Draw(m).ellipse([0, 0, N-1, N-1], fill=255)
pv = Image.new("RGB", (N, N), (33, 33, 33)); pv.paste(prev, (0, 0), m)
pv.save(out.rsplit(".", 1)[0] + "_circle_preview.png")
