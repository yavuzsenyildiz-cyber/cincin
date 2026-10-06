# Iki yuzey arasinda kalan acikligi (ornek: tas duvar ile ustteki egimli tas yuzey arasindaki ince ucgen bosluk) kapatir.
# Kullanim:
#   1) Acikligin etrafindaki yuzeyleri/kenarlari secin (grubun icine girip), YA DA aciklik iki ayri grup arasindaysa
#      o iki grubu (gerekirse kolonu da) disaridan secin.
#   2) Ruby Console'a:  load "C:/cincin_terrain/aciklik_kapat.rb"
# Script yalnizca tek yuzlu (acik) kenarlari izler, bunlari 1 cm toleransla birlestirir, 1.5 m'ye kadar kopukluklari
# duz cizgiyle baglar ve olusan her kapali halkayi yuzeyle kapatir. Yeni yuzeyler komsu yuzeyin malzemesini (iki yuzune
# de) alir. Secili yuzeylerden malzemesi olmayanlar da (arka yuz grisi gorunenler) komsu tas malzemesiyle boyanir.
# Sonuc begenilmezse tek Ctrl+Z ile geri alinir.
dir = File.dirname(__FILE__) + "/"
TOL = 0.01.m
MAXGAP = 1.5.m
begin
  m = Sketchup.active_model
  sel = m.selection.to_a
  raise "Once acikligin cevresindeki yuzeyleri/kenarlari veya iki grubu secin" if sel.empty?
  et = m.edit_transform
  segs = [] # [p1, p2, kaynak_etiketi, komsu_yuz]
  mats = Hash.new(0)
  bare = []

  border = lambda do |e, tr, tag|
    next unless e.faces.length <= 1
    segs << [e.start.position.transform(tr), e.end.position.transform(tr), tag, e.faces.first]
  end
  scan = lambda do |ents, tr, tag|
    ents.each do |x|
      case x
      when Sketchup::Face
        mats[x.material] += x.area if x.material
        x.edges.each { |e| border.(e, tr, tag) }
      when Sketchup::Group, Sketchup::ComponentInstance
        scan.(x.definition.entities, tr * x.transformation, tag)
      end
    end
  end

  tags = []
  sel.each do |x|
    case x
    when Sketchup::Face
      mats[x.material] += x.area if x.material
      bare << x if x.material.nil? && x.back_material.nil?
      x.edges.each { |e| border.(e, et, :ctx) }
      tags << :ctx
    when Sketchup::Edge
      border.(x, et, :ctx); tags << :ctx
    when Sketchup::Group, Sketchup::ComponentInstance
      scan.(x.definition.entities, et * x.transformation, x.entityID); tags << x.entityID
    end
  end
  segs.uniq! { |s| [s[0].to_a.map { |q| q.round(3) }, s[1].to_a.map { |q| q.round(3) }].sort }

  # Birden fazla grup seciliyse: yalnizca baska bir grubun acik kenarina MAXGAP'ten yakin kenarlar (yani bosluga bakanlar)
  if tags.uniq.length > 1 && tags.any? { |t| t != :ctx }
    pd = lambda do |p, a, b|
      ab = b - a; l2 = ab.dot(ab)
      return p.distance(a) if l2 == 0
      t = [[(p - a).dot(ab) / l2, 0.0].max, 1.0].min
      p.distance(Geom::Point3d.new(a.x + ab.x * t, a.y + ab.y * t, a.z + ab.z * t))
    end
    sd = lambda do |s, u|
      mid = ->(a, b) { Geom::Point3d.new((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2) }
      [pd.(s[0], u[0], u[1]), pd.(s[1], u[0], u[1]), pd.(mid.(s[0], s[1]), u[0], u[1]),
       pd.(u[0], s[0], s[1]), pd.(u[1], s[0], s[1])].min
    end
    cell = ->(p) { [(p.x / MAXGAP).floor, (p.y / MAXGAP).floor, (p.z / MAXGAP).floor] }
    grid = Hash.new { |h, k| h[k] = [] }
    segs.each_with_index { |s, i| [s[0], s[1]].each { |p| grid[cell.(p)] << i } }
    segs = segs.each_with_index.select do |s, i|
      near = []
      [s[0], s[1]].each do |p|
        c = cell.(p)
        [-1, 0, 1].product([-1, 0, 1], [-1, 0, 1]).each { |d| near.concat(grid[[c[0] + d[0], c[1] + d[1], c[2] + d[2]]]) }
      end
      near.uniq.any? { |j| segs[j][2] != s[2] && sd.(s, segs[j]) <= MAXGAP }
    end.map(&:first)
  end

  # Kenar ucu noktalarini toleransla birlestir, graf kur
  pts = []
  vid = lambda do |p|
    i = pts.index { |q| q.distance(p) <= TOL }
    i || (pts << p; pts.length - 1)
  end
  adj = Hash.new { |h, k| h[k] = [] }
  nbr = {}
  segs.each do |a, b, _t, f|
    i, j = vid.(a), vid.(b)
    next if i == j || adj[i].include?(j)
    adj[i] << j; adj[j] << i
    nbr[[i, j].sort] = f
  end

  len = ->(i, j) { pts[i].distance(pts[j]) }
  # 1) Tamamen acik kenarlarla cevrili delikler: tum dugumleri 2 dereceli bilesenler
  loops = []
  seen = {}
  adj.keys.each do |s|
    next if seen[s]
    comp = []; st = [s]
    until st.empty?
      v = st.pop; next if seen[v]
      seen[v] = true; comp << v; st.concat(adj[v])
    end
    next unless comp.length > 2 && comp.all? { |v| adj[v].length == 2 }
    l = [s]; prev = nil
    loop { nx = adj[l.last].find { |w| w != prev && w != l[-1] }; break if nx.nil? || nx == s; prev = l.last; l << nx }
    loops << l
  end
  # 2) Kopuk uclar: her bostaki ucu (tek kenarli dugum) MAXGAP icindeki en yakin komsu olmayan dugume kopruyle bagla,
  #    sonra koprunun iki ucu arasindaki en kisa kenar yolunu bul -> halka = yol + kopru
  bridges = []
  adj.keys.select { |v| adj[v].length == 1 }.each do |u|
    c = adj.keys.reject { |w| w == u || adj[u].include?(w) }.min_by { |w| len.(u, w) }
    next unless c && len.(u, c) <= MAXGAP
    bridges << [u, c].sort
  end
  bridges.uniq!
  bridges.each { |u, w| adj[u] << w; adj[w] << u }
  bridges.each do |u, w|
    dist = { u => 0.0 }; from = {}; todo = [u]; done = {}
    until todo.empty?
      x = todo.min_by { |q| dist[q] }; todo.delete(x)
      next if done[x]
      done[x] = true
      break if x == w
      adj[x].each do |y|
        next if (x == u && y == w) || (x == w && y == u)
        d = dist[x] + len.(x, y)
        next if d > 300.m
        if dist[y].nil? || d < dist[y] then dist[y] = d; from[y] = x; todo << y end
      end
    end
    next unless from[w]
    l = [w]; l << from[l.last] while l.last != u
    loops << l
  end
  loops.uniq! { |l| l.sort }
  loops.reject! { |l| l.length < 3 }
  raise "Kapatilacak kapali aciklik bulunamadi (acik kenar=#{segs.length}). Acikligin cevresini daha net secin." if loops.empty? && bare.empty?

  dom = mats.max_by { |_k, v| v }
  dmat = dom && dom[0]
  m.start_operation("Aciklik kapat", true)
  ents = m.active_entities
  inv = et.inverse
  nf = 0; nt = 0; bad = []
  loops.each_with_index do |l, li|
    wp = l.map { |i| pts[i] }
    lp = wp.map { |p| p.transform(inv) }
    fmat = nil
    l.each_with_index { |i, k| f = nbr[[i, l[(k + 1) % l.length]].sort]; (fmat = f.material; break) if f && f.material }
    fmat ||= dmat
    plane = Geom.fit_plane_to_points(lp)
    flat = lp.all? { |p| p.distance_to_plane(plane) < 5.mm }
    done = false
    if flat
      begin
        fc = ents.add_face(lp)
        if fc then fc.material = fmat; fc.back_material = fmat; nf += 1; done = true end
      rescue
      end
    end
    next if done
    # duzlemsel degil: duzleme izdusumde kulak kirpma ile ucgenle
    n = Geom::Vector3d.new(plane[0], plane[1], plane[2])
    ax = n.axes
    uv = lp.map { |p| v = p - ORIGIN; [v.dot(ax[0]), v.dot(ax[1])] }
    area = 0.0
    uv.each_with_index { |a, k| b = uv[(k + 1) % uv.length]; area += a[0] * b[1] - b[0] * a[1] }
    idx = (0...lp.length).to_a
    idx.reverse! if area < 0
    cross = ->(o, a, b) { (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]) }
    inside = lambda do |p, a, b, c|
      cross.(a, b, p) >= 0 && cross.(b, c, p) >= 0 && cross.(c, a, p) >= 0
    end
    tris = []
    guard = 0
    while idx.length > 3 && guard < 10000
      guard += 1
      k = (0...idx.length).find do |q|
        i0, i1, i2 = idx[q - 1], idx[q], idx[(q + 1) % idx.length]
        cross.(uv[i0], uv[i1], uv[i2]) > 0 &&
          idx.none? { |j| ![i0, i1, i2].include?(j) && inside.(uv[j], uv[i0], uv[i1], uv[i2]) }
      end
      k ||= 0 # cok ince / kendini kesen halkada yine de ilerle
      tris << [idx[k - 1], idx[k], idx[(k + 1) % idx.length]]
      idx.delete_at(k)
    end
    tris << idx if idx.length == 3
    pm = Geom::PolygonMesh.new(lp.length, tris.length)
    pi = lp.map { |p| pm.add_point(p) }
    tris.each { |a, b, c| pm.add_polygon(pi[a], pi[b], pi[c]) rescue nil }
    begin
      g = ents.add_group; g.name = "ACIKLIK_KAPAMA_#{li + 1}"
      g.entities.add_faces_from_mesh(pm, Geom::PolygonMesh::AUTO_SOFTEN | Geom::PolygonMesh::SMOOTH_SOFT_EDGES, fmat, fmat)
      g.explode
      nt += 1
    rescue => e
      bad << "halka#{li + 1}: #{e.message[0, 60]}"
    end
  end
  bare.each { |f| next unless f.valid?; f.material = dmat; f.back_material = dmat }
  m.commit_operation
  msg = "OK kapatilan_aciklik=#{nf + nt} (duz=#{nf}, ucgenlenmis=#{nt}) boyanan_yuz=#{bare.length} " \
        "malzeme=#{dmat ? dmat.display_name : '-'} acik_kenar=#{segs.length}#{bad.empty? ? '' : ' HATA: ' + bad.join(' / ')}"
  File.write(dir + "aciklik_result.txt", msg) rescue nil
  puts msg
  UI.messagebox(msg)
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  msg = "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}"
  File.write(dir + "aciklik_result.txt", msg) rescue nil
  puts msg
  UI.messagebox(msg)
end
