# P115 bahceleri: parsel, binalar arasi orta cizgilerden 3 yapiya bolunur; her bahce kendi yapisinin +-0.00 kotunda (dogal arazi kalmaz).
# Arazi P115 icinde bu kotlara gore yeniden kurulur; bahce kenarlarinda (parsel siniri ve bahceler arasi) dik istinat duvari.
# Girdi: pk_mesh.txt (acik PLANKOTE modelinin arazisi), pk_rings.txt, tesviye.json, yollar.json
# Cikti: p115_mesh.txt, p115_bahce.txt, p115_duvar.txt
import numpy as np, json, shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import contains_xy
from matplotlib.tri import Triangulation, LinearTriInterpolator
from scipy.spatial import Delaunay
H0=105.07
V=[];F=[]
for l in open('pk_mesh.txt'):
    t=l.split()
    if t[0]=='V': V.append([float(x) for x in t[1:6]])
    elif t[0]=='F': F.append([int(x) for x in t[1:4]])
V=np.array(V); F=np.array(F)
nat_i=LinearTriInterpolator(Triangulation(V[:,0],V[:,1],F),V[:,2])
nat=lambda x,y: np.asarray(nat_i(x,y).filled(np.nan))
uvA=np.linalg.lstsq(np.c_[V[:,:2],np.ones(len(V))],V[:,3:5],rcond=None)[0]
PAR={}
for l in open('pk_rings.txt'):
    t=l.split()
    if t[0]=='R': PAR[t[1]]=Polygon([tuple(map(float,p.split(',')[:2])) for p in ' '.join(t[2:]).split(';')])
J=json.load(open('tesviye.json'))
idx=[k for k,n in enumerate(J['names']) if n.startswith('P115')]
names=[J['names'][k] for k in idx]; Z=np.array([J['Z'][k] for k in idx]); fps=[Polygon(J['fp'][k]) for k in idx]
r=json.load(open('yollar.json'))['YOL1']; a=np.array(r['a']); t=np.array(r['t']); n=np.array(r['n'])
def srng(p): s=(np.array(p.exterior.coords)-a)@t; return s.min(),s.max()
def slab(s0,s1): return Polygon([a+s*t+q*n for s,q in ((s0,-500),(s1,-500),(s1,500),(s0,500))])
order=sorted(range(3),key=lambda i:srng(fps[i])[0])
cuts=[-1e4]+[(srng(fps[order[i]])[1]+srng(fps[order[i+1]])[0])/2 for i in range(2)]+[1e4]
P=PAR['115']; gard=[None]*3
for j,i in enumerate(order):
    g=P.intersection(slab(cuts[j],cuts[j+1]))
    if g.geom_type!='Polygon': g=max(g.geoms,key=lambda q:q.area)
    gard[i]=g
def final(x,y):
    f=nat(x,y)
    for i,g in enumerate(gard): f[contains_xy(g,x,y)]=Z[i]
    for i,fp in enumerate(fps): f[contains_xy(fp,x,y)]=Z[i]-0.05     # kirmizi taban yuzeyi arazi ile cakismasin
    return f
def ringpts(poly,step=0.5):
    c=np.array(poly.exterior.coords); out=[]
    for p0,p1 in zip(c[:-1],c[1:]):
        m=max(1,int(np.hypot(*(p1-p0))/step)); out.append(p0+(p1-p0)*np.linspace(0,1,m,endpoint=False)[:,None])
    return np.vstack(out)
