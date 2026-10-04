import re, json, numpy as np
from shapely.geometry import Polygon, MultiPoint, Point, box
from shapely.ops import voronoi_diagram, unary_union
from shapely import contains_xy, prepare
from shapely.strtree import STRtree
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, cKDTree
from pyproj import Transformer

H0 = 105.07
T0 = np.array([566386.10, 4178494.76])
SMAX = 0.12      # arac yolu boyuna egim siniri
TMAX = 0.03      # enine egim siniri
LV = (3.82, 5.82, 9.82)
ROAD = {3.82: 109.90, 5.82: 110.80, 9.82: 113.97}   # bati ucundaki yol kotlari

V = np.array([[float(x) for x in l.split()[1:6]] for l in open("mesh.txt") if l.startswith("V ")])
nat = LinearNDInterpolator(V[:, :2], V[:, 2] - H0)
MEAN = float(np.nanmean(V[:, 2] - H0))


def Tn(x, y):
    z = nat(x, y)
    return np.where(np.isnan(z), MEAN, z)


def T1(x, y):
    z = nat(x, y)
    return float(z) if np.isfinite(z) else MEAN


# ---- orijinal yatay yuzler
faces = []
for l in open("faces.txt", encoding="utf-8"):
    if not l.startswith("F "):
        continue
    m = re.match(r"F (\S+) (?:\[(.*?)\]|(\S+)) (.*)", l.strip())
    Pp = np.array([[float(c) for c in p.split(",")] for p in m.group(4).split()])
    ar = 0.5 * abs(np.dot(Pp[:, 0], np.roll(Pp[:, 1], -1)) - np.dot(Pp[:, 1], np.roll(Pp[:, 0], -1)))
    if ar > 0.5 and np.ptp(Pp[:, 2]) < 0.01:
        mat = ("[" + m.group(2) + "]") if m.group(2) else "-"
        L = min(LV, key=lambda q: abs(q - Pp[0, 2]))
        faces.append(dict(L=L, mat=mat, poly=Polygon(Pp[:, :2]).buffer(0), area=ar))
B = json.load(open("buildings.json"))

# ---- yol duzlemleri (bati ucu = yol kotu, egim araziyi izler, sinirli)
planes = {}
for L in LV:
    pav = unary_union([f["poly"] for f in faces if f["L"] == L and "Pavers" in f["mat"]])
    allL = unary_union([f["poly"] for f in faces if f["L"] == L])
    xs, ys = np.meshgrid(np.arange(allL.bounds[0], allL.bounds[2], 0.5), np.arange(allL.bounds[1], allL.bounds[3], 0.5))
    P = np.c_[xs.ravel(), ys.ravel()]
    P = P[contains_xy(pav, P[:, 0], P[:, 1])]
    zn = Tn(P[:, 0], P[:, 1])
    w = P[:, 0] <= P[:, 0].min() + 3
    xw, yw = P[w].mean(0)
    zw = ROAD[L] - H0
    A = np.c_[P[:, 0] - xw, P[:, 1] - yw]
    (s, t), *_ = np.linalg.lstsq(A, zn - zw, rcond=None)
    t = float(np.clip(t, -TMAX, TMAX))
    s = float(np.linalg.lstsq(A[:, :1], zn - zw - t * A[:, 1], rcond=None)[0][0])
    s = float(np.clip(s, -SMAX, SMAX))
    planes[L] = dict(xw=float(xw), yw=float(yw), zw=float(zw), s=s, t=t)
    d = zw + s * A[:, 0] + t * A[:, 1] - zn
    print("yol L=%.2f: giris kotu %.2f (yol %.2f) | boyuna %+.1f%% enine %+.1f%% | arazi farki ort %+.2f min %+.1f max %+.1f" %
          (L, zw + H0, ROAD[L], s * 100, t * 100, d.mean(), d.min(), d.max()))


def plane(L, x, y):
    p = planes[L]
    return p["zw"] + p["s"] * (np.asarray(x) - p["xw"]) + p["t"] * (np.asarray(y) - p["yw"])


# ---- Oneri A: P116 dogu bolumu (x>69 binalar + dogu yol parcasi) yukseltilir, P115 yolundan girilir
OPT = json.load(open("optA.json"))
RAISE = float(OPT["raise_"])
RAMP_W = 3.0   # baglanti rampasi derinligi (m)


def raised(q):
    return q["L"] == 5.82 and q["cx"] > 69


