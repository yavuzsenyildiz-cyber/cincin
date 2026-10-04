# 1) bahce duvari altlarini (tas istinat) arazinin en alcak noktasina kadar indir (yeniden kur)
# 2) tugla (riser) duvarlarin alt kenarlarinin altina arazi kadar etek ekle
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  lines = File.readlines(dir + "grid3.txt", chomp: true)
  nx, ny, gx0, gy0, st = lines[0].split.map(&:to_f); nx = nx.to_i; ny = ny.to_i
  tz = lines[1, ny].map { |r| r.split.map(&:to_f) }
  terr = lambda do |x, y|
    i = ((x - gx0) / st).clamp(0, nx - 1.001); j = ((y - gy0) / st).clamp(0, ny - 1.001)
    i0 = i.floor; j0 = j.floor; fi = i - i0; fj = j - j0
    (tz[j0][i0] * (1 - fi) + tz[j0][i0 + 1] * fi) * (1 - fj) + (tz[j0 + 1][i0] * (1 - fi) + tz[j0 + 1][i0 + 1] * fi) * fj
  end
  mat = m.materials["ETEK_DUVAR"] || m.materials.add("ETEK_DUVAR")
  m.start_operation("Duvar altlari + riser etek", true)
  m.entities.grep(Sketchup::Group).select { |g| g.name == "ISTINAT_BAHCE_DUVAR" }.each(&:erase!)
  g = m.entities.add_group; g.name = "ISTINAT_BAHCE_DUVAR"; g.layer = m.layers.add("ISTINAT")
  boxes = 0; maxd = 0.0
  m.entities.grep(Sketchup::ComponentInstance).each do |e|
    next unless e.definition.name.start_with?("Modern")
    zf = e.bounds.min.z.to_m
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
    ([[pt[0], pt[1], pt[2], pt[3]]] + (0..3).map { |i| j = (i + 1) % 4; [pb[i], pb[j], pt[j], pt[i]] }).each do |pts|
      begin; f = g.entities.add_face(pts); f.material = mat; f.back_material = mat; rescue; end
    end
    boxes += 1; maxd = [maxd, zf - zb].max
  end
  # riser duvarlarin alt kenari
  g2 = m.entities.add_group; g2.name = "ISTINAT_RISER_ALT"; g2.layer = m.layers.add("ISTINAT")
  quads = 0
  m.entities.grep(Sketchup::Face).each do |f|
    next unless f.material && f.material.name.include?("Brick")
    vs = f.vertices.map { |v| p = v.position; [p.x.to_m, p.y.to_m, p.z.to_m] }
    bots = vs.select { |a| vs.any? { |b| (b[0] - a[0]).abs < 0.02 && (b[1] - a[1]).abs < 0.02 && b[2] > a[2] + 0.2 } }
    next if bots.length < 2
    ax = (bots.map { |b| b[0] }.max - bots.map { |b| b[0] }.min) >= (bots.map { |b| b[1] }.max - bots.map { |b| b[1] }.min) ? 0 : 1
    bots = bots.sort_by { |b| b[ax] }
    (0...bots.length - 1).each do |i|
      a = bots[i]; b = bots[i + 1]
      ta = terr.call(a[0], a[1]) - 0.2; tb = terr.call(b[0], b[1]) - 0.2
      next if a[2] - ta < 0.1 && b[2] - tb < 0.1
      next if ta > a[2] && tb > b[2]
      ta = [ta, a[2]].min; tb = [tb, b[2]].min
      pts = [Geom::Point3d.new(a[0].m, a[1].m, ta.m), Geom::Point3d.new(b[0].m, b[1].m, tb.m), Geom::Point3d.new(b[0].m, b[1].m, b[2].m), Geom::Point3d.new(a[0].m, a[1].m, a[2].m)]
      begin; q = g2.entities.add_face(pts); q.material = mat; q.back_material = mat; quads += 1; rescue; end
    end
  end
  m.commit_operation
  vw = m.active_view; cam0 = vw.camera
  vw.camera = Sketchup::Camera.new(Geom::Point3d.new(60.m, 6.m, 16.m), Geom::Point3d.new(80.m, 55.m, 4.m), Geom::Vector3d.new(0, 0, 1))
  vw.write_image(dir + "check16.png", 1600, 900, true, 0.0)
  vw.camera = cam0
  File.write(dir + "result16.txt", "OK duvar_tabani_kutu=#{boxes} max_derinlik=#{maxd.round(2)} riser_etek_yuz=#{quads}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "result16.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
