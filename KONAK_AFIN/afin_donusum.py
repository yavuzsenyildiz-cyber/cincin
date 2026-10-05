# Pafta köşe tespiti
import numpy as np, json
from PIL import Image
a=(np.array(Image.open('L18A-08C-4A.jpg'))<128).astype(np.int32)
def peaks(vertical, lo, hi, t0, t1, step=100):
    out=[]
    for t in range(t0,t1-step+1,step):
        prof=a[t:t+step, lo:hi].sum(0) if vertical else a[lo:hi, t:t+step].sum(1)
        k=prof.argmax(); w=np.arange(max(k-6,0),min(k+7,len(prof))); v=prof[w]*(prof[w]>0.5*prof[k])
        if prof[k]/step>0.7: out.append((t+step/2, lo+(w*v).sum()/v.sum()))
    return np.array(out)
def line(p):
    m,c=np.polyfit(p[:,0],p[:,1],1); return m,c,np.abs(p[:,1]-(m*p[:,0]+c)).max()
# local edge segments near each corner (~700 px)
seg={
 'L_top':(True,370,440,370,1070),'L_bot':(True,370,440,2750,3450),
 'R_top':(True,2800,2870,370,1070),'R_bot':(True,2800,2870,2750,3450),
 'T_left':(False,330,390,410,1110),'T_right':(False,330,390,2100,2800),
 'B_left':(False,3420,3480,410,1110),'B_right':(False,3420,3480,2100,2800)}
L={k:line(peaks(*v)) for k,v in seg.items()}
for k,v in L.items(): print(k,np.round(v,4))
def inter(vl,hl):
    # vertical: x=m1*y+c1 ; horizontal: y=m2*x+c2
    m1,c1,_=vl; m2,c2,_=hl
    y=(m2*c1+c2)/(1-m2*m1); x=m1*y+c1; return x,y
C={'TL':inter(L['L_top'],L['T_left']),'TR':inter(L['R_top'],L['T_right']),
   'BL':inter(L['L_bot'],L['B_left']),'BR':inter(L['R_bot'],L['B_right'])}
print(C); json.dump(C,open('corners.json','w'))

# Karelaj artısı tespiti
import numpy as np, cv2, json
img=cv2.imread('L18A-08C-4A.jpg',0); inv=(255-img).astype(np.float32)
A=np.array([[0.224039514,-0.000907979],[-0.000000290,-0.224252987]]);c=np.array([510831.3259,4253373.7396])
# cross template: arms 12px each side, 2px thick, empty center-ring irrelevant
T=np.zeros((31,31),np.float32); T[14:17,3:28]=255; T[3:28,14:17]=255
found=[]
for E in range(511000,511500,100):
  for N in range(4252600,4253300,100):
    x,y=np.linalg.solve(A,np.array([E,N])-c)
    if not(420<x<2800 and 380<y<3430): continue
    r=18; x0,y0=int(round(x))-r-15,int(round(y))-r-15
    win=inv[y0:y0+2*r+31, x0:x0+2*r+31]
    res=cv2.matchTemplate(win,T,cv2.TM_CCOEFF_NORMED)
    _,mx,_,ml=cv2.minMaxLoc(res)
    # subpixel via parabola
    def sub(a,i):
        return 0 if i<=0 or i>=len(a)-1 else 0.5*(a[i-1]-a[i+1])/(a[i-1]-2*a[i]+a[i+1])
    px=x0+ml[0]+15+sub(res[ml[1]],ml[0]); py=y0+ml[1]+15+sub(res[:,ml[0]],ml[1])
    found.append(dict(E=E,N=N,x=float(px),y=float(py),score=float(mx),pred=(float(x),float(y))))
for f in found: print(f['E'],f['N'],'score=%.2f'%f['score'],'dx=%.1f dy=%.1f'%(f['x']-f['pred'][0],f['y']-f['pred'][1]))
json.dump(found,open('grid.json','w'))

# Dengeleme
import numpy as np, json, math
C=json.load(open('corners.json')); G=json.load(open('grid.json'))
W={'TL':(510917.28,4253293.08),'TR':(511463.14,4253293.84),'BL':(510918.22,4252599.30),'BR':(511464.13,4252600.06)}
pts=[(k,C[k][0],C[k][1],*W[k]) for k in W]
pts+=[('G%d_%d'%(g['E']-511000,g['N']-4252000),g['x'],g['y'],g['E'],g['N']) for g in G if abs(g['x']-g['pred'][0])<9 and abs(g['y']-g['pred'][1])<3]
def fit(P):
    A=np.array([[p[1],p[2],1] for p in P]);E=np.array([p[3] for p in P]);N=np.array([p[4] for p in P])
    pe=np.linalg.lstsq(A,E,rcond=None)[0];pn=np.linalg.lstsq(A,N,rcond=None)[0]
    return pe,pn,E-A@pe,N-A@pn
