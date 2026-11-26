import zipfile, re, numpy as np, sys
z=zipfile.ZipFile(r"G:\Blender\blender-mcp\Projects\NewCupProject\SnoopyCup\STL\SnoopyCupProject.3mf")
CODE={'4':1,'8':2,'0C':3,'1C':4,'2C':5}
out=sys.argv[1]
for oid in (36,39,37,27,12,10):
    t=z.read(f'3D/Objects/object_{oid}.model').decode()
    v=np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"',t),float)
    tri=re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"(?: paint_color="([0-9A-F]+)")?',t)
    f=np.array([[int(a),int(b),int(c)] for a,b,c,_ in tri]); p=np.array([CODE.get(x,0) for *_,x in tri],np.int8)
    np.savez(f"{out}/obj{oid}.npz",v=v,f=f,p=p)
    print(oid, len(v), len(f), np.round(v.min(0),2), np.round(v.max(0),2), np.bincount(p))
