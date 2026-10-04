begin
  m = Sketchup.active_model
  out = []
  m.entities.grep(Sketchup::ComponentInstance).each do |e|
    next unless e.definition.name.start_with?("Modern")
    b = e.bounds
    out << "W %.3f %.3f %.3f %.3f %.3f %.3f" % [b.min.x.to_m, b.min.y.to_m, b.min.z.to_m, b.max.x.to_m, b.max.y.to_m, b.max.z.to_m]
  end
  add_faces = lambda do |ents, tag|
    ents.grep(Sketchup::Face).each do |f|
      pts = f.vertices.map { |v| p = v.position; "%.2f,%.2f,%.2f" % [p.x.to_m, p.y.to_m, p.z.to_m] }
      out << "#{tag} " + pts.join(";")
    end
  end
  m.entities.grep(Sketchup::Face).each do |f|
    next unless f.material && f.material.name.include?("Brick")
    pts = f.vertices.map { |v| p = v.position; "%.2f,%.2f,%.2f" % [p.x.to_m, p.y.to_m, p.z.to_m] }
    out << "R " + pts.join(";")
  end
  m.entities.grep(Sketchup::Group).select { |g| g.name == "ISTINAT_TERAS_KENAR" }.each { |g| add_faces.call(g.entities, "S") }
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/walls_live.txt", out.join(10.chr))
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/walls_live.txt", "ERR #{e.class}: #{e.message}")
end
