import numpy as np, json, shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import contains_xy
from matplotlib.tri import Triangulation, LinearTriInterpolator
from scipy.spatial import Delaunay
H0=105.07; K=1.5; SUB=0.50
V=[];F=[]
for l in open('pk_merged_mesh.txt'):
    t=l.split()
    if t[0]=='V': V.append([float(x) for x in t[1:6]])
    elif t[0]=='F': F.append([int(x) for x in t[1:4]])
V=np.array(V); F=np.array(F)
nat_i=LinearTriInterpolator(Triangulation(V[:,0],V[:,1],F),V[:,2])
nat=lambda x,y: np.asarray(nat_i(x,y).filled(np.nan))
uvA=np.linalg.lstsq(np.c_[V[:,:2],np.ones(len(V))],V[:,3:5],rcond=None)[0]
J=json.load(open('tesviye.json')); Z=np.array(J['Z'])
lots=[Polygon(p) for p in J['lots']]
def final(x,y):
    n=nat(x,y); pts=shapely.points(x,y)
    inl=np.full(len(x),-1)
    for k,lp in enumerate(lots): inl[contains_xy(lp,x,y)]=k
    D=np.array([shapely.distance(lp,pts) for lp in lots])
    lo=(Z[:,None]-D/K).max(0); hi=(Z[:,None]+D/K).min(0)
    f=np.clip(n,lo,hi); bad=lo>hi; near=D.argmin(0); ar=np.arange(len(x))
    f[bad]=np.clip(n[bad],(Z[near]-D[near,ar]/K)[bad],(Z[near]+D[near,ar]/K)[bad])
    f[inl>=0]=Z[inl[inl>=0]]
    return f
U=unary_union(lots); region=U.buffer(20)
outer=V[~contains_xy(region,V[:,0],V[:,1])][:,:3]
x0,y0,x1,y1=region.bounds
gx,gy=np.meshgrid(np.arange(x0,x1,1.0),np.arange(y0,y1,1.0)); g=np.c_[gx.ravel(),gy.ravel()]
bnd=unary_union([lp.boundary for lp in lots])
g=g[contains_xy(region,g[:,0],g[:,1])]
g=g[shapely.distance(bnd,shapely.points(g[:,0],g[:,1]))>0.3]
def ringpts(poly,step=0.5):
    out=[]
    for r in ([poly] if poly.geom_type=='Polygon' else list(poly.geoms)):
        c=np.array(r.exterior.coords)
        for a,b in zip(c[:-1],c[1:]):
            n=max(1,int(np.hypot(*(b-a))/step)); out.append(a+(b-a)*np.linspace(0,1,n,endpoint=False)[:,None])
    return np.vstack(out)
ins=[];
for k,lp in enumerate(lots):
    p=ringpts(lp.buffer(-0.05,join_style=2)); ins.append(np.c_[p,np.full(len(p),Z[k])])
ins=np.vstack(ins)
o=np.vstack([ringpts(lp.buffer(0.05,join_style=2)) for lp in lots])
o=o[~np.any([contains_xy(lp.buffer(-0.04,join_style=2),o[:,0],o[:,1]) for lp in lots],axis=0)]  # komsu lot icine dusenleri at
# region siniri
rb=ringpts(region,1.0)
P2=np.vstack([g,o,rb]); z2=final(P2[:,0],P2[:,1])
A=np.vstack([outer,ins,np.c_[P2,z2]])
# yakin kopyalari ayikla
_,ui=np.unique(np.round(A[:,:2],2),axis=0,return_index=True); A=A[np.sort(ui)]
T=Delaunay(A[:,:2]).simplices
p=A[:,:2]; u=p[T[:,1]]-p[T[:,0]]; w=p[T[:,2]]-p[T[:,0]]; cr=u[:,0]*w[:,1]-u[:,1]*w[:,0]
T=T[np.abs(cr)>1e-6]; cr=cr[np.abs(cr)>1e-6]; T[cr<0]=T[cr<0][:,[0,2,1]]
UV=np.c_[A[:,:2],np.ones(len(A))]@uvA
with open('tes_mesh.txt','w') as f:
    for a,uv in zip(A,UV): f.write('V %.3f %.3f %.3f %.6f %.6f\n'%(a[0],a[1],a[2],uv[0],uv[1]))
    for t in T: f.write('F %d %d %d\n'%tuple(t))
print('mesh',len(A),'nokta',len(T),'ucgen')
# platform / bina / bahce verisi
with open('tes_objs.txt','w') as f:
    for k,nm in enumerate(J['names']):
        f.write('B %s %.3f %.3f %s\n'%(nm,Z[k],Z[k]+SUB,';'.join('%.3f,%.3f'%tuple(q) for q in J['fp'][k])))
        f.write('L %s %.3f %s\n'%(nm,Z[k],';'.join('%.3f,%.3f'%tuple(q) for q in np.array(lots[k].exterior.coords)[:-1])))
# rapor csv
import csv
with open(r"C:/Users/YOGA/OneDrive/MİMARİ/CİNCİN/GUNCEL_D5_SKETCHUP/SketchUp/CINCIN_yapi_kotlandirma.csv",'w',newline='',encoding='utf-8-sig') as f:
    wr=csv.writer(f,delimiter=';')
    YB=json.load(open('yapi_bolum.json'))
    wr.writerow(['yapi','bagimsiz bolumler','kose kotlari (tabii zemin)','±0.00 kotu (kose ort., PAIY md.21/5)','zemin kat doseme ust kotu (+0.50)','platform/bahce kotu','platform alani m2','kazi m3','dolgu m3','platform kenarinda max sev yuksekligi m','komsu yapi platformuna kot farki m'])
    for k,nm in enumerate(J['names']):
        wr.writerow([nm,', '.join(YB[nm]),' / '.join('%.2f'%(z+H0) for z in J['zc'][k]),'%.2f'%(Z[k]+H0),'%.2f'%(Z[k]+H0+SUB),'%.2f'%(Z[k]+H0),'%.0f'%lots[k].area,'%.0f'%J['cut'][k],'%.0f'%J['fill'][k],'%.2f'%J['wall'][k],'%.2f'%J['step'][k]])
