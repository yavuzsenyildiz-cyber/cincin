dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  out = "C:/Users/YOGA/OneDrive/MİMARİ/CİNCİN/GUNCEL_D5_SKETCHUP/SketchUp/CINCIN_arazi_KOTLANDIRMA.skp"
  ok = m.save(out)
  ro = m.rendering_options; ro["Texture"] = true
  File.write(dir + "saveas.txt", "OK #{ok} path=#{m.path} title=#{m.title} tex=#{ro['Texture']} rmode=#{ro['RenderMode']}")
rescue => e
  File.write(dir + "saveas.txt", "ERR #{e.class}: #{e.message}")
end
