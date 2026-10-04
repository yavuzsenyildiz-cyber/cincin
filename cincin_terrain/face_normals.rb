begin
  m = Sketchup.active_model
  out = []
  m.entities.grep(Sketchup::Face).reject { |f| f.layer.name == "ARAZI_TM27" }.each do |f|
    n = f.normal; c = f.bounds.center; b = f.bounds
    out << "%s nz=%.2f mat=%s back=%s c=(%.1f,%.1f,%.2f) w=%.1f d=%.1f area=%.1f" % [f.persistent_id.to_s[-5..-1], n.z, (f.material ? f.material.name : "-"), (f.back_material ? f.back_material.name : "-"), c.x.to_m, c.y.to_m, c.z.to_m, (b.max.x - b.min.x).to_m, (b.max.y - b.min.y).to_m, f.area * 0.0254 * 0.0254]
  end
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/normals.txt", out.join(10.chr))
rescue => e
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/normals.txt", "ERR #{e.class}: #{e.message}")
end
