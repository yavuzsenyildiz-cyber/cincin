# Uzatilmis (gerilmis) bahce duvarlarini duzelt: cit orijinal boyuna donsun ve ustte dursun, altina tas istinat duvari (kutu) konsun.
dir = "C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  W = File.readlines(dir + "walls.txt", chomp: true).map { |l| a = l.split.map(&:to_f); { x: a[0], y: a[1], h: a[3] } }
  mat = m.materials["ETEK_DUVAR"] || m.materials.add("ETEK_DUVAR")
  mat.color = Sketchup::Color.new(150, 135, 120) if mat.texture.nil? && mat.color.red == 255
  m.start_operation("Citleri normal boya dondur, tas istinat ekle", true)
  g = m.entities.add_group; g.name = "ISTINAT_BAHCE_DUVAR"; g.layer = m.layers.add("ISTINAT")
  fixed = 0; maxr = 0.0; sumr = 0.0
  m.entities.grep(Sketchup::ComponentInstance).each do |e|
    next unless e.definition.name.start_with?("Modern")
    b = e.bounds
    cx = (b.min.x + b.max.x).to_m / 2.0; cy = (b.min.y + b.max.y).to_m / 2.0
    w = W.min_by { |q| (q[:x] - cx)**2 + (q[:y] - cy)**2 }
    next if (w[:x] - cx)**2 + (w[:y] - cy)**2 > 0.05**2
    h0 = w[:h]; zmin = b.min.z.to_m; zmax = b.max.z.to_m; hcur = zmax - zmin
    next if hcur - h0 < 0.15
    t = e.transformation; lb = e.definition.bounds
    cn = [[lb.min.x, lb.min.y], [lb.max.x, lb.min.y], [lb.max.x, lb.max.y], [lb.min.x, lb.max.y]].map { |lx, ly| q = t * Geom::Point3d.new(lx, ly, lb.min.z); [q.x, q.y] }
    ztop_r = zmax - h0                     # istinat ustu = citin tabani
    # cit: orijinal boya don, ustte dur
    e.transform!(Geom::Transformation.scaling(Geom::Point3d.new(b.center.x, b.center.y, b.min.z), 1.0, 1.0, h0 / hcur))
    e.transform!(Geom::Transformation.new(Geom::Vector3d.new(0, 0, (ztop_r - zmin).m)))
    # tas istinat kutusu (zmin .. ztop_r)
    pb = cn.map { |x, y| Geom::Point3d.new(x, y, zmin.m) }
    pt = cn.map { |x, y| Geom::Point3d.new(x, y, ztop_r.m) }
    faces = [pt] + (0..3).map { |i| j = (i + 1) % 4; [pb[i], pb[j], pt[j], pt[i]] }
    faces.each { |pts| begin; f = g.entities.add_face(pts); f.material = mat; f.back_material = mat; rescue; end }
    fixed += 1; r = ztop_r - zmin; maxr = [maxr, r].max; sumr += r
  end
  m.commit_operation
  vw = m.active_view; cam0 = vw.camera
  vw.camera = Sketchup::Camera.new(Geom::Point3d.new(20.m, -10.m, 18.m), Geom::Point3d.new(60.m, 45.m, 4.m), Geom::Vector3d.new(0, 0, 1))
  vw.write_image(dir + "check15.png", 1600, 900, true, 0.0)
  vw.camera = cam0
  File.write(dir + "result15.txt", "OK duzeltilen_duvar=#{fixed} istinat_yuk_ort=#{(sumr / [fixed, 1].max).round(2)} max=#{maxr.round(2)}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "result15.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
