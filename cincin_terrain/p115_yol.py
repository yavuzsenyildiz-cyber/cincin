# P115: kitlelerin arkasindan (kuzey serit) arac yolu -> YAPI2/YAPI3 arasi otopark -> YAPI3 arkasinda yaya yolu.
# Kotlandirma (Plansiz Alanlar Imar Yon.): bahceler +-0.00 = bina kose tabii zemin ortalamasi; zemin kat esigi +-0.00 + s, s<=1.20.
# Yol <=%12, otopark <=%5, yaya yolu %8 (asarsa merdiven). Kuzey kapilar yolla ayni kotta; sokak hicbir yerde dosemenin ustune cikmaz.
# Girdi: pk_mesh.txt, pk_rings.txt, tesviye.json, yollar.json, git HEAD kitle_dump.json (kapilar)
# Cikti: p115y_mesh.txt (ucgen basina malzeme), p115y_duvar.txt, p115y_park.txt, p115y_etiket.txt, p115y_merdiven.txt
import numpy as np, json, shapely, subprocess
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union, nearest_points
from shapely import contains_xy
from matplotlib.tri import Triangulation, LinearTriInterpolator
from scipy.spatial import Delaunay
from scipy.optimize import linprog
H0=105.07; W=3.0; S_ROAD=0.12; S_PARK=0.05; S_WALK=0.08; S_STAIR=0.50; SMAX_SILL=1.20; DOOR_GAP=0.02
FACADE_REACH=6.0; STALL_W=2.5; STALL_D=5.0; AISLE=5.5; PARAPET=0.0   # korkuluk duvari yok: duvar ustu yesille/yolla ayni hizada biter
V=[];F=[]
for l in open('pk_mesh.txt'):
    t=l.split()
    if t[0]=='V': V.append([float(x) for x in t[1:6]])
    elif t[0]=='F': F.append([int(x) for x in t[1:4]])
V=np.array(V); F=np.array(F)
nat_i=LinearTriInterpolator(Triangulation(V[:,0],V[:,1],F),V[:,2])
nat=lambda x,y: np.asarray(nat_i(np.asarray(x,float),np.asarray(y,float)).filled(np.nan))
uvA=np.linalg.lstsq(np.c_[V[:,:2],np.ones(len(V))],V[:,3:5],rcond=None)[0]
ring=None
for l in open('pk_rings.txt'):
    t=l.split()
    if t[0]=='R' and t[1]=='115': ring=[tuple(map(float,p.split(',')[:2])) for p in ' '.join(t[2:]).split(';')]
P=Polygon(ring)
J=json.load(open('tesviye.json'))
ids=[k for k,n in enumerate(J['names']) if n.startswith('P115')]
names=[J['names'][k] for k in ids]; Z=np.array([J['Z'][k] for k in ids]); fps=[Polygon(J['fp'][k]) for k in ids]
# bahce (+-0.00) = kitle subasman alti (modeldeki KITLE_ taban kotu): subasman yesile oturur, arada bosluk kalmaz
ZB_KITLE={'P115-YAPI1':6.30,'P115-YAPI2':2.80,'P115-YAPI3':-0.25}
Z=np.array([ZB_KITLE.get(n,z) for n,z in zip(names,Z)])
# yapi ekseni: bina uzun kenari yonu (duvarlar/otopark buna gore dik ve paralel)
_c=np.array(fps[0].minimum_rotated_rectangle.exterior.coords); _e=[(_c[i+1]-_c[i]) for i in range(4)]
U=max(_e,key=lambda v:np.hypot(*v)); U=U/np.hypot(*U); U=U if U[0]>0 else -U; NU=np.array([-U[1],U[0]])   # NU kuzeye
uc=lambda p_: float(np.dot(np.asarray(p_,float)[:2],U))
def slab_u(u0,u1):
    u0=max(u0,-1e4); u1=min(u1,1e4)
    return Polygon([U*u0-NU*1e3,U*u1-NU*1e3,U*u1+NU*1e3,U*u0+NU*1e3])
def urange(poly): c_=np.array(poly.exterior.coords)@U; return float(c_.min()),float(c_.max())
# gercek kitle taban izleri (modelden, bolge_dump.txt): yol/duvar bunlara gore kesilir
real_fp=[]
import re as _re
for _l in open('bolge_dump.txt'):
    if _l.startswith('  TABAN '):
        _p=[tuple(map(float,q.split(','))) for q in _l.split()[1].split(';')]
        if len(_p)>=3: real_fp.append(shapely.MultiPoint(_p).convex_hull)
FPu=unary_union(fps+real_fp)

