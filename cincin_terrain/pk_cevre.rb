# PLANKOTE arazisi + 2 km cevre arazi (uydu dokulu), esyukselti egrisi ve kot yazisi YOK -> yeni .skp
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
out = "C:/Users/YOGA/OneDrive/MİMARİ/CİNCİN/GUNCEL_D5_SKETCHUP/SketchUp/CINCIN_arazi_PLANKOTE_cevre.skp"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  unless m.path.to_s.empty? && m.entities.length <= 1
    raise "Bu komut yalnizca YENI ve BOS bir modelde calisir (File > New). Acik model: #{m.title}"
  end
  m.entities.grep(Sketchup::ComponentInstance).each(&:erase!)
  uo = m.options["UnitsOptions"]; uo["LengthUnit"] = 4; uo["LengthPrecision"] = 2
  m.start_operation("PLANKOTE + cevre arazi", true)
  ents = m.entities
  t_ar = m.layers.add("ARAZI_PLANKOTE_CEVRE"); t_pa = m.layers.add("PARSEL_SINIR")

  mat = m.materials.add("ARAZI_PLANKOTE_UYDU"); mat.texture = dir + "sat.jpg"
  v = []; f = []
  File.foreach(dir + "pk_merged_mesh.txt") { |ln| t = ln.split; v << t[1..5].map(&:to_f) if t[0] == "V"; f << t[1..3].map(&:to_i) if t[0] == "F" }
  pm = Geom::PolygonMesh.new(v.length, f.length)
  v.each { |p| i = pm.add_point(Geom::Point3d.new(p[0].m, p[1].m, p[2].m)); pm.set_uv(i, Geom::Point3d.new(p[3], p[4], 0), true) }
  f.each { |t| pm.add_polygon(t[0] + 1, t[1] + 1, t[2] + 1) }
  g = ents.add_group; g.name = "ARAZI (PLANKOTE + 2 km cevre, z=0 -> kot 105.07)"; g.layer = t_ar
  g.entities.add_faces_from_mesh(pm, Geom::PolygonMesh::AUTO_SOFTEN | Geom::PolygonMesh::SMOOTH_SOFT_EDGES, mat, mat)

  gp = ents.add_group; gp.name = "PARSEL_SINIR"; gp.layer = t_pa
  File.foreach(dir + "pk_rings.txt") do |ln|
    t = ln.split(" ", 3)
    pts = t[2].split(";").map { |q| x, y, z = q.split(",").map(&:to_f); Geom::Point3d.new(x.m, y.m, (z + 0.1).m) }
    gp.entities.add_edges(pts + [pts.first])
  end

  m.commit_operation
  vw = m.active_view
  vw.camera = Sketchup::Camera.new(Geom::Point3d.new(80.m, -260.m, 160.m), Geom::Point3d.new(80.m, 60.m, 0), Geom::Vector3d.new(0, 0, 1))
  vw.write_image(dir + "pk_cevre_view.png", 1400, 900, true, 0.0)
  ok = m.save(out)
  File.write(dir + "pk_result.txt", "OK kaydedildi=#{ok} yuz=#{g.entities.grep(Sketchup::Face).length} -> #{out}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "pk_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
