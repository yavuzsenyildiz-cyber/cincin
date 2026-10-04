import numpy as np, json
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely import contains_xy, prepare
from shapely.strtree import STRtree
from matplotlib.tri import Triangulation, LinearTriInterpolator
from scipy.spatial import Delaunay
H0=105.07; SUB=0.50; K=1.5   # subasman, sev (yatay/dusey)
V=[];F=[]
for l in open('pk_merged_mesh.txt'):
    t=l.split()
    if t[0]=='V': V.append([float(x) for x in t[1:6]])
    elif t[0]=='F': F.append([int(x) for x in t[1:4]])
V=np.array(V); F=np.array(F)
nat_i=LinearTriInterpolator(Triangulation(V[:,0],V[:,1],F),V[:,2])
nat=lambda x,y: np.asarray(nat_i(x,y).filled(np.nan))
uvA=np.linalg.lstsq(np.c_[V[:,:2],np.ones(len(V))],V[:,3:5],rcond=None)[0]
# binalar
B=[]
for l in open('bina_iz.txt'):
    h=l.split(' | ')[0].split(' ',3)
    P=np.array([[float(c) for c in q.split(',')] for q in h[3].split(';')])
    B.append(dict(name=h[1],P=P,poly=Polygon(P)))
# bahceler (bahce_mesh.txt sinirlarindan)
G=[]
L=open('bahce_mesh.txt').read().splitlines(); i=0
while i<len(L):
    _,nm,nv,nt=L[i].split(); nv=int(nv); nt=int(nt); i+=1+nv+nt
    ring=np.array([[float(c) for c in q.split(',')[:2]] for q in L[i][2:].split(';')]); i+=1
    G.append(dict(name=nm,poly=Polygon(ring).buffer(0)))
for g in G:
    sc=[(g['poly'].intersection(b['poly'].buffer(0.4)).area,-g['poly'].distance(b['poly']),k) for k,b in enumerate(B)]
    g['b']=max(sc)[2]
for k,b in enumerate(B):
    gs=[g['poly'] for g in G if g['b']==k]
    b['lot']=unary_union([b['poly'].buffer(0.02)]+[p.buffer(0.02) for p in gs]).buffer(-0.02)
    if b['lot'].geom_type!='Polygon': b['lot']=max(b['lot'].geoms,key=lambda q:q.area)
    zc=nat(b['P'][:,0],b['P'][:,1])
    b['zc']=zc; b['z0']=float(zc.mean())        # Md.21/5: tabii zemin ortalamasi
    b['ngarden']=len(gs)
# lotlar arasi cakisma temizligi (once kucuk index)
for k,b in enumerate(B):
    for j in range(k):
        b['lot']=b['lot'].difference(B[j]['lot'])
        if b['lot'].geom_type!='Polygon': b['lot']=max(b['lot'].geoms,key=lambda q:q.area)
# ---- 4'lu bolumleri yapilara grupla (birbirine degen izler)
from shapely.ops import unary_union as UU
par=list(range(len(B)))
def fnd(i):
    while par[i]!=i: i=par[i]
    return i
for i in range(len(B)):
    for j in range(i):
        if B[i]['poly'].buffer(0.1).intersects(B[j]['poly']): par[fnd(i)]=fnd(j)
grp={}
for i in range(len(B)): grp.setdefault(fnd(i),[]).append(i)
Y=[]
for gi,(r,mem) in enumerate(sorted(grp.items(),key=lambda kv:(B[kv[1][0]]['name'][:4],min(B[m]['P'][:,0].min() for m in kv[1])))):
    fpu=UU([B[m]['poly'].buffer(0.02,join_style=2) for m in mem]).buffer(-0.02,join_style=2).simplify(0.05)
    P=np.array(fpu.exterior.coords)[:-1]
    lot=UU([B[m]['lot'].buffer(0.02,join_style=2) for m in mem]).buffer(-0.02,join_style=2)
    if lot.geom_type!='Polygon': lot=max(lot.geoms,key=lambda q:q.area)
    zc=nat(P[:,0],P[:,1])
    Y.append(dict(name='%s-YAPI%d'%(B[mem[0]]['name'][:4],gi+1),P=P,poly=fpu,lot=lot,zc=zc,z0=float(zc.mean()),
                  ngarden=sum(B[m]['ngarden'] for m in mem),units=[B[m]['name'] for m in mem]))
    print(Y[-1]['name'],'bolumler:',', '.join(Y[-1]['units']),'kose sayisi',len(P))
