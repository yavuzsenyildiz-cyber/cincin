# P116: 115 ile ayni kurgu - kitlelerin kuzeyinde (115 siniri boyunca) arac yolu, dogu ucta otopark, bahceler guneyde.
# En az hafriyat/istinat: bahce +-0.00 = tabii zemin ortalamasi (tesviye.json), kitle zemini +-0.00+20 cm, esik +-0.00+50 cm.
# Kotlandirma (Plansiz Alanlar Imar Yon.): bahceler +-0.00 = bina kose tabii zemin ortalamasi; zemin kat esigi +-0.00 + s, s<=1.20.
# Yol <=%12, otopark <=%5, yaya yolu %8 (asarsa merdiven). Kuzey kapilar yolla ayni kotta; sokak hicbir yerde dosemenin ustune cikmaz.
# Girdi: pk_mesh.txt, pk_rings.txt, tesviye.json, yollar.json, git HEAD kitle_dump.json (kapilar)
# Cikti: p116y_mesh.txt (ucgen basina malzeme), p116y_duvar.txt, p116y_park.txt, p116y_etiket.txt, p116y_merdiven.txt
from scipy.interpolate import LinearNDInterpolator
import numpy as np, json, shapely, subprocess
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union, nearest_points
from shapely import contains_xy
from matplotlib.tri import Triangulation, LinearTriInterpolator
from scipy.spatial import Delaunay
from scipy.optimize import linprog
H0=105.07; W=3.0; S_ROAD=0.12; S_PARK=0.05; S_WALK=0.05; S_STAIR=0.50; SMAX_SILL=1.20; DOOR_GAP=0.02
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
    if t[0]=='R' and t[1]=='116': ring=[tuple(map(float,p.split(',')[:2])) for p in ' '.join(t[2:]).split(';')]
P=Polygon(ring)                                           # 116: kuzey sinir 115 ile ortak, kaydirma yok
KUZEY_KAYMA=0.0
# ---- komsu parsel tasarimi (varsa): ortak sinirda duvarlar yuksek tarafca kurulur, disaridaki kot komsunun tasarim kotundan okunur ----
import os
import komsu
NB_PFX='p115y_'
SHARED=LineString(ring[0:2])                                    # birincil komsu ile ortak sinir
NBS=[n_ for n_ in (komsu.yukle('p115y_',LineString(ring[0:2])),komsu.yukle('p117y_',LineString([ring[4],ring[5]]))) if n_ is not None]
_nb0=next((n_ for n_ in NBS if n_['pfx']==NB_PFX),None)
NB_POLY=_nb0['poly'] if _nb0 else None; nbz=_nb0['z'] if _nb0 else None
NB_ALL=unary_union([n_['poly'] for n_ in NBS]) if NBS else None                      # tum komsu tasarim alanlari
_sh=[n_['shared'] for n_ in NBS if n_['shared'] is not None]
SHARED_ALL=unary_union(_sh) if _sh else None                                          # komsularla ortak sinirlar
J=json.load(open('tesviye.json'))
ids=[k for k,n in enumerate(J['names']) if n.startswith('P116')]
names=[J['names'][k] for k in ids]; Z=np.array([J['Z'][k] for k in ids]); fps=[Polygon(J['fp'][k]) for k in ids]
# kitle zemini (zb) = +-0.00 + 20 cm; esik = +-0.00 + 50 cm (subasman). Bahce zb'de.
Z=Z+0.20
# yapi ekseni: bina uzun kenari yonu (duvarlar/otopark buna gore dik ve paralel)
_c=np.array(fps[0].minimum_rotated_rectangle.exterior.coords); _e=[(_c[i+1]-_c[i]) for i in range(4)]
U=max(_e,key=lambda v:np.hypot(*v)); U=U/np.hypot(*U); U=U if U[0]>0 else -U; NU=np.array([-U[1],U[0]])   # NU kuzeye
uc=lambda p_: float(np.dot(np.asarray(p_,float)[:2],U))
def slab_u(u0,u1):
    u0=max(u0,-1e4); u1=min(u1,1e4)
    return Polygon([U*u0-NU*1e3,U*u1-NU*1e3,U*u1+NU*1e3,U*u0+NU*1e3])
def urange(poly): c_=np.array(poly.exterior.coords)@U; return float(c_.min()),float(c_.max())
# tasarim siniri: son evin 2 m doguna 18 m otopark/donus alani; ucu aratada kalan dar uc kisim dogal birakilir (hafriyat/istinat en az)
PARK_UZUN=18.0
U_END=max(urange(f_)[1] for f_ in fps)+2.0+PARK_UZUN
P=P.intersection(slab_u(-1e4,U_END)).buffer(0)
# gercek kitle taban izleri: kitle_plan.json kutlelerinin (bbox) bina eksenine donuk dikdortgeni (L x D, bbox sagdan hesaplanir)
real_fp=[]
_th=float(np.arctan2(U[1],U[0]))
for _p in json.load(open('kitle_plan.json')):
    if not _p['yapi'].startswith('P116'): continue
    _b=_p['bounds']; _W=_b[3]-_b[0]; _H=_b[4]-_b[1]
    _D=(_H-_W*np.sin(_th)*0)/1.0
    # bbox_w = L cos + D sin ; bbox_h = L sin + D cos
    _M=np.array([[np.cos(_th),np.sin(_th)],[np.sin(_th),np.cos(_th)]]); _L,_D=np.linalg.solve(_M,[_W,_H])
    _x0=_b[0]+_D*np.sin(_th); _y0=_b[1]
    _P0=np.array([_x0,_y0]); _P1=_P0+_L*U; _P3=_P0+_D*NU; _P2=_P1+_P3-_P0
    real_fp.append(Polygon([_P0,_P1,_P2,_P3]))
# gercek izler yol tarafinda cephe (duvar) hattinda kesilir: kapi onu basamak cikintilari izi buyutmesin
def _kes(r):
    k_=int(np.argmin([r.distance(f_) for f_ in fps])); nf_=float(np.max(np.array(fps[k_].exterior.coords)@NU))+0.01
    return r.intersection(Polygon([U*-1e4+NU*(nf_-1e3),U*1e4+NU*(nf_-1e3),U*1e4+NU*nf_,U*-1e4+NU*nf_]))
real_fp=[_kes(r) for r in real_fp]
real_fp=[r if r.geom_type=='Polygon' else max(r.geoms,key=lambda q:q.area) for r in real_fp if not r.is_empty]
FPu=unary_union(fps+real_fp)
# yol yalniz evin YOL CEPHESINDE (cephe hattinin 30 cm icinden kuzeye) iz icine girer: kose sivrisi havada kalmaz,
# evin yanlarinda/bahce tarafinda yol ize sizmaz (bahcede bosluk olmaz)
_nf=[]
for f_ in fps:
    nf_=float(np.max(np.array(f_.exterior.coords)@NU))
    u0_,u1_=urange(f_)
    _nf.append(Polygon([U*(u0_-3)+NU*(nf_-0.30),U*(u1_+3)+NU*(nf_-0.30),U*(u1_+3)+NU*(nf_+1e3),U*(u0_-3)+NU*(nf_+1e3)]))