# ---- binalar: kat = yol duzlemi (bina merkezinde)
for q in B:
    off = RAISE if raised(q) else 0.0
    q["floor"] = float(plane(q["L"], q["cx"], q["cy"])) + (q["zb"] - q["L"]) + off
    q["pad"] = float(plane(q["L"], q["cx"], q["cy"])) + off
seeds = {L: [q for q in B if q["L"] == L] for L in LV}

# ---- Voronoi hucreleri (yol disi alanlar en yakin binaya)
cells = {}
for L in LV:
    pts = MultiPoint([(q["cx"], q["cy"]) for q in seeds[L]])
    vd = voronoi_diagram(pts, envelope=box(-80, -40, 280, 170))
    cl = []
    for q in seeds[L]:
        c = [g for g in vd.geoms if g.contains(Point(q["cx"], q["cy"]))]
        cl.append((c[0], q))
    cells[L] = cl

# ---- parcalar: yol (egimli) + platform/cim (yatay)
pieces = []   # dict(poly, L, kind, z, mat)


def polys_of(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [h for h in getattr(g, "geoms", []) if h.geom_type == "Polygon"]


for L in LV:
    others = [f for f in faces if f["L"] == L and "Pavers" not in f["mat"]]
    pads = []
    for c, q in cells[L]:
        a, b = q["a"], q["b"]
        pad = box(a[0] - 0.2, a[1] - 0.2, b[0] + 0.2, b[1] + 0.2).intersection(c)
        # (pad z degeri q["pad"]; yukseltilen binalarda RAISE dahil)
        for g in polys_of(pad):
            pads.append(dict(poly=g, L=L, kind="pad", z=q["pad"], mat="-", area=g.area))
    # yol disi yuzler: hucrelere bol
    nonstreet = []
    for f in sorted(others, key=lambda f: -f["area"]):
        for c, q in cells[L]:
            for g in polys_of(f["poly"].intersection(c)):
                if g.area > 0.05:
                    nonstreet.append(dict(poly=g, L=L, kind="pad", z=q["pad"], mat=f["mat"], area=g.area))
    pav = unary_union([f["poly"] for f in faces if f["L"] == L and "Pavers" in f["mat"]])
    block = unary_union([p["poly"] for p in pads + nonstreet])
    street = pav.difference(block).buffer(0)
    pmat = max([f for f in faces if f["L"] == L and "Pavers" in f["mat"]], key=lambda f: f["area"])["mat"]
    sp = [g for g in polys_of(street) if g.area > 0.5]
    big = max(sp, key=lambda g: g.area) if L == 5.82 else None
    for g in sp:
        pieces.append(dict(poly=g, L=L, kind="street", z=None, mat=pmat, area=g.area, off=(RAISE if g is big else 0.0), east=(g is big)))
    pieces += pads + nonstreet

# baglanti rampasi: P116 dogu yolu ile P115 yolunun ortak siniri boyunca, P116 tarafinda RAMP_W derinliginde
east = [p for p in pieces if p.get("east")][0]
p115 = unary_union([p["poly"] for p in pieces if p["kind"] == "street" and p["L"] == 9.82])
shared = east["poly"].boundary.intersection(p115.buffer(0.6))
band = east["poly"].intersection(shared.buffer(RAMP_W)).buffer(0)
rest = east["poly"].difference(band).buffer(0)
pieces.remove(east)
for g in polys_of(rest):
    if g.area > 0.3:
        pieces.append(dict(poly=g, L=5.82, kind="street", z=None, mat=east["mat"], area=g.area, off=RAISE, east=True))
SH = shared


def ramp_z(x, y):
    d = SH.distance(Point(x, y))
    w = max(0.0, 1.0 - d / RAMP_W)
    lo = float(plane(5.82, x, y)) + RAISE
    hi = float(plane(9.82, x, y))
    return lo + (hi - lo) * w


from shapely.ops import triangulate
nramp = 0
for g in polys_of(band):
    gd = g.segmentize(1.0)
    for t in triangulate(gd):
        if t.area > 0.01 and g.buffer(0.01).contains(t.centroid):
            pieces.append(dict(poly=t, L=5.82, kind="ramp", z=None, mat=east["mat"], area=t.area))
            nramp += 1
print("parca:", len(pieces), "| yol parcasi:", sum(1 for p in pieces if p["kind"] == "street"), "| rampa ucgeni:", nramp,
      "| rampa uzunlugu %.1f m, egim ~%%%.1f" % (SH.length, (float(plane(9.82, SH.centroid.x, SH.centroid.y)) - float(plane(5.82, SH.centroid.x, SH.centroid.y)) - RAISE) / RAMP_W * 100))


def hgt(p, x, y):
    if p["kind"] == "street":
        return float(plane(p["L"], x, y)) + p.get("off", 0.0)
    if p["kind"] == "ramp":
        return ramp_z(x, y)
    return p["z"]


# ---- yuzler
order = [p for p in pieces if p["kind"] == "street"] + sorted([p for p in pieces if p["kind"] != "street"], key=lambda p: -p["area"])
with open("dfaces.txt", "w") as f:
    for p in order:
        rings = [list(p["poly"].exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in p["poly"].interiors]
        txt = " | ".join(";".join("%.3f,%.3f,%.4f" % (x, y, hgt(p, x, y)) for x, y in r) for r in rings)
        f.write("P " + p["mat"].replace(" ", "~") + " " + txt + "\n")

# ---- komsuluk: kademe/bordur duvarlari + dis kenar etekleri
for p in pieces:
    prepare(p["poly"])
tree = STRtree([p["poly"] for p in pieces])
wallc = np.array([[float(v) for v in l.split()[:2]] for l in open("walls.txt")])
risers, skirts = [], []
rmax = 0.0
for i, p in enumerate(pieces):
    rings = [p["poly"].exterior] + list(p["poly"].interiors)
    for r in rings:
        c = list(r.coords)
        for k in range(len(c) - 1):
            (x1, y1), (x2, y2) = c[k], c[k + 1]
            d = np.hypot(x2 - x1, y2 - y1)
            if d < 0.05:
                continue
            n = max(1, int(np.ceil(d)))
            nx_, ny_ = -(y2 - y1) / d, (x2 - x1) / d
            for s_ in range(n):
                xa, ya = x1 + (x2 - x1) * s_ / n, y1 + (y2 - y1) * s_ / n
                xb, yb = x1 + (x2 - x1) * (s_ + 1) / n, y1 + (y2 - y1) * (s_ + 1) / n
                mx, my = (xa + xb) / 2, (ya + yb) / 2
                q1 = Point(mx + 0.3 * nx_, my + 0.3 * ny_)
                q2 = Point(mx - 0.3 * nx_, my - 0.3 * ny_)
                out = q1 if not p["poly"].contains(q1) else (q2 if not p["poly"].contains(q2) else None)
                if out is None:
                    continue
                cand = [j for j in tree.query(out) if j != i and pieces[j]["poly"].contains(out)]
                if cand:
                    j = cand[0]
                    if j < i:
                        continue
                    za = [hgt(p, xa, ya), hgt(p, xb, yb)]
                    zb_ = [hgt(pieces[j], xa, ya), hgt(pieces[j], xb, yb)]
                    lo = [min(u, v) for u, v in zip(za, zb_)]
                    hi = [max(u, v) for u, v in zip(za, zb_)]
                    if max(hi[0] - lo[0], hi[1] - lo[1]) < 0.03:
                        continue
                    rmax = max(rmax, hi[0] - lo[0], hi[1] - lo[1])
                    risers.append((xa, ya, lo[0], xb, yb, lo[1], xb, yb, hi[1], xa, ya, hi[0]))
                else:
                    if len(wallc) and np.min(np.hypot(wallc[:, 0] - mx, wallc[:, 1] - my)) < 3.0:
                        continue
                    za = [hgt(p, xa, ya), hgt(p, xb, yb)]
                    tz = [T1(xa, ya), T1(xb, yb)]
                    top = [max(u, v) for u, v in zip(za, tz)]
                    bot = [min(u, v) - 0.05 for u, v in zip(za, tz)]
                    if max(top[0] - bot[0], top[1] - bot[1]) < 0.25:
                        continue
                    top = [min(u, v + 6) for u, v in zip(top, bot)]
                    skirts.append((xa, ya, bot[0], xb, yb, bot[1], xb, yb, top[1], xa, ya, top[0]))
with open("drisers.txt", "w") as f:
    for q in risers:
        f.write("Q " + " ".join("%.3f" % v for v in q) + "\n")
with open("dskirts.txt", "w") as f:
    for q in skirts:
        f.write("Q " + " ".join("%.3f" % v for v in q) + "\n")
print("bordur/kademe duvari: %d parca (en yuksek %.2f m) | dis etek: %d parca" % (len(risers), rmax, len(skirts)))


def surf(L, x, y):
    pt = Point(x, y)
    for j in tree.query(pt):
        if pieces[j]["L"] == L and pieces[j]["poly"].contains(pt):
            return hgt(pieces[j], x, y)
    for j in tree.query(pt):
        if pieces[j]["poly"].contains(pt):
            return hgt(pieces[j], x, y)
    return float(plane(L, x, y))


# ---- binalar
with open("dbuild.txt", "w") as f:
    for q in B:
        f.write("%.3f %.3f %.4f\n" % (q["cx"], q["cy"], q["floor"] - q["zb"]))

# ---- agaclar
with open("dtrees.txt", "w") as f:
    for l in open("C:/Users/YOGA/AppData/Local/Temp/bbox_live.txt", encoding="utf-8"):
        m = re.match(r"(C|G):(.*?) min\(([^)]*)\) max\(([^)]*)\)", l.strip())
        if m and "Cypress" in m.group(2):
            a = [float(v) for v in m.group(3).split(",")]
            b = [float(v) for v in m.group(4).split(",")]
            L = min(LV, key=lambda q: abs(q - a[2]))
            cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            f.write("%.3f %.3f %.4f\n" % (cx, cy, surf(L, cx, cy) + (a[2] - L)))

# ---- arazi (kazi: tasarim yuzeyi - 0.05, bina izi)
x0, x1, y0, y1 = -10, 185, 5, 110
S = 1.0
gx = np.arange(x0, x1 + S, S)
gy = np.arange(y0, y1 + S, S)
GX, GY = np.meshgrid(gx, gy)
E = np.c_[GX.ravel(), GY.ravel()]
zT = Tn(E[:, 0], E[:, 1])
zc = zT.copy()
for p in pieces:
    im = contains_xy(p["poly"], E[:, 0], E[:, 1])
    if not im.any():
        continue
    if p["kind"] == "street":
        hz = plane(p["L"], E[im, 0], E[im, 1]) + p.get("off", 0.0)
    elif p["kind"] == "ramp":
        hz = np.array([ramp_z(x, y) for x, y in E[im]])
    else:
        hz = np.full(im.sum(), p["z"])
    zc[im] = np.minimum(zc[im], hz - 0.05)
for q in B:
    a, b = q["a"], q["b"]
    mk = (E[:, 0] >= a[0] - 0.5) & (E[:, 0] <= b[0] + 0.5) & (E[:, 1] >= a[1] - 0.5) & (E[:, 1] <= b[1] + 0.5)
    zc[mk] = np.minimum(zc[mk], q["floor"] - 0.05)
print("kazi %.0f m3 | max %.2f m" % (np.clip(zT - zc, 0, None).sum() * S * S, np.max(zT - zc)))
with open("grid7.txt", "w") as f:
    f.write("%d %d %s %s %s\n" % (len(gx), len(gy), x0, y0, S))
    for r in zc.reshape(GX.shape):
        f.write(" ".join("%.3f" % v for v in r) + "\n")
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
with open("mesh7.txt", "w") as f:
    for (x, y), z, u, v in zip(XY, Zk, Mn @ cu[:2] + cu[2], Mn @ cv[:2] + cv[2]):
        f.write("V %.3f %.3f %.3f %.6f %.6f\n" % (x, y, z, u, v))
    for p, q_, r in tri:
        f.write("F %d %d %d\n" % (p, q_, r))

# ---- bahce citleri: taban kotu
rows = []
for l in open("walls.txt"):
    x, y, L, h = map(float, l.split())
    P_ = surf(L, x, y)
    t = T1(x, y)
    if t < P_ - 0.1:
        base = P_
    elif t > P_ + 0.3:
        ring = [t] + [T1(x + dx, y + dy) for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2), (1.4, 1.4), (-1.4, 1.4), (1.4, -1.4), (-1.4, -1.4))]
        base = max(P_, max(ring) + 0.2 - h)
    else:
        base = max(P_, t) - 0.05
    rows.append((x, y, base))
with open("dwalls.txt", "w") as f:
    for x, y, b in rows:
        f.write("%.3f %.3f %.4f\n" % (x, y, b))

# ---- ozet: arac yolu kontrolu
json.dump({str(k): v for k, v in planes.items()}, open("dplanes.json", "w"))
for L in LV:
    p = planes[L]
    g = np.hypot(p["s"], p["t"]) * 100
    print("ARAC YOLU L=%.2f: bilesik egim %.1f%% (%s)" % (L, g, "uygun" if abs(p["s"]) <= SMAX and abs(p["t"]) <= TMAX else "SINIRDA"))
fl = np.array([q["floor"] - q["zb"] for q in B])
print("bina kot degisimi: ort %+.2f min %+.2f max %+.2f m" % (fl.mean(), fl.min(), fl.max()))