# ---------- kapilar ----------
d=json.loads(subprocess.check_output(['git','show','HEAD:cincin_terrain/kitle_dump.json']))
doors=[]
for r in d['doors']:
    if r['def']!='kapı': continue
    b=r['bounds']; c=np.array([(b[0]+b[3])/2,(b[1]+b[4])/2])
    k=int(np.argmin([fp.exterior.distance(Point(*c)) for fp in fps]))
    if fps[k].exterior.distance(Point(*c))>1.5: continue
    rg=np.array(fps[k].exterior.coords); best=min(((LineString([a,bb]).distance(Point(*c)),a,bb) for a,bb in zip(rg[:-1],rg[1:])),key=lambda q:q[0])
    e=(best[2]-best[1])/np.hypot(*(best[2]-best[1])); n=np.array([e[1],-e[0]])
    if np.dot(n,c-np.array(fps[k].centroid.coords[0]))<0: n=-n
    foot=best[1]+np.dot(c-best[1],e)*e
    doors.append(dict(k=k,c=foot,n=n,north=n[1]>0.7))

# ---------- eksen: kuzey sinirdan W/2 iceride + batidan kamu yoluna giris ----------
north=LineString(ring[0:13])                         # bati ucundan (10.48,85.57) dogu ucuna (155.89,95.96)
off=north.offset_curve(-W/2,join_style=2)
if off.geom_type!='LineString': off=max(off.geoms,key=lambda g:g.length)
oc=np.array(off.coords); oc=oc[np.argsort(oc[:,0])] if oc[0,0]>oc[-1,0] else oc
sw=LineString([ring[-1],ring[0]])                    # guneybati kenar = kamu yolu (18.35,76.94)->(10.48,85.57)
# giris: guneybati kenarda, kotu YAPI1 bahcesine en yakin nokta (bina batisinda kalsin)
cand=[sw.interpolate(f_,normalized=True) for f_ in np.linspace(0.05,0.95,37)]
Jp=min(cand,key=lambda q: abs(float(nat(q.x,q.y))-Z[0]) + 0.02*q.distance(Point(*oc[np.argmin(np.abs(oc[:,0]-22))])))
start_i=int(np.argmin(np.abs(oc[:,0]-22.0)))
axis_pts=[np.array([Jp.x,Jp.y])]+[p for p in oc if p[0]>=oc[start_i,0]]
axis=LineString(axis_pts)
L=axis.length; st=np.arange(0,L,1.0); st=np.r_[st,L] if st[-1]<L-0.3 else st
SP=np.array([axis.interpolate(s).coords[0] for s in st]); zn=nat(SP[:,0],SP[:,1])
def s_at_x(x): return st[int(np.argmin(np.abs(SP[:,0]-x)))]
xr=lambda k: (fps[k].bounds[0],fps[k].bounds[2])
s_park0=s_at_x(xr(1)[1]+2.0); s_park1=s_at_x(xr(2)[0]-2.0)
zone=np.where(st<s_park0,'yol',np.where(st<=s_park1,'otopark','yaya'))

# ---------- seritler ----------
band=north.buffer(W,cap_style=2,join_style=2).intersection(P)          # kuzey sinirdan W icerisi
from shapely.affinity import translate
north_ext=unary_union([unary_union([translate(fp,0,dy) for dy in np.arange(0,15,0.25)]).intersection(P).difference(fp) for fp in fps])
band=unary_union([band,north_ext]).buffer(0.01).buffer(-0.01)      # cephe ile kuzey sinir arasi tamamen sert zemin (kapi onu = yol kotu)
entry=LineString([axis_pts[0],axis_pts[1]]).buffer(W/2,cap_style=2).intersection(P)
xs_park0=uc(SP[st==s_park0][0]); xs_park1=uc(SP[st==s_park1][0])
west_fill=P.intersection(slab_u(-1e4,uc(axis_pts[1])-1.0))          # giris ile kuzey serit arasi bosluk -> rampa
# evler arasi yol genisletme (YAPI1 dogu ucu - YAPI2 bati ucu): 5.5 m
_ord=sorted(range(3),key=lambda k:urange(fps[k])[0])
_u2=urange(fps[_ord[1]])[0]
u_gap0=max(urange(q)[1] for q in fps+real_fp if urange(q)[1]<_u2+0.5)        # YAPI1 (gercek iz dahil) dogu ucu
u_gap1=min(urange(q)[0] for q in fps+real_fp if urange(q)[0]>u_gap0)          # YAPI2 bati ucu
ROAD_W2=5.5
wide=north.buffer(ROAD_W2,cap_style=2,join_style=2).intersection(P).intersection(slab_u(u_gap0,u_gap1))
road_poly=unary_union([band.intersection(slab_u(-1e4,xs_park0)),entry,west_fill,wide]).buffer(0.01).buffer(-0.01).difference(FPu.buffer(0.05))
# not: bati ucta giris seridi (3 m) disinda ~17 m2 kaliyor; 2.5x5 park yeri sigmiyor -> rampa/asfalt olarak kalir
park_poly=P.intersection(slab_u(xs_park0,xs_park1)).difference(FPu.buffer(0.05))
walk_poly=band.intersection(slab_u(xs_park1,1e4)).difference(FPu.buffer(0.05))
# YAPI1 ile YAPI2 arasi otopark: kuzeyden yola acilan 5.5 m koridor (bati) + dogu tarafta 5 m derin park yerleri.
# Duz platform; yola bitisik 2.5 m serit yol kotundan platform kotuna yumusak baglanir (giris).
LOT_W=10.5; LOT_APRON=2.5; AISLE_L=5.5
LOT_U=(u_gap0+3.9,u_gap0+3.9+LOT_W)
lot_poly=P.intersection(slab_u(*LOT_U)).difference(road_poly).difference(FPu.buffer(0.05)).buffer(-0.01).buffer(0.01)
if lot_poly.geom_type!='Polygon': lot_poly=max(lot_poly.geoms,key=lambda q:q.area)
for nm_,pp in (('yol',road_poly),('otopark',park_poly),('yaya',walk_poly)):
    if pp.geom_type!='Polygon': print('uyari:',nm_,'parcali',pp.geom_type)