P=pts
for it in range(5):
    pe,pn,re,rn=fit(P); v=np.hypot(re,rn); s0=math.sqrt((re@re+rn@rn)/(2*len(P)-6))
    bad=[i for i in range(len(P)) if v[i]>3*s0 and not P[i][0] in W]
    if not bad: break
    print('atilan:',[P[i][0] for i in bad]); P=[p for i,p in enumerate(P) if i not in bad]
print('nokta sayisi',len(P),'(4 kose +',len(P)-4,'karelaj)')
print('E = %.9f*x + %.9f*y + %.4f'%tuple(pe)); print('N = %.9f*x + %.9f*y + %.4f'%tuple(pn))
print('birim agirlik ort. hatasi s0 = %.3f m'%s0)
for p,a,b in zip(P,re,rn): print('%-10s vE=%6.2f vN=%6.2f'%(p[0],a,b))
json.dump(dict(pe=list(pe),pn=list(pn),s0=s0,n=len(P),pts=[[p[0],p[1],p[2],p[3],p[4],float(a),float(b)] for p,a,b in zip(P,re,rn)]),open('fit.json','w'))

# Çıktı üretimi
import numpy as np, json, math
import rasterio
from rasterio.transform import Affine
from rasterio.warp import reproject, Resampling
from rasterio.crs import CRS
from PIL import Image
F=json.load(open('fit_grid.json')); pe,pn=F['pe'],F['pn']
crs=CRS.from_epsg(5253)
# 1) world file for original jpg (index/pixel-center convention)
open('L18A-08C-4A.jgw','w').write('\r\n'.join('%.10f'%v for v in [pe[0],pn[0],pe[1],pn[1],pe[2],pn[2]])+'\r\n')
open('L18A-08C-4A.prj','w').write(crs.to_wkt(version='WKT1_ESRI'))
# 2) north-up GeoTIFF
src=np.array(Image.open('L18A-08C-4A.jpg')); H,Wd=src.shape
st=Affine(pe[0],pe[1],pe[2]-0.5*(pe[0]+pe[1]), pn[0],pn[1],pn[2]-0.5*(pn[0]+pn[1]))
cs=[st*(c,r) for c,r in [(0,0),(Wd,0),(0,H),(Wd,H)]]; res=0.20
x0=math.floor(min(c[0] for c in cs)); y1=math.ceil(max(c[1] for c in cs))
w=int(math.ceil((max(c[0] for c in cs)-x0)/res)); h=int(math.ceil((y1-min(c[1] for c in cs))/res))
dt=Affine(res,0,x0,0,-res,y1); dst=np.full((h,w),255,np.uint8)
reproject(src,dst,src_transform=st,src_crs=crs,dst_transform=dt,dst_crs=crs,resampling=Resampling.cubic,dst_nodata=255)
with rasterio.open('L18A-08C-4A_AFIN_TM27.tif','w',driver='GTiff',height=h,width=w,count=1,dtype='uint8',crs=crs,transform=dt,compress='lzw',nodata=255) as d: d.write(dst,1)
open('L18A-08C-4A_AFIN_TM27.tfw','w').write('\r\n'.join('%.10f'%v for v in [res,0,0,-res,x0+res/2,y1-res/2])+'\r\n')
open('L18A-08C-4A_AFIN_TM27.prj','w').write(crs.to_wkt(version='WKT1_ESRI'))
# 3) GCP report
L=['Nokta;Piksel_x;Piksel_y;Saga(E);Yukari(N);vE(m);vN(m)']+['%s;%.2f;%.2f;%.2f;%.2f;%.3f;%.3f'%tuple(p) for p in F['pts']]
L+=['','Afin parametreleri (piksel merkezi, x sag / y asagi):','E = %.9f*x + %.9f*y + %.4f'%tuple(pe),'N = %.9f*x + %.9f*y + %.4f'%tuple(pn),
    'Nokta sayisi;%d'%F['n'],'Birim agirlik ort. hatasi (m);%.3f'%F['s0'],'Koordinat sistemi;TUREF / ITRF96 TM27 (EPSG:5253)',
    'Cikti GeoTIFF;%dx%d piksel, 0.20 m, sol-ust E=%d N=%d'%(w,h,x0,y1)]
open('L18A-08C-4A_AFIN_RAPOR.csv','w',encoding='utf-8-sig').write('\n'.join(L)+'\n')
print(w,h,x0,y1)