FPu_ic=FPu.difference(unary_union(_nf))

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
north=LineString(ring[0:2]).intersection(slab_u(-1e4,U_END))   # kuzey sinir (115 ile ortak) tasarim ucuna kadar
off=north.offset_curve(-W/2,join_style=2)
if off.geom_type!='LineString': off=max(off.geoms,key=lambda g:g.length)
oc=np.array(off.coords); oc=oc[np.argsort(oc[:,0])] if oc[0,0]>oc[-1,0] else oc
sw=LineString([ring[-1],ring[0]])                    # guneybati kenar = kamu yolu (18.35,76.94)->(10.48,85.57)
# giris: guneybati kenarda, kotu YAPI1 bahcesine en yakin nokta (bina batisinda kalsin)
cand=[sw.interpolate(f_,normalized=True) for f_ in np.linspace(0.05,0.95,37)]
# giris: kamu yolu kenarinda, kuzey uca (115 siniri) en yakin ve yolun ev kotuna 12%'yi asmadan inebilecegi nokta
_ufac=min(urange(f_)[0] for f_ in fps)-uc(oc[0])
def _gerek(q):                                                             # q'dan ilk evin cephesine mesafe boyunca inis payi
    d_=q.distance(Point(*oc[0]))+_ufac
    return float(nat(q.x,q.y))-(float(Z[0])+0.30+0.9*S_ROAD*d_)
_ok=[q for q in sorted(cand,key=lambda q:q.distance(Point(*oc[0]))) if _gerek(q)<=0]
Jp=_ok[0] if _ok else min(cand,key=lambda q:_gerek(q))
print('giris noktasi (%.1f,%.1f) kamu yolu kotu +%.2f'%(Jp.x,Jp.y,float(nat(Jp.x,Jp.y))+H0))
start_i=int(np.argmin(np.abs(oc[:,0]-22.0)))
axis_pts=[np.array([Jp.x,Jp.y])]+[p for p in oc if p[0]>=oc[start_i,0]]
axis=LineString(axis_pts)
L=axis.length; st=np.arange(0,L,1.0); st=np.r_[st,L] if st[-1]<L-0.3 else st
SP=np.array([axis.interpolate(s).coords[0] for s in st]); zn=nat(SP[:,0],SP[:,1])
def s_at_x(x): return st[int(np.argmin(np.abs(SP[:,0]-x)))]
xr=lambda k: (fps[k].bounds[0],fps[k].bounds[2])
_ord0=sorted(range(3),key=lambda k:fps[k].bounds[0])
s_park0=s_at_x(xr(_ord0[2])[1]+2.0); s_park1=float(st[-1])
zone=np.where(st<s_park0,'yol','otopark')

# ---------- seritler ----------
band=north.buffer(W,cap_style=2,join_style=2).intersection(P)          # kuzey sinirdan W icerisi
from shapely.affinity import translate
north_ext=unary_union([unary_union([translate(fp,0,dy) for dy in np.arange(0,15,0.25)]).intersection(P).difference(fp) for fp in fps])
band=unary_union([band,north_ext]).buffer(0.01).buffer(-0.01)      # cephe ile kuzey sinir arasi tamamen sert zemin (kapi onu = yol kotu)
entry=LineString([axis_pts[0],axis_pts[1]]).buffer(W/2,cap_style=2).intersection(P)
xs_park0=uc(SP[st==s_park0][0]); xs_park1=uc(SP[st==s_park1][0])
west_fill=P.intersection(slab_u(-1e4,uc(axis_pts[1])-1.0))          # giris ile kuzey serit arasi bosluk -> rampa
# 116: evler arasi bosluk 4.3 m (yol genisletme yok), ara otopark yok, yaya yolu yok
_ord=sorted(range(3),key=lambda k:urange(fps[k])[0])
u_gap0=urange(fps[_ord[0]])[1]; u_gap1=urange(fps[_ord[1]])[0]
road_poly=unary_union([band.intersection(slab_u(-1e4,xs_park0)),entry,west_fill]).buffer(0.01).buffer(-0.01).difference(FPu_ic)
PARK_KIS=3.0     # otopark bati ucta 3 m kisalir (YAPI6 bahcesi buyur); kuzeydeki W serit gecis icin yol/otopark kalir
park_poly=unary_union([band.intersection(slab_u(xs_park0,1e4)),P.intersection(slab_u(xs_park0+PARK_KIS,1e4))]).difference(FPu_ic)
_k3=-1; U_CUT=1e5
walk_poly=Polygon()
LOT_W=10.5; LOT_APRON=2.5; AISLE_L=5.5; LOT_U=(0.0,0.0)
lot_poly=Polygon()
for nm_,pp in (('yol',road_poly),('otopark',park_poly)):
    if pp.geom_type!='Polygon': print('uyari:',nm_,'parcali',pp.geom_type)

# ---------- LP: eksen kotlari + esik paylari ----------
ns=len(st); nS=3; nv=ns+nS+ns+(ns-1)+2*nS      # z, s_k, |z-zn| yardimci, merdiven asimi, zb_k (bina taban kotu), |zb-Znat| yardimci
iZ=ns+nS+ns+(ns-1); iD=iZ+nS
Z0=Z.copy()                                      # tabii zemin ortalamasindan turetilen oneri (+-0.00 + 20 cm)
DZ_MAX=1.2; C_BINA=5.0                           # bina kotu +-1.2 m oynayabilir; sapma maliyeti (m3 esdegeri) yolun 100 katindan fazla
A=[];b=[];Aeq=[];beq=[]
c=np.zeros(nv); c[ns+nS:ns+nS+ns]=0.05; c[ns+nS+ns:ns+nS+ns+ns-1]=3.0; c[iD:iD+nS]=C_BINA
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
    row=zrow(dd['c']); row[iZ+dd["k"]]=-1; row[ns+dd["k"]]=-1; Aeq.append(row); beq.append(0.0)                 # kapi onunde yol = subasman alti (zb)
for i in range(ns):                                                                             # cephe boyunca yol esigi gecmesin
    for k in range(3):
        bx=fps[k].bounds                                                                        # yalniz cephenin yaninda (uclarin otesinde degil)
        if bx[0]-0.5<=SP[i][0]<=bx[2]+0.5 and Point(*SP[i]).distance(fps[k])<W/2+FACADE_REACH:   # yol ekseni ile cephe arasi genis olabilir
            row=np.zeros(nv); row[i]=1; row[iZ+k]=-1; row[ns+k]=-1; A.append(row); b.append(0.0)             # cephe boyunca yol subasman altini gecmez (subasman tamamen gorunur)
# 115'in otopark platformu 116 yolunun hemen kuzeyinde: yol ile otopark ayni kotta olsun (ortak sinirda kot farki/duvar kalmaz)
_padc=[]
if NB_POLY is not None and os.path.exists(NB_PFX+'park.txt'):
    from shapely.ops import unary_union as _uu
    _st=sorted([Polygon([tuple(map(float,q_.split(','))) for q_ in l_.split()[2].split(';')]) for l_ in open(NB_PFX+'park.txt')],key=lambda q_:q_.centroid.x)
    _cl=[[_st[0]]]
    for q_ in _st[1:]:
        (_cl[-1] if q_.bounds[0]-_cl[-1][-1].bounds[2]<3.0 else _cl.append([])) if False else None
        if q_.bounds[0]-_cl[-1][-1].bounds[2]<3.0: _cl[-1].append(q_)
        else: _cl.append([q_])
    _big=max(_cl,key=len)                                                  # en buyuk otopark kumesi (yola bitisik platform)
    _xmin,_xmax=min(q_.bounds[0] for q_ in _big)+0.5,max(q_.bounds[2] for q_ in _big)
    for i in range(ns):
        pn=SP[i]+NU*(W/2+0.4)
        if _xmin<=pn[0]<=_xmax and NB_POLY.contains(Point(*pn)):
            zq_=float(nbz([pn[0]],[pn[1]])[0])
            if not np.isnan(zq_) and i>0:
                _padc.append((i,zq_))
bounds=[(None,None)]*ns+[(0,SMAX_SILL)]*nS+[(0,None)]*ns+[(0,None)]*(ns-1)+[(Z0[k_]-DZ_MAX,Z0[k_]+DZ_MAX) for k_ in range(nS)]+[(0,None)]*nS
for k_ in range(nS):                                                   # |zb-Z0| yardimcisi
    r1=np.zeros(nv); r1[iZ+k_]=1; r1[iD+k_]=-1; A.append(r1); b.append(Z0[k_])
    r2=np.zeros(nv); r2[iZ+k_]=-1; r2[iD+k_]=-1; A.append(r2); b.append(-Z0[k_])
