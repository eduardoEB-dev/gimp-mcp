import re, sys
base=r"G:/gimp-mcp/Projects/Capibara/Drafts/"
for name in ["Capibara_Brown.svg","Capibara_Brown2.svg"]:
    svg=open(base+name,encoding='utf-8').read()
    paths=re.findall(r'd="([^"]+)"', svg)
    areas=[]
    for p in paths:
        toks=p.split(); cmds=[]; i=0; cur=[0,0]
        while i<len(toks):
            c=toks[i]
            if c in ("M","m"):
                x=float(toks[i+1]);y=float(toks[i+2]); cur=[x,y]; cmds.append(cur); i+=3
            elif c in ("C","c"):
                x1=float(toks[i+1]);y1=float(toks[i+2]);x2=float(toks[i+3]);y2=float(toks[i+4]);xe=float(toks[i+5]);ye=float(toks[i+6])
                for tt in (0.25,0.5,0.75,1.0):
                    a=(1-tt)**3; b=3*(1-tt)**2*tt; d=3*(1-tt)*tt**2; e=tt**3
                    cmds.append([a*cur[0]+b*x1+d*x2+e*xe, a*cur[1]+b*y1+d*y2+e*ye])
                cur=[xe,ye]; i+=7
            else:
                i+=1
        A=0
        for k in range(len(cmds)):
            x0,y0=cmds[k];x1,y1=cmds[(k+1)%len(cmds)]
            A+=x0*y1-x1*y0
        areas.append(abs(A)/2)
    print(name,'n_paths',len(paths),'n_small(<21000u2)',sum(1 for a in areas if a<21000),'total',sum(areas))
    print('  areas desc:',[round(a) for a in sorted(areas,reverse=True)[:30]])
