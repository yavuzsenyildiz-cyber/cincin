import json,numpy as np
from matplotlib.tri import Triangulation, LinearTriInterpolator
H0=105.07; W=4.0; SMAX=0.12
V=[];F=[]
for l in open('pk_merged_mesh.txt'):
    t=l.split()
    if t[0]=='V': V.append([float(x) for x in t[1:4]])
    elif t[0]=='F': F.append([int(x) for x in t[1:4]])
V=np.array(V); it=LinearTriInterpolator(Triangulation(V[:,0],V[:,1],F),V[:,2])
nat=lambda p: np.asarray(it(p[:,0],p[:,1]).filled(np.nan))
J=json.load(open('tesviye.json')); Z=np.array(J['Z'])
ROADS={'YOL1':((21.06,74.22),(162.98,82.66),-3.0,138.0),'YOL2':((33.60,60.91),(135.21,67.05),-3.0,100.0)}
out={}
for nm,(a,b,u0,u1) in ROADS.items():
    a=np.array(a);b=np.array(b);t=(b-a)/np.linalg.norm(b-a);n=np.array([-t[1],t[0]])
    u=np.arange(u0,u1+0.01,1.0); C=a+u[:,None]*t
    zn=nat(C)
    # komsu platformlar
    tgt=zn.copy(); adj=[]
    for k,f in enumerate(J['fp']):
        f=np.array(f); s=(f-a)@n; uu=(f-a)@t
        if abs(s).min()<4:
            adj.append(J['names'][k]); m=(u>=uu.min()-2)&(u<=uu.max()+2)
            tgt[m]=np.where(np.isnan(tgt[m])|(tgt[m]==zn[m]),Z[k],(tgt[m]+Z[k])/2)
    z=np.empty_like(u); z[0]=zn[0]
    for i in range(1,len(u)): z[i]=np.clip(tgt[i],z[i-1]-SMAX,z[i-1]+SMAX)
    for i in range(len(u)-2,0,-1): z[i]=np.clip(z[i],z[i+1]-SMAX,z[i+1]+SMAX)
    z[0]=zn[0]
    print(nm,'baslangic (genel yol) kot %.2f'%(zn[0]+H0),'komsu yapilar',adj)
    for k in adj:
        i=J['names'].index(k); f=np.array(J['fp'][i]); uu=(f-a)@t; m=(u>=uu.min())&(u<=uu.max())
        print('   %s platform %.2f | yol kotu bu yapi onunde %.2f..%.2f | fark %.2f..%.2f'%(k,Z[i]+H0,z[m].min()+H0,z[m].max()+H0,(z[m]-Z[i]).min(),(z[m]-Z[i]).max()))
    g=np.abs(np.diff(z)); print('   max boyuna egim %.1f%%  uzunluk %.0f m'%(g.max()*100,u1-u0))
    out[nm]=dict(a=a.tolist(),t=t.tolist(),n=n.tolist(),u=u.tolist(),z=z.tolist(),zn=zn.tolist(),W=W)
json.dump(out,open('yollar.json','w'))