# ---------- LP: eksen kotlari + esik paylari ----------
ns=len(st); nS=3; nv=ns+nS+ns+(ns-1)      # z, s_k, |z-zn| yardimci, merdiven asimi
A=[];b=[];Aeq=[];beq=[]
c=np.zeros(nv); c[ns+nS:ns+nS+ns]=0.05; c[ns+nS+ns:]=3.0
for i in range(ns-1):
    lim={'yol':S_ROAD,'otopark':S_PARK,'yaya':S_WALK}[zone[i+1] if zone[i]!=zone[i+1] else zone[i]]
    if zone[i]=='yol' or zone[i+1]=='yol': lim=S_ROAD
    ds_=st[i+1]-st[i]
    row=np.zeros(nv); row[i+1]=1; row[i]=-1
    if zone[i]=='yaya' or zone[i+1]=='yaya':
        sk=np.zeros(nv); sk[ns+nS+ns+i]=1
        A+=[row-sk,-row-sk]; b+=[lim*ds_,lim*ds_]
        A+=[row,-row]; b+=[S_STAIR*ds_,S_STAIR*ds_]
    else:
        A+=[row,-row]; b+=[lim*ds_,lim*ds_]
for i in range(ns):
    row=np.zeros(nv); row[i]=1; row[ns+nS+i]=-1; A.append(row); b.append(zn[i])
    row=np.zeros(nv); row[i]=-1; row[ns+nS+i]=-1; A.append(row); b.append(-zn[i])
def zrow(pt):
    s=axis.project(Point(*pt)); i=min(int(np.searchsorted(st,s))-1,ns-2); i=max(i,0); fr=(s-st[i])/(st[i+1]-st[i])
    row=np.zeros(nv); row[i]=1-fr; row[i+1]=fr; return row
for dd in doors:
    if not dd['north']: continue
    row=zrow(dd['c']); row[ns+dd['k']]=-1; Aeq.append(row); beq.append(Z[dd['k']]-DOOR_GAP)    # yol = esik - 2 cm
for i in range(ns):                                                                             # cephe boyunca yol esigi gecmesin
    for k in range(3):
        bx=fps[k].bounds                                                                        # yalniz cephenin yaninda (uclarin otesinde degil)
        if bx[0]-0.5<=SP[i][0]<=bx[2]+0.5 and Point(*SP[i]).distance(fps[k])<W/2+FACADE_REACH:   # yol ekseni ile cephe arasi genis olabilir
            row=np.zeros(nv); row[i]=1; row[ns+k]=-1; A.append(row); b.append(Z[k]-DOOR_GAP)
bounds=[(None,None)]*ns+[(0,SMAX_SILL)]*nS+[(0,None)]*ns+[(0,None)]*(ns-1)
# esikler modeldeki kitle kapi kotlarina sabit (kitleler yerinde kalir): yerel kot +6.60 / +3.10 / +0.05
ESIK_SABIT={'P115-YAPI1':6.60,'P115-YAPI2':3.10,'P115-YAPI3':0.05}
for k in range(nS):
    if names[k] in ESIK_SABIT: sv=max(0.0,ESIK_SABIT[names[k]]-Z[k]); bounds[ns+k]=(sv,sv)
bounds[0]=(zn[0],zn[0])                                                                         # kamu yoluna baglanti
res=linprog(c,A_ub=np.array(A),b_ub=np.array(b),A_eq=np.array(Aeq) if Aeq else None,b_eq=np.array(beq) if Aeq else None,bounds=bounds,method='highs')
if res.status!=0:
    print('kapi esitligi saglanamadi, kapilar yumusatiliyor:',res.message)
    for row,bq in zip(Aeq,beq): A+=[row,-row]; b+=[bq+0.6,-(bq-0.6)]     # +-0.6 m tolerans
    res=linprog(c,A_ub=np.array(A),b_ub=np.array(b),bounds=bounds,method='highs')
assert res.status==0,res.message
x=res.x; za=x[:ns]; sill=x[ns:ns+nS]; Lk=Z+sill
zax=lambda s: np.interp(s,st,za)

