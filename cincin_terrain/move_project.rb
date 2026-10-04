# Uc terasi parsel basina araziye gore indir (yol baglı, bati %40 doğal arazi ortalaması)
begin
  dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
  m = Sketchup.active_model
  begin; m.abort_operation; rescue; end
  m.close_active while m.active_path
  # (z, indirme m): z=3.82 P117 -> 0.00 ; z=5.82 P116 -> 2.59 ; z=9.82 P115 -> 5.24
  pts = [[3.82, 0.0], [5.82, 2.59], [9.82, 5.24]]
  dz = lambda do |z|
    if z <= pts[0][0] then pts[0][1]
    elsif z >= pts[2][0] then pts[2][1]
    else
      a, b = (z <= pts[1][0]) ? [pts[0], pts[1]] : [pts[1], pts[2]]
      a[1] + (b[1] - a[1]) * (z - a[0]) / (b[0] - a[0])
    end
  end
  m.start_operation("Teraslari araziye gore indir", true)
  moved = 0; maxd = 0.0
  (m.entities.grep(Sketchup::Group) + m.entities.grep(Sketchup::ComponentInstance)).each do |e|
    next if e.layer.name == "ARAZI_TM27"
    d = dz.call(e.bounds.min.z.to_m)
    next if d.abs < 0.005
    e.transform!(Geom::Transformation.new(Geom::Vector3d.new(0, 0, -d.m)))
    moved += 1; maxd = [maxd, d].max
  end
  verts = m.entities.grep(Sketchup::Edge).flat_map(&:vertices).uniq
  vecs = verts.map { |v| Geom::Vector3d.new(0, 0, -dz.call(v.position.z.to_m).m) }
  m.entities.transform_by_vectors(verts, vecs)
  m.commit_operation
  File.write(dir + "h0.txt", "105.07")
  File.write(dir + "result4.txt", "OK ogeler_tasindi=#{moved} vertex=#{verts.length} max_indirme=#{maxd.round(2)}")
  load dir + "build_terrain3.rb"   # dogal arazi, H0=105.07
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/result4.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