# esikler modeldeki kitle kapi kotlarina sabit (kitleler yerinde kalir): yerel kot +6.60 / +3.10 / +0.05
for k in range(nS): bounds[ns+k]=(0.30,0.30)                           # esik = zb + 30 cm (zb ile 1 basamak)
bounds[0]=(zn[0],zn[0])                                                                         # kamu yoluna baglanti
_A0=list(A); _b0=list(b)
for PAD_TOL in (0.02,0.10,0.20,0.30,0.45,0.70,None):                 # komsu otopark kotuna en yakin uygulanabilir yol
    A=list(_A0); b=list(_b0)
    if PAD_TOL is not None:
        for i_,zq_ in _padc:
            row=np.zeros(nv); row[i_]=1; A.append(row); b.append(zq_+PAD_TOL); A.append(-row); b.append(-(zq_-PAD_TOL))
    res=linprog(c,A_ub=np.array(A),b_ub=np.array(b),A_eq=np.array(Aeq) if Aeq else None,b_eq=np.array(beq) if Aeq else None,bounds=bounds,method='highs')
    if res.status==0: break
if _padc: print('115 otopark ile yol kot farki <= %s m'%PAD_TOL)
if res.status!=0:
    print('kapi esitligi saglanamadi, kapilar yumusatiliyor:',res.message)
    for row,bq in zip(Aeq,beq): A+=[row,-row]; b+=[bq+0.6,-(bq-0.6)]     # +-0.6 m tolerans
    res=linprog(c,A_ub=np.array(A),b_ub=np.array(b),bounds=bounds,method='highs')
assert res.status==0,res.message
x=res.x; za=x[:ns]; sill=x[ns:ns+nS]
Z=np.round(x[iZ:iZ+nS],3); Lk=Z+sill                                  # bina tabani kotlari LP sonucu
print('bina taban kotlari (zb): '+', '.join('%s %.2f (oneri %.2f, sapma %+.2f)'%(names[k_],Z[k_]+H0,Z0[k_]+H0,Z[k_]-Z0[k_]) for k_ in range(nS)))
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
hard=unary_union([road_poly,park_poly,walk_poly,lot_poly]).buffer(0.03,join_style=2).buffer(-0.03,join_style=2)   # kilcal bosluklar kapanir
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
hard=unary_union([road_poly,park_poly,walk_poly,lot_poly]).buffer(0.03,join_style=2).buffer(-0.03,join_style=2)   # kilcal bosluklar kapanir
for j,k in enumerate(order): gard[k]=P.intersection(slab_u(cuts[j],cuts[j+1])).difference(hard)
# bahce sivrileri (1 m'den dar seritler) yola katilir: yol ustunde anlamsiz duvar kutulari olusmasin
sliv=[]
for k in range(3):
    g_=gard[k]; gc_=g_.buffer(-0.5,join_style=2).buffer(0.5,join_style=2).intersection(g_)
    sl=g_.difference(gc_).difference(FPu)
    if not sl.is_empty and sl.area>0.01: sliv.append(sl)
for j,k in enumerate(order):                                   # evin kuzey cephe hattinin otesindeki (yol tarafi) bahce parcalari
    nmax=float(np.max(np.array(fps[k].exterior.coords)@NU))      # cephe (duvar) hatti; kapi onu basamaklari degil
    kuz=Polygon([U*-1e4+NU*nmax,U*1e4+NU*nmax,U*1e4+NU*(nmax+1e3),U*-1e4+NU*(nmax+1e3)])
    ky=gard[k].intersection(kuz).difference(FPu)
    if k==_k3: ky=ky.difference(slab_u(U_CUT,1e4))                              # son bolumun on bahcesi korunur
    if ky.area>0.05: sliv.append(ky); print('%s cephe onu bahce parcasi yola: %.1f m2'%(names[k],ky.area))
road_ana=road_poly                                                              # ana tasit yolu (otopark girisi egimi buna gore)
if sliv:
    _sv=unary_union(sliv)
    _sv_lot=unary_union([g_ for g_ in getattr(_sv,'geoms',[_sv]) if g_.distance(lot_poly)<0.1]) if not _sv.is_empty else Polygon()
    if not _sv_lot.is_empty:                                                     # otoparka bitisik sivriler otoparka (yola degil)
        lot_poly=unary_union([lot_poly,_sv_lot]).buffer(0.01).buffer(-0.01)
        if lot_poly.geom_type!='Polygon': lot_poly=max(lot_poly.geoms,key=lambda q:q.area)
        sliv=[_sv.difference(_sv_lot)]
    print('yola katilan bahce sivrisi: %.1f m2'%unary_union(sliv).area)
    road_poly=unary_union([road_poly]+sliv).buffer(0.01).buffer(-0.01)
    hard=unary_union([road_poly,park_poly,walk_poly,lot_poly]).buffer(0.03,join_style=2).buffer(-0.03,join_style=2)   # kilcal bosluklar kapanir
    for j,k in enumerate(order): gard[k]=P.intersection(slab_u(cuts[j],cuts[j+1])).difference(hard)

# ---------- otoparktan bahcelere gomulu merdivenler (guney uclarda, bahceye dogru) ----------
RISER=0.17; TREAD=0.30; ST_W=1.20
gm_stairs=[]; gm_zones=[]; gm_info=[]      # (poly, ramp fonk) ve basamak bloklari
_pk=park_poly if park_poly.geom_type=='Polygon' else max(park_poly.geoms,key=lambda q:q.area)
Z_LOT=float(za[int(np.argmin([abs(uc(q)-(LOT_U[0]+AISLE_L/2)) for q in SP]))])     # ara otopark duz platform kotu
for u_e,sg_,k,mod_ in ((xs_park0+PARK_KIS,-1,order[2],'guney'),):
    # park kenarinin guney ucu
    _ln=LineString([U*u_e+NU*-1e3,U*u_e+NU*1e3]).intersection(P)
    _c=np.array(_ln.coords) if _ln.geom_type=='LineString' else np.array(max(_ln.geoms,key=lambda g:g.length).coords)
    if mod_ in ('guney','lot'): n_s=float((_c@NU).min())+1.5               # guney sinir duvarindan 1.5 m iceride
    else:                                                                   # yaya seridinin ortasinda
        _bl=LineString([U*(u_e+0.05)+NU*-1e3,U*(u_e+0.05)+NU*1e3]).intersection(band); _bc=np.array(_bl.coords) if _bl.geom_type=='LineString' else np.array(max(_bl.geoms,key=lambda g:g.length).coords)
        n_s=float((_bc@NU).mean())-ST_W/2
    n0=n_s; n1=n_s+ST_W
    pp_=U*(u_e-sg_*0.3)+NU*(n0+ST_W/2)
    zp=Z_LOT if mod_=='lot' else float(zax(axis.project(Point(*pp_))))
    h_=Z[k]-zp; ns_=max(int(np.ceil(abs(h_)/RISER)),1); r_=h_/ns_; run=(ns_-1)*TREAD
    gzone=Polygon([U*u_e+NU*n0,U*(u_e+sg_*run)+NU*n0,U*(u_e+sg_*run)+NU*n1,U*u_e+NU*n1])
    if gzone.area>0 and not gzone.is_valid: gzone=gzone.buffer(0)
    for i_ in range(1,ns_):
        d0=(i_-1)*TREAD; d1=i_*TREAD
        q=Polygon([U*(u_e+sg_*d0)+NU*n0,U*(u_e+sg_*d1)+NU*n0,U*(u_e+sg_*d1)+NU*n1,U*(u_e+sg_*d0)+NU*n1])
        zt_=zp+i_*r_; zb_=min(zp,Z[k])-0.3
        gm_stairs.append((zb_,zt_,[tuple(c) for c in np.array(q.exterior.coords)[:-1]]))
    if h_>0:          # bahce yuksek: merdiven bahceye gomulu (bahceden oyulur; yanlarda istinat)
        def _ramp(x,y,u_e=u_e,sg_=sg_,zp=zp,r_=r_):
            d=np.clip(((np.c_[x,y]@U)-u_e)*sg_,0,None); return zp+d/TREAD*r_-0.02
        gm_zones.append((gzone,_ramp)); gm_info.append((u_e,sg_,n0,n1,zp,Z[k],run))
        gard[k]=gard[k].difference(gzone)
    print('%s bahcesine merdiven: %s %.2f m, %d rihtim x %.1f cm, kosu %.2f m'%(names[k],'cikis (gomulu)' if h_>0 else 'inis',abs(h_),ns_,abs(r_)*100,run))

