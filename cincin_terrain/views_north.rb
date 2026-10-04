begin
  dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
  m = Sketchup.active_model; vw = m.active_view; cam0 = vw.camera
  # 1) plan: kuzey seridi (paralel)
  c = Sketchup::Camera.new(Geom::Point3d.new(85.m, 88.m, 300.m), Geom::Point3d.new(85.m, 88.m, 0.m), Geom::Vector3d.new(0, 1, 0))
  c.perspective = false; c.height = 55.m; vw.camera = c
  vw.write_image(dir + "n1.png", 1600, 900, true, 0.0)
  # 2) kuzeyden (yukari yamactan) guneye bakis, P115 ustunden
  c = Sketchup::Camera.new(Geom::Point3d.new(85.m, 125.m, 45.m), Geom::Point3d.new(85.m, 85.m, 6.m), Geom::Vector3d.new(0, 0, 1))
  c.perspective = true; c.fov = 55; vw.camera = c
  vw.write_image(dir + "n2.png", 1600, 900, true, 0.0)
  # 3) teras icinden kuzeye (yamaca) bakis
  c = Sketchup::Camera.new(Geom::Point3d.new(70.m, 70.m, 14.m), Geom::Point3d.new(70.m, 100.m, 8.m), Geom::Vector3d.new(0, 0, 1))
  c.perspective = true; c.fov = 60; vw.camera = c
  vw.write_image(dir + "n3.png", 1600, 900, true, 0.0)
  vw.camera = cam0
  File.write(dir + "result13.txt", "OK")
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/result13.txt", "ERR #{e.class}: #{e.message}")
end
