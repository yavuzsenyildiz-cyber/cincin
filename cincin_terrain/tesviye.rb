# Yonetmelige gore kotlandirma: her bina + bahcesi tek platform (kazi/dolgu), arazi yeniden
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  raise "Once CINCIN_arazi_PLANKOTE_cevre.skp acik olmali (acik: #{m.title})" unless m.title.include?("PLANKOTE_cevre")
  m.start_operation("Kotlandirma + kazi/dolgu", true)
  ents = m.entities
  # eski: dogal araziyi gizli etikete al, eski bina/bahce/tesviye gruplarini sil
  t_dog = m.layers.add("ARAZI_DOGAL (tesviye oncesi)"); t_dog.visible = false
  ents.grep(Sketchup::Group).each do |g|
    if g.name.start_with?("ARAZI (PLANKOTE") then g.layer = t_dog
    elsif g.name =~ /^(BINA_OTURUM|BAHCE|ARAZI_TESVIYE|BINA_SUBASMAN|BINA_KOT|PLATFORM)/ then g.erase!
    end
  end
  t_ar = m.layers.add("ARAZI_TESVIYE"); t_pl = m.layers.add("BAHCE_PLATFORM")
  t_bi = m.layers.add("BINA_SUBASMAN"); t_ko = m.layers.add("BINA_KOT")
  mat = m.materials["ARAZI_PLANKOTE_UYDU"]
  cim = m.materials["BAHCE_CIM"] || m.materials.add("BAHCE_CIM"); cim.color = Sketchup::Color.new(96, 150, 60)
  bmat = m.materials["BINA_OTURUM"] || m.materials.add("BINA_OTURUM"); bmat.color = Sketchup::Color.new(220, 60, 40); bmat.alpha = 1.0
  # arazi
  v = []; f = []
  File.foreach(dir + "tes_mesh.txt") { |ln| t = ln.split; v << t[1..5].map(&:to_f) if t[0] == "V"; f << t[1..3].map(&:to_i) if t[0] == "F" }
  pm = Geom::PolygonMesh.new(v.length, f.length)
  idx = v.map { |p| i = pm.add_point(Geom::Point3d.new(p[0].m, p[1].m, p[2].m)); pm.set_uv(i, Geom::Point3d.new(p[3], p[4], 0), true); i }
  f.each { |t| a, b, c = t.map { |q| idx[q] }; pm.add_polygon(a, b, c) unless a == b || b == c || a == c }
  ga = ents.add_group; ga.name = "ARAZI_TESVIYE (kazi/dolgu sonrasi, sev 2:3)"; ga.layer = t_ar
  ga.entities.add_faces_from_mesh(pm, Geom::PolygonMesh::AUTO_SOFTEN | Geom::PolygonMesh::SMOOTH_SOFT_EDGES, mat, mat)
  # platformlar, binalar, kotlar
  gp = ents.add_group; gp.name = "PLATFORM_BAHCE"; gp.layer = t_pl
  gb = ents.add_group; gb.name = "BINA_SUBASMAN (+0.50)"; gb.layer = t_bi
  gk = ents.add_group; gk.name = "BINA_KOT"; gk.layer = t_ko
  pts = ->(s, z) { s.split(";").map { |q| x, y = q.split(",").map(&:to_f); Geom::Point3d.new(x.m, y.m, z.m) } }
  fps = {}; n = 0
  File.foreach(dir + "tes_objs.txt") do |ln|
    t = ln.split
    if t[0] == "B"
      name, z0, zk, poly = t[1], t[2].to_f, t[3].to_f, t[4]
      fps[name] = poly
      sg = gb.entities.add_group; sg.name = name
      fc = sg.entities.add_face(pts.(poly, z0)); fc.reverse! if fc.normal.z < 0
      fc.pushpull((zk - z0).m)
      sg.entities.grep(Sketchup::Face).each { |q| q.material = bmat }
      c = pts.(poly, zk).inject(Geom::Vector3d.new(0, 0, 0)) { |s, p| s + Geom::Vector3d.new(p.x, p.y, p.z) }
      k = pts.(poly, zk).length
      cp = Geom::Point3d.new(c.x / k, c.y / k, zk.m + 0.05.m)
      tx = gk.entities.add_text("#{name}\n±0.00 = +#{'%.2f' % (z0 + 105.07)}\nZ.K. = +#{'%.2f' % (zk + 105.07)}", cp, Geom::Vector3d.new(0, 0, 3.m))
      n += 1
    else
      name, z0, poly = t[1], t[2].to_f, t[3]
      sg = gp.entities.add_group; sg.name = "#{name} platform +#{'%.2f' % (z0 + 105.07)}"
      fc = sg.entities.add_face(pts.(poly, z0 + 0.02)); fc.reverse! if fc.normal.z < 0
      fc.material = cim; fc.back_material = cim
      # bina izini platformdan bosalt
      hole = sg.entities.add_face(pts.(fps[name], z0 + 0.02)) rescue nil
      hole.erase! if hole && hole.valid?
    end
  end
  m.commit_operation
  ok = m.save
  vw = m.active_view
  vw.camera = Sketchup::Camera.new(Geom::Point3d.new(85.m, -40.m, 60.m), Geom::Point3d.new(85.m, 65.m, 0), Geom::Vector3d.new(0, 0, 1))
  vw.write_image(dir + "tes_view.png", 1600, 1000, true, 0.0)
  File.write(dir + "tes_result.txt", "OK bina=#{n} kaydedildi=#{ok} yuz=#{ga.entities.grep(Sketchup::Face).length}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "tes_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
