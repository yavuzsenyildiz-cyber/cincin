import json, sys, csv, shutil, numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import nearest_points, unary_union
from scipy.optimize import lsq_linear
H0=105.07; SMAX=0.12; SUB=0.50
OPT = len(sys.argv)>1 and sys.argv[1]=='opt'
R=json.load(open('yollar_eski.json' if OPT else 'yollar.json'))
J=json.load(open('tesviye.json')); YB=json.load(open('yapi_bolum.json'))
Z={n:J['Z'][i] for i,n in enumerate(J['names'])}
U={}
for l in open('bina_iz.txt'):
    h=l.split(' | ')[0].split(' ',3)
    U[h[1]]=Polygon(np.array([[float(c) for c in q.split(',')] for q in h[3].split(';')]))
road={}
for nm,r in R.items():
    a=np.array(r['a']); t=np.array(r['t']); u=np.array(r['u'])
    road[nm]=dict(a=a,t=t,n=np.array(r['n']),u=u,z=np.array(r['z']),zn=np.array(r['zn']),W=r['W'],
                  line=LineString([a+u[0]*t,a+u[-1]*t]))
    road[nm]['strip']=road[nm]['line'].buffer(r['W']/2,cap_style=2)

units=[]
for yp,bl in YB.items():
    for b in bl:
        P=U[b]; cen=P.centroid
        best=None
        for rn,r in road.items():
            c=np.array(P.exterior.coords)
            for e in range(len(c)-1):
                p0,p1=c[e],c[e+1]; L=np.hypot(*(p1-p0))
                if L<4: continue
                mid=(p0+p1)/2; d=p1-p0; nrm=np.array([d[1],-d[0]])/L
                if np.dot(nrm,mid-np.array([cen.x,cen.y]))<0: nrm=-nrm
                pr=nearest_points(Point(mid),r['strip'])[1]; v=np.array([pr.x,pr.y])-mid
                dist=np.hypot(*v)
                if dist<1e-6 or np.dot(nrm,v)/dist<0.5: continue
                key=(dist,-L)
                if best is None or key<best[0]: best=(key,rn,mid,np.array([pr.x,pr.y]),L,dist)
        _,rn,E,Pr,L,dist=best
        r=road[rn]; uu=float(np.clip(np.dot(Pr-r['a'],r['t']),r['u'][0],r['u'][-1]))
        units.append(dict(b=b,yapi=yp,road=rn,E=E,Pr=Pr,facade=L,dist=dist,u=uu,Z=Z[yp],poly=P))

def blocked(un):
    seg=LineString([un['E'],un['Pr']]).buffer(0.6,cap_style=2)
    others=[v['poly'] for v in units if v['b']!=un['b']]
    return any(seg.intersection(o).area>0.01 for o in others)

if OPT:
    shutil.copy('yollar.json','yollar_eski_yedek.json') if False else None
    for rn,r in road.items():
        us=[x for x in units if x['road']==rn]
        u=r['u']; N=len(u); du=1.0
        rows=[];b=[]
        for x in us:
            i=int(np.floor((x['u']-u[0])/du)); i=min(i,N-2); fr=(x['u']-u[i])/du
            row=np.zeros(N-1); row[:i]=1; row[i]=fr; rows.append(row); b.append(x['Z']-r['zn'][0])
        for i in range(N):                      # arazi takibi (zayif)
            row=np.zeros(N-1); row[:i]=1; rows.append(row*0.12); b.append((r['zn'][i]-r['zn'][0])*0.12)
        A=np.array(rows); b=np.array(b)
        sol=lsq_linear(A,b,bounds=(-SMAX*du,SMAX*du))
        z=r['zn'][0]+np.r_[0,np.cumsum(sol.x)]
        R[rn]['z']=z.tolist(); r['z']=z
    json.dump(R,open('yollar.json','w'))
    print('yol profilleri yeniden hesaplandi (yollar.json)')

rows=[]; fail=0
for x in units:
    r=road[x['road']]; zr=float(np.interp(x['u'],r['u'],r['z']))
    dz=zr-x['Z']; slope=dz/max(x['dist'],0.5)
    ok_block=not blocked(x)
    durum='SEVIYEDE' if abs(dz)<=0.20 else ('MERDIVEN/RAMPA' if abs(dz)<=1.5 else 'YETERSIZ')
    if durum=='YETERSIZ' or not ok_block: fail+=1
    rows.append([x['b'],x['yapi'],x['road'],'%.1f'%x['facade'],'%.1f'%x['dist'],'%.2f'%(x['Z']+H0),'%.2f'%(zr+H0),'%.2f'%dz,'%.0f'%(slope*100),'evet' if ok_block else 'ENGELLI',durum])
hdr=['bolum','yapi','cephe_yolu','cephe_uzunlugu_m','yola_mesafe_m','platform_kotu','yol_kotu','kot_farki_m','giris_egimi_%','engelsiz_yaya_baglantisi','durum']
tag='sonra' if OPT else 'once'
with open('cephe_raporu_%s.csv'%tag,'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f,delimiter=';'); w.writerow(hdr); w.writerows(rows)
print(' | '.join(hdr))
for r in rows: print(' | '.join(r))
print('SORUNLU bolum sayisi:',fail,'/',len(units))
if OPT:
    with open('giris_yollari.txt','w') as f:
        for x in units:
            r=road[x['road']]; zr=float(np.interp(x['u'],r['u'],r['z']))
            d=x['Pr']-x['E']; L=np.hypot(*d); t=d/L; n=np.array([-t[1],t[0]]); hw=0.6
            q=[x['E']-n*hw,x['E']+n*hw,x['Pr']+n*hw,x['Pr']-n*hw]; zz=[x['Z'],x['Z'],zr,zr]
            f.write('G %s %s\n'%(x['b'],' '.join('%.3f %.3f %.3f'%(p[0],p[1],z) for p,z in zip(q,zz))))
    print('giris_yollari.txt yazildi')
