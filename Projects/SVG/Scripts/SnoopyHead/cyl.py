# cylindrical raycast around axis || Y through (0, *, ZC): args stl out ds y0 y1 th0 th1(deg) zc rref
import bpy, numpy as np, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
a=sys.argv[sys.argv.index('--')+1:]
stl,out=a[0],a[1]; ds,y0,y1,t0,t1,zc,rr=map(float,a[2:9])
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.wm.stl_import(filepath=stl)
me=bpy.context.selected_objects[0].data
bvh=BVHTree.FromPolygons([v.co.copy() for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
ys=np.arange(y0,y1,ds); th=np.radians(np.arange(t0,t1,np.degrees(ds/rr)))
P=np.full((len(ys),len(th),3),np.nan); N=P.copy()
for j,t in enumerate(th):
    r=Vector((np.sin(t),0,-np.cos(t)))
    for i,y in enumerate(ys):
        h=bvh.ray_cast(Vector((0,y,zc))+r*150,-r)
        if h[0] is not None: P[i,j]=h[0][:]; N[i,j]=h[1][:]
np.savez(out,P=P,N=N,ys=ys,th=th)
print("done")
