begin
  dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
  m = Sketchup.active_model; vw = m.active_view; cam0 = vw.camera
  mk = lambda do |eye, tg, ortho, h, file|
    c = Sketchup::Camera.new(eye, tg, Geom::Vector3d.new(0, 0, 1))
    c.perspective = !ortho
    c.height = h.m if ortho
    vw.camera = c
    vw.write_image(dir + file, 1600, 900, true, 0.0)
  end
  # 1) guneybatidan perspektif
  mk.call(Geom::Point3d.new(-40.m, -60.m, 60.m), Geom::Point3d.new(85.m, 58.m, 2.m), false, 0, "v1.png")
  # 2) guneyden kot gorunusu (paralel)
  c = Sketchup::Camera.new(Geom::Point3d.new(85.m, -300.m, 8.m), Geom::Point3d.new(85.m, 58.m, 8.m), Geom::Vector3d.new(0, 0, 1))
  c.perspective = false; c.height = 90.m; vw.camera = c
  vw.write_image(dir + "v2.png", 1600, 900, true, 0.0)
  # 3) ustten plan (paralel)
  c = Sketchup::Camera.new(Geom::Point3d.new(85.m, 58.m, 400.m), Geom::Point3d.new(85.m, 58.m, 0.m), Geom::Vector3d.new(0, 1, 0))
  c.perspective = false; c.height = 130.m; vw.camera = c
  vw.write_image(dir + "v3.png", 1600, 900, true, 0.0)
  vw.camera = cam0
  File.write(dir + "result7.txt", "OK")
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/result7.txt", "ERR #{e.class}: #{e.message}")
end
