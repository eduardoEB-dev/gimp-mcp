import numpy as np, sys
def load(p):
    d=open(p,'rb').read()
    n=np.frombuffer(d[80:84],np.uint32)[0]
    a=np.frombuffer(d[84:84+n*50],dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]))
    return a['v'].astype(np.float64)
if __name__=='__main__':
    v=load(sys.argv[1]); print(v.shape, v.reshape(-1,3).min(0), v.reshape(-1,3).max(0))
