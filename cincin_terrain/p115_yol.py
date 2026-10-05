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
FPu=unary_union(fps)

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
def slab_x(x0,x1): return box(x0,-1e3,x1,1e3)
xs_park0=float(SP[st==s_park0][0][0]); xs_park1=float(SP[st==s_park1][0][0])
west_fill=P.intersection(slab_x(-1e3,axis_pts[1][0]-1.0))          # giris ile kuzey serit arasi bosluk -> rampa
road_poly=unary_union([band.intersection(slab_x(-1e3,xs_park0)),entry,west_fill]).buffer(0.01).buffer(-0.01).difference(FPu.buffer(0.05))
# not: bati ucta giris seridi (3 m) disinda ~17 m2 kaliyor; 2.5x5 park yeri sigmiyor -> rampa/asfalt olarak kalir
park_poly=P.intersection(slab_x(xs_park0,xs_park1)).difference(FPu.buffer(0.05))
walk_poly=band.intersection(slab_x(xs_park1,1e3)).difference(FPu.buffer(0.05))
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
cuts=[-1e3]+[(fps[order[j]].bounds[2]+fps[order[j+1]].bounds[0])/2 for j in range(2)]+[1e3]
hard=unary_union([road_poly,park_poly,walk_poly])
gard=[None]*3
for j,k in enumerate(order):
    g=P.intersection(slab_x(cuts[j],cuts[j+1])).difference(hard)
    gard[k]=g

# ---------- arazi ----------
def feat_z(x,y):
    s=np.array([axis.project(Point(a_,b_)) for a_,b_ in zip(x,y)]); return zax(s)
def final(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float); f=nat(x,y)
    for k,g in enumerate(gard): f[contains_xy(g,x,y)]=Z[k]
    m=contains_xy(hard,x,y)
    if m.any(): f[m]=feat_z(x[m],y[m])
    for k,fp in enumerate(fps): f[contains_xy(fp,x,y)]=Z[k]-0.05
    return f
def ringpts(poly,step=0.5):
    out=[]
    for pg in ([poly] if poly.geom_type=='Polygon' else list(poly.geoms)):
        for rr in [pg.exterior]+list(pg.interiors):
            c_=np.array(rr.coords)
            for p0,p1 in zip(c_[:-1],c_[1:]):
                m=max(1,int(np.hypot(*(p1-p0))/step)); out.append(p0+(p1-p0)*np.linspace(0,1,m,endpoint=False)[:,None])
    return np.vstack(out)
feats=[*gard,road_poly,park_poly,walk_poly,*fps]
region=P.buffer(15)
outer=V[~contains_xy(region,V[:,0],V[:,1])][:,:3]
x0,y0,x1,y1=region.bounds
gx,gy=np.meshgrid(np.arange(x0,x1,1.0),np.arange(y0,y1,1.0)); g=np.c_[gx.ravel(),gy.ravel()]
bnd=unary_union([q.boundary for q in feats]+[P.boundary])
g=g[contains_xy(region,g[:,0],g[:,1])]; g=g[shapely.distance(bnd,shapely.points(g[:,0],g[:,1]))>0.3]
pts=[g,ringpts(region,1.0)]
for q in feats+[P]:
    for o_ in (-0.05,0.05):
        qq=q.buffer(o_,join_style=2)
        if not qq.is_empty: pts.append(ringpts(qq,0.4))
