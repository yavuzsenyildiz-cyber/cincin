import re, numpy as np
from shapely.geometry import Polygon
from matplotlib.tri import Triangulation, LinearTriInterpolator
H0=105.07
V=[];F=[]
for l in open('pk_merged_mesh.txt'):
    t=l.split()
    if t[0]=='V': V.append([float(x) for x in t[1:4]])
    elif t[0]=='F': F.append([int(x) for x in t[1:4]])
V=np.array(V); it=LinearTriInterpolator(Triangulation(V[:,0],V[:,1],F),V[:,2])
z=lambda p: np.asarray(it(p[:,0],p[:,1]).filled(np.nan))
B=[]
for l in open('bina_iz.txt'):
    h=l.split(' | ')[0].split(' ',3); B.append((h[1],Polygon([tuple(map(float,q.split(','))) for q in h[3].split(';')])))
G=[]
for l in open('faces.txt',encoding='utf-8'):
    if 'Grass Dark Green' not in l or not l.startswith('F '): continue
    m=re.match(r"F (\S+) (?:\[(.*?)\]|(\S+)) (.*)", l.strip())
    P=np.array([[float(v) for v in p.split(',')] for p in m.group(4).split()])
    # remove consecutive duplicates
    keep=[0]+[i for i in range(1,len(P)) if np.hypot(*(P[i,:2]-P[keep[-1] if False else i-1,:2]))>1e-3]
    P=P[keep]; G.append(P[:,:2])
out=open('bahce.txt','w'); tot=0; ov=0
for k,P in enumerate(G,1):
    pg=Polygon(P).buffer(0); tot+=pg.area
    d=[(pg.distance(b),n) for n,b in B]; dd,near=min(d)
    ov+=sum(pg.intersection(b).area for n,b in B)
    zc=z(P)
    dr=[]
    for i in range(len(P)):
        a,b=P[i],P[(i+1)%len(P)]; n=max(2,int(np.hypot(*(b-a))/0.5))
        s=np.linspace(0,1,n,endpoint=False)[:,None]; dr.append(a+(b-a)*s)
    dr=np.vstack(dr); dz=z(dr)
    name='BAHCE-%02d (%s)'%(k,near)
    out.write('G %s|%.3f|%s|%s\n'%(name,np.nanmean(dz),';'.join('%.3f,%.3f'%tuple(q) for q in P),';'.join('%.3f,%.3f,%.3f'%(q[0],q[1],w) for q,w in zip(dr,dz))))
    print(name,'alan %.0f m2, en yakin bina %.1f m, kot %.2f-%.2f'%(pg.area,dd,np.nanmin(dz)+H0,np.nanmax(dz)+H0))
print('toplam bahce',len(G),'alan %.0f'%tot,'bina ile cakisan %.1f m2'%ov)

# ---- bina izleri disinda kalan bahce + araziyi izleyen yuzey (1 m grid)
from shapely.ops import unary_union
from shapely import contains_xy
from scipy.spatial import Delaunay
bu=unary_union([b for n,b in B])
seen=set(); out=open('bahce_mesh.txt','w'); n=0; area=0
for k,P in enumerate(G,1):
    key=tuple(np.round(P.ravel(),2))
    if key in seen: continue
    seen.add(key)
    pg=Polygon(P).buffer(0).difference(bu)
    near=min((Polygon(P).distance(b),nm) for nm,b in B)[1]
    for g in polys_of(pg) if False else ([pg] if pg.geom_type=='Polygon' else list(pg.geoms)):
        if g.area<1: continue
        n+=1; area+=g.area
        ring=np.array(g.exterior.coords)[:-1]
        bd=[]
        for i in range(len(ring)):
            a,b=ring[i],ring[(i+1)%len(ring)]; m_=max(1,int(np.hypot(*(b-a))/0.5))
            bd.append(a+(b-a)*np.linspace(0,1,m_,endpoint=False)[:,None])
        bd=np.vstack(bd)
        x0,y0,x1,y1=g.bounds
        gx,gy=np.meshgrid(np.arange(x0,x1,1.0),np.arange(y0,y1,1.0)); gp=np.c_[gx.ravel(),gy.ravel()]
        gp=gp[contains_xy(g.buffer(-0.3),gp[:,0],gp[:,1])]
        Pt=np.vstack([bd,gp]); T=Delaunay(Pt).simplices
        c=Pt[T].mean(1); T=T[contains_xy(g,c[:,0],c[:,1])]
        zz=z(Pt)+0.05
        out.write('G BAHCE-%02d_%s %d %d\n'%(n,near,len(Pt),len(T)))
        for p,w in zip(Pt,zz): out.write('%.3f %.3f %.3f\n'%(p[0],p[1],w))
        for t in T: out.write('%d %d %d\n'%tuple(t))
        out.write('L '+';'.join('%.3f,%.3f,%.3f'%(p[0],p[1],w+0.05) for p,w in zip(bd,zz[:len(bd)]))+'\n')
print('bahce parca',n,'net alan %.0f m2'%area)
