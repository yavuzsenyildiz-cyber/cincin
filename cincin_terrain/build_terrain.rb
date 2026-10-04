# CINCIN arazi (TM27, uydu dokulu) -> modele ekler. H0 = model z=0'in kotu (m).
begin
  H0 = 99.78
  dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
  log = dir + "result.txt"
  m = Sketchup.active_model
  v = []; f = []
  File.foreach(dir + "mesh.txt") do |ln|
    t = ln.split
    v << t[1..5].map(&:to_f) if t[0] == "V"
    f << t[1..3].map(&:to_i) if t[0] == "F"
  end
  m.start_operation("ARAZI_TM27_KOT ekle", true)
  mat = m.materials.add("ARAZI_UYDU_TM27")
  mat.texture = dir + "sat.jpg"
  pm = Geom::PolygonMesh.new(v.length, f.length)
  v.each_with_index do |p, i|
    idx = pm.add_point(Geom::Point3d.new(p[0].m, p[1].m, (p[2] - H0).m))
    pm.set_uv(idx, Geom::Point3d.new(p[3], p[4], 0), true)
  end
  f.each { |t| pm.add_polygon(t[0] + 1, t[1] + 1, t[2] + 1) }
  g = m.entities.add_group
  g.name = "ARAZI_TM27_KOT (z=0 -> kot #{H0})"
  tag = m.layers.add("ARAZI_TM27")
  g.layer = tag
  g.entities.add_faces_from_mesh(pm, Geom::PolygonMesh::AUTO_SOFTEN | Geom::PolygonMesh::SMOOTH_SOFT_EDGES, mat, mat)
  m.commit_operation
  b = g.bounds
  out = ["OK faces=#{g.entities.grep(Sketchup::Face).length}",
         "bounds min(%.2f,%.2f,%.2f) max(%.2f,%.2f,%.2f)" % [b.min.x.to_m, b.min.y.to_m, b.min.z.to_m, b.max.x.to_m, b.max.y.to_m, b.max.z.to_m]]
  # kontrol goruntusu (kamerayi sonra geri yukle)
  vw = m.active_view; cam = vw.camera
  c0 = Geom::Point3d.new(80.m, -90.m, 70.m); tg = Geom::Point3d.new(80.m, 55.m, 8.m)
  vw.camera = Sketchup::Camera.new(c0, tg, Geom::Vector3d.new(0, 0, 1))
  vw.write_image(dir + "check.png", 1400, 900, true, 0.0)
  vw.camera = cam
  File.write(log, out.join("\n"))
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
