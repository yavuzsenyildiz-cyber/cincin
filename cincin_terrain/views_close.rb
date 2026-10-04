begin
  dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
  m = Sketchup.active_model; vw = m.active_view; cam0 = vw.camera
  [["c1.png", [60, 30, 14], [85, 60, 4]], ["c2.png", [125, 38, 16], [100, 58, 4]], ["c3.png", [60, 100, 22], [60, 75, 7]]].each do |f, e, t|
    c = Sketchup::Camera.new(Geom::Point3d.new(e[0].m, e[1].m, e[2].m), Geom::Point3d.new(t[0].m, t[1].m, t[2].m), Geom::Vector3d.new(0, 0, 1))
    c.perspective = true; c.fov = 55; vw.camera = c
    vw.write_image(dir + f, 1600, 900, true, 0.0)
  end
  vw.camera = cam0
  File.write(dir + "result19.txt", "OK")
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/result19.txt", "ERR #{e.class}: #{e.message}")
end
