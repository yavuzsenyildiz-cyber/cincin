# Teras kademeleri: her bina icin yatay platform (Voronoi hucresi), aralarinda tas basamak duvari.
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  stone = m.materials["[Brick_Tumbled]"] || m.materials["ETEK_DUVAR"] || m.materials.add("ETEK_DUVAR")
  m.start_operation("Teras kademeleri", true)

  # 1) eski egimli teras yuzleri + eski duvar/etek gruplari
  %w[ISTINAT_TERAS_KENAR ISTINAT_BAHCE_DUVAR ISTINAT_RISER_ALT TERAS_KADEME].each do |nm|
    m.entities.grep(Sketchup::Group).select { |g| g.name == nm }.each(&:erase!)
  end
  old_faces = m.entities.grep(Sketchup::Face)
  old_edges = old_faces.flat_map(&:edges).uniq
  nold = old_faces.length
  m.entities.erase_entities(old_faces)
  old_edges.each { |e| e.erase! if e.valid? && e.faces.empty? }

  # 2) yeni yatay teras yuzleri (buyukten kucuge)
  nf = 0; bad = 0
  File.foreach(dir + "newfaces.txt") do |ln|
    t = ln.split(" ", 4); next unless t[0] == "F"
    mat = m.materials[t[1].tr("~", " ")]
    z = t[2].to_f
    pts = t[3].split(";").map { |p| x, y = p.split(",").map(&:to_f); Geom::Point3d.new(x.m, y.m, z.m) }
    begin
      f = m.entities.add_face(pts)
      f.reverse! if f.normal.z < 0
      if mat then f.material = mat; f.back_material = mat end
      nf += 1
    rescue
      bad += 1
    end
  end

  # 3) kademe (basamak) duvarlari
  g = m.entities.add_group; g.name = "TERAS_KADEME"; g.layer = m.layers.add("ISTINAT")
  nq = 0
  File.foreach(dir + "risers.txt") do |ln|
    t = ln.split; next unless t[0] == "Q"
    v = t[1..12].map(&:to_f)
    pts = (0..3).map { |i| Geom::Point3d.new(v[i * 3].m, v[i * 3 + 1].m, v[i * 3 + 2].m) }
    begin
      f = g.entities.add_face(pts); f.material = stone; f.back_material = stone; nq += 1
    rescue
    end
  end

  # 4) agaclar
  T = {}
  File.foreach(dir + "trees2.txt") { |ln| a = ln.split.map(&:to_f); T["%.2f,%.2f" % [a[0], a[1]]] = a[4] }
  nt = 0
  m.entities.grep(Sketchup::ComponentInstance).each do |e|
    next unless e.definition.name.include?("Cypress")
    b = e.bounds
    k = "%.2f,%.2f" % [(b.min.x + b.max.x).to_m / 2.0, (b.min.y + b.max.y).to_m / 2.0]
    tz = T[k]; next unless tz
    d = tz - b.min.z.to_m
    next if d.abs < 0.005
    e.transform!(Geom::Transformation.new(Geom::Vector3d.new(0, 0, d.m))); nt += 1
  end

  # 5) cit duvarlari + tas tabanlar
  W = File.readlines(dir + "walls2.txt", chomp: true).map { |l| a = l.split.map(&:to_f); { x: a[0], y: a[1], z: a[2] } }
  lines = File.readlines(dir + "grid6.txt", chomp: true)
  nx, ny, gx0, gy0, st = lines[0].split.map(&:to_f); nx = nx.to_i; ny = ny.to_i
  tz = lines[1, ny].map { |r| r.split.map(&:to_f) }
  terr = lambda do |x, y|
    i = ((x - gx0) / st).clamp(0, nx - 1.001); j = ((y - gy0) / st).clamp(0, ny - 1.001)
    i0 = i.floor; j0 = j.floor; fi = i - i0; fj = j - j0
    (tz[j0][i0] * (1 - fi) + tz[j0][i0 + 1] * fi) * (1 - fj) + (tz[j0 + 1][i0] * (1 - fi) + tz[j0 + 1][i0 + 1] * fi) * fj
  end
  gb = m.entities.add_group; gb.name = "ISTINAT_BAHCE_DUVAR"; gb.layer = m.layers.add("ISTINAT")
  nw = 0; nb = 0
  m.entities.grep(Sketchup::ComponentInstance).each do |e|
    next unless e.definition.name.start_with?("Modern")
    b = e.bounds
    cx = (b.min.x + b.max.x).to_m / 2.0; cy = (b.min.y + b.max.y).to_m / 2.0
    w = W.min_by { |q| (q[:x] - cx)**2 + (q[:y] - cy)**2 }
    next if (w[:x] - cx)**2 + (w[:y] - cy)**2 > 0.05**2
    d = w[:z] - b.min.z.to_m
    e.transform!(Geom::Transformation.new(Geom::Vector3d.new(0, 0, d.m))) if d.abs > 0.005
    nw += 1
    zf = w[:z]
    t = e.transformation; lb = e.definition.bounds
    cn = [[lb.min.x, lb.min.y], [lb.max.x, lb.min.y], [lb.max.x, lb.max.y], [lb.min.x, lb.max.y]].map { |lx, ly| q = t * Geom::Point3d.new(lx, ly, lb.min.z); [q.x.to_m, q.y.to_m] }
    sm = []
    5.times { |a| 5.times { |c| u = a / 4.0; v = c / 4.0
      px = (cn[0][0] * (1 - u) + cn[1][0] * u) * (1 - v) + (cn[3][0] * (1 - u) + cn[2][0] * u) * v
      py = (cn[0][1] * (1 - u) + cn[1][1] * u) * (1 - v) + (cn[3][1] * (1 - u) + cn[2][1] * u) * v
      sm << terr.call(px, py) } }
    zb = sm.min - 0.15
    next if zf - zb < 0.05
    pb = cn.map { |x, y| Geom::Point3d.new(x.m, y.m, zb.m) }
    pt = cn.map { |x, y| Geom::Point3d.new(x.m, y.m, zf.m) }
    ([pt] + (0..3).map { |i| j = (i + 1) % 4; [pb[i], pb[j], pt[j], pt[i]] }).each do |pts|
      begin; f = gb.entities.add_face(pts); f.material = stone; f.back_material = stone; rescue; end
    end
    nb += 1
  end

  # 6) etek duvarlari (teras kenari)
  gs = m.entities.add_group; gs.name = "ISTINAT_TERAS_KENAR"; gs.layer = m.layers.add("ISTINAT")
  ns = 0
  File.foreach(dir + "skirts2.txt") do |ln|
    t = ln.split; next unless t[0] == "Q"
    v = t[1..8].map(&:to_f)
    pts = [Geom::Point3d.new(v[0].m, v[1].m, v[2].m), Geom::Point3d.new(v[4].m, v[5].m, v[6].m),
           Geom::Point3d.new(v[4].m, v[5].m, v[7].m), Geom::Point3d.new(v[0].m, v[1].m, v[3].m)]
    begin; f = gs.entities.add_face(pts); f.material = stone; f.back_material = stone; ns += 1; rescue; end
  end

  m.commit_operation
  File.write(dir + "result18.txt", "OK eski_yuz=#{nold} yeni_yuz=#{nf} hatali=#{bad} kademe_duvar=#{nq} agac=#{nt} cit=#{nw} tas_taban=#{nb} etek=#{ns}")
  File.write(dir + "h0.txt", "105.07")
  load dir + "build_terrain7.rb"
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "result18.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
