import numpy as np
from scipy.spatial import Delaunay, cKDTree
from matplotlib.path import Path
from matplotlib.tri import Triangulation, LinearTriInterpolator
from collections import Counter, defaultdict
H0=105.07
def load(fn):
    V=[];F=[]
    for l in open(fn):
        t=l.split()
        if t[0]=='V': V.append([float(x) for x in t[1:6]])
        elif t[0]=='F': F.append([int(x) for x in t[1:4]])
    return np.array(V),np.array(F)
V,F=load('mesh.txt'); V[:,2]-=H0
P,PF=load('pk_mesh.txt')
# pk boundary loop
E=Counter()
for a,b,c in PF:
    for e in ((a,b),(b,c),(c,a)): E[tuple(sorted(e))]+=1
adj=defaultdict(list)
for (a,b),n in E.items():
    if n==1: adj[a].append(b); adj[b].append(a)
start=next(iter(adj)); loop=[start]; prev=None
while True:
    nx=[q for q in adj[loop[-1]] if q!=prev][0]
    if nx==start: break
    prev=loop[-1]; loop.append(nx)
print('boundary loop',len(loop),'of',len(adj))
B=P[loop,:3]; poly=Path(B[:,:2])
# outer surface interpolator (original, before blending)
ot=Triangulation(V[:,0],V[:,1],F); oi=LinearTriInterpolator(ot,V[:,2])
dzb=B[:,2]-oi(B[:,0],B[:,1]).filled(0)
print('seam dz mean %.2f std %.2f'%(dzb.mean(),dzb.std()))
# distance of outer verts to pk boundary (densified)
seg=[];segdz=[]
for i in range(len(B)):
    a,b=B[i],B[(i+1)%len(B)]; da,db=dzb[i],dzb[(i+1)%len(B)]
    n=max(2,int(np.hypot(*(b[:2]-a[:2]))/0.5))
    for s in np.linspace(0,1,n,endpoint=False):
        seg.append(a[:2]+(b[:2]-a[:2])*s); segdz.append(da+(db-da)*s)
seg=np.array(seg); segdz=np.array(segdz); kd=cKDTree(seg)
d,j=kd.query(V[:,:2])
inside=poly.contains_points(V[:,:2])
keep=(~inside)&(d>3.0)
R=30.0
w=np.clip(1-d/R,0,1)**2
Vo=V[keep].copy(); Vo[:,2]+=(segdz[j]*w)[keep]
A=np.vstack([P,Vo])
tri=Delaunay(A[:,:2]).simplices
# drop degenerate / slivers? keep all; orient CCW (up normals)
p=A[:,:2]; u=p[tri[:,1]]-p[tri[:,0]]; v_=p[tri[:,2]]-p[tri[:,0]]; cr=u[:,0]*v_[:,1]-u[:,1]*v_[:,0]
tri=tri[np.abs(cr)>1e-9]; cr=cr[np.abs(cr)>1e-9]
tri[cr<0]=tri[cr<0][:,[0,2,1]]
with open('pk_merged_mesh.txt','w') as f:
    for v in A: f.write('V %.3f %.3f %.3f %.6f %.6f\n'%tuple(v))
    for t in tri: f.write('F %d %d %d\n'%tuple(t))
print('verts',len(A),'faces',len(tri),'pk',len(P),'outer kept',keep.sum(),'removed',(~keep).sum())
# quick preview hillshade
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig,ax=plt.subplots(1,2,figsize=(14,7))
for a_,lim in zip(ax,[(-300,450,-300,400),(-30,200,-20,130)]):
    a_.tripcolor(A[:,0],A[:,1],tri,A[:,2],shading='gouraud',cmap='terrain'); a_.triplot(A[:,0],A[:,1],tri,lw=0.15,color='k')
    a_.plot(*np.vstack([B[:,:2],B[:1,:2]]).T,'r-',lw=1); a_.set_xlim(lim[:2]); a_.set_ylim(lim[2:]); a_.set_aspect('equal')
plt.savefig('pk_merged_preview.png',dpi=90)