# ---------- arazi ----------

def _feat_z0(x,y):
    s=np.array([axis.project(Point(a_,b_)) for a_,b_ in zip(x,y)]); return zax(s)
def feat_z(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float)           # 5 noktali ortalama (r=1 m): eksen izdusumu sicramalari/keskin kirik yok
    z_=(_feat_z0(x,y)+_feat_z0(x+1,y)+_feat_z0(x-1,y)+_feat_z0(x,y+1)+_feat_z0(x,y-1))/5.0
    return pad_blend(x,y,z_)
PAD_BL=3.0
def pad_blend(x,y,z_):                                                   # 115 otoparki onunde yol yuzeyi ortak sinirda otopark kotuna egimle baglanir (duvar/basamak yok)
    if not _padc: return z_
    z_=np.array(z_,float); pts=shapely.points(x,y); d=shapely.distance(SHARED,pts)
    wx=np.clip(np.minimum(x-_xmin,_xmax-x)/1.5+1.0,0,1)
    w=np.clip(1-d/PAD_BL,0,1)*wx; m=np.where(w>0)[0]
    if len(m)==0: return z_
    pr=np.array([SHARED.interpolate(SHARED.project(Point(x[i],y[i]))).coords[0] for i in m])+NU*0.3
    zt=nbz(pr[:,0],pr[:,1]); ok=~np.isnan(zt)
    w_=w[m][ok]; w_=w_*w_*(3-2*w_)
    z_[m[ok]]=z_[m[ok]]+w_*(zt[ok]-z_[m[ok]])
    return z_
def final(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float); f=nat(x,y)
    if 'nat_agiz' in globals():
        o_=~contains_xy(P,x,y)
        if o_.any(): f[o_]=nat_agiz(x[o_],y[o_])
    for n_ in NBS:                                                                     # komsu parselin tasarim kotu
        mn=contains_xy(n_['poly'],x,y)&~contains_xy(P,x,y)
        if mn.any():
            zz=n_['z'](x[mn],y[mn]); ix=np.where(mn)[0]; okm=~np.isnan(zz); f[ix[okm]]=zz[okm]
    for k,g in enumerate(gard): f[contains_xy(g,x,y)]=Z[k]
    m=contains_xy(hard,x,y)
    if m.any(): f[m]=feat_z(x[m],y[m])
    m=contains_xy(lot_poly,x,y)
    if m.any(): f[m]=lot_z(x[m],y[m])
    for zn_,rf_ in gm_zones:
        m=contains_xy(zn_,x,y)
        if m.any(): f[m]=rf_(x[m],y[m])
    for k,fp in enumerate(fps): f[contains_xy(fp,x,y)]=Z[k]-0.05
    return f
Z_LOT=None
def lot_z(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float)
    d=shapely.distance(road_ana,shapely.points(x,y)); w_=np.clip(1-d/LOT_APRON,0,1)
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
for zn_,rf_ in gm_zones: parts.append((zn_,'kaldirim',rf_))
for j_,k in enumerate(order):                                   # bina izleri: yol tarafi (kuzey) kaldirim, bahce tarafi cim
    fz=FPu.intersection(P).intersection(slab_u(cuts[j_],cuts[j_+1])).difference(hard)
    if fz.is_empty: continue
    _c=np.array(fps[k].exterior.coords); nf=float((_c@NU).max()); u0f,u1f=float((_c@U).min()),float((_c@U).max())
    # kaldirim: yalniz evin onu - cephe hatti ile yol arasi, evin boyu kadar; evin yanlari ve bahce tarafi yesil
    kald=fz.intersection(Polygon([U*u0f+NU*(nf-0.05),U*u1f+NU*(nf-0.05),U*u1f+NU*(nf+1e3),U*u0f+NU*(nf+1e3)]))
    if k==_k3: kald=kald.difference(slab_u(U_CUT,1e4))
    parts.append((kald,'kaldirim',const(Z[k])))
    parts.append((fz.difference(kald),'cim',const(Z[k])))
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
# parsel icinde hicbir alana dusmeyen artik parcalar (birlesim sivrileri) doldurulur: zeminde bosluk kalmaz
_kap=unary_union([q for q,_,_ in parts if not q.is_empty])
_art=P.difference(_kap)
for g_ in getattr(_art,'geoms',[_art]):
    if g_.geom_type=='Polygon' and g_.area>1e-5:
        tg_='asfalt' if hard.buffer(0.05).contains(g_.representative_point()) else 'cim'
        parts.append((g_,tg_,final))
# kisitli ucgenleme: alan 1 m karelere bolunur, her kare kendi sinirina oturan ucgenlerle tam doldurulur (bosluk/tasma yok)
_vid={}
def tri_cdt(poly,tag,zf,step=1.0):
    if poly.is_empty: return
    x0_,y0_,x1_,y1_=poly.bounds
    cells=[]
    for gx_ in np.arange(np.floor(x0_),x1_,step):
        for gy_ in np.arange(np.floor(y0_),y1_,step):
            c_=poly.intersection(box(gx_,gy_,gx_+step,gy_+step))
            for g_ in getattr(c_,'geoms',[c_]):
                if g_.geom_type=='Polygon' and g_.area>1e-6: cells.append(shapely.segmentize(g_,0.5))
    if not cells: return
    tris=shapely.constrained_delaunay_triangles(shapely.GeometryCollection(cells) if len(cells)>1 else cells[0])
    pts=[]; idx=[]
    for t_ in getattr(tris,'geoms',[tris]):
        cc=np.array(t_.exterior.coords)[:3]
        if abs((cc[1,0]-cc[0,0])*(cc[2,1]-cc[0,1])-(cc[1,1]-cc[0,1])*(cc[2,0]-cc[0,0]))<1e-8: continue
        pts.append(cc)
    if not pts: return
    pts=np.array(pts); flat=pts.reshape(-1,2)
    zz=zf(flat[:,0],flat[:,1])
    base=sum(len(v_) for v_ in VV); loc={}; A3=[]
    ids=[]
    for (x_,y_),z_ in zip(flat,zz):
        key=(round(x_,3),round(y_,3))
        if key not in loc: loc[key]=len(A3); A3.append((x_,y_,z_))
        ids.append(loc[key])
    ids=np.array(ids).reshape(-1,3)
    A3=np.array(A3)
    q2=A3[:,:2]; u=q2[ids[:,1]]-q2[ids[:,0]]; w=q2[ids[:,2]]-q2[ids[:,0]]; cr=u[:,0]*w[:,1]-u[:,1]*w[:,0]
    ids[cr<0]=ids[cr<0][:,[0,2,1]]
    VV.append(A3); FF.extend((t_+base,tag) for t_ in ids)
for poly,tag,zf in parts:
    for pg in ([poly] if poly.geom_type=='Polygon' else [q for q in getattr(poly,'geoms',[]) if q.geom_type=='Polygon']):
        tri_cdt(pg,tag,zf)
