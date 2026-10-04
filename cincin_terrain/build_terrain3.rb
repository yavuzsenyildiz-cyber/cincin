begin
  dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
  h0 = File.read(dir + "h0.txt").strip.to_f
  m = Sketchup.active_model
  m.close_active while m.active_path
  v = []; f = []
  File.foreach(dir + "mesh.txt") do |ln|
    t = ln.split
    v << t[1..5].map(&:to_f) if t[0] == "V"
    f << t[1..3].map(&:to_i) if t[0] == "F"
  end
  m.start_operation("ARAZI kota gore duzenle", true)
  old = m.entities.grep(Sketchup::Group).select { |g| g.name.start_with?("ARAZI_TM27_KOT") }
  old.each(&:erase!)
  mat = m.materials["ARAZI_UYDU_TM27"] || m.materials.add("ARAZI_UYDU_TM27")
  mat.texture = dir + "sat.jpg"
  pm = Geom::PolygonMesh.new(v.length, f.length)
  v.each do |p|
    idx = pm.add_point(Geom::Point3d.new(p[0].m, p[1].m, (p[2] - h0).m))
    pm.set_uv(idx, Geom::Point3d.new(p[3], p[4], 0), true)
  end
  f.each { |t| pm.add_polygon(t[0] + 1, t[1] + 1, t[2] + 1) }
  g = m.entities.add_group
  g.name = "ARAZI_TM27_KOT (z=0 -> kot #{h0}; dogal arazi; yol bagli H0)"
  g.layer = m.layers.add("ARAZI_TM27")
  g.entities.add_faces_from_mesh(pm, Geom::PolygonMesh::AUTO_SOFTEN | Geom::PolygonMesh::SMOOTH_SOFT_EDGES, mat, mat)
  m.commit_operation
  b = g.bounds
  out = ["OK silinen_eski=#{old.length} faces=#{g.entities.grep(Sketchup::Face).length} h0=#{h0}",
         "bounds min(%.2f,%.2f,%.2f) max(%.2f,%.2f,%.2f)" % [b.min.x.to_m, b.min.y.to_m, b.min.z.to_m, b.max.x.to_m, b.max.y.to_m, b.max.z.to_m]]
  vw = m.active_view; cam = vw.camera
  vw.camera = Sketchup::Camera.new(Geom::Point3d.new(80.m, -70.m, 55.m), Geom::Point3d.new(80.m, 55.m, 6.m), Geom::Vector3d.new(0, 0, 1))
  vw.write_image(dir + "check3.png", 1400, 900, true, 0.0)
  vw.camera = cam
  File.write(dir + "result3.txt", out.join("\n"))
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/result3.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
