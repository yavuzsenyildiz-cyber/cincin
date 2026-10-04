import re, json, numpy as np
from shapely.geometry import Polygon, MultiPoint, Point, box
from shapely.ops import voronoi_diagram, unary_union
from shapely import contains_xy
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, cKDTree
from pyproj import Transformer

H0 = 105.07
T0 = np.array([566386.10, 4178494.76])
planes = {float(k): v for k, v in json.load(open("planes.json")).items()}


def plane(L, x, y):
    p = planes[L]
    return p["zw"] + p["s"] * (x - p["xw"]) + p["t"] * (y - p["yw"])


B = json.load(open("buildings.json"))
V = np.array([[float(x) for x in l.split()[1:6]] for l in open("mesh.txt") if l.startswith("V ")])
nat = LinearNDInterpolator(V[:, :2], V[:, 2] - H0)
MEAN = float(np.nanmean(V[:, 2] - H0))


def Tn(x, y):
    z = nat(x, y)
    return np.where(np.isnan(z), MEAN, z)


def T1(x, y):
    z = nat(x, y)
    return float(z) if np.isfinite(z) else MEAN


seeds = {}
for L in (3.82, 5.82, 9.82):
    qs = [q for q in B if q["L"] == L]
    seeds[L] = np.array([[q["cx"], q["cy"], plane(L, q["cx"], q["cy"])] for q in qs])
kd = {L: cKDTree(seeds[L][:, :2]) for L in seeds}


