# ortho raycast: args stl out res dx dy dz  (view dir), up = +Z
import bpy, numpy as np, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a=sys.argv[sys.argv.index('--')+1:]
stl,out,res=a[0],a[1],float(a[2]); d=np.array(list(map(float,a[3:6]))); d/=np.linalg.norm(d)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=stl)
me=bpy.context.selected_objects[0].data
V=np.array([v.co[:] for v in me.vertices])
bvh=BVHTree.FromPolygons([Vector(v) for v in V],[tuple(p.vertices) for p in me.polygons])
up=np.array([0,0,1.]); u=np.cross(up,d); u/=np.linalg.norm(u); w=np.cross(d,u)  # u right, w up
pu,pw,pd=V@u,V@w,V@d
if len(a)>6:
    c=np.array(list(map(float,a[6:9]))); hs=float(a[9]); cu,cw=c@u,c@w
    us=np.arange(cu-hs,cu+hs,res); ws=np.arange(cw-hs,cw+hs,res)
else:
    us=np.arange(pu.min()-1,pu.max()+1,res); ws=np.arange(pw.min()-1,pw.max()+1,res)
D=np.full((len(ws),len(us)),np.nan); N=np.full((len(ws),len(us),3),np.nan); P=np.full((len(ws),len(us),3),np.nan)
dv=Vector(d); o0=-(abs(pd).max()+50)
for i,ww in enumerate(ws):
    for j,uu in enumerate(us):
        h=bvh.ray_cast(Vector(u*uu+w*ww+d*o0),dv)
        if h[0] is not None: P[i,j]=h[0][:]; N[i,j]=h[1][:]; D[i,j]=h[3]
np.savez(out,D=D,N=N,P=P,us=us,ws=ws,u=u,w=w,d=d)
print("done")