# ---------- merdiven (yaya yolunda %8'i asan yerler) ----------
stairs=[]
for i in range(ns-1):
    if zone[i]=='yaya' or zone[i+1]=='yaya':
        g_=abs(za[i+1]-za[i])/(st[i+1]-st[i])
        if g_>S_WALK+0.005:
            nst=int(np.ceil(abs(za[i+1]-za[i])/0.17)); stairs.append((st[i],st[i+1],nst))

# ---------- bahceler ----------
order=sorted(range(3),key=lambda k:fps[k].bounds[0])
order=sorted(range(3),key=lambda k:urange(fps[k])[0])
cuts=[-1e4]+[(urange(fps[order[j]])[1]+urange(fps[order[j+1]])[0])/2 for j in range(2)]+[1e4]
hard=unary_union([road_poly,park_poly,walk_poly,lot_poly])
gard=[None]*3
for j,k in enumerate(order):
    g=P.intersection(slab_u(cuts[j],cuts[j+1])).difference(hard)
    gard[k]=g
# giris kosesi pahi: YAPI1 bahcesinin giris yoluna bakan (kuzeybati) kosesi kirilip yola katilir -> arac donusu kolay
PAH=3.0
g1=gard[order[0]]; g1p=g1 if g1.geom_type=='Polygon' else max(g1.geoms,key=lambda q:q.area)
gc=np.array(g1p.exterior.coords)[:-1]
ic_=int(np.argmin(np.hypot(*(gc-np.array(axis_pts[1])).T)))
C_=gc[ic_]
def _komsu(st_):                                               # kenar boyunca koseden >=1 m uzaktaki ilk nokta
    i_=ic_
    for _ in range(len(gc)):
        i_=(i_+st_)%len(gc)
        if np.hypot(*(gc[i_]-C_))>=1.0: return gc[i_]
    return gc[(ic_+st_)%len(gc)]
Pp=_komsu(-1); Pn=_komsu(1)
A_p=C_+(Pp-C_)/np.hypot(*(Pp-C_))*min(PAH,np.hypot(*(Pp-C_))*0.8); B_p=C_+(Pn-C_)/np.hypot(*(Pn-C_))*min(PAH,np.hypot(*(Pn-C_))*0.8)
pah=Polygon([C_,A_p,B_p]).buffer(0.02,join_style=2).intersection(g1p).difference(FPu.buffer(0.5))
print('giris kosesi pahi: kose (%.2f,%.2f), alan %.1f m2'%(C_[0],C_[1],pah.area))
# kamu yolu agzi: giris seridi ile parsel guneybati kosesi arasindaki bahce sivrisi duz bir pahla yola katilir
_sw=np.array(ring[-1]); _s2=np.array(ring[-2])                                    # (18.35,76.94) ve (21.06,74.22)
_ax=np.array(axis_pts[1])-np.array(axis_pts[0]); _ax/=np.hypot(*_ax); _an=np.array([_ax[1],-_ax[0]])
if np.dot(_an,_sw-np.array(axis_pts[0]))<0: _an=-_an                              # seridin bahce tarafi
_l0=np.array(axis_pts[0])+_an*W/2
mouth=shapely.MultiPoint([tuple(_l0-_ax*1.0),tuple(_l0+_ax*PAH),tuple(_sw),tuple(_sw+(_s2-_sw)/np.hypot(*(_s2-_sw))*PAH)]).convex_hull
mouth=mouth.intersection(P).difference(FPu.buffer(0.5))
print('kamu yolu agzi pahi: alan %.1f m2'%mouth.area)
road_poly=unary_union([road_poly,pah,mouth]).buffer(0.01).buffer(-0.01)
hard=unary_union([road_poly,park_poly,walk_poly,lot_poly])
for j,k in enumerate(order): gard[k]=P.intersection(slab_u(cuts[j],cuts[j+1])).difference(hard)

# ---------- arazi ----------

def feat_z(x,y):
    s=np.array([axis.project(Point(a_,b_)) for a_,b_ in zip(x,y)]); return zax(s)
def final(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float); f=nat(x,y)
    for k,g in enumerate(gard): f[contains_xy(g,x,y)]=Z[k]
    m=contains_xy(hard,x,y)
    if m.any(): f[m]=feat_z(x[m],y[m])
    m=contains_xy(lot_poly,x,y)
    if m.any(): f[m]=lot_z(x[m],y[m])
    for k,fp in enumerate(fps): f[contains_xy(fp,x,y)]=Z[k]-0.05
    return f
Z_LOT=None
def lot_z(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float)
    d=shapely.distance(road_poly,shapely.points(x,y)); w_=np.clip(1-d/LOT_APRON,0,1)
    return Z_LOT+(feat_z(x,y)-Z_LOT)*w_
def ringpts(poly,step=0.5):
    out=[]
    for pg in ([poly] if poly.geom_type=='Polygon' else list(poly.geoms)):
        for rr in [pg.exterior]+list(pg.interiors):
            c_=np.array(rr.coords)
            for p0,p1 in zip(c_[:-1],c_[1:]):
                m=max(1,int(np.hypot(*(p1-p0))/step)); out.append(p0+(p1-p0)*np.linspace(0,1,m,endpoint=False)[:,None])
    return np.vstack(out)
