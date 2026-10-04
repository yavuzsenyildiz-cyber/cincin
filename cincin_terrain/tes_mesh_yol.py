import numpy as np, json, shapely
from shapely.geometry import Polygon, LineString
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
lots0=[Polygon(p) for p in J['lots']]

R=json.load(open('yollar.json')); roads=[]
for nm,r in R.items():
    a=np.array(r['a']); t=np.array(r['t']); n=np.array(r['n']); u=np.array(r['u']); z=np.array(r['z'])
    roads.append(dict(nm=nm,a=a,t=t,n=n,u=u,z=z,W=r['W'],
        line=LineString([a+u[0]*t,a+u[-1]*t])))
for r in roads: r['strip']=r['line'].buffer(r['W']/2,cap_style=2)
RS=unary_union([r['strip'] for r in roads])

lots=[]
for l in lots0:
    d=l.difference(RS)
    if d.geom_type!='Polygon': d=max(d.geoms,key=lambda q:q.area)
    lots.append(d)

def road_state(r,x,y):
    s=(x-r['a'][0])*r['t'][0]+(y-r['a'][1])*r['t'][1]
    uc=np.clip(s,r['u'][0],r['u'][-1])
    px=r['a'][0]+uc*r['t'][0]; py=r['a'][1]+uc*r['t'][1]
    dist=np.hypot(x-px,y-py)
    return np.maximum(0,dist-r['W']/2), np.interp(uc,r['u'],r['z']), dist<=r['W']/2+1e-9

def final(x,y):
    n=nat(x,y); pts=shapely.points(x,y)
    inl=np.full(len(x),-1)
    for k,lp in enumerate(lots): inl[contains_xy(lp,x,y)]=k
    D=np.array([shapely.distance(lp,pts) for lp in lots])
    lo=(Z[:,None]-D/K).max(0); hi=(Z[:,None]+D/K).min(0)
    f=np.clip(n,lo,hi); bad=lo>hi; near=D.argmin(0); ar=np.arange(len(x))
    f[bad]=np.clip(n[bad],(Z[near]-D[near,ar]/K)[bad],(Z[near]+D[near,ar]/K)[bad])
    f[inl>=0]=Z[inl[inl>=0]]
    for r in roads:
        De,zr,ins=road_state(r,x,y)
        f=np.where(inl>=0,f,np.clip(f,zr-De/K,zr+De/K))
    for r in roads:
        De,zr,ins=road_state(r,x,y)
        f=np.where(ins,zr,f)
    return f

U=unary_union(lots+[RS]); region=U.buffer(20)
outer=V[~contains_xy(region,V[:,0],V[:,1])][:,:3]
x0,y0,x1,y1=region.bounds
gx,gy=np.meshgrid(np.arange(x0,x1,1.0),np.arange(y0,y1,1.0)); g=np.c_[gx.ravel(),gy.ravel()]
bnd=unary_union([lp.boundary for lp in lots]+[RS.boundary])
g=g[contains_xy(region,g[:,0],g[:,1])]
g=g[shapely.distance(bnd,shapely.points(g[:,0],g[:,1]))>0.3]
def ringpts(poly,step=0.5):
    out=[]
    for r in ([poly] if poly.geom_type=='Polygon' else list(poly.geoms)):
        c=np.array(r.exterior.coords)
        for a,b in zip(c[:-1],c[1:]):
            n=max(1,int(np.hypot(*(b-a))/step)); out.append(a+(b-a)*np.linspace(0,1,n,endpoint=False)[:,None])
    return np.vstack(out)
ins=[]
for k,lp in enumerate(lots):
    p=ringpts(lp.buffer(-0.05,join_style=2)); ins.append(np.c_[p,np.full(len(p),Z[k])])
