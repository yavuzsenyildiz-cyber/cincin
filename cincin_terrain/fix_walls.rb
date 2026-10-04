# Bahce duvarlari: asagi yamacta teras kenarini tutan (teras+korkuluk), yukari yamacta istinat (arazi+0.3) olacak sekilde boylandir.
require 'json'
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  pl = JSON.parse(File.read(dir + "planes.json"))
  lines = File.readlines(dir + "grid.txt", chomp: true)
  nx, ny, gx0, gy0, st = lines[0].split.map(&:to_f); nx = nx.to_i; ny = ny.to_i
  tz = lines[1, ny].map { |r| r.split.map(&:to_f) }
  terr = lambda do |x, y|
    i = ((x - gx0) / st).clamp(0, nx - 1.001); j = ((y - gy0) / st).clamp(0, ny - 1.001)
    i0 = i.floor; j0 = j.floor; fi = i - i0; fj = j - j0
    (tz[j0][i0] * (1 - fi) + tz[j0][i0 + 1] * fi) * (1 - fj) + (tz[j0 + 1][i0] * (1 - fi) + tz[j0 + 1][i0 + 1] * fi) * fj
  end
  plane = lambda { |l, x, y| p = pl[l.to_s]; p["zw"] + p["s"] * (x - p["xw"]) + p["t"] * (y - p["yw"]) }
  W = File.readlines(dir + "walls.txt", chomp: true).map { |l| a = l.split.map(&:to_f); { x: a[0], y: a[1], l: a[2], h: a[3] } }
  m.start_operation("Bahce duvarlarini boylandir", true)
  n = { fill: 0, cut: 0, flat: 0, nomatch: 0 }; maxh = 0.0
  m.entities.grep(Sketchup::ComponentInstance).each do |e|
    next unless e.definition.name.start_with?("Modern")
    b = e.bounds
    cx = (b.min.x + b.max.x).to_m / 2.0; cy = (b.min.y + b.max.y).to_m / 2.0
    w = W.min_by { |q| (q[:x] - cx)**2 + (q[:y] - cy)**2 }
    if (w[:x] - cx)**2 + (w[:y] - cy)**2 > 0.05**2 then n[:nomatch] += 1; next end
    p = plane.call(w[:l], cx, cy); t = terr.call(cx, cy); h0 = w[:h]
    if t < p - 0.1 then zb = t - 0.05; ztop = p + h0; n[:fill] += 1
    elsif t > p + 0.3 then zb = p - 0.05; ztop = t + 0.3; n[:cut] += 1
    else zb = [p, t].max - 0.05; ztop = zb + h0; n[:flat] += 1 end
    hnew = [[ztop - zb, h0].max, 4.0].min; maxh = [maxh, hnew].max
    zcur = b.min.z.to_m; hcur = (b.max.z - b.min.z).to_m
    s = hnew / hcur
    e.transform!(Geom::Transformation.scaling(Geom::Point3d.new(b.center.x, b.center.y, b.min.z), 1.0, 1.0, s))
    e.transform!(Geom::Transformation.new(Geom::Vector3d.new(0, 0, (zb - zcur).m)))
  end
  m.commit_operation
  vw = m.active_view; cam0 = vw.camera
  vw.camera = Sketchup::Camera.new(Geom::Point3d.new(-30.m, 40.m, 20.m), Geom::Point3d.new(60.m, 60.m, 4.m), Geom::Vector3d.new(0, 0, 1))
  vw.write_image(dir + "check10.png", 1600, 900, true, 0.0)
  vw.camera = cam0
  File.write(dir + "result10.txt", "OK asagi(fill)=#{n[:fill]} yukari(cut)=#{n[:cut]} duz=#{n[:flat]} eslesmeyen=#{n[:nomatch]} max_yukseklik=#{maxh.round(2)}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "result10.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