Z_LOT=float(za[int(np.argmin([abs(uc(q)-(LOT_U[0]+AISLE_L/2)) for q in SP]))])     # koridor ortasinda yol kotu
feats=[*gard,road_poly,park_poly,walk_poly,lot_poly,*fps]
region=P.buffer(15)
bnd=unary_union([q.boundary for q in feats]+[P.boundary])
# Her alan ayri ucgenlenir (ucgenler alan sinirini asmaz): yesil sivri/egik ucgenler olusmaz; kot farki olan
# sinirlari gercek duvarlar kapatir.
const=lambda zc: (lambda x,y: np.full(len(x),zc))
parts=[]
for k,gg in enumerate(gard): parts.append((gg.difference(FPu),'cim',const(Z[k])))
# bina izleri (girinti/avlu dahil) bahceyle ayni kotta yesil: teras/tas yuzey kalmaz
for pp_,tg in ((road_poly,'asfalt'),(park_poly,'otopark'),(walk_poly,'yaya')): parts.append((pp_,tg,feat_z))
parts.append((lot_poly,'otopark',lot_z))
for j_,k in enumerate(order): parts.append((FPu.intersection(P).intersection(slab_u(cuts[j_],cuts[j_+1])),'cim',const(Z[k])))   # bina izleri (gercek iz dahil)
VV=[]; FF=[]
def tri_part(poly,tag,zf,step=1.0,extra=None):
    if poly.is_empty: return
    x0_,y0_,x1_,y1_=poly.bounds
    gx,gy=np.meshgrid(np.arange(x0_,x1_,step),np.arange(y0_,y1_,step)); gp=np.c_[gx.ravel(),gy.ravel()]
    gp=gp[contains_xy(poly,gp[:,0],gp[:,1])]
    if len(gp): gp=gp[shapely.distance(poly.boundary,shapely.points(gp[:,0],gp[:,1]))>0.25]
    rp=ringpts(poly,0.4)
    pp_=np.vstack([gp,rp]) if len(gp) else rp
    zz=zf(pp_[:,0],pp_[:,1])
    A3=np.c_[pp_,zz]
    if extra is not None: A3=np.vstack([A3,extra])
    A3=A3[~np.isnan(A3[:,2])]
    _,ui=np.unique(np.round(A3[:,:2],3),axis=0,return_index=True); A3=A3[np.sort(ui)]
    if len(A3)<3: return
    try: Tt=Delaunay(A3[:,:2]).simplices
    except Exception: return
    c3=A3[Tt][:,:,:2].mean(1)
    keep=contains_xy(poly,c3[:,0],c3[:,1]) if extra is None else ~contains_xy(P,c3[:,0],c3[:,1])
    Tt=Tt[keep]
    q2=A3[:,:2]; u=q2[Tt[:,1]]-q2[Tt[:,0]]; w=q2[Tt[:,2]]-q2[Tt[:,0]]; cr=u[:,0]*w[:,1]-u[:,1]*w[:,0]
    Tt=Tt[np.abs(cr)>1e-6]; cr=cr[np.abs(cr)>1e-6]; Tt[cr<0]=Tt[cr<0][:,[0,2,1]]
    base=sum(len(v_) for v_ in VV); VV.append(A3); FF.extend((t_+base,tag) for t_ in Tt)
for poly,tag,zf in parts:
    for pg in ([poly] if poly.geom_type=='Polygon' else [q for q in getattr(poly,'geoms',[]) if q.geom_type=='Polygon']):
        tri_part(pg,tag,zf)
# parsel disi: dogal arazi
outer=V[contains_xy(region,V[:,0],V[:,1])&~contains_xy(P,V[:,0],V[:,1])][:,:3]
far=V[~contains_xy(region,V[:,0],V[:,1])][:,:3]
tri_part(region.difference(P),'arazi',nat,step=1.0,extra=np.vstack([outer,far]))
A_=np.vstack(VV)
UV=np.c_[A_[:,:2],np.ones(len(A_))]@uvA
with open('p115y_mesh.txt','w') as f:
    for v_,uv in zip(A_,UV): f.write('V %.3f %.3f %.3f %.6f %.6f\n'%(v_[0],v_[1],v_[2],uv[0],uv[1]))
    for t_,m_ in FF: f.write('F %d %d %d %s\n'%(t_[0],t_[1],t_[2],m_))