# parsel disi: dogal arazi
outer=V[contains_xy(region,V[:,0],V[:,1])&~contains_xy(P,V[:,0],V[:,1])][:,:3]
far=V[~contains_xy(region,V[:,0],V[:,1])][:,:3]
# giris agzi disinda dogal arazi yola baglanir (yol kenari havada kalmasin): 5 m icinde yol kotundan dogal kota
opening=P.exterior.intersection(unary_union([mouth.buffer(0.3),sw.buffer(0.2).intersection(Jp.buffer(W/2+2.0)),sw.buffer(0.2).intersection(road_poly.buffer(0.3))])).difference(unary_union(gard).buffer(0.3))   # yolun bati kenara degdigi her yer arac girisi
AGIZ_D=5.0
_cP=np.array(P.centroid.coords[0])
def nat_agiz(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float); z0=nat(x,y)
    if opening.is_empty: return z0
    d=shapely.distance(opening,shapely.points(x,y)); w=np.clip(1-d/AGIZ_D,0,1); m=np.where(w>0)[0]
    for i_ in m:
        q=nearest_points(opening,Point(x[i_],y[i_]))[0]; qi=np.array([q.x,q.y]); qi=qi+(_cP-qi)/np.hypot(*(_cP-qi))*0.1   # parselin hemen ici = yol kotu
        zr=float(final([qi[0]],[qi[1]])[0])
        if not np.isnan(zr): z0[i_]=w[i_]*zr+(1-w[i_])*(z0[i_] if not np.isnan(z0[i_]) else zr)
    return z0
outer[:,2]=nat_agiz(outer[:,0],outer[:,1])
# 116: dogal arazi disi (rim) 115 tarafindan uretilir (cift yuzey/ust uste binme olmasin)
# ---------- kenar perdeleri: her alanin kenarindan alcak komsuya kadar dikey yuzey (bosluk/aciklik kalmaz) ----------
# Duvarlarin 1 cm gerisinde: duvar olan yerde gorunmez, olmayan her kosede acikligi kapatir. Ev izi kenarlari tas, digerleri beton.
nperde=0
for poly,tag,zf in parts:
    tas_=tag=='kaldirim' or (not poly.is_empty and poly.intersection(FPu).area>0.5*poly.area)
    for pg in ([poly] if poly.geom_type=='Polygon' else [q for q in getattr(poly,'geoms',[]) if q.geom_type=='Polygon']):
        for rr in [pg.exterior]+list(pg.interiors):
            c_=np.array(shapely.segmentize(rr,0.5).coords)
            if len(c_)<3: continue
            a_=c_[:-1]; b_=c_[1:]; d_=b_-a_; L_=np.hypot(d_[:,0],d_[:,1]); ok=L_>1e-4
            a_,b_,d_,L_=a_[ok],b_[ok],d_[ok],L_[ok]
            nn=np.c_[-d_[:,1],d_[:,0]]/L_[:,None]; mid=(a_+b_)/2
            ic=contains_xy(pg,mid[:,0]+nn[:,0]*0.02,mid[:,1]+nn[:,1]*0.02); nn[~ic]*=-1      # ice dogru normal
            zs_a=zf(a_[:,0],a_[:,1]); zs_b=zf(b_[:,0],b_[:,1])
            oa=a_-nn*0.06; ob=b_-nn*0.06
            zo_a=final(oa[:,0],oa[:,1]); zo_b=final(ob[:,0],ob[:,1])
            dz=np.maximum(zs_a-zo_a,zs_b-zo_b)
            for i_ in np.where(dz>0.02)[0]:
                if np.isnan(zo_a[i_]) or np.isnan(zo_b[i_]): continue
                zb_=min(zo_a[i_],zo_b[i_])-0.05
                pa=a_[i_]+nn[i_]*0.01; pb=b_[i_]+nn[i_]*0.01
                q4=np.array([[pa[0],pa[1],zs_a[i_]],[pb[0],pb[1],zs_b[i_]],[pb[0],pb[1],zb_],[pa[0],pa[1],zb_]])
                base=sum(len(v_) for v_ in VV); VV.append(q4)
                tg_='perde_tas' if tas_ else 'perde_beton'
                FF.append((np.array([base,base+1,base+2]),tg_)); FF.append((np.array([base,base+2,base+3]),tg_)); nperde+=1
print('kenar perdesi: %d parca'%nperde)
open('p116y_agiz.txt','w').write(opening.wkt)
open('p116y_poly.txt','w').write(';'.join('%.3f,%.3f'%tuple(q_) for q_ in np.array(P.exterior.coords)))
A_=np.vstack(VV)
UV=np.c_[A_[:,:2],np.ones(len(A_))]@uvA
with open('p116y_mesh.txt','w') as f:
    for v_,uv in zip(A_,UV): f.write('V %.3f %.3f %.3f %.6f %.6f\n'%(v_[0],v_[1],v_[2],uv[0],uv[1]))
    for t_,m_ in FF: f.write('F %d %d %d %s\n'%(t_[0],t_[1],t_[2],m_))

# ---------- duvarlar ----------
walls=[]; WL={}
GARD_U=unary_union(gard)
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
                if not P.contains(Point(*(mid+nn*0.06))): continue                             # ic taraf parsel disinda (sinirdaki kil payi sivri): duvar yok
                if LineString([a_,b_]).intersection(FPu.buffer(0.35)).length>=0.6*np.hypot(*(b_-a_)): continue   # cepheye yapisik parcalar (temel perdesi kapatir): egik tepeli ucgen duvar olmasin
                if sw.distance(Point(*mid))<0.2 and (Point(*mid).distance(Jp)<W/2+2.0 or opening.buffer(0.3).contains(Point(*mid))): continue   # kamu yolundan arac girisi: acik
                if P.exterior.distance(Point(*mid))<0.2 and mouth.buffer(0.3).contains(Point(*mid)): continue   # yol agzinda parsel kenari: acik                         # bina cephesine yapisik parcalar (dolgu blok kapatir)
                zi=final([a_[0]+nn[0]*0.06,b_[0]+nn[0]*0.06],[a_[1]+nn[1]*0.06,b_[1]+nn[1]*0.06])
                zo=final([a_[0]-nn[0]*0.06,b_[0]-nn[0]*0.06],[a_[1]-nn[1]*0.06,b_[1]-nn[1]*0.06])
                if np.isnan(zo).any() or (np.abs(zi-zo).max()<0.10 and P.exterior.distance(Point(*mid))>0.05): continue   # 10 cm alti fark duvar degil (parsel sinirinda duvar kesintisiz)
                if SHARED_ALL is not None and SHARED_ALL.distance(Point(*mid))<0.2 and np.abs(zi-zo).max()<0.10: continue   # komsu ile ayni kot (yol-otopark): duvar/bordur yok
                if hard.buffer(0.02).contains(Point(*(mid+nn*0.06))) and hard.buffer(0.02).contains(Point(*(mid-nn*0.06))): continue   # iki yani tasit alani: duvar yok
                outside_feat=allf.contains(Point(*(mid-nn*0.06)))
                if outside_feat and zi.mean()<=zo.mean(): continue                             # oteki taraf cizer
                if SHARED_ALL is not None and SHARED_ALL.distance(Point(*mid))<0.2 and zi.mean()<zo.mean(): continue   # ortak sinir: duvari yuksek taraf kurar
                nlow=-nn if zi.mean()>zo.mean() else nn          # duvar alcak tarafa dogru kalinlasir
                if hard.contains(Point(*(mid-nlow*0.2))) is False and hard.contains(Point(*(mid+nlow*0.2))) and GARD_U.contains(Point(*(mid-nlow*0.2))):
                    nlow=-nlow                                                                  # yol ile bahce arasinda govde bahce tarafinda: yol kenari cephe hizasinda temiz kalir
                    hi_ek=0.01
                else: hi_ek=0.0
                lo=np.minimum(zi,zo); hi=np.maximum(zi,zo)
                zi4=final([a_[0]+nn[0]*0.4,b_[0]+nn[0]*0.4],[a_[1]+nn[1]*0.4,b_[1]+nn[1]*0.4])     # koseler: duvar ustu yanindaki en yuksek zemine kadar
                zo4=final([a_[0]-nn[0]*0.4,b_[0]-nn[0]*0.4],[a_[1]-nn[1]*0.4,b_[1]-nn[1]*0.4])
                for q4,z4 in ((nn*0.4,zi4),(-nn*0.4,zo4)):                                     # yalniz parsel ici (bahce/yol) kotlari; dogal arazi degil
                    in4=contains_xy(P,np.array([a_[0]+q4[0],b_[0]+q4[0]]),np.array([a_[1]+q4[1],b_[1]+q4[1]]))
                    z4[~in4]=np.nan
                if (hi-lo).max()>=0.30: hi=np.nanmax(np.vstack([hi,zi4,zo4]),axis=0)          # kucuk kot farklarinda ucgen tepe olusmasin
                hi=hi+hi_ek                                                                    # bahce icindeki duvar ustu cimle cakismasin
                if zi.mean()>zo.mean() and (zi-zo).max()>0.5: hi=hi+PARAPET; ty='dolgu'
                else: ty='istinat' if zi.mean()<zo.mean() else 'basamak'
                walls.append((a_,b_,lo,hi,ty,nlow)); WL[ty]=WL.get(ty,0)+np.hypot(*(b_-a_))
