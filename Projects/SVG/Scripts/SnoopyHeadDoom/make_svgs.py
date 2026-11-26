# Doom Snoopy eyes + brows -> SVG outlines (mm) traced from hero jpg.
# Near side (viewer's left, Eye_L/Brow_L) traced; far side is foreshortened -> mirrored instead (Eye_R/Brow_R).
import numpy as np, os, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from PIL import Image
from scipy import ndimage as nd
SRC=r"G:\Blender\blender-mcp\Projects\SnoopyDrDoom\Images\Snoopy Dr Doom.jpg"
OUT=r"G:\gimp-mcp\Projects\SVG\SnoopyHeadDoomSVGs"
X0,Y0,X1,Y1=495,125,580,185      # crop: near eye + brow (orig px)
UP=8                              # upsample
MMPX=float(sys.argv[1]) if len(sys.argv)>1 else 0.30   # mm per orig px (head ~half candle scale)
CX=583                            # face centreline (crease between eyes, orig px) -> mirror axis
THR=110; GAP=0.6                  # dark threshold; min gap brow<->eye (mm)

im=Image.open(SRC).convert('L').crop((X0,Y0,X1,Y1))
g=np.asarray(im.resize((im.width*UP,im.height*UP),Image.BICUBIC)).astype(float)
g=nd.gaussian_filter(g,UP*0.4)
M=nd.binary_fill_holes(g<THR)
lab,n=nd.label(M); M=lab==1+int(np.argmax(nd.sum(M,lab,range(1,n+1))))   # biggest blob = eye+brow
# split brow / eye: per column, brow = top dark run, capped at median brow thickness where eye merges below
top=np.argmax(M,0); has=M.any(0)
run=np.array([np.argmin(M[t:,j]) if has[j] else 0 for j,t in enumerate(top)])
T=int(np.median(run[has&(run<1.6*np.median(run[has]))]))+UP
B=np.zeros_like(M)
for j in np.nonzero(has)[0]: B[top[j]:top[j]+min(run[j],T),j]=True
W=np.where(B,1,np.where(M,2,0))
gp=int(round(GAP/MMPX*UP/2))
parts={}
for nm,k in (("Brow",1),("Eye",2)):
    r=W==k
    other=nd.binary_dilation(W==3-k,iterations=gp)
    r=nd.binary_opening(r&~other,iterations=2)
    lab,n=nd.label(r); r=lab==1+int(np.argmax(nd.sum(r,lab,range(1,n+1))))
    parts[nm]=r

def contour(m):
    cs=plt.contour(nd.gaussian_filter(m.astype(float),2),[0.5]); plt.close('all')
    p=max(cs.allsegs[0],key=len)
    return nd.gaussian_filter1d(p,3,axis=0,mode='wrap')

def rdp(p, eps):
    if len(p)<3: return p
    a,b=p[0],p[-1]; ab=b-a; L=np.linalg.norm(ab)
    d=np.abs(np.cross(ab,p-a))/L if L>1e-12 else np.linalg.norm(p-a,axis=1)
    i=int(np.argmax(d))
    if d[i]>eps: return np.vstack([rdp(p[:i+1],eps)[:-1],rdp(p[i:],eps)])
    return np.vstack([a,b])

def write_svg(fn, polys, title, margin=2.0):
    allp=np.vstack(polys); lo=allp.min(0)-margin; hi=allp.max(0)+margin; w,h=hi-lo
    d=""
    for p in polys:
        q=rdp(np.vstack([p,p[:1]]),0.01)-lo
        d+="M"+" L".join(f"{x:.3f},{y:.3f}" for x,y in q[:-1])+" Z "
    s=(f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" height="{h:.3f}mm" '
       f'viewBox="0 0 {w:.3f} {h:.3f}">\n<title>{title}</title>\n<path d="{d.strip()}" fill="#000000" fill-rule="nonzero" stroke="none"/>\n</svg>\n')
    open(os.path.join(OUT,fn),'w').write(s); return w,h

# px (col,row upsampled) -> mm, x relative to face centreline, svg y down
res={}
for nm,m in parts.items():
    p=contour(m); mm=np.c_[(p[:,0]/UP+X0-CX)*MMPX,(p[:,1]/UP+Y0)*MMPX]
    res[nm+"_L"]=mm
    res[nm+"_R"]=np.c_[-mm[:,0],mm[:,1]][::-1]
for nm,p in res.items():
    w,h=write_svg(nm+".svg",[p],f"Doom Snoopy {nm} - outline mm")
    print(nm,f"{w-4:.1f} x {h-4:.1f} mm")
w,h=write_svg("Head_All.svg",list(res.values()),"Doom Snoopy eyes + brows - placed as on face, mm")
print("Head_All",f"{w-4:.1f} x {h-4:.1f} mm")
# QA
fig,ax=plt.subplots(1,2,figsize=(14,5))
ax[0].imshow(g,cmap='gray');
for nm,m in parts.items(): ax[0].contour(m,[0.5],colors='r',linewidths=.8)
for p in res.values(): ax[1].fill(p[:,0],-p[:,1],'k')
ax[1].set_aspect('equal'); plt.tight_layout(); plt.savefig(os.path.join(os.path.dirname(__file__),'qa.png'),dpi=60)