# ---------- duvarlar ----------
walls=[]; WL={}
groups=[('bahce',q) for q in gard]+[('sokak',hard)]
allf=unary_union(gard+[hard])
for tag,q in groups:
    for pg in ([q] if q.geom_type=='Polygon' else list(q.geoms)):
        c_=np.array(pg.exterior.coords)
        for p0,p1 in zip(c_[:-1],c_[1:]):
            if np.hypot(*(p1-p0))<0.05: continue
            m=max(1,int(round(np.hypot(*(p1-p0)))))
            for i in range(m):
                a_=p0+(p1-p0)*i/m; b_=p0+(p1-p0)*(i+1)/m; mid=(a_+b_)/2
                dv=b_-a_; nn=np.array([-dv[1],dv[0]])/max(np.hypot(*dv),1e-9)
                if not pg.contains(Point(*(mid+nn*0.06))): nn=-nn
                if FPu.distance(LineString([a_,b_]))<0.6: continue
                if sw.distance(Point(*mid))<0.2 and Point(*mid).distance(Jp)<W/2+2.0: continue   # kamu yolundan arac girisi: acik
                if P.exterior.distance(Point(*mid))<0.2 and mouth.buffer(0.3).contains(Point(*mid)): continue   # yol agzinda parsel kenari: acik                         # bina cephesine yapisik parcalar (dolgu blok kapatir)
                zi=final([a_[0]+nn[0]*0.06,b_[0]+nn[0]*0.06],[a_[1]+nn[1]*0.06,b_[1]+nn[1]*0.06])
                zo=final([a_[0]-nn[0]*0.06,b_[0]-nn[0]*0.06],[a_[1]-nn[1]*0.06,b_[1]-nn[1]*0.06])
                if np.isnan(zo).any() or np.abs(zi-zo).max()<0.05: continue
                outside_feat=allf.contains(Point(*(mid-nn*0.06)))
                if outside_feat and zi.mean()<=zo.mean(): continue                             # oteki taraf cizer
                nlow=-nn if zi.mean()>zo.mean() else nn          # duvar alcak tarafa dogru kalinlasir
                lo=np.minimum(zi,zo); hi=np.maximum(zi,zo)
                zi4=final([a_[0]+nn[0]*0.4,b_[0]+nn[0]*0.4],[a_[1]+nn[1]*0.4,b_[1]+nn[1]*0.4])     # koseler: duvar ustu yanindaki en yuksek zemine kadar
                zo4=final([a_[0]-nn[0]*0.4,b_[0]-nn[0]*0.4],[a_[1]-nn[1]*0.4,b_[1]-nn[1]*0.4])
                hi=np.nanmax(np.vstack([hi,zi4,zo4]),axis=0)
                if zi.mean()>zo.mean() and (zi-zo).max()>0.5: hi=hi+PARAPET; ty='dolgu'
                else: ty='istinat' if zi.mean()<zo.mean() else 'basamak'
                walls.append((a_,b_,lo,hi,ty,nlow)); WL[ty]=WL.get(ty,0)+np.hypot(*(b_-a_))
with open('p115y_duvar.txt','w') as f:
    from collections import Counter
    cnt=Counter([tuple(np.round(w_[0],2)) for w_ in walls]+[tuple(np.round(w_[1],2)) for w_ in walls])
    for a_,b_,lo,hi,ty,nl in walls:
        e0=int(cnt[tuple(np.round(a_,2))]<2); e1=int(cnt[tuple(np.round(b_,2))]<2)       # zincir ucu -> uc yuzu kapat
        tv_=(b_-a_)/max(np.hypot(*(b_-a_)),1e-9)                                           # zincir uclari 30 cm uzar: kose bosluklari kapanir
        if e0: a_=a_-tv_*0.30
        if e1: b_=b_+tv_*0.30
        f.write('W %s %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %d %d\n'%(ty,a_[0],a_[1],b_[0],b_[1],lo[0]-0.3,lo[1]-0.3,hi[0],hi[1],nl[0],nl[1],e0,e1))

# ---------- istinattan YAPI1 bahcesine (yesile) inen merdiven: kot farkinin en az oldugu duvar parcasi ----------
RISER=0.17; TREAD=0.30; ST_W=1.20; TH=0.30
cand=[]
for a_,b_,lo,hi,ty,nl in walls:
    mid=(a_+b_)/2
    if not gard[0].contains(Point(*(mid+nl*0.6))): continue                 # alcak taraf YAPI1 bahcesi
    if not hard.buffer(0.05).contains(Point(*(mid-nl*0.3))): continue        # yuksek taraf yol (istinatin ustu)
    if (hi-lo).mean()<0.35: continue
    if FPu.distance(Point(*mid))<2.5: continue                                # bina kosesine sikismasin
    if pah.buffer(0.6).contains(Point(*mid)): continue                       # giris pahina degil, duz istinata
    run_=TH+np.ceil((hi-lo).mean()/RISER)*TREAD+0.5
    tip=mid+nl*run_                                                           # merdiven bahceye sigmali, binaya carpmamali
    if not gard[0].buffer(-0.05).contains(LineString([mid+nl*TH,tip]).buffer(ST_W/2,cap_style=2)): continue
    cand.append(((hi-lo).mean(),mid,nl,float(hi.mean()),float(lo.mean())))