def zcell(L, x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    _, i = kd[L].query(np.c_[x.ravel(), y.ravel()])
    return seeds[L][i, 2].reshape(x.shape)


# yatay teras yuzleri
faces = []
for l in open("faces.txt", encoding="utf-8"):
    if not l.startswith("F "):
        continue
    m = re.match(r"F (\S+) (?:\[(.*?)\]|(\S+)) (.*)", l.strip())
    Pp = np.array([[float(c) for c in p.split(",")] for p in m.group(4).split()])
    ar = 0.5 * abs(np.dot(Pp[:, 0], np.roll(Pp[:, 1], -1)) - np.dot(Pp[:, 1], np.roll(Pp[:, 0], -1)))
    if ar > 0.5 and np.ptp(Pp[:, 2]) < 0.01:
        mat = ("[" + m.group(2) + "]") if m.group(2) else "-"
        faces.append((round(Pp[0, 2], 2), mat, Polygon(Pp[:, :2]).buffer(0), ar))
print("yatay teras yuzu:", len(faces))
U = {L: unary_union([p for z, _, p, _ in faces if abs(z - L) < 0.01]) for L in seeds}

# Voronoi hucreleri (en yakin bina)
cells = {}
for L in seeds:
    pts = MultiPoint([tuple(s[:2]) for s in seeds[L]])
    vd = voronoi_diagram(pts, envelope=box(-80, -40, 280, 170))
    cl = []
    for s in seeds[L]:
        c = [g for g in vd.geoms if g.contains(Point(s[0], s[1]))]
        if c:
            cl.append((c[0].intersection(U[L]), s[2]))
    cells[L] = cl

# yeni yuzler (buyukten kucuge)
newf = []
for z, mat, poly, ar in sorted(faces, key=lambda t: -t[3]):
    L = min(seeds, key=lambda q: abs(q - z))
    for cpoly, zc in cells[L]:
        inter = poly.intersection(cpoly)
        geoms = [inter] if inter.geom_type == "Polygon" else [g for g in getattr(inter, "geoms", []) if g.geom_type == "Polygon"]
        for g in geoms:
            if g.area < 0.02:
                continue
            newf.append((mat, zc, list(g.exterior.coords)[:-1]))
with open("newfaces.txt", "w") as f:
    for mat, zc, ring in newf:
        f.write("F " + mat.replace(" ", "~") + " %.4f " % zc + ";".join("%.3f,%.3f" % (x, y) for x, y in ring) + "\n")
print("yeni yuz:", len(newf))

# kademe duvarlari
quads = []


def lines_of(g):
    if g.geom_type == "LineString":
        return [g]
    return [h for h in getattr(g, "geoms", []) if h.geom_type == "LineString"]


for L in seeds:
    cl = cells[L]
    for i in range(len(cl)):
        for j in range(i + 1, len(cl)):
            a, za = cl[i]
            b, zb = cl[j]
            if a.is_empty or b.is_empty:
                continue
            for g in lines_of(a.boundary.intersection(b.boundary)):
                zl, zh = min(za, zb), max(za, zb)
                if zh - zl < 0.03:
                    continue
                c = list(g.coords)
                for k in range(len(c) - 1):
                    (x1, y1), (x2, y2) = c[k], c[k + 1]
                    if np.hypot(x2 - x1, y2 - y1) < 0.05:
                        continue
                    quads.append((x1, y1, zl, x2, y2, zl, x2, y2, zh, x1, y1, zh))
Ls = sorted(seeds)
for ia in range(3):
    for ib in range(ia + 1, 3):
        A, Bq = Ls[ia], Ls[ib]
        for g in lines_of(U[A].boundary.intersection(U[Bq].buffer(0.25))):
            c = list(g.coords)
            for k in range(len(c) - 1):
                (x1, y1), (x2, y2) = c[k], c[k + 1]
                d = np.hypot(x2 - x1, y2 - y1)
                if d < 0.05:
                    continue
                n = max(1, int(d))
                for s in range(n):
                    t0, t1 = s / n, (s + 1) / n
                    xa, ya = x1 + (x2 - x1) * t0, y1 + (y2 - y1) * t0
                    xb, yb = x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1
                    xm, ym = (xa + xb) / 2, (ya + yb) / 2
                    zA = float(zcell(A, [xm], [ym])[0])
                    zB = float(zcell(Bq, [xm], [ym])[0])
                    zl, zh = min(zA, zB), max(zA, zB)
                    if zh - zl < 0.03:
                        continue
                    quads.append((xa, ya, zl, xb, yb, zl, xb, yb, zh, xa, ya, zh))
with open("risers.txt", "w") as f:
    for q in quads:
        f.write("Q " + " ".join("%.3f" % v for v in q) + "\n")
print("kademe duvar parcasi:", len(quads))

# arazi
x0, x1, y0, y1 = -10, 185, 5, 110
S = 1.0
gx = np.arange(x0, x1 + S, S)
gy = np.arange(y0, y1 + S, S)
GX, GY = np.meshgrid(gx, gy)
E = np.c_[GX.ravel(), GY.ravel()]
zT = Tn(E[:, 0], E[:, 1])
zc = zT.copy()
for L in seeds:
    im = contains_xy(U[L], E[:, 0], E[:, 1])
    pz = zcell(L, E[:, 0], E[:, 1])
    zc = np.where(im, np.minimum(zc, pz - 0.05), zc)
for q in B:
    a, b = q["a"], q["b"]
    mk = (E[:, 0] >= a[0] - 0.8) & (E[:, 0] <= b[0] + 0.8) & (E[:, 1] >= a[1] - 0.8) & (E[:, 1] <= b[1] + 0.8)
    zc = np.where(mk, np.minimum(zc, q["zf"] - 0.05), zc)
print("kazi %.0f m3 | max %.2f m" % (np.clip(zT - zc, 0, None).sum() * S * S, np.max(zT - zc)))
out = V[(V[:, 0] < x0 - 1) | (V[:, 0] > x1 + 1) | (V[:, 1] < y0 - 1) | (V[:, 1] > y1 + 1)]
XY = np.vstack([E, out[:, :2]])
Zk = np.concatenate([zc + H0, out[:, 2]])
tri = Delaunay(XY).simplices
a_, b_, c_ = XY[tri[:, 0]], XY[tri[:, 1]], XY[tri[:, 2]]
ar = (b_[:, 0] - a_[:, 0]) * (c_[:, 1] - a_[:, 1]) - (c_[:, 0] - a_[:, 0]) * (b_[:, 1] - a_[:, 1])
tri[ar < 0] = tri[ar < 0][:, [0, 2, 1]]
tr = Transformer.from_crs("EPSG:5253", "EPSG:4326", always_xy=True)


def merc(xy):
    lon, lat = tr.transform(xy[:, 0] + T0[0], xy[:, 1] + T0[1])
    n = 2 ** 18 * 256
    return np.c_[(lon + 180) / 360 * n, (1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / np.pi) / 2 * n]


M = merc(V[:, :2])
mu = M.mean(0)
A_ = np.c_[M - mu, np.ones(len(M))]
cu = np.linalg.lstsq(A_, V[:, 3], rcond=None)[0]
cv = np.linalg.lstsq(A_, V[:, 4], rcond=None)[0]
Mn = merc(XY) - mu
Uu = Mn @ cu[:2] + cu[2]
Wv = Mn @ cv[:2] + cv[2]
with open("mesh6.txt", "w") as f:
    for (x, y), z, u, v in zip(XY, Zk, Uu, Wv):
        f.write("V %.3f %.3f %.3f %.6f %.6f\n" % (x, y, z, u, v))
    for p, q_, r in tri:
        f.write("F %d %d %d\n" % (p, q_, r))
with open("grid6.txt", "w") as f:
    f.write("%d %d %s %s %s\n" % (len(gx), len(gy), x0, y0, S))
    for r in zc.reshape(GX.shape):
        f.write(" ".join("%.3f" % v for v in r) + "\n")

# agaclar
trees = []
for l in open("C:/Users/YOGA/AppData/Local/Temp/bbox_live.txt", encoding="utf-8"):
    m = re.match(r"(C|G):(.*?) min\(([^)]*)\) max\(([^)]*)\)", l.strip())
    if m and "Cypress" in m.group(2):
        a = [float(v) for v in m.group(3).split(",")]
        b = [float(v) for v in m.group(4).split(",")]
        z = a[2]
        L = min(seeds, key=lambda q: abs(q - z))
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        trees.append((cx, cy, L, z, float(zcell(L, [cx], [cy])[0]) + (z - L)))
with open("trees2.txt", "w") as f:
    for t in trees:
        f.write("%.3f %.3f %s %.3f %.4f\n" % t)
print("agac:", len(trees))

# duvarlar
rows = []
for l in open("walls.txt"):
    x, y, L, h = map(float, l.split())
    P_ = float(zcell(L, [x], [y])[0])
    t = T1(x, y)
    if t < P_ - 0.1:
        base = P_
    elif t > P_ + 0.3:
        ring = [t] + [T1(x + dx, y + dy) for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2), (1.4, 1.4), (-1.4, 1.4), (1.4, -1.4), (-1.4, -1.4))]
        base = max(P_, max(ring) + 0.2 - h)
    else:
        base = max(P_, t) - 0.05
    rows.append((x, y, base))