P2=np.vstack(pts); A_=np.vstack([outer,np.c_[P2,final(P2[:,0],P2[:,1])]])
A_=A_[~np.isnan(A_[:,2])]
_,ui=np.unique(np.round(A_[:,:2],2),axis=0,return_index=True); A_=A_[np.sort(ui)]
T=Delaunay(A_[:,:2]).simplices
p=A_[:,:2]; u=p[T[:,1]]-p[T[:,0]]; w=p[T[:,2]]-p[T[:,0]]; cr=u[:,0]*w[:,1]-u[:,1]*w[:,0]
T=T[np.abs(cr)>1e-6]; cr=cr[np.abs(cr)>1e-6]; T[cr<0]=T[cr<0][:,[0,2,1]]
cen=A_[T][:,:,:2].mean(1); T=T[~np.isnan(nat(cen[:,0],cen[:,1]))|contains_xy(P,cen[:,0],cen[:,1])]
cen=A_[T][:,:,:2].mean(1); zr_=A_[T][:,:,2].max(1)-A_[T][:,:,2].min(1)      # dik gecis seridi (testere disi) ucgenleri: yerine gercek duvar
dB=shapely.distance(bnd,shapely.points(cen[:,0],cen[:,1])); dF=shapely.distance(FPu.boundary,shapely.points(cen[:,0],cen[:,1]))
T=T[~((zr_>0.05)&(dB<0.15)&(dF>0.15))]
cen=A_[T][:,:,:2].mean(1)
mat=np.full(len(T),'arazi',dtype=object)
for k,gg in enumerate(gard): mat[contains_xy(gg,cen[:,0],cen[:,1])]='cim'
mat[contains_xy(road_poly,cen[:,0],cen[:,1])]='asfalt'; mat[contains_xy(park_poly,cen[:,0],cen[:,1])]='otopark'; mat[contains_xy(walk_poly,cen[:,0],cen[:,1])]='yaya'
UV=np.c_[A_[:,:2],np.ones(len(A_))]@uvA
with open('p115y_mesh.txt','w') as f:
    for v_,uv in zip(A_,UV): f.write('V %.3f %.3f %.3f %.6f %.6f\n'%(v_[0],v_[1],v_[2],uv[0],uv[1]))
    for t_,m_ in zip(T,mat): f.write('F %d %d %d %s\n'%(t_[0],t_[1],t_[2],m_))

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
                if FPu.distance(LineString([a_,b_]))<0.6: continue                         # bina cephesine yapisik parcalar (dolgu blok kapatir)
                zi=final([a_[0]+nn[0]*0.06,b_[0]+nn[0]*0.06],[a_[1]+nn[1]*0.06,b_[1]+nn[1]*0.06])
                zo=final([a_[0]-nn[0]*0.06,b_[0]-nn[0]*0.06],[a_[1]-nn[1]*0.06,b_[1]-nn[1]*0.06])
                if np.isnan(zo).any() or np.abs(zi-zo).max()<0.05: continue
                outside_feat=allf.contains(Point(*(mid-nn*0.06)))
                if outside_feat and zi.mean()<=zo.mean(): continue                             # oteki taraf cizer
                nlow=-nn if zi.mean()>zo.mean() else nn          # duvar alcak tarafa dogru kalinlasir
                lo=np.minimum(zi,zo); hi=np.maximum(zi,zo)
                if zi.mean()>zo.mean() and (zi-zo).max()>0.5: hi=hi+PARAPET; ty='dolgu'
                else: ty='istinat' if zi.mean()<zo.mean() else 'basamak'
                walls.append((a_,b_,lo,hi,ty,nlow)); WL[ty]=WL.get(ty,0)+np.hypot(*(b_-a_))
with open('p115y_duvar.txt','w') as f:
    from collections import Counter
    cnt=Counter([tuple(np.round(w_[0],2)) for w_ in walls]+[tuple(np.round(w_[1],2)) for w_ in walls])
    for a_,b_,lo,hi,ty,nl in walls:
        e0=int(cnt[tuple(np.round(a_,2))]<2); e1=int(cnt[tuple(np.round(b_,2))]<2)       # zincir ucu -> uc yuzu kapat
        f.write('W %s %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %.3f %d %d\n'%(ty,a_[0],a_[1],b_[0],b_[1],lo[0]-0.3,lo[1]-0.3,hi[0],hi[1],nl[0],nl[1],e0,e1))

# ---------- istinattan YAPI1 bahcesine (yesile) inen merdiven: kot farkinin en az oldugu duvar parcasi ----------
RISER=0.17; TREAD=0.30; ST_W=1.20; TH=0.30
cand=[]
for a_,b_,lo,hi,ty,nl in walls:
    mid=(a_+b_)/2
    if not gard[0].contains(Point(*(mid+nl*0.6))): continue                 # alcak taraf YAPI1 bahcesi
    if not hard.buffer(0.05).contains(Point(*(mid-nl*0.3))): continue        # yuksek taraf yol (istinatin ustu)
    if (hi-lo).mean()<0.35: continue
    run_=TH+np.ceil((hi-lo).mean()/RISER)*TREAD+0.5
    tip=mid+nl*run_                                                           # merdiven bahceye sigmali, binaya carpmamali
    if not gard[0].buffer(-0.05).contains(LineString([mid+nl*TH,tip]).buffer(ST_W/2,cap_style=2)): continue
    cand.append(((hi-lo).mean(),mid,nl,float(hi.mean()),float(lo.mean())))
stair2=[]
if cand:
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
nb=north.intersection(slab_x(xs_park0,xs_park1)); nbc=np.array(nb.coords) if nb.geom_type=='LineString' else np.array(max(nb.geoms,key=lambda g:g.length).coords)
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