# gomulu merdiven: oyuga degen otomatik duvarlar oyuk sinirinda kesilir; yerine merdivenin iki yaninda,
# oyugun DISINDA, duz tepeli (bahce kotu) istinat duvarlari -> V/ucgen parca ve aciklik olusmaz
if gm_zones:
    _zu=unary_union([z_ for z_,_ in gm_zones]).buffer(0.01,join_style=2)
    yeni=[]
    for a_,b_,lo,hi,ty,nl in walls:
        ln=LineString([a_,b_])
        if not ln.intersects(_zu): yeni.append((a_,b_,lo,hi,ty,nl)); continue
        kal=ln.difference(_zu); L_=ln.length
        for g_ in getattr(kal,'geoms',[kal]):
            if g_.is_empty or g_.length<0.05: continue
            c_=np.array(g_.coords); t0=np.dot(c_[0]-a_,b_-a_)/L_**2; t1=np.dot(c_[-1]-a_,b_-a_)/L_**2
            yeni.append((c_[0],c_[-1],lo[0]+(lo[1]-lo[0])*np.array([t0,t1]),hi[0]+(hi[1]-hi[0])*np.array([t0,t1]),ty,nl))
    # merdiven agzina yakin parcalarin tepesi duz (bahce kotu): egik/ucgen tepe olmasin
    yeni=[(a_,b_,np.full(2,lo.min()),np.full(2,hi.max()),ty,nl) if LineString([a_,b_]).distance(_zu)<0.8 else (a_,b_,lo,hi,ty,nl) for a_,b_,lo,hi,ty,nl in yeni]
    # merdiven yanindaki parcalarin govdesi otoparka/yola tasmasin (bahce tarafinda)
    yeni=[(a_,b_,lo,hi,ty,(-nl if (LineString([a_,b_]).distance(_zu)<0.8 and hard.contains(Point(*((a_+b_)/2+nl*0.2)))) else nl)) for a_,b_,lo,hi,ty,nl in yeni]
    walls=yeni
    for u_e,sg_,n0,n1,zp,zg,run in gm_info:
        for nn_,dn in ((n0,-1.0),(n1,1.0)):
            a_=U*u_e+NU*nn_; b_=U*(u_e+sg_*run)+NU*nn_
            walls.append((a_,b_,np.array([zp,zp]),np.array([zg+0.01,zg+0.01]),'istinat_m',NU*dn))   # _m: merdiven yani, uzatilmaz
# parsel sinirindaki duvarlarin govdesi hep parsel disinda: ic yuzler sinir cizgisinde ayni hizada (kademe olmaz)
_wb=[]
for a_,b_,lo,hi,ty,nl in walls:
    mid=(a_+b_)/2
    if P.exterior.distance(Point(*mid))<0.05 and P.contains(Point(*(mid+nl*0.15))): nl=-nl
    _wb.append((a_,b_,lo,hi,ty,nl))
walls=_wb
# parsel ici duvarlar zeminle ayni seviye: tepe yuksek zeminin 5 mm altinda, govde yuksek tarafin altinda (ustten gorunmez)
_wi=[]
for a_,b_,lo,hi,ty,nl in walls:
    mid=(a_+b_)/2
    if ty.endswith('_m') or P.exterior.distance(Point(*mid))<0.05 or (gm_zones and LineString([a_,b_]).distance(_zu)<0.8):
        _wi.append((a_,b_,lo,hi,ty,nl)); continue                                     # sinir, merdiven yani: oldugu gibi
    d_=b_-a_; L_=np.hypot(*d_)
    if L_<1e-6: continue
    n_=np.array([-d_[1],d_[0]])/L_
    xs=np.array([a_[0]+n_[0]*0.06,b_[0]+n_[0]*0.06,a_[0]-n_[0]*0.06,b_[0]-n_[0]*0.06])
    ys=np.array([a_[1]+n_[1]*0.06,b_[1]+n_[1]*0.06,a_[1]-n_[1]*0.06,b_[1]-n_[1]*0.06])
    zz=final(xs,ys)
    if np.isnan(zz).any(): _wi.append((a_,b_,lo,hi,ty,nl)); continue
    zp_,zm_=zz[:2],zz[2:]
    up=n_ if zp_.mean()>zm_.mean() else -n_
    hi2=np.maximum(zp_,zm_)-0.005; lo2=np.minimum(zp_,zm_)
    _wi.append((a_,b_,lo2,hi2,ty,up))
walls=_wi
# ust uste binen (ayni konumda iki kez uretilen) duvarlar tekillesir: yuksek olan kalir
_tek={}
for w_ in walls:
    key=tuple(sorted([tuple(np.round(w_[0],1)),tuple(np.round(w_[1],1))]))
    if key not in _tek or w_[3].max()>_tek[key][3].max(): _tek[key]=w_
walls=list(_tek.values())
# ust uste binen kopyalar (birkac mm kaymis): baska duvarlarin %80'ini kapladigi parca atilir -> ortada uc yuzu/cikinti kalmaz
walls.sort(key=lambda w_: -np.hypot(*(w_[1]-w_[0])))
_kabul=[]; _kab_geo=[]
for w_ in walls:
    ln=LineString([w_[0],w_[1]])
    if _kab_geo and ln.length>0:
        yakin=[g_ for g_ in _kab_geo if g_.distance(ln)<0.06]
        if yakin:
            _ub=unary_union(yakin).buffer(0.06,cap_style=2)
            ort=ln.intersection(_ub).length
            if ort>=0.8*ln.length: continue
            if ort>0.05:                                                              # kismen ortusen: yalniz ortusmeyen kismi kalir
                kal=ln.difference(_ub)
                for g_ in getattr(kal,'geoms',[kal]):
                    if g_.geom_type!='LineString' or g_.length<0.1: continue
                    c_=np.array(g_.coords); L_=ln.length
                    t0=np.dot(c_[0]-w_[0],w_[1]-w_[0])/L_**2; t1=np.dot(c_[-1]-w_[0],w_[1]-w_[0])/L_**2
                    lo_=w_[2][0]+(w_[2][1]-w_[2][0])*np.array([t0,t1]); hi_=w_[3][0]+(w_[3][1]-w_[3][0])*np.array([t0,t1])
                    _kabul.append((c_[0],c_[-1],lo_,hi_,w_[4],w_[5])); _kab_geo.append(LineString([c_[0],c_[-1]]))
                continue
    _kabul.append(w_); _kab_geo.append(ln)
