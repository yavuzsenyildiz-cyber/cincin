# Binalari kademele (subasman), teras kenarlarina etek duvari ekle, araziyi (kazili) yeniden kur.
require 'json'
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  B = JSON.parse(File.read(dir + "buildings.json"))
  m.start_operation("Binalari kademele + etek duvari", true)
  moved = 0; maxd = 0.0
  (m.entities.grep(Sketchup::Group) + m.entities.grep(Sketchup::ComponentInstance)).each do |e|
    next if e.layer.name == "ARAZI_TM27"
    nm = e.respond_to?(:definition) ? e.definition.name : e.name
    next unless nm.to_s.start_with?("Group#")
    b = e.bounds
    cx = (b.min.x + b.max.x).to_m / 2.0; cy = (b.min.y + b.max.y).to_m / 2.0
    q = B.min_by { |r| (r["cx"] - cx)**2 + (r["cy"] - cy)**2 }
    next if (q["cx"] - cx)**2 + (q["cy"] - cy)**2 > 0.05**2
    next if q["db"] > -0.05
    e.transform!(Geom::Transformation.new(Geom::Vector3d.new(0, 0, q["db"].m)))
    moved += 1; maxd = [maxd, -q["db"]].max
  end
  # etek duvarlari
  mat = m.materials["Brick_Tumbled"] || m.materials.add("ETEK_DUVAR")
  mat.color = Sketchup::Color.new(150, 135, 120) unless m.materials["Brick_Tumbled"]
  g = m.entities.add_group; g.name = "ISTINAT_TERAS_KENAR"; g.layer = m.layers.add("ISTINAT")
  nq = 0; bad = 0
  File.foreach(dir + "skirts.txt") do |ln|
    t = ln.split; next unless t[0] == "Q"
    v = t[1..8].map(&:to_f)
    pts = [Geom::Point3d.new(v[0].m, v[1].m, v[2].m), Geom::Point3d.new(v[4].m, v[5].m, v[6].m),
           Geom::Point3d.new(v[4].m, v[5].m, v[7].m), Geom::Point3d.new(v[0].m, v[1].m, v[3].m)]
    begin
      f = g.entities.add_face(pts); f.material = mat; f.back_material = mat; nq += 1
    rescue
      bad += 1
    end
  end
  m.commit_operation
  File.write(dir + "result11.txt", "OK bina_kademelenen=#{moved} max_alcalma=#{maxd.round(2)} etek_yuz=#{nq} hatali=#{bad}")
  File.write(dir + "h0.txt", "105.07")
  load dir + "build_terrain4.rb"
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "result11.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