stair2=[]
if False and cand:                                                             # istinat->bahce merdiveni istenmedi (kaldirildi)
    hgt,mid,nl,ztop,zbot=min(cand,key=lambda q:q[0])
    n_=int(np.ceil((ztop-zbot)/RISER)); r_=(ztop-zbot)/n_
    tw=np.array([-nl[1],nl[0]])
    for i in range(1,n_):                                                     # i. basamak: ust kottan i rihtim asagi
        d0=TH+(i-1)*TREAD; d1=d0+TREAD
        q=[mid+nl*d0+tw*ST_W/2,mid+nl*d1+tw*ST_W/2,mid+nl*d1-tw*ST_W/2,mid+nl*d0-tw*ST_W/2]
        stair2.append((ztop-i*r_,q))
    print('istinat->bahce merdiveni: (%.2f,%.2f) yuksek %.2f m, %d rihtim x %.1f cm, kosu %.2f m'%(mid[0],mid[1],ztop-zbot,n_,r_*100,(n_-1)*TREAD))
else: print('istinat->bahce merdiveni icin uygun yer bulunamadi')
with open('p115y_basamak.txt','w') as f:
    for zt,q in stair2: f.write('T %.3f %.3f %s\n'%(zbot-0.3,zt,';'.join('%.3f,%.3f'%tuple(p_) for p_ in q)))

# ---------- otopark yerleri ----------
pp=park_poly if park_poly.geom_type=='Polygon' else max(park_poly.geoms,key=lambda q:q.area)
nb=north.intersection(slab_u(xs_park0,xs_park1)); nbc=np.array(nb.coords) if nb.geom_type=='LineString' else np.array(max(nb.geoms,key=lambda g:g.length).coords)
tv=(nbc[-1]-nbc[0])/np.hypot(*(nbc[-1]-nbc[0])); nv_=np.array([tv[1],-tv[0]])          # guneye
best=[]
for off_ in np.arange(0,STALL_W,0.5):
    for q0 in (AISLE,):
        stl=[]; s_=off_
        Ls=np.hypot(*(nbc[-1]-nbc[0]))
        while s_+STALL_W<=Ls+5:
            o0=nbc[0]+tv*s_+nv_*q0
            rc=Polygon([o0,o0+tv*STALL_W,o0+tv*STALL_W+nv_*STALL_D,o0+nv_*STALL_D])
            if pp.buffer(0.01).contains(rc) and rc.distance(FPu)>0.3: stl.append(rc)
            s_+=STALL_W
        if len(stl)>len(best): best=stl
lot_st=[]
rectUN=lambda u0,u1,n0,n1: Polygon([U*u0+NU*n0,U*u1+NU*n0,U*u1+NU*n1,U*u0+NU*n1])
_lc=np.array(lot_poly.exterior.coords)@NU
nn_=_lc.max()
us_=LOT_U[0]+AISLE_L
while nn_>_lc.min():                                           # yoldan apron kadar iceride basla
    nn_-=0.25
    pt_=Point(*(U*(us_+2.5)+NU*nn_))
    if lot_poly.contains(pt_) and shapely.distance(road_poly,pt_)>=LOT_APRON: break
while True:
    rc=rectUN(us_,us_+STALL_D,nn_-STALL_W,nn_)
    if not lot_poly.buffer(0.05).contains(rc): break
    lot_st.append(rc); nn_-=STALL_W
# otoparkin guneybati kosesinden ust kottaki YAPI1 bahcesine merdiven: bati duvar boyunca kuzeye yukselir,
# en ustte duvar ustu = bahce kotu (bahceye gecilir)
k1=_ord[0]; hgt=Z[k1]-Z_LOT
lot_stair=[]
if hgt>0.2:
    n_=int(np.ceil(hgt/RISER)); r_=hgt/n_
    u0_=LOT_U[0]+0.02; u1_=u0_+ST_W
    n_lo=min(np.array(lot_poly.exterior.coords)@NU)
    while not lot_poly.contains(Point(*(U*(u0_+ST_W/2)+NU*(n_lo+0.3)))): n_lo+=0.1
    n_lo+=0.3
    for i_ in range(1,n_):
        lot_stair.append((Z_LOT+i_*r_,[tuple(q) for q in np.array(rectUN(u0_,u1_,n_lo+(i_-1)*TREAD,n_lo+i_*TREAD).exterior.coords)[:-1]]))
    print('otopark->YAPI1 bahce merdiveni: %.2f m, %d rihtim x %.1f cm, kosu %.2f m'%(hgt,n_,r_*100,(n_-1)*TREAD))
with open('p115y_basamak.txt','a') as f:
    for zt,q in lot_stair: f.write('T %.3f %.3f %s\n'%(Z_LOT-0.3,zt,';'.join('%.3f,%.3f'%tuple(p_) for p_ in q)))
print('ara otopark: %d arac, platform +%.2f'%(len(lot_st),Z_LOT+H0))
best=best+lot_st
with open('p115y_park.txt','w') as f:
    for rc in best:
        cc=np.array(rc.centroid.coords[0]); zz=float(final([cc[0]],[cc[1]])[0])
        f.write('S %.3f %s\n'%(zz+0.03,';'.join('%.3f,%.3f'%tuple(q) for q in np.array(rc.exterior.coords)[:-1])))
