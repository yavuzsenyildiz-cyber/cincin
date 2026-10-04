# Teraslari yola baglı, araziyi izleyen egimli duzlemlere oturt; dogal araziyi H0=105.07 ile yeniden kur.
require 'json'
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  lv = [3.82, 5.82, 9.82]
  zs = m.entities.grep(Sketchup::Face).reject { |f| f.layer.name == "ARAZI_TM27" }.map { |f| f.vertices.map { |v| v.position.z.to_m.round(2) } }.flatten.uniq
  unless zs.include?(5.82) && zs.include?(9.82) && !zs.any? { |z| (z - 3.23).abs < 0.02 || (z - 4.58).abs < 0.02 }
    File.write(dir + "result5.txt", "ABORT: geri alma sonrasi seviyeler beklenmedik: #{zs.sort.inspect}")
  else
    pl = JSON.parse(File.read(dir + "planes.json"))
    d_at = lambda do |i, x, y|
      p = pl[lv[i].to_s]
      p["zw"] + p["s"] * (x - p["xw"]) + p["t"] * (y - p["yw"]) - lv[i]
    end
    dz = lambda do |x, y, z|
      if z <= lv[0] then d_at.call(0, x, y)
      elsif z >= lv[2] then d_at.call(2, x, y)
      else
        i = (z <= lv[1]) ? 0 : 1
        w = (z - lv[i]) / (lv[i + 1] - lv[i])
        (1 - w) * d_at.call(i, x, y) + w * d_at.call(i + 1, x, y)
      end
    end
    m.start_operation("Teraslari egimli duzlemlere oturt", true)
    m.entities.grep(Sketchup::Group).select { |g| g.name.start_with?("ARAZI_TM27_KOT") }.each(&:erase!)
    moved = 0; maxd = -99.0; mind = 99.0
    (m.entities.grep(Sketchup::Group) + m.entities.grep(Sketchup::ComponentInstance)).each do |e|
      b = e.bounds
      d = dz.call((b.min.x + b.max.x).to_m / 2.0, (b.min.y + b.max.y).to_m / 2.0, b.min.z.to_m)
      next if d.abs < 0.005
      e.transform!(Geom::Transformation.new(Geom::Vector3d.new(0, 0, d.m)))
      moved += 1; maxd = [maxd, d].max; mind = [mind, d].min
    end
    verts = m.entities.grep(Sketchup::Edge).flat_map(&:vertices).uniq
    vecs = verts.map { |v| q = v.position; Geom::Vector3d.new(0, 0, dz.call(q.x.to_m, q.y.to_m, q.z.to_m).m) }
    m.entities.transform_by_vectors(verts, vecs)
    m.commit_operation
    File.write(dir + "h0.txt", "105.07")
    File.write(dir + "result5.txt", "OK ogeler=#{moved} vertex=#{verts.length} delta_min=#{mind.round(2)} delta_max=#{maxd.round(2)}")
    load dir + "build_terrain3.rb"
  end
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "result5.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
