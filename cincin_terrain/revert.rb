# Mevcut durumu yedekle, sonra kayitli ozgun dosyayi yeniden ac (kaydetmeden).
begin
  dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
  m = Sketchup.active_model
  ok = m.save_copy(dir + "yedek_3_kademeli.skp")
  File.write(dir + "result6.txt", "BACKUP #{ok}")
  Sketchup.open_file("C:/Users/YOGA/OneDrive/MİMARİ/CİNCİN/GUNCEL_D5_SKETCHUP/SketchUp/3dmodel3.skp")
  File.write(dir + "result6.txt", "OPENED title=#{Sketchup.active_model.title} modified=#{Sketchup.active_model.modified?}")
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/result6.txt", "ERR #{e.class}: #{e.message}")
end
