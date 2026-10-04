# PLANKOTE arazi modelini yeni bir .skp dosyasina kaydet (acik projeye dokunmadan: islem sonunda geri alinir).
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
out = "C:/Users/YOGA/OneDrive/MİMARİ/CİNCİN/GUNCEL_D5_SKETCHUP/SketchUp/CINCIN_arazi_PLANKOTE.skp"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  unless m.path.to_s.empty? && m.entities.length <= 1
    raise "Bu komut yalnizca YENI ve BOS bir modelde calisir (File > New). Acik model: #{m.title}"
  end
  m.entities.grep(Sketchup::ComponentInstance).each(&:erase!)
  uo = m.options["UnitsOptions"]; uo["LengthUnit"] = 4; uo["LengthPrecision"] = 2
  m.start_operation("PLANKOTE arazi", true)
  ents = m.entities
  t_ar = m.layers.add("ARAZI_PLANKOTE"); t_c1 = m.layers.add("ESYUKSELTI_1M"); t_c5 = m.layers.add("ESYUKSELTI_0.5M")
  t_pa = m.layers.add("PARSEL_SINIR"); t_ko = m.layers.add("KOT_NOKTALARI")

  # arazi (uydu dokulu)
  mat = m.materials.add("ARAZI_PLANKOTE_UYDU"); mat.texture = dir + "sat.jpg"
  v = []; f = []
  File.foreach(dir + "pk_mesh.txt") { |ln| t = ln.split; v << t[1..5].map(&:to_f) if t[0] == "V"; f << t[1..3].map(&:to_i) if t[0] == "F" }
  pm = Geom::PolygonMesh.new(v.length, f.length)
  v.each { |p| i = pm.add_point(Geom::Point3d.new(p[0].m, p[1].m, p[2].m)); pm.set_uv(i, Geom::Point3d.new(p[3], p[4], 0), true) }
  f.each { |t| pm.add_polygon(t[0] + 1, t[1] + 1, t[2] + 1) }
  g = ents.add_group; g.name = "ARAZI (PLANKOTE, 214 kot)"; g.layer = t_ar
  g.entities.add_faces_from_mesh(pm, Geom::PolygonMesh::AUTO_SOFTEN | Geom::PolygonMesh::SMOOTH_SOFT_EDGES, mat, mat)

  # esyukselti egrileri (5 cm yukarida)
  gc = ents.add_group; gc.name = "ESYUKSELTI"; nc = 0
  File.foreach(dir + "pk_contours.txt") do |ln|
    t = ln.split(" ", 3); z = t[1].to_f + 0.05
    pts = t[2].split(";").map { |q| x, y = q.split(",").map(&:to_f); Geom::Point3d.new(x.m, y.m, z.m) }
    next if pts.length < 2
    es = gc.entities.add_curve(pts) rescue gc.entities.add_edges(pts)
    (es || []).each { |e| e.layer = (t[0] == "M" ? t_c1 : t_c5) }
    nc += 1
  end

  # parsel sinirlari
  gp = ents.add_group; gp.name = "PARSEL_SINIR"; gp.layer = t_pa
  File.foreach(dir + "pk_rings.txt") do |ln|
    t = ln.split(" ", 3)
    pts = t[2].split(";").map { |q| x, y, z = q.split(",").map(&:to_f); Geom::Point3d.new(x.m, y.m, (z + 0.1).m) }
    gp.entities.add_edges(pts + [pts.first])
  end

  # kot noktalari + yazilari
  gk = ents.add_group; gk.name = "KOT_NOKTALARI"; gk.layer = t_ko; nk = 0
  File.foreach(dir + "pk_spots.txt") do |ln|
    x, y, z, kot = ln.split
    p = Geom::Point3d.new(x.to_f.m, y.to_f.m, (z.to_f + 0.1).m)
    gk.entities.add_cpoint(p)
    tx = gk.entities.add_text(kot, p); tx.layer = t_ko
    nk += 1
  end

  m.commit_operation
  m.active_view.zoom_extents
  ok = m.save(out)
  File.write(dir + "pk_result.txt", "OK kaydedildi=#{ok} esyukselti=#{nc} kot=#{nk} -> #{out}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "pk_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
