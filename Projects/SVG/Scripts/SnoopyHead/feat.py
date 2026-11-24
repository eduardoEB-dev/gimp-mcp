import numpy as np
from scipy import ndimage as nd
def ngauss(A,ok,s):
    a=nd.gaussian_filter(np.where(ok,A,0),s); b=nd.gaussian_filter(ok.astype(float),s); return a/np.maximum(b,1e-9)
def normal_dev(N, px, sig_mm=3.0, iters=3, thr=4.0, Pz=None, ztop=189.9):
    if Pz is None: Pz=np.zeros(N.shape[:2])
    """angle (deg) between normal and smoothed normal field; smoothing excludes feature pixels"""
    ok=np.isfinite(N[...,0])&(np.nan_to_num(Pz,nan=0)<ztop); ok=nd.binary_erosion(ok,iterations=int(0.4/px)); Nf=np.where(ok[...,None],N,0); ex=np.zeros_like(ok)
    for _ in range(iters):
        S=np.stack([ngauss(Nf[...,k],ok&~ex,sig_mm/px) for k in range(3)],-1)
        S/=np.maximum(np.linalg.norm(S,axis=-1,keepdims=True),1e-9)
        ang=np.degrees(np.arccos(np.clip((Nf*S).sum(-1),-1,1))); ang[~ok]=0
        ex|=False
        ex=nd.binary_dilation(ang>thr,iterations=int(0.5/px))
    return ang
def feature_mask(N, px, Pz=None, thr=4.0, sig_mm=3.0, min_area_mm2=4.0, sel=None, hi=14.0, grow_mm=0.6):
    ang=normal_dev(N,px,sig_mm,thr=thr,Pz=Pz)
    A=nd.gaussian_filter(ang,0.1/px)
    M=(A>thr)&nd.binary_dilation(A>hi,iterations=int(grow_mm/px))
    M=nd.binary_closing(M,iterations=int(0.3/px))
    M=nd.binary_fill_holes(M)
    lab,nl=nd.label(M); ar=nd.sum(M,lab,range(1,nl+1))*px*px
    keep=[i+1 for i in range(nl) if ar[i]>=min_area_mm2 and (sel is None or sel(lab==i+1))]
    return np.isin(lab,keep),ang