with open("walls2.txt", "w") as f:
    for x, y, b in rows:
        f.write("%.3f %.3f %.4f\n" % (x, y, b))
print("duvar:", len(rows))

# etek duvarlar
wallc = np.array([[r[0], r[1]] for r in rows])
sq = []
tot = 0.0
for L in seeds:
    bnd = U[L].boundary
    for ln in lines_of(bnd):
        d = ln.length
        if d < 2:
            continue
        s = np.r_[np.arange(0, d, 1.0), d]
        pts = np.array([ln.interpolate(v).coords[0] for v in s])
        for i in range(len(pts) - 1):
            mx, my = (pts[i] + pts[i + 1]) / 2
            if np.min(np.hypot(wallc[:, 0] - mx, wallc[:, 1] - my)) < 3.0:
                continue
            other = False
            for L2 in seeds:
                if L2 == L:
                    continue
                for ox, oy in ((0.8, 0), (-0.8, 0), (0, 0.8), (0, -0.8)):
                    if U[L2].contains(Point(mx + ox, my + oy)):
                        other = True
            if other:
                continue
            pz = [float(zcell(L, [pts[i][0]], [pts[i][1]])[0]), float(zcell(L, [pts[i + 1][0]], [pts[i + 1][1]])[0])]
            tz_ = [T1(*pts[i]), T1(*pts[i + 1])]
            top = [max(a, b) for a, b in zip(pz, tz_)]
            bot = [min(a, b) - 0.05 for a, b in zip(pz, tz_)]
            if max(top[0] - bot[0], top[1] - bot[1]) < 0.25:
                continue
            top = [min(t, b + 5) for t, b in zip(top, bot)]
            sq.append((pts[i][0], pts[i][1], bot[0], top[0], pts[i + 1][0], pts[i + 1][1], bot[1], top[1]))
            tot += float(np.hypot(*(pts[i + 1] - pts[i])))
with open("skirts2.txt", "w") as f:
    for q in sq:
        f.write("Q " + " ".join("%.3f" % v for v in q) + "\n")
print("etek:", len(sq), "parca", round(tot), "m")
