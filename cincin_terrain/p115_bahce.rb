# P115 bahceleri (+-0.00 kotlarinda) + P115 bolgesinde yeniden kurulan arazi + istinat/basamak duvarlari.
# Orijinal PLANKOTE arazisi silinmez, gizlenir. Kaydetmez; Ctrl+Z geri alir.
#   load "C:/Users/YOGA/OneDrive/MİMARİ/CİNCİN/cincin_terrain/p115_bahce.rb"
dir = File.dirname(__FILE__) + "/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  m.start_operation("P115 bahceler", true)
  ents = m.entities
  ents.grep(Sketchup::Group).select { |g| g.name =~ /^(P115_ARAZI|P115_BAHCE|P115_DUVAR)/ }.each(&:erase!)
  orig = ents.grep(Sketchup::Group).select { |g| g.name.start_with?("ARAZI (PLANKOTE") }
  orig.each { |g| g.hidden = true }
  mk = lambda { |n, r, g, b| x = m.materials[n] || m.materials.add(n); x.color = Sketchup::Color.new(r, g, b); x }
  mat = m.materials["ARAZI_PLANKOTE_UYDU"] || mk.("ARAZI_PLANKOTE_UYDU", 120, 120, 90)
  cim = mk.("BAHCE_CIM", 96, 150, 60); bet = mk.("ISTINAT_BETON", 150, 150, 150)
  v = []; f = []
  File.foreach(dir + "p115_mesh.txt") { |ln| t = ln.split; v << t[1..5].map(&:to_f) if t[0] == "V"; f << t[1..3].map(&:to_i) if t[0] == "F" }
  pm = Geom::PolygonMesh.new(v.length, f.length)
  idx = v.map { |p| i = pm.add_point(Geom::Point3d.new(p[0].m, p[1].m, p[2].m)); pm.set_uv(i, Geom::Point3d.new(p[3], p[4], 0), true); i }
  f.each { |t| a, b, c = t.map { |q| idx[q] }; pm.add_polygon(a, b, c) unless a == b || b == c || a == c }
  ga = ents.add_group; ga.name = "P115_ARAZI (bahceler +-0.00, gerisi tabii)"; ga.layer = orig.first ? orig.first.layer : m.layers.add("ARAZI")
  ga.entities.add_faces_from_mesh(pm, Geom::PolygonMesh::AUTO_SOFTEN | Geom::PolygonMesh::SMOOTH_SOFT_EDGES, mat, mat)
  pts = ->(s, z) { s.split(";").map { |q| x, y = q.split(",").map(&:to_f); Geom::Point3d.new(x.m, y.m, z.m) } }
  gb = ents.add_group; gb.name = "P115_BAHCE"; gb.layer = m.layers.add("BAHCE")
  nb = 0
  File.foreach(dir + "p115_bahce.txt") do |ln|
    t = ln.split; next unless t[0] == "L"
    z = t[2].to_f
    sg = gb.entities.add_group; sg.name = "#{t[1]} bahce +#{'%.2f' % (z + 105.07)}"
    fc = sg.entities.add_face(pts.(t[3], z + 0.02)); fc.reverse! if fc.normal.z < 0
    fc.material = cim; fc.back_material = cim
    h = sg.entities.add_face(pts.(t[4], z + 0.02)) rescue nil
    h.erase! if h && h.valid?
    nb += 1
  end
  gw = ents.add_group; gw.name = "P115_DUVAR (istinat + basamak)"; gw.layer = m.layers.add("ISTINAT_DUVARI")
  wm = Geom::PolygonMesh.new; nw = 0
  File.foreach(dir + "p115_duvar.txt") do |ln|
    t = ln.split; next unless t[0] == "W"
    x0, y0, x1, y1, l0, l1, h0, h1 = t[2..9].map(&:to_f)
    a = wm.add_point(Geom::Point3d.new(x0.m, y0.m, l0.m)); b = wm.add_point(Geom::Point3d.new(x1.m, y1.m, l1.m))
    c = wm.add_point(Geom::Point3d.new(x1.m, y1.m, h1.m)); d = wm.add_point(Geom::Point3d.new(x0.m, y0.m, h0.m))
    begin; wm.add_polygon(a, b, c); wm.add_polygon(a, c, d); nw += 1; rescue; end
  end
  gw.entities.add_faces_from_mesh(wm, Geom::PolygonMesh::AUTO_SOFTEN, bet, bet) if wm.count_polygons > 0
  m.commit_operation
  File.write(dir + "p115_bahce_result.txt", "OK bahce=#{nb} duvar=#{nw} arazi_yuz=#{ga.entities.grep(Sketchup::Face).length} gizlenen_arazi=#{orig.length}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "p115_bahce_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(2).join("\n")}")
end