rin=ringpts(RS.buffer(-0.05,join_style=2)); ins.append(np.c_[rin,final(rin[:,0],rin[:,1])])
ins=np.vstack(ins)
o=np.vstack([ringpts(lp.buffer(0.05,join_style=2)) for lp in lots]+[ringpts(RS.buffer(0.05,join_style=2))])
inner=lots+[RS]
o=o[~np.any([contains_xy(q.buffer(-0.04,join_style=2),o[:,0],o[:,1]) for q in inner],axis=0)]
rb=ringpts(region,1.0)
P2=np.vstack([g,o,rb]); z2=final(P2[:,0],P2[:,1])
A=np.vstack([outer,ins,np.c_[P2,z2]])
_,ui=np.unique(np.round(A[:,:2],2),axis=0,return_index=True); A=A[np.sort(ui)]
T=Delaunay(A[:,:2]).simplices
p=A[:,:2]; u=p[T[:,1]]-p[T[:,0]]; w=p[T[:,2]]-p[T[:,0]]; cr=u[:,0]*w[:,1]-u[:,1]*w[:,0]
T=T[np.abs(cr)>1e-6]; cr=cr[np.abs(cr)>1e-6]; T[cr<0]=T[cr<0][:,[0,2,1]]
UV=np.c_[A[:,:2],np.ones(len(A))]@uvA
with open('tes_mesh_yol.txt','w') as f:
    for a,uv in zip(A,UV): f.write('V %.3f %.3f %.3f %.6f %.6f\n'%(a[0],a[1],a[2],uv[0],uv[1]))
    for t in T: f.write('F %d %d %d\n'%tuple(t))
print('mesh',len(A),'nokta',len(T),'ucgen')

# yol yuzeyi (her 1 m'lik dilim bir dortgen)
with open('yol_yuzey.txt','w') as f:
    for r in roads:
        u=r['u']; z=r['z']; h=r['W']/2
        for i in range(len(u)-1):
            q=[]
            for j in (i,i+1):
                c=r['a']+u[j]*r['t']
                q.append((c-r['n']*h,z[j]));
            for j in (i+1,i):
                c=r['a']+u[j]*r['t']
                q.append((c+r['n']*h,z[j]))
            f.write('Q %s %s\n'%(r['nm'],' '.join('%.3f %.3f %.3f'%(p[0][0],p[0][1],p[1]) for p in q)))

# platform / bina verisi (bahce platformlari yoldan kirpilmis)
with open('tes_objs_yol.txt','w') as f:
    for k,nm in enumerate(J['names']):
        f.write('B %s %.3f %.3f %s\n'%(nm,Z[k],Z[k]+SUB,';'.join('%.3f,%.3f'%tuple(q) for q in J['fp'][k])))
        f.write('L %s %.3f %s\n'%(nm,Z[k],';'.join('%.3f,%.3f'%tuple(q) for q in np.array(lots[k].exterior.coords)[:-1])))

# rapor
with open('rapor_yol.txt','w',encoding='utf-8') as f:
    for r in roads:
        z=r['z']; g=np.abs(np.diff(z))
        f.write('%s: uzunluk %.0f m, genislik %.1f m, kot %.2f..%.2f, max boyuna egim %%%.1f\n'%(r['nm'],r['u'][-1]-r['u'][0],r['W'],z.min()+H0,z.max()+H0,g.max()*100))
        for k,nm in enumerate(J['names']):
            d=r['strip'].distance(lots[k])
            if d<1.5:
                s=np.array(lots[k].exterior.coords); De,zr,_=road_state(r,s[:,0],s[:,1]); m=De<0.5
                if m.any(): f.write('   %s: yol-platform kot farki %.2f..%.2f m (platform %.2f, yol %.2f..%.2f)\n'%(nm,(zr[m]-Z[k]).min(),(zr[m]-Z[k]).max(),Z[k]+H0,zr[m].min()+H0,zr[m].max()+H0))
        f.write('   kirpilan platform alani: %s\n'%', '.join('%s %.0f m2'%(J['names'][k],lots0[k].area-lots[k].area) for k in range(len(lots)) if lots0[k].area-lots[k].area>0.5))
print(open('rapor_yol.txt',encoding='utf-8').read())

# onizleme
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(14,7)); tr=Triangulation(A[:,0],A[:,1],T)
cs=ax.tricontourf(tr,A[:,2]+H0,levels=np.arange(np.floor((A[:,2]+H0).min()),np.ceil((A[:,2]+H0).max())+1,1),cmap='terrain')
ax.tricontour(tr,A[:,2]+H0,levels=np.arange(np.floor((A[:,2]+H0).min()),np.ceil((A[:,2]+H0).max())+1,1),colors='k',linewidths=0.3)
for l in lots: ax.plot(*l.exterior.xy,'g-',lw=1)
for r in roads: ax.plot(*r['strip'].exterior.xy,'r-',lw=1)
ax.set_xlim(x0+10,x1-10); ax.set_ylim(y0+10,y1-10); ax.set_aspect('equal'); plt.colorbar(cs,ax=ax,shrink=0.6,label='kot')
plt.savefig('tes_yol_preview.png',dpi=110,bbox_inches='tight')
