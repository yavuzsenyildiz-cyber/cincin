begin
  m = Sketchup.active_model
  L = []
  L << "title=#{m.title} modified=#{m.modified?} active_path=#{m.active_path.inspect}"
  L << "top: " + m.entities.map { |e| e.class.to_s.split('::').last }.group_by { |x| x }.map { |k, v| "#{k}=#{v.length}" }.join(" ")
  m.entities.grep(Sketchup::Group).each do |g|
    b = g.bounds
    L << "G #{g.name[0, 40]} [#{g.layer.name}] z %.2f..%.2f faces=%d" % [b.min.z.to_m, b.max.z.to_m, g.entities.grep(Sketchup::Face).length] if g.layer.name == "ARAZI_TM27" || g.name.start_with?("ARAZI")
  end
  zs = m.entities.grep(Sketchup::Face).reject { |f| f.layer.name == "ARAZI_TM27" }.map { |f| f.vertices.map { |v| v.position.z.to_m.round(2) } }.flatten.uniq.sort
  L << "loose face z-levels: #{zs.inspect}"
  bz = m.entities.grep(Sketchup::Group).reject { |g| g.layer.name == "ARAZI_TM27" || g.name.start_with?("ARAZI") }.map { |g| g.bounds.min.z.to_m.round(2) }.sort
  L << "bina grup min z: #{bz.inspect}"
  L << "materials: " + m.materials.map(&:name).select { |n| n.include?("ARAZI") }.inspect
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/state.txt", L.join(10.chr))
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/state.txt", "ERR #{e.class}: #{e.message}")
end
