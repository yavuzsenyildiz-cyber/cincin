# Kademelenen binalari teras duzlemine (bitmis zemin) geri al; araziyi bina cukursuz yeniden kur.
require 'json'
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  B = JSON.parse(File.read(dir + "buildings.json"))
  m.start_operation("Binalari teras duzlemine geri al", true)
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
    e.transform!(Geom::Transformation.new(Geom::Vector3d.new(0, 0, (-q["db"]).m)))
    moved += 1; maxd = [maxd, -q["db"]].max
  end
  m.commit_operation
  File.write(dir + "result17.txt", "OK binalar_geri_alindi=#{moved} max=#{maxd.round(2)}")
  load dir + "build_terrain5.rb"
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "result17.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
