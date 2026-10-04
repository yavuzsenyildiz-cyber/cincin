import ezdxf, numpy as np, csv
from matplotlib.tri import Triangulation, LinearTriInterpolator
O=np.array([566386.10,4178494.76]); H0=105.07
V=[];F=[]
for l in open('pk_merged_mesh.txt'):
    t=l.split()
    if t[0]=='V': V.append([float(x) for x in t[1:4]])
    elif t[0]=='F': F.append([int(x) for x in t[1:4]])
V=np.array(V); it=LinearTriInterpolator(Triangulation(V[:,0],V[:,1],F),V[:,2])
z=lambda p: np.asarray(it(p[:,0],p[:,1]).filled(np.nan))
d=ezdxf.readfile(r"C:/Users/YOGA/OneDrive/MİMARİ/CİNCİN/1_KITLE_YERLESIM/CINCIN_189-tümparseller_kitle_yerlesimson.dxf")
fp=[]
for e in d.modelspace():
    if e.dxf.layer in('0','BINA_115','BINA_116') and e.dxftype() in('LWPOLYLINE','POLYLINE'):
        p=np.array([(x,y) for x,y in e.get_points('xy')] if e.dxftype()=='LWPOLYLINE' else [(v.dxf.location.x,v.dxf.location.y) for v in e.vertices])
        if np.allclose(p[0],p[-1]): p=p[:-1]
        par={'0':'117','BINA_115':'115','BINA_116':'116'}[e.dxf.layer]
        fp.append((par,p))
fp.sort(key=lambda q:(q[0],q[1][:,0].mean()))
rows=[];out=open('bina_iz.txt','w')
for k,(par,p) in enumerate(fp,1):
    m=p-O; zc=z(m)
    # draped outline, 0.5 m sampling
    dr=[]
    for i in range(len(m)):
        a,b=m[i],m[(i+1)%len(m)]; n=max(2,int(np.hypot(*(b-a))/0.5))
        s=np.linspace(0,1,n,endpoint=False)[:,None]; dr.append(a+(b-a)*s)
    dr=np.vstack(dr); dz=z(dr)
    name='P%s-B%02d'%(par,k)
    out.write('B %s %.3f %s | %s\n'%(name,zc.mean(),';'.join('%.3f,%.3f'%tuple(q) for q in m),';'.join('%.3f,%.3f,%.3f'%(q[0],q[1],w) for q,w in zip(dr,dz))))
    for j,(q,r,w) in enumerate(zip(p,m,zc),1):
        rows.append([name,par,j,'%.2f'%q[0],'%.2f'%q[1],'%.2f'%r[0],'%.2f'%r[1],'%.2f'%(w+H0)])
    print(name,'kot min %.2f max %.2f fark %.2f'%(zc.min()+H0,zc.max()+H0,np.ptp(zc)))
out.close()
with open(r"C:/Users/YOGA/OneDrive/MİMARİ/CİNCİN/GUNCEL_D5_SKETCHUP/SketchUp/CINCIN_bina_oturum_koordinat.csv",'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f,delimiter=';'); w.writerow(['bina','parsel','kose','Y_saga (TM27)','X_yukari (TM27)','model_x','model_y','arazi_kotu']); w.writerows(rows)
print(len(fp),'bina')