walls=_kabul
with open('p116y_duvar.txt','w') as f:
    from collections import Counter
    _uc=np.array([w_[0] for w_ in walls]+[w_[1] for w_ in walls])
    def _komsu_say(q_): return int((np.hypot(_uc[:,0]-q_[0],_uc[:,1]-q_[1])<0.10).sum())   # 10 cm icindeki uc sayisi (zincir baglantisi)
    for a_,b_,lo,hi,ty,nl in walls:
        e0=int(_komsu_say(a_)<2); e1=int(_komsu_say(b_)<2)                             # zincir ucu -> uc yuzu kapat
        tv_=(b_-a_)/max(np.hypot(*(b_-a_)),1e-9)                                           # zincir uclari 30 cm uzar: kose bosluklari kapanir
        uzat_ok=lambda q: not hard.contains(Point(*q)) and not (gm_zones and unary_union([z_ for z_,_ in gm_zones]).buffer(0.02).contains(Point(*q)))   # uc yola/merdiven oyuguna tasmasin
        def eve_uzat(p_,d_):                                                            # uc evin 2 m yakinindaysa ayni hizada eve kadar uzar
            ray=LineString([p_,p_+d_*2.0]); x_=ray.intersection(FPu)
            if x_.is_empty: return None
            t_=min(np.dot(np.array(q_)-p_,d_) for g_ in getattr(x_,'geoms',[x_]) for q_ in g_.coords)
            return p_+d_*(t_+0.05) if 0.0<t_<2.0 else None
        if ty.endswith('_m'): e0=e1=0                                                   # merdiven yan duvari tam boyunda
        if e0:
            q_=eve_uzat(a_,-tv_)
            if q_ is not None: a_=q_
            elif uzat_ok(a_-tv_*0.30): a_=a_-tv_*0.30
        if e1:
            q_=eve_uzat(b_,tv_)
            if q_ is not None: b_=q_
            elif uzat_ok(b_+tv_*0.30): b_=b_+tv_*0.30
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
with open('p116y_basamak.txt','w') as f:
    for zt,q in stair2: f.write('T %.3f %.3f %s\n'%(zbot-0.3,zt,';'.join('%.3f,%.3f'%tuple(p_) for p_ in q)))

# ---------- otopark yerleri ----------
pp=park_poly if park_poly.geom_type=='Polygon' else max(park_poly.geoms,key=lambda q:q.area)
nb=north.intersection(slab_u(xs_park0,xs_park1)); nbc=np.array(nb.coords) if nb.geom_type=='LineString' else np.array(max(nb.geoms,key=lambda g:g.length).coords)
tv=(nbc[-1]-nbc[0])/np.hypot(*(nbc[-1]-nbc[0])); nv_=np.array([tv[1],-tv[0]])          # guneye
best=[]
for off_ in np.arange(0,STALL_W,0.5):
    for q0 in (0.0,AISLE):                                                       # kuzey sinira dayali ya da guneye dayali dik park sirasi
        stl=[]; s_=off_
        Ls=np.hypot(*(nbc[-1]-nbc[0]))
        while s_+STALL_W<=Ls+5:
            o0=nbc[0]+tv*s_+nv_*q0
            rc=Polygon([o0,o0+tv*STALL_W,o0+tv*STALL_W+nv_*STALL_D,o0+nv_*STALL_D])
            if pp.buffer(0.01).contains(rc) and rc.distance(FPu)>0.3: stl.append(rc)
            s_+=STALL_W
        if len(stl)>len(best): best=stl
lot_st=[]; lot_stair=[]
rectUN=lambda u0,u1,n0,n1: Polygon([U*u0+NU*n0,U*u1+NU*n0,U*u1+NU*n1,U*u0+NU*n1])
# kuzey kapilar: yol subasman altinda -> kapi onune esikten yola basamak (1.40 m genis, 30 cm tread)
kapi_bas=[]; _gor=[]
for dd in doors:
    if not dd['north'] or any(np.hypot(*(dd['c']-q_))<1.5 for q_ in _gor): continue
    _gor.append(dd['c']); k=dd['k']
    zr=float(zax(axis.project(Point(*(dd['c']+dd['n']*0.5)))))
    if k==_k3 and uc(dd['c'])>U_CUT: zr=Z[k]                                    # son bolum: kapi onu bahce
    hh=Lk[k]-zr
    if hh<0.05: continue
    nb_=int(np.ceil(hh/RISER)); rb_=hh/nb_
    e_=np.array([dd['n'][1],-dd['n'][0]])
    for i_ in range(1,nb_):
        d0=(i_-1)*TREAD-(0.15 if i_==1 else 0.0); d1=i_*TREAD          # ilk basamak cepheye 15 cm girer: aralik kalmaz
        q=[dd['c']+dd['n']*d0+e_*0.7,dd['c']+dd['n']*d1+e_*0.7,dd['c']+dd['n']*d1-e_*0.7,dd['c']+dd['n']*d0-e_*0.7]
        kapi_bas.append((zr-0.3,Lk[k]-i_*rb_,q))
    print('%s kuzey kapi basamagi: %.2f m, %d rihtim'%(names[k],hh,nb_))
with open('p116y_basamak.txt','a') as f:
    for zb_,zt_,q in kapi_bas: f.write('T %.3f %.3f %s\n'%(zb_,zt_,';'.join('%.3f,%.3f'%tuple(p_) for p_ in q)))
    for zb_,zt_,q in gm_stairs: f.write('T %.3f %.3f %s\n'%(zb_,zt_,';'.join('%.3f,%.3f'%tuple(p_) for p_ in q)))
    for zt,q in lot_stair: f.write('T %.3f %.3f %s\n'%(Z_LOT-0.3,zt,';'.join('%.3f,%.3f'%tuple(p_) for p_ in q)))

best=best+lot_st
with open('p116y_park.txt','w') as f:
    for rc in best:
        cc=np.array(rc.centroid.coords[0]); zz=float(final([cc[0]],[cc[1]])[0])
        f.write('S %.3f %s\n'%(zz+0.03,';'.join('%.3f,%.3f'%tuple(q) for q in np.array(rc.exterior.coords)[:-1])))
with open('p116y_merdiven.txt','w') as f:
    for s0,s1,nst in stairs:
        for j in range(nst+1):
            s=s0+(s1-s0)*j/nst; pt=np.array(axis.interpolate(s).coords[0]); a_=np.array(axis.interpolate(max(s-0.2,0)).coords[0]); b_=np.array(axis.interpolate(min(s+0.2,L)).coords[0])
            tv_=(b_-a_)/np.hypot(*(b_-a_)); nn=np.array([-tv_[1],tv_[0]])
            f.write('M %.3f %.3f %.3f %.3f %.3f\n'%(*(pt+nn*W/2),*(pt-nn*W/2),float(zax(s))+0.03))
# etiketler
with open('p116y_etiket.txt','w') as f:
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
    if len(ii)==0: continue
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
ax.set_aspect('equal'); plt.savefig('p116y_onizleme.png',dpi=110,bbox_inches='tight')
with open('p116y_taban.txt','w') as f:
    for k in range(3):
        f.write('B %s %.3f %.3f %s\n'%(names[k],Z[k]-0.05,Lk[k],';'.join('%.3f,%.3f'%tuple(q) for q in np.array(fps[k].exterior.coords)[:-1])))

