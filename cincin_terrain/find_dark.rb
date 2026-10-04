begin
  m = Sketchup.active_model
  out = []
  dark = m.materials.select { |mt| c = mt.color; (c.red + c.green + c.blue) < 90 && mt.alpha > 0.5 }
  out << "koyu malzemeler: " + dark.map { |mt| "#{mt.name}(#{mt.color.red},#{mt.color.green},#{mt.color.blue})" }.inspect
  rects = { "A" => [35.5, 62.5, 43.5, 74.5], "B" => [44, 48, 66, 60] }
  walk = lambda do |ents, tr, path|
    ents.each do |e|
      if e.is_a?(Sketchup::Face)
        mat = e.material; bk = e.back_material
        dm = mat && ((mat.color.red + mat.color.green + mat.color.blue) < 90)
        db = bk && ((bk.color.red + bk.color.green + bk.color.blue) < 90)
        next unless dm || db
        pts = e.vertices.map { |v| (tr * v.position) }
        xs = pts.map { |p| p.x.to_m }; ys = pts.map { |p| p.y.to_m }; zs = pts.map { |p| p.z.to_m }
        rects.each do |nm, (x0, y0, x1, y1)|
          next if xs.max < x0 || xs.min > x1 || ys.max < y0 || ys.min > y1
          out << "#{nm} #{path} FACE mat=#{mat ? mat.name : '-'} back=#{bk ? bk.name : '-'} dm=#{dm} db=#{db} x[%.1f,%.1f] y[%.1f,%.1f] z[%.2f,%.2f] nz=%.2f" % [xs.min, xs.max, ys.min, ys.max, zs.min, zs.max, e.normal.z]
        end
      elsif e.is_a?(Sketchup::Group)
        next if e.layer.name == "ARAZI_TM27"
        walk.call(e.entities, tr * e.transformation, path + "/G:" + e.name[0, 12])
      elsif e.is_a?(Sketchup::ComponentInstance)
        next if e.definition.name =~ /Cypress|Heather|Sree/
        walk.call(e.definition.entities, tr * e.transformation, path + "/C:" + e.definition.name[0, 12])
      end
    end
  end
  walk.call(m.entities, Geom::Transformation.new, "")
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/dark.txt", out.first(60).join(10.chr))
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/dark.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(2).join(10.chr)}")
end