with open('p115y_merdiven.txt','w') as f:
    for s0,s1,nst in stairs:
        for j in range(nst+1):
            s=s0+(s1-s0)*j/nst; pt=np.array(axis.interpolate(s).coords[0]); a_=np.array(axis.interpolate(max(s-0.2,0)).coords[0]); b_=np.array(axis.interpolate(min(s+0.2,L)).coords[0])
            tv_=(b_-a_)/np.hypot(*(b_-a_)); nn=np.array([-tv_[1],tv_[0]])
            f.write('M %.3f %.3f %.3f %.3f %.3f\n'%(*(pt+nn*W/2),*(pt-nn*W/2),float(zax(s))+0.03))
# etiketler
with open('p115y_etiket.txt','w') as f:
    for k in range(3):
        cc=np.array(fps[k].centroid.coords[0])
        f.write('E %.3f %.3f %.3f %s|+-0.00 = +%.2f|zemin kat esigi = +%.2f (s=%.2f)\n'%(cc[0],cc[1],Lk[k]+0.3,names[k],Z[k]+H0,Lk[k]+H0,sill[k]))
    for s,lab in ((s_park0*0.5,'ARAC YOLU'),((s_park0+s_park1)/2,'OTOPARK %d arac'%len(best)),((s_park1+L)/2,'YAYA YOLU')):
        pt=np.array(axis.interpolate(s).coords[0]); f.write('E %.3f %.3f %.3f %s\n'%(pt[0],pt[1],float(zax(s))+1.5,lab))

# ---------- rapor ----------
print('giris (kamu yolu) kot +%.2f'%(za[0]+H0))
for k in range(3): print('%s: +-0.00 +%.2f | zemin kat esigi +%.2f (s=%.2f) | bahce %.0f m2'%(names[k],Z[k]+H0,Lk[k]+H0,sill[k],gard[k].area-fps[k].area if gard[k].contains(fps[k].representative_point()) else gard[k].area))
for zn_ in ('yol','otopark','yaya'):
    m=zone==zn_; ii=np.where(m)[0]
    sl=np.abs(np.diff(za[ii]))/np.diff(st[ii]) if len(ii)>1 else np.array([0])
    print('%s: %.0f m, kot %.2f..%.2f, egim maks %%%.1f'%(zn_,st[ii].max()-st[ii].min(),za[ii].min()+H0,za[ii].max()+H0,sl.max()*100))
print('otopark: %d arac, alan %.0f m2'%(len(best),park_poly.area))
for dd in doors:
    zr=float(zax(axis.project(Point(*dd['c'])))); k=dd['k']
    print('  kapi %s %s: esik +%.2f, onundeki yol/zemin %s'%(names[k],'kuzey' if dd['north'] else 'yan  ',Lk[k]+H0,('+%.2f (fark %.2f)'%(zr+H0,Lk[k]-zr)) if dd['north'] else 'bahce +%.2f (%d basamak)'%(Z[k]+H0,int(np.ceil(sill[k]/0.17)) if sill[k]>0.05 else 0)))
print('merdiven: %s'%(', '.join('%.0f-%.0f m arasi %d basamak'%(a_,b_,n_) for a_,b_,n_ in stairs) or 'yok'))
print('duvar:',{k:round(v) for k,v in WL.items()},'| sokak dogal zeminden sapma maks %.2f m'%np.nanmax(np.abs(za-zn)))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(16,5))
ax.plot(*P.exterior.xy,'k-',lw=1)
for gg in gard:
    for pg in ([gg] if gg.geom_type=='Polygon' else gg.geoms): ax.fill(*pg.exterior.xy,color='#7c5',alpha=0.7)
for pp_,cl in ((road_poly,'#444'),(park_poly,'#999'),(walk_poly,'#cb9')):
    for pg in ([pp_] if pp_.geom_type=='Polygon' else pp_.geoms): ax.fill(*pg.exterior.xy,color=cl)
for fp in fps: ax.fill(*fp.exterior.xy,color='#e43')
for rc in best: ax.plot(*rc.exterior.xy,'w-',lw=0.7)
for a_,b_,lo,hi,ty,nl in walls: ax.plot([a_[0],b_[0]],[a_[1],b_[1]],'m-' if ty=='istinat' else ('c-' if ty.startswith('dolgu') else 'y-'),lw=1.5)
for dd in doors: ax.plot(*dd['c'],'k*' if dd['north'] else 'b*')
ax.set_aspect('equal'); plt.savefig('p115y_onizleme.png',dpi=110,bbox_inches='tight')
with open('p115y_taban.txt','w') as f:
    for k in range(3):
        f.write('B %s %.3f %.3f %s\n'%(names[k],Z[k]-0.05,Lk[k],';'.join('%.3f,%.3f'%tuple(q) for q in np.array(fps[k].exterior.coords)[:-1])))
