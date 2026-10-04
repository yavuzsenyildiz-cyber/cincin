# Agaclari (en yakin eslesmeyle) kendi teras kademesinin kotuna oturt.
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  H = Hash.new { |h, k| h[k] = [] }
  File.foreach(dir + "trees2.txt") do |ln|
    a = ln.split.map(&:to_f); next if a.length < 5
    H[[(a[0] / 0.1).floor, (a[1] / 0.1).floor]] << a
  end
  m.start_operation("Agaclari kademeye oturt", true)
  total = 0; matched = 0; moved = 0; maxd = 0.0
  m.entities.grep(Sketchup::ComponentInstance).each do |e|
    next unless e.definition.name.include?("Cypress")
    total += 1
    b = e.bounds
    cx = (b.min.x + b.max.x).to_m / 2.0; cy = (b.min.y + b.max.y).to_m / 2.0
    best = nil; bd = 0.03**2
    (-1..1).each { |i| (-1..1).each { |j| H[[(cx / 0.1).floor + i, (cy / 0.1).floor + j]].each { |a| d = (a[0] - cx)**2 + (a[1] - cy)**2; if d < bd then bd = d; best = a end } } }
    next unless best
    matched += 1
    d = best[4] - b.min.z.to_m
    next if d.abs < 0.005
    e.transform!(Geom::Transformation.new(Geom::Vector3d.new(0, 0, d.m))); moved += 1; maxd = [maxd, d.abs].max
  end
  m.commit_operation
  File.write(dir + "result20.txt", "OK agac=#{total} eslesen=#{matched} tasinan=#{moved} max_kayma=#{maxd.round(2)}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "result20.txt", "ERR #{e.class}: #{e.message}")
end
