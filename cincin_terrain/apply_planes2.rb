# v2: yol kotuna bagli egimli teras duzlemleri; duvarlar araziye; yol/disaridaki geometri sabit; ters (siyah) arka yuzler duzelt.
require 'json'
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  lv = [3.82, 5.82, 9.82]
  zs = m.entities.grep(Sketchup::Face).reject { |f| f.layer.name == "ARAZI_TM27" }.map { |f| f.vertices.map { |v| v.position.z.to_m.round(2) } }.flatten.uniq
  unless zs.include?(5.82) && zs.include?(9.82) && !zs.any? { |z| (z - 3.23).abs < 0.02 || (z - 4.58).abs < 0.02 }
    File.write(dir + "result5.txt", "ABORT: seviyeler beklenmedik: #{zs.sort.first(12).inspect}")
  else
    pl = JSON.parse(File.read(dir + "planes.json"))
    lines = File.readlines(dir + "grid.txt", chomp: true)
    nx, ny, gx0, gy0, st = lines[0].split.map(&:to_f); nx = nx.to_i; ny = ny.to_i
    tz = lines[1, ny].map { |r| r.split.map(&:to_f) }
    mk = lines[1 + ny, ny]
    terr = lambda do |x, y|
      i = ((x - gx0) / st).clamp(0, nx - 1.001); j = ((y - gy0) / st).clamp(0, ny - 1.001)
      i0 = i.floor; j0 = j.floor; fi = i - i0; fj = j - j0
      a = tz[j0][i0]; b = tz[j0][i0 + 1]; c = tz[j0 + 1][i0]; d = tz[j0 + 1][i0 + 1]
      (a * (1 - fi) + b * fi) * (1 - fj) + (c * (1 - fi) + d * fi) * fj
    end
    inmask = lambda do |x, y|
      i = ((x - gx0) / st).round; j = ((y - gy0) / st).round
      i >= 0 && j >= 0 && i < nx && j < ny && mk[j][i] == "1"
    end
    d_at = lambda { |i, x, y| p = pl[lv[i].to_s]; p["zw"] + p["s"] * (x - p["xw"]) + p["t"] * (y - p["yw"]) - lv[i] }
    dz = lambda do |x, y, z|
      if z <= lv[0] then d_at.call(0, x, y)
      elsif z >= lv[2] then d_at.call(2, x, y)
      else
        i = (z <= lv[1]) ? 0 : 1; w = (z - lv[i]) / (lv[i + 1] - lv[i])
        (1 - w) * d_at.call(i, x, y) + w * d_at.call(i + 1, x, y)
      end
    end
    m.start_operation("Teraslar v2 (yol bagli, egimli)", true)
    m.entities.grep(Sketchup::Group).select { |g| g.name.start_with?("ARAZI_TM27_KOT") }.each(&:erase!)
    moved = 0; walls = 0; skipped = 0
    (m.entities.grep(Sketchup::Group) + m.entities.grep(Sketchup::ComponentInstance)).each do |e|
      b = e.bounds
      cx = (b.min.x + b.max.x).to_m / 2.0; cy = (b.min.y + b.max.y).to_m / 2.0; zmin = b.min.z.to_m
      if e.is_a?(Sketchup::ComponentInstance) && e.definition.name.start_with?("Modern")
        d = terr.call(cx, cy) - 0.05 - zmin; walls += 1
      elsif inmask.call(cx, cy)
        d = dz.call(cx, cy, zmin)
      else
        skipped += 1; next
      end
      next if d.abs < 0.005
      e.transform!(Geom::Transformation.new(Geom::Vector3d.new(0, 0, d.m))); moved += 1
    end
    verts = m.entities.grep(Sketchup::Edge).flat_map(&:vertices).uniq.select { |v| q = v.position; inmask.call(q.x.to_m, q.y.to_m) }
    vecs = verts.map { |v| q = v.position; Geom::Vector3d.new(0, 0, dz.call(q.x.to_m, q.y.to_m, q.z.to_m).m) }
    m.entities.transform_by_vectors(verts, vecs)
    # ters (siyah) arka yuzler: arka malzemeyi on yuze esitle / varsayilan yap
    fixed = 0; seen = {}
    fix = lambda do |ents|
      ents.each do |e|
        if e.is_a?(Sketchup::Face)
          bk = e.back_material
          if bk && (bk.color.red + bk.color.green + bk.color.blue) < 30
            e.back_material = e.material; fixed += 1
          end
        elsif e.is_a?(Sketchup::Group)
          next if e.layer.name == "ARAZI_TM27"
          fix.call(e.entities)
        elsif e.is_a?(Sketchup::ComponentInstance)
          next if seen[e.definition]
          seen[e.definition] = true; fix.call(e.definition.entities)
        end
      end
    end
    fix.call(m.entities)
    m.commit_operation
    File.write(dir + "h0.txt", "105.07")
    File.write(dir + "result5.txt", "OK tasinan=#{moved} duvar=#{walls} sabit(maske disi)=#{skipped} vertex=#{verts.length} arka_yuz_duzeltilen=#{fixed}")
    load dir + "build_terrain3.rb"
  end
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "result5.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
