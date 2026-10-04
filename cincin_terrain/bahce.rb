# Bahceleri (3dmodel3 cim yuzeyleri, bina izi disi) araziyi izleyerek CINCIN_arazi_PLANKOTE_cevre modeline ekler
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  raise "Once CINCIN_arazi_PLANKOTE_cevre.skp acik olmali (acik: #{m.title})" unless m.title.include?("PLANKOTE_cevre")
  m.start_operation("Bahceler", true)
  m.entities.grep(Sketchup::Group).select { |g| g.name.start_with?("BAHCE") }.each(&:erase!)
  tag = m.layers.add("BAHCE")
  mat = m.materials["BAHCE_CIM"] || m.materials.add("BAHCE_CIM")
  mat.color = Sketchup::Color.new(96, 150, 60)
  lmat = m.materials["BAHCE_SINIR"] || m.materials.add("BAHCE_SINIR"); lmat.color = Sketchup::Color.new(30, 90, 20)
  gb = m.entities.add_group; gb.name = "BAHCELER (araziyi izleyen)"; gb.layer = tag
  lines = File.readlines(dir + "bahce_mesh.txt"); i = 0; n = 0
  while i < lines.length
    _, name, nv, nt = lines[i].split; nv = nv.to_i; nt = nt.to_i; i += 1
    pts = lines[i, nv].map { |l| x, y, z = l.split.map(&:to_f); Geom::Point3d.new(x.m, y.m, z.m) }; i += nv
    pm = Geom::PolygonMesh.new(nv, nt)
    idx = pts.map { |p| pm.add_point(p) }
    lines[i, nt].each do |l|
      a, b, c = l.split.map { |q| idx[q.to_i] }
      pm.add_polygon(a, b, c) unless a == b || b == c || a == c
    end
    i += nt
    lp = lines[i].sub(/^L /, "").strip.split(";").map { |q| x, y, z = q.split(",").map(&:to_f); Geom::Point3d.new(x.m, y.m, z.m) }; i += 1
    sg = gb.entities.add_group; sg.name = name
    sg.entities.add_faces_from_mesh(pm, Geom::PolygonMesh::AUTO_SOFTEN | Geom::PolygonMesh::SMOOTH_SOFT_EDGES, mat, mat)
    sg.entities.grep(Sketchup::Face).each { |f| f.reverse! if f.normal.z < 0; f.material = mat; f.back_material = mat }
    sg.entities.add_edges(lp + [lp.first]).each { |e| e.material = lmat }
    n += 1
  end
  m.commit_operation
  ok = m.save
  vw = m.active_view
  vw.camera = Sketchup::Camera.new(Geom::Point3d.new(85.m, -60.m, 70.m), Geom::Point3d.new(85.m, 68.m, 0), Geom::Vector3d.new(0, 0, 1))
  vw.write_image(dir + "bahce_view.png", 1400, 900, true, 0.0)
  File.write(dir + "bahce_result.txt", "OK bahce=#{n} kaydedildi=#{ok}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "bahce_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
