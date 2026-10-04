# Arac yollarini (YOL1, YOL2) araziye isler: arazi yeniden kurulur, bahce platformlari yoldan kirpilir, yol yuzeyi eklenir.
# Calistirma: SketchUp'ta CINCIN_arazi_KOTLANDIRMA.skp acikken Ruby Console'a:
#   load "C:/Users/YOGA/OneDrive/MİMARİ/CİNCİN/cincin_terrain/yol_uygula.rb"
dir = File.dirname(__FILE__) + "/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  raise "Once CINCIN_arazi_KOTLANDIRMA.skp acik olmali (acik: #{m.title})" unless m.title.include?("KOTLANDIRMA")
  m.start_operation("Arac yollari + arazi guncelle", true)
  ents = m.entities
  ents.grep(Sketchup::Group).select { |g| g.name =~ /^(ARAZI_TESVIYE|PLATFORM_BAHCE|ARAC_YOLU)/ }.each(&:erase!)
  t_ar = m.layers.add("ARAZI_TESVIYE"); t_pl = m.layers.add("BAHCE_PLATFORM"); t_yo = m.layers.add("ARAC_YOLU")
  mat = m.materials["ARAZI_PLANKOTE_UYDU"]
  cim = m.materials["BAHCE_CIM"] || m.materials.add("BAHCE_CIM"); cim.color = Sketchup::Color.new(96, 150, 60)
  asf = m.materials["ARAC_YOLU_ASFALT"] || m.materials.add("ARAC_YOLU_ASFALT"); asf.color = Sketchup::Color.new(70, 70, 75)

  v = []; f = []
  File.foreach(dir + "tes_mesh_yol.txt") { |ln| t = ln.split; v << t[1..5].map(&:to_f) if t[0] == "V"; f << t[1..3].map(&:to_i) if t[0] == "F" }
  pm = Geom::PolygonMesh.new(v.length, f.length)
  idx = v.map { |p| i = pm.add_point(Geom::Point3d.new(p[0].m, p[1].m, p[2].m)); pm.set_uv(i, Geom::Point3d.new(p[3], p[4], 0), true); i }
  f.each { |t| a, b, c = t.map { |q| idx[q] }; pm.add_polygon(a, b, c) unless a == b || b == c || a == c }
  ga = ents.add_group; ga.name = "ARAZI_TESVIYE (yollu, kazi/dolgu sonrasi, sev 2:3)"; ga.layer = t_ar
  ga.entities.add_faces_from_mesh(pm, Geom::PolygonMesh::AUTO_SOFTEN | Geom::PolygonMesh::SMOOTH_SOFT_EDGES, mat, mat)

  pts = lambda do |s, z|
    a = s.split(";").map { |q| x, y = q.split(",").map(&:to_f); Geom::Point3d.new(x.m, y.m, z.m) }
    o = []
    a.each { |p| o << p if o.empty? || o.last.distance(p) > 2.mm }
    o.pop while o.length > 1 && o.first.distance(o.last) <= 2.mm
    o
  end
  gp = ents.add_group; gp.name = "PLATFORM_BAHCE (yoldan kirpilmis)"; gp.layer = t_pl
  fps = {}; nplat = 0; badp = 0; msgp = []
  File.foreach(dir + "tes_objs_yol.txt") do |ln|
    t = ln.split
    if t[0] == "B" then fps[t[1]] = t[4]
    elsif t[0] == "L"
      name, z0, poly = t[1], t[2].to_f, t[3]
      begin
        sg = gp.entities.add_group; sg.name = "#{name} platform +#{'%.2f' % (z0 + 105.07)}"
        fc = sg.entities.add_face(pts.(poly, z0 + 0.02)); fc.reverse! if fc.normal.z < 0
        fc.material = cim; fc.back_material = cim
        hole = sg.entities.add_face(pts.(fps[name], z0 + 0.02)) rescue nil
        hole.erase! if hole && hole.valid?
        nplat += 1
      rescue => e
        badp += 1; msgp << "#{name}: #{e.message[0, 50]}"
        sg.erase! if sg && sg.valid?
      end
    end
  end

  gy = ents.add_group; gy.name = "ARAC_YOLU"; gy.layer = t_yo
  nq = 0; bad = 0
  File.foreach(dir + "yol_yuzey.txt") do |ln|
    t = ln.split; next unless t[0] == "Q"
    c = t[2..13].map(&:to_f)
    q = (0..3).map { |i| Geom::Point3d.new(c[i * 3].m, c[i * 3 + 1].m, (c[i * 3 + 2] + 0.15).m) }
    begin
      fc = gy.entities.add_face(q); fc.reverse! if fc.normal.z < 0
      fc.material = asf; fc.back_material = asf; nq += 1
    rescue
      bad += 1
    end
  end
  gy.entities.grep(Sketchup::Edge).each { |e| e.hidden = true if e.faces.length == 2 }
  m.commit_operation

  vw = m.active_view
  vw.camera = Sketchup::Camera.new(Geom::Point3d.new(85.m, -40.m, 60.m), Geom::Point3d.new(85.m, 65.m, 0), Geom::Vector3d.new(0, 0, 1))
  vw.write_image(dir + "yol_view.png", 1600, 1000, true, 0.0)
  File.write(dir + "yol_result.txt", "OK platform=#{nplat} platform_hatali=#{badp} #{msgp.join(' / ')} yol_dilimi=#{nq} hatali=#{bad} arazi_yuz=#{ga.entities.grep(Sketchup::Face).length}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "yol_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
