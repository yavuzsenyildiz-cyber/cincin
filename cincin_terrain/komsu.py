# Komsu parsel tasarimlarini (p11Xy_poly.txt + p11Xy_mesh.txt + p11Xy_agiz.txt) okur.
# Her parsel betigi komsularinin tasarim kotlarini kullanir: ortak sinirda duvari yuksek taraf kurar,
# parsel disi kot komsunun tasarim yuzeyinden okunur, dogal arazi kenari tek sahipce (115) uretilir.
import os, numpy as np, shapely.wkt
from shapely.geometry import Polygon
from scipy.interpolate import LinearNDInterpolator

def yukle(pfx, shared=None):
    if not (os.path.exists(pfx+'poly.txt') and os.path.exists(pfx+'mesh.txt')): return None
    poly=Polygon([tuple(map(float,q.split(','))) for q in open(pfx+'poly.txt').read().split()[0].split(';')])
    v=[]; fc=[]
    for l in open(pfx+'mesh.txt'):
        t=l.split()
        if t[0]=='V': v.append([float(q) for q in t[1:4]])
        elif t[0]=='F': fc.append([int(q) for q in t[1:4]])
    v=np.array(v); fc=np.array(fc)
    u=v[fc[:,1],:2]-v[fc[:,0],:2]; w=v[fc[:,2],:2]-v[fc[:,0],:2]
    fc=fc[np.abs(u[:,0]*w[:,1]-u[:,1]*w[:,0])>1e-4]                        # dikey/dejenere yuzler atilir
    ui=np.unique(fc); I=LinearNDInterpolator(v[ui][:,:2],v[ui][:,2])
    z=lambda x,y: np.asarray(I(np.asarray(x,float),np.asarray(y,float)),float)
    agiz=shapely.wkt.loads(open(pfx+'agiz.txt').read()) if os.path.exists(pfx+'agiz.txt') else None
    return dict(pfx=pfx,poly=poly,z=z,shared=shared,agiz=agiz)
