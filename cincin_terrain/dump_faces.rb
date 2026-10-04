begin
  m = Sketchup.active_model
  out = []
  cnt = Hash.new(0)
  m.entities.each { |e| cnt[e.class.to_s] += 1 }
  out << "COUNTS " + cnt.map { |k, v| "#{k}=#{v}" }.join(" ")
  m.entities.grep(Sketchup::Face).each do |f|
    next if f.layer.name == "ARAZI_TM27"
    pts = f.outer_loop.vertices.map { |v| p = v.position; "%.3f,%.3f,%.3f" % [p.x.to_m, p.y.to_m, p.z.to_m] }
    out << "F #{f.layer.name} #{f.material ? f.material.name : '-'} #{pts.join(' ')}"
  end
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/faces.txt", out.join(10.chr))
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/faces.txt", "ERR #{e.class}: #{e.message}")
end
