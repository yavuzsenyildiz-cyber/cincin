# Arac yollarini duzlem denkleminden tam hassasiyetle olustur (delikler dahil).
require 'json'
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  pl = JSON.parse(File.read(dir + "dplanes.json"))
  m.start_operation("Arac yollari", true)
  ok = 0; bad = 0; msg = []
  File.foreach(dir + "streets.txt") do |ln|
    t = ln.chomp.split(" ", 5); next unless t[0] == "S"
    mat = m.materials[t[1].tr("~", " ")]; p = pl[t[2]]; off = t[3].to_f
    zf = lambda { |x, y| p["zw"] + p["s"] * (x - p["xw"]) + p["t"] * (y - p["yw"]) + off }
    rings = t[4].split(" | ").map { |r| r.split(";").map { |q| x, y = q.split(",").map(&:to_f); Geom::Point3d.new(x.m, y.m, zf.call(x, y).m) } }
    begin
      f = m.entities.add_face(rings[0])
      rings[1..-1].each { |h| begin; hf = m.entities.add_face(h); hf.erase! if hf && hf.valid? && hf != f; rescue; end }
      f.reverse! if f.normal.z < 0
      if mat then f.material = mat; f.back_material = mat end
      ok += 1
    rescue => e
      bad += 1; msg << e.message[0, 60]
    end
  end
  m.commit_operation
  File.write(dir + "result22.txt", "OK yol_yuzu=#{ok} hatali=#{bad} #{msg.uniq.join(' / ')}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "result22.txt", "ERR #{e.class}: #{e.message}")
end