region=P.buffer(15)
outer=V[~contains_xy(region,V[:,0],V[:,1])][:,:3]
x0,y0,x1,y1=region.bounds
gx,gy=np.meshgrid(np.arange(x0,x1,1.0),np.arange(y0,y1,1.0)); g=np.c_[gx.ravel(),gy.ravel()]
bnd=unary_union([q.boundary for q in gard]+[q.boundary for q in fps])
g=g[contains_xy(region,g[:,0],g[:,1])]; g=g[shapely.distance(bnd,shapely.points(g[:,0],g[:,1]))>0.3]
ins=np.vstack([np.c_[ringpts(q.buffer(-0.05,join_style=2)),np.full(len(ringpts(q.buffer(-0.05,join_style=2))),Z[i])] for i,q in enumerate(gard)])
o=ringpts(P.buffer(0.05,join_style=2))
rb=ringpts(region,1.0)
P2=np.vstack([g,o,rb]); A=np.vstack([outer,ins,np.c_[P2,final(P2[:,0],P2[:,1])]])
A=A[~np.isnan(A[:,2])]                     # PLANKOTE arazisi disi (kot yok) atilir
_,ui=np.unique(np.round(A[:,:2],2),axis=0,return_index=True); A=A[np.sort(ui)]
T=Delaunay(A[:,:2]).simplices
p=A[:,:2]; u=p[T[:,1]]-p[T[:,0]]; w=p[T[:,2]]-p[T[:,0]]; cr=u[:,0]*w[:,1]-u[:,1]*w[:,0]
T=T[np.abs(cr)>1e-6]; cr=cr[np.abs(cr)>1e-6]; T[cr<0]=T[cr<0][:,[0,2,1]]
cen=A[T][:,:,:2].mean(1); T=T[~np.isnan(nat(cen[:,0],cen[:,1]))|contains_xy(P,cen[:,0],cen[:,1])]   # kapsama disi ucgenler atilir
UV=np.c_[A[:,:2],np.ones(len(A))]@uvA
with open('p115_mesh.txt','w') as f:
    for v_,uv in zip(A,UV): f.write('V %.3f %.3f %.3f %.6f %.6f\n'%(v_[0],v_[1],v_[2],uv[0],uv[1]))
    for t_ in T: f.write('F %d %d %d\n'%tuple(t_))
with open('p115_bahce.txt','w') as f:
    for i in range(3):
        f.write('L %s %.3f %s %s\n'%(names[i],Z[i],';'.join('%.3f,%.3f'%tuple(q) for q in np.array(gard[i].exterior.coords)[:-1]),';'.join('%.3f,%.3f'%tuple(q) for q in np.array(fps[i].exterior.coords)[:-1])))
walls=[]; L_={'istinat':0,'dolgu':0,'basamak':0}
for i,q in enumerate(gard):
    c=np.array(q.exterior.coords)
    for p0,p1 in zip(c[:-1],c[1:]):
        m=max(1,int(round(np.hypot(*(p1-p0)))))
        for k in range(m):
            s0=p0+(p1-p0)*k/m; s1=p0+(p1-p0)*(k+1)/m; mid=(s0+s1)/2
            other=[j for j in range(3) if j!=i and gard[j].distance(shapely.Point(*mid))<0.1]
            if other:
                j=other[0]
                if Z[i]>Z[j]: walls.append((s0,s1,[Z[j]]*2,[Z[i]]*2,'basamak')); L_['basamak']+=np.hypot(*(s1-s0))
                continue
            nb=nat(np.array([s0[0],s1[0]]),np.array([s0[1],s1[1]]))
            if np.isnan(nb).any() or np.abs(nb-Z[i]).max()<0.05: continue
            if nb.mean()>Z[i]: walls.append((s0,s1,[Z[i]]*2,list(nb),'istinat')); L_['istinat']+=np.hypot(*(s1-s0))
            else: walls.append((s0,s1,list(nb),[Z[i]]*2,'dolgu')); L_['dolgu']+=np.hypot(*(s1-s0))
with open('p115_duvar.txt','w') as f:
    for s0,s1,lo,hi,ty in walls: f.write('W %s %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f\n'%(ty,s0[0],s0[1],s1[0],s1[1],lo[0],lo[1],hi[0],hi[1]))
for i in range(3):
    nb=nat(*ringpts(gard[i],1.0).T); print('%s bahce %.0f m2 (bina %.0f m2) kot +%.2f | kenarda tabii zemin %.2f..%.2f'%(names[i],gard[i].area-fps[i].area,fps[i].area,Z[i]+H0,np.nanmin(nb)+H0,np.nanmax(nb)+H0))
hh=[max(abs(h-l) for h,l in zip(w[3],w[2])) for w in walls]
print('duvar: istinat %.0f m, dolgu %.0f m, bahceler arasi basamak %.0f m, en yuksek %.1f m'%(L_['istinat'],L_['dolgu'],L_['basamak'],max(hh)))
