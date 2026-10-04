begin
  m = Sketchup.active_model
  rects = { "A(P116 bati)" => [34, 62, 44, 75], "B(P117 bati)" => [44, 46, 66, 61] }
  out = []
  rects.each do |nm, (x0, y0, x1, y1)|
    out << "== #{nm} x[#{x0},#{x1}] y[#{y0},#{y1}]"
    (m.entities.grep(Sketchup::Group) + m.entities.grep(Sketchup::ComponentInstance) + m.entities.grep(Sketchup::Face)).each do |e|
      next if e.respond_to?(:layer) && e.layer.name == "ARAZI_TM27"
      b = e.bounds
      bx0, bx1, by0, by1 = b.min.x.to_m, b.max.x.to_m, b.min.y.to_m, b.max.y.to_m
      next if bx1 < x0 || bx0 > x1 || by1 < y0 || by0 > y1
      next if e.is_a?(Sketchup::ComponentInstance) && e.definition.name =~ /Cypress|Heather|Sree/
      mats = []
      if e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
        ents = e.respond_to?(:definition) ? e.definition.entities : e.entities
        mats = ents.grep(Sketchup::Face).map { |f| f.material ? f.material.name : "-" }.tally.sort_by { |_, v| -v }.first(4)
      else
        mats = [[e.material ? e.material.name : "-", 1]]
      end
      out << "%s %s [%s] x[%.1f,%.1f] y[%.1f,%.1f] z[%.2f,%.2f] hid=%s mats=%s" % [e.class.to_s.split('::').last, (e.respond_to?(:definition) ? e.definition.name[0, 28] : (e.respond_to?(:name) ? e.name[0, 28] : "")), e.layer.name, bx0, bx1, by0, by1, b.min.z.to_m, b.max.z.to_m, e.hidden?, mats.inspect]
    end
  end
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/black.txt", out.join(10.chr))
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/black.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(2).join(10.chr)}")
end
