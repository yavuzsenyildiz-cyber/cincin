# 32 bina oturum izini acik CINCIN_arazi_PLANKOTE_cevre modeline ekler ve kaydeder
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  raise "Once CINCIN_arazi_PLANKOTE_cevre.skp acik olmali (acik: #{m.title})" unless m.title.include?("PLANKOTE_cevre")
  m.start_operation("Bina oturum izleri", true)
  old = m.entities.grep(Sketchup::Group).select { |g| g.name.start_with?("BINA_OTURUM") }
  old.each(&:erase!)
  t_iz = m.layers.add("BINA_OTURUM_IZ"); t_du = m.layers.add("BINA_OTURUM_DUZLEM")
  mat = m.materials["BINA_OTURUM"] || m.materials.add("BINA_OTURUM")
  mat.color = Sketchup::Color.new(220, 60, 40); mat.alpha = 0.6
  gi = m.entities.add_group; gi.name = "BINA_OTURUM_IZ (araziye oturan)"; gi.layer = t_iz
  gd = m.entities.add_group; gd.name = "BINA_OTURUM_DUZLEM (kose ort. kotunda)"; gd.layer = t_du
  n = 0
  File.foreach(dir + "bina_iz.txt") do |ln|
    head, drape = ln.split(" | ")
    _, name, zm, poly = head.split(" ", 4)
    zm = zm.to_f
    # araziyi izleyen kirmizi cizgi (10 cm yukarida)
    dp = drape.strip.split(";").map { |q| x, y, z = q.split(",").map(&:to_f); Geom::Point3d.new(x.m, y.m, (z + 0.1).m) }
    es = gi.entities.add_edges(dp + [dp.first])
    es.each { |e| e.material = mat }
    # yatay oturum yuzeyi
    pts = poly.split(";").map { |q| x, y = q.split(",").map(&:to_f); Geom::Point3d.new(x.m, y.m, zm.m) }
    sg = gd.entities.add_group; sg.name = name
    fc = sg.entities.add_face(pts)
    fc.reverse! if fc.normal.z < 0
    fc.material = mat; fc.back_material = mat
    n += 1
  end
  m.commit_operation
  ok = m.save
  vw = m.active_view
  vw.camera = Sketchup::Camera.new(Geom::Point3d.new(85.m, -60.m, 70.m), Geom::Point3d.new(85.m, 68.m, 0), Geom::Vector3d.new(0, 0, 1))
  vw.write_image(dir + "bina_iz_view.png", 1400, 900, true, 0.0)
  File.write(dir + "bina_result.txt", "OK bina=#{n} kaydedildi=#{ok}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "bina_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