# ---------- bahce duvari: kuzey, dogu, bati parsel sinirindaki istinat duvarlarinin ustunde, kademeli ----------
# 2.5 m'lik bolmeler; her bolmenin tabani o bolmedeki istinat duvari ustunun en yukseginde (kademeli).
BAY=2.5
_pe=list(P.exterior.coords)[:-1]
_kuz=LineString(ring[0:2])                                 # 115 ile ortak sinir: bahce duvari 115'in tarafinda
bays=[]
for i_ in range(len(_pe)):
    a_=np.array(_pe[i_]); b_=np.array(_pe[(i_+1)%len(_pe)])
    if _kuz.distance(Point(*((a_+b_)/2)))<0.2: continue                                   # kuzey (115 ile ortak) sinir haric
    if abs(uc((a_+b_)/2)-U_END)<0.2: continue                                              # tasarim kesim cizgisi (dogal arazi) haric
    L_=np.hypot(*(b_-a_))
    if L_<0.5: continue
    t_=(b_-a_)/L_; out=np.array([t_[1],-t_[0]])
    if P.contains(Point(*((a_+b_)/2+out*0.2))): out=-out                                 # disari normal
    nb=max(int(np.ceil(L_/BAY)),1)
    for j_ in range(nb):
        p0=a_+t_*L_*j_/nb; p1=a_+t_*L_*(j_+1)/nb
        sm=np.array([p0+(p1-p0)*f_ for f_ in np.linspace(0,1,6)])
        mid=(p0+p1)/2
        if opening.buffer(0.6).contains(Point(*mid)) or mouth.buffer(0.3).contains(Point(*mid)): continue   # arac girisi acik
        zi=final(sm[:,0]-out[0]*0.3,sm[:,1]-out[1]*0.3); zo=final(sm[:,0]+out[0]*0.6,sm[:,1]+out[1]*0.6)
        zz=np.nanmax(np.vstack([zi,zo]),axis=0)
        if np.isnan(zz).all(): continue
        bays.append((p0,p1,float(np.nanmax(zz)),out,float(np.nanmin(zz))))
with open('p116y_bahce_duvari.txt','w') as f:
    for p0,p1,zb_,out,zm_ in bays: f.write('B %.3f %.3f %.3f %.3f %.3f %.4f %.4f %.3f\n'%(p0[0],p0[1],p1[0],p1[1],zb_,out[0],out[1],zm_))
print('bahce duvari: %d bolme, %.0f m'%(len(bays),sum(np.hypot(*(b[1]-b[0])) for b in bays)))

# ---------- bitki citleri: otopark-bahce sinirlari boyunca ve her bagimsiz bolum arasinda (bahce ayrimi) ----------
CIT_IC=0.45     # citin bahce sinirindan iceri mesafesi (duvar govdesinin arkasi)
_engel=[]       # merdiven agizlari: cit kesilir
if gm_zones: _engel.append(unary_union([z_ for z_,_ in gm_zones]).buffer(0.45))      # cit merdiven yan duvarina kadar uzanir (45 cm: cit yarim genisligi + duvar)
if lot_stair: _engel.append(unary_union([Polygon(q) for _,q in lot_stair]).buffer(0.45))
_engel=unary_union(_engel) if _engel else Polygon()
citler=[]
# cit kuzey uclari icin girintileri izleyen gercek ev izi (dis kabuk girintileri doldurdugu icin cit evden uzakta kaliyordu)
_gercek=[]
for _l in open('bolge_dump.txt'):
    if _l.startswith('  TABAN '):
        _pp=[tuple(map(float,q_.split(','))) for q_ in _l.split()[1].split(';')]
        if len(_pp)>=4: _gercek.append(shapely.concave_hull(shapely.MultiPoint(_pp),ratio=0.12))
FPc=unary_union(_gercek).buffer(0.05) if _gercek else FPu
# bagimsiz bolum planlari (bina_iz.txt: B01..B12) -> her yapi icin u sirali bolum listesi
_bol={k:[] for k in range(3)}
for _l in open('bina_iz.txt'):
    _t=_l.split()
    if _t[0]!='B' or not _t[1].startswith('P116'): continue                    # yalniz bu parselin bolumleri
    _q=Polygon([tuple(map(float,p_.split(','))) for p_ in _t[3].split(';')])
    _k=int(np.argmin([_q.centroid.distance(f_) for f_ in fps])); _bol[_k].append((_t[1],_q))
for _k in _bol: _bol[_k].sort(key=lambda bq: float(np.mean(np.array(bq[1].exterior.coords)@U)))
def _cit_ekle(ln,z_,g_):
    for g2 in getattr(ln,'geoms',[ln]):
        if g2.geom_type!='LineString' or g2.length<0.6: continue
        g3=g2.difference(_engel)
        for g4 in getattr(g3,'geoms',[g3]):
            if g4.geom_type=='LineString' and g4.length>=0.6:
                c_=np.array(g4.coords)
                # uclar 40 cm uzatilir: eve/guney citine/otopark citine degip birlesir (merdiven yani haric)
                for ucn,yon_ in ((0,-1),(-1,1)):
                    a_=c_[ucn]; b_=c_[1 if ucn==0 else -2]; d_=(a_-b_)/max(np.hypot(*(a_-b_)),1e-9)
                    q_=a_+d_*0.40
                    if not _engel.buffer(0.02).contains(Point(*q_)) and P.buffer(-0.05).contains(Point(*q_)): c_[ucn]=q_
                for p0,p1 in zip(c_[:-1],c_[1:]):
                    if np.hypot(*(p1-p0))>0.05: citler.append((p0,p1,z_))
_otop=unary_union([park_poly,lot_poly])
for k in range(3):
    g_=gard[k].difference(FPu)
    if g_.is_empty: continue
    # (a) otopark ile bahce siniri: siniri CIT_IC kadar bahceye kaydir
    sb=g_.boundary.intersection(_otop.buffer(0.08))
    for s2 in getattr(sb,'geoms',[sb]):
        if s2.geom_type!='LineString' or s2.length<0.6: continue
        for sd in (CIT_IC,-CIT_IC):
            o_=s2.offset_curve(sd)
            if o_.is_empty: continue
            if g_.buffer(-0.1).contains(o_.interpolate(0.5,normalized=True)):
                _cit_ekle(o_.intersection(g_.buffer(-0.05)),Z[k],g_); break
    # (b) bagimsiz bolumler arasi: gercek bolum sinirlarindan (bina_iz.txt) bahce tarafinda evden guney sinira cit
    for (b0_,q0_),(b1_,q1_) in zip(_bol[k][:-1],_bol[k][1:]):
        c0_=np.array(q0_.exterior.coords)[:-1]; c1_=np.array(q1_.exterior.coords)[:-1]
        u_=0.5*(float((c0_@U).max())+float((c1_@U).min()))                        # iki bolumun ortak siniri
        ns_=min(float((c0_@NU).min()),float((c1_@NU).min()))
        ln=LineString([U*u_+NU*(ns_+1.0),U*u_+NU*(ns_-40)]).intersection(gard[k].difference(FPc).buffer(-0.05))
        _cit_ekle(ln,Z[k],g_)
    # (c) guney parsel siniri boyunca (bahce icinde, sinirdan CIT_IC iceride)
    _gs=LineString([ring[4],ring[5]]).offset_curve(-CIT_IC) if True else None
    for sd in (CIT_IC,-CIT_IC):
        o_=LineString([ring[4],ring[5]]).offset_curve(sd)
        if P.contains(o_.interpolate(0.5,normalized=True)):
            _cit_ekle(o_.intersection(g_.buffer(-0.05)),Z[k],g_); break
with open('p116y_bitki.txt','w') as f:
    for p0,p1,z_ in citler: f.write('H %.3f %.3f %.3f %.3f %.3f\n'%(p0[0],p0[1],p1[0],p1[1],z_))
print('bitki citi: %d parca, %.0f m'%(len(citler),sum(np.hypot(*(c[1]-c[0])) for c in citler)))


