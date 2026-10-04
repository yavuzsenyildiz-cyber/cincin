begin
  dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
  m = Sketchup.active_model; vw = m.active_view; cam0 = vw.camera
  tag = m.layers["ARAZI_TM27"]
  was = tag.visible?
  tag.visible = false
  c = Sketchup::Camera.new(Geom::Point3d.new(45.m, 70.m, 300.m), Geom::Point3d.new(45.m, 70.m, 0.m), Geom::Vector3d.new(0, 1, 0))
  c.perspective = false; c.height = 75.m; vw.camera = c
  vw.write_image(dir + "wb.png", 1600, 900, true, 0.0)
  tag.visible = was
  vw.camera = cam0
  File.write(dir + "result9.txt", "OK tag_gorunur_geri=#{tag.visible?}")
rescue => e
  begin; m.layers["ARAZI_TM27"].visible = true; rescue; end
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/result9.txt", "ERR #{e.class}: #{e.message}")
end
