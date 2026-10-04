begin
  dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
  m = Sketchup.active_model; vw = m.active_view; cam0 = vw.camera
  c = Sketchup::Camera.new(Geom::Point3d.new(88.m, -45.m, 19.8.m), Geom::Point3d.new(88.m, 60.m, 3.m), Geom::Vector3d.new(0, 0, 1))
  c.perspective = true; c.fov = 50; vw.camera = c
  vw.write_image(dir + "d_guney.png", 1600, 900, true, 0.0)
  c = Sketchup::Camera.new(Geom::Point3d.new(88.m, 175.m, 54.4.m), Geom::Point3d.new(88.m, 60.m, 3.m), Geom::Vector3d.new(0, 0, 1))
  c.perspective = true; c.fov = 50; vw.camera = c
  vw.write_image(dir + "d_kuzey.png", 1600, 900, true, 0.0)
  c = Sketchup::Camera.new(Geom::Point3d.new(255.m, 60.m, 15.3.m), Geom::Point3d.new(88.m, 60.m, 3.m), Geom::Vector3d.new(0, 0, 1))
  c.perspective = true; c.fov = 50; vw.camera = c
  vw.write_image(dir + "d_dogu.png", 1600, 900, true, 0.0)
  c = Sketchup::Camera.new(Geom::Point3d.new(-75.m, 60.m, 40.4.m), Geom::Point3d.new(88.m, 60.m, 3.m), Geom::Vector3d.new(0, 0, 1))
  c.perspective = true; c.fov = 50; vw.camera = c
  vw.write_image(dir + "d_bati.png", 1600, 900, true, 0.0)
  vw.camera = cam0
  File.write(dir + "result12.txt", "OK")
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/result12.txt", "ERR #{e.class}: #{e.message}")
end