B=Y
lots=[b['lot'] for b in B]; Z=np.array([b['z0'] for b in B])
U=unary_union(lots); region=U.buffer(20)
def final(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float); n=nat(x,y)
    zin=np.full(len(x),np.nan)
    for k,lp in enumerate(lots):
        m=contains_xy(lp,x,y); zin[m]=Z[k]
    out=np.isnan(zin)
    if out.any():
        xo,yo=x[out],y[out]
        D=np.array([lp.boundary.distance([Point(a,b) for a,b in zip(xo,yo)]) if False else np.array([lp.distance(Point(a,b)) for a,b in zip(xo,yo)]) for lp in lots])
        lo=(Z[:,None]-D/K).max(0); hi=(Z[:,None]+D/K).min(0)
        no=n[out]; f=np.clip(no,lo,hi)
        bad=lo>hi; near=D.argmin(0)
        f[bad]=np.clip(no[bad],(Z[near]-D[near,np.arange(len(xo))]/K)[bad],(Z[near]+D[near,np.arange(len(xo))]/K)[bad])
        zin[out]=f
    return zin, n
# hacim (0.25 m raster)
x0,y0,x1,y1=region.bounds; s=0.25
gx,gy=np.meshgrid(np.arange(x0,x1,s),np.arange(y0,y1,s)); px,py=gx.ravel(),gy.ravel()
m=contains_xy(region,px,py); px,py=px[m],py[m]
# hizli: once lot disi noktalarda mesafe hesaplamak pahali; vektorize shapely
import shapely
pts=shapely.points(px,py)
inlot=np.full(len(px),-1)
for k,lp in enumerate(lots): inlot[contains_xy(lp,px,py)]=k
n=nat(px,py)
Dall=np.array([shapely.distance(lp,pts) for lp in lots])
lo=(Z[:,None]-Dall/K).max(0); hi=(Z[:,None]+Dall/K).min(0)
f=np.clip(n,lo,hi); bad=lo>hi; near=Dall.argmin(0); ar=np.arange(len(px))
f[bad]=np.clip(n[bad],(Z[near]-Dall[near,ar]/K)[bad],(Z[near]+Dall[near,ar]/K)[bad])
f[inlot>=0]=Z[inlot[inlot>=0]]
d=f-n; A=s*s
print('TOPLAM kazi %.0f m3  dolgu %.0f m3  net %+.0f m3'%(-d[d<0].sum()*A,d[d>0].sum()*A,d.sum()*A))
rep=[]
for k,b in enumerate(B):
    mk=inlot==k; dk=d[mk]
    # komsu ile kot farki / dis kenar duvar yuksekligi (lot siniri boyunca)
    ring=np.array(b['lot'].exterior.coords); ed=[]
    for a_,c_ in zip(ring[:-1],ring[1:]):
        nn=max(1,int(np.hypot(*(c_-a_))/0.5)); ed.append(a_+(c_-a_)*np.linspace(0,1,nn,endpoint=False)[:,None])
    ed=np.vstack(ed); c=np.array(b['lot'].centroid.coords[0])
    o=ed+(ed-c)/np.linalg.norm(ed-c,axis=1)[:,None]*0.1
    fo,_=final(o[:,0],o[:,1]); nb=np.abs(fo-Z[k]); nb[np.abs(fo-Z[k])<0.2]=0; wall=np.abs(nat(ed[:,0],ed[:,1])-Z[k])
    b['step']=float(np.nanmax(nb))
    b.update(cut=-dk[dk<0].sum()*A,fill=dk[dk>0].sum()*A,wall=float(np.nanmax(wall)),lotA=b['lot'].area)
    print('%s ±0.00=%.2f (kose %.2f..%.2f) zemin kat dos.=%.2f | lot %.0f m2 bahce %d | kazi %.0f dolgu %.0f | platform kenarinda max sev yuk. %.2f | komsu yapiya kot farki %.2f'%(b['name'],b['z0']+H0,b['zc'].min()+H0,b['zc'].max()+H0,b['z0']+H0+SUB,b['lotA'],b['ngarden'],b['cut'],b['fill'],b['wall'],b['step']))
json.dump(dict(Z=Z.tolist(),names=[b['name'] for b in B],lots=[list(map(list,np.array(b['lot'].exterior.coords)[:-1])) for b in B],
  cut=[b['cut'] for b in B],fill=[b['fill'] for b in B],wall=[b['wall'] for b in B],step=[b['step'] for b in B],zc=[b['zc'].tolist() for b in B],
  fp=[b['P'].tolist() for b in B]),open('tesviye.json','w'))
json.dump({b['name']:b['units'] for b in B},open('yapi_bolum.json','w'))
np.save('tes_raster.npy',np.c_[px,py,n,f])
