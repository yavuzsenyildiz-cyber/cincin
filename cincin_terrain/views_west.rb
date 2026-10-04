begin
  dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
  m = Sketchup.active_model; vw = m.active_view; cam0 = vw.camera
  # 1) bati uc plan (paralel)
  c = Sketchup::Camera.new(Geom::Point3d.new(45.m, 70.m, 300.m), Geom::Point3d.new(45.m, 70.m, 0.m), Geom::Vector3d.new(0, 1, 0))
  c.perspective = false; c.height = 75.m; vw.camera = c
  vw.write_image(dir + "w1.png", 1600, 900, true, 0.0)
  # 2) yoldan (batidan) dogu'ya bakis
  c = Sketchup::Camera.new(Geom::Point3d.new(-22.m, 75.m, 22.m), Geom::Point3d.new(40.m, 72.m, 6.m), Geom::Vector3d.new(0, 0, 1))
  c.perspective = true; c.fov = 60; vw.camera = c
  vw.write_image(dir + "w2.png", 1600, 900, true, 0.0)
  # 3) guneybatidan yakin
  c = Sketchup::Camera.new(Geom::Point3d.new(5.m, 30.m, 18.m), Geom::Point3d.new(40.m, 65.m, 5.m), Geom::Vector3d.new(0, 0, 1))
  c.perspective = true; c.fov = 60; vw.camera = c
  vw.write_image(dir + "w3.png", 1600, 900, true, 0.0)
  vw.camera = cam0
  File.write(dir + "result8.txt", "OK")
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/result8.txt", "ERR #{e.class}: #{e.message}")
end
