# Head eyes + smile -> true-size SVG outlines at feature base (mm). Grids from ray2.py (eyes) / cyl.py (smile).
import numpy as np, os, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy import ndimage as nd
from feat import feature_mask
OUT=r"D:\gimp-mcp\Projects\SVG\SnoopyHeadSVGs"; PX=0.05

def chart(P, right, up):
    """arc-length chart of a ray grid: X along columns, Y along rows, signed by right/up, 0 at grid centre"""
    ci,cj=P.shape[0]//2,P.shape[1]//2
    dc=np.linalg.norm(np.diff(P,axis=1),axis=-1); dr=np.linalg.norm(np.diff(P,axis=0),axis=-1)
    X=np.concatenate([np.zeros((P.shape[0],1)),np.cumsum(dc,1)],1); X-=X[:,[cj]]
    Y=np.concatenate([np.zeros((1,P.shape[1])),np.cumsum(dr,0)],0); Y-=Y[[ci],:]
    if (P[ci,-1]-P[ci,0])@right<0: X=-X
    if (P[-1,cj]-P[0,cj])@up<0: Y=-Y
    return X,Y

def contours(M):
    cs=plt.contour(nd.gaussian_filter(M.astype(float),1.5),[0.5]); plt.close('all')
    return [p for p in cs.allsegs[0] if len(p)>20]

def smooth_closed(p, s=3):
    return nd.gaussian_filter1d(p,s,axis=0,mode='wrap')

def rdp(p, eps):
    if len(p)<3: return p
    a,b=p[0],p[-1]; ab=b-a; L=np.linalg.norm(ab)
    d=np.abs(np.cross(ab,p-a))/L if L>1e-12 else np.linalg.norm(p-a,axis=1)
    i=int(np.argmax(d))
    if d[i]>eps: return np.vstack([rdp(p[:i+1],eps)[:-1],rdp(p[i:],eps)])
    return np.vstack([a,b])

def to_mm(seg, X, Y):
    rc=np.c_[seg[:,1],seg[:,0]].T   # contour gives (col,row)
    return np.c_[nd.map_coordinates(X,rc,order=1), -nd.map_coordinates(Y,rc,order=1)]   # svg y down

def write_svg(fn, polys, title, margin=2.0):
    allp=np.vstack(polys); lo=allp.min(0)-margin; hi=allp.max(0)+margin; w,h=hi-lo
    d=""
    for p in polys:
        q=rdp(np.vstack([p,p[:1]]),0.01)-lo
        d+="M"+" L".join(f"{x:.3f},{y:.3f}" for x,y in q[:-1])+" Z "
    s=(f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" height="{h:.3f}mm" '
       f'viewBox="0 0 {w:.3f} {h:.3f}">\n<title>{title}</title>\n<path d="{d.strip()}" fill="#000000" fill-rule="nonzero" stroke="none"/>\n</svg>\n')
    open(os.path.join(OUT,fn),'w').write(s); return w,h

res={}
# eyes: grid viewed along eye normal (outside -> in)
for nm,fn in (("Eye_R","z_eR.npz"),("Eye_L","z_eL.npz")):
    f=np.load(fn); P,N,d=f['P'],f['N'],f['d']
    up=np.array([0,0,1.]); right=np.cross(d,up); right/=np.linalg.norm(right); up=np.cross(right,d)
    c=np.array(N.shape[:2])//2
    M,_=feature_mask(N,PX,Pz=P[...,2],thr=5,sel=lambda m: m[c[0]-40:c[0]+40,c[1]-40:c[1]+40].any())
    X,Y=chart(np.nan_to_num(P),right,up)
    res[nm]=(M,[smooth_closed(to_mm(s,X,Y)) for s in contours(M)],P,N,d)
# smile: cylindrical grid around Y axis; outside view, up = +Y (toward neck/ears), right = -X (non-mirrored)
f=np.load('cyl.npz'); P,N=f['P'],f['N']
M,_=feature_mask(N,PX,thr=5)
lab,nl=nd.label(M); ext=[np.ptp(np.nonzero(lab==i)[1]) for i in range(1,nl+1)]; M=lab==1+int(np.argmax(ext))
X,Y=chart(P,np.array([-1.,0,0]),np.array([0,1.,0]))
res["Smile"]=(M,[smooth_closed(to_mm(s,X,Y)) for s in contours(M)],P,N,None)

for nm,(M,polys,*_) in res.items():
    w,h=write_svg(nm+".svg",polys,f"Snoopy head {nm} - base outline, true size mm")
    print(nm,len(polys),[len(p) for p in polys],f"{w-4:.1f} x {h-4:.1f} mm")
# combined sheet, spaced 8 mm
x=0; allp=[]
for nm in ("Eye_L","Smile","Eye_R"):   # front-view order (R = +X, same as EarR)
    ps=res[nm][1]; a=np.vstack(ps); off=np.array([x-a[:,0].min(), -a[:,1].min()])
    allp+= [p+off for p in ps]; x+=np.ptp(a[:,0])+8
write_svg("Head_All.svg",allp,"Snoopy head eyes + smile - base outlines, true size mm")
np.save('polys.npy',np.array({k:v[1] for k,v in res.items()},dtype=object),allow_pickle=True)
# QA overlays
fig,ax=plt.subplots(1,3,figsize=(30,8),gridspec_kw={'width_ratios':[1,1,3]})
for a,nm in zip(ax,("Eye_R","Eye_L","Smile")):
    M,polys,P,N,d=res[nm]; L=np.array([0.3,-0.6,0.5]) if d is not None else np.array([0.3,-0.6,-0.7]); L/=np.linalg.norm(L)
    a.imshow(np.abs(N@L),origin='lower',cmap='gray',aspect='auto'); a.contour(M,[0.5],colors='r',linewidths=.7); a.set_title(nm)
plt.tight_layout(); plt.savefig('qa.png',dpi=45)
