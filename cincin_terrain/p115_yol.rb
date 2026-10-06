# P115: kitlelerin arkasindan arac yolu + YAPI2/YAPI3 arasi otopark + YAPI3 arkasinda yaya yolu; bahceler +-0.00; istinat duvarlari.
# Onceki P115 arazi/bahce/duvar/merdiven/bahce duvari gruplarini yeniler; istinatlar tas kapli, kirmizi P115_KITLE_TABAN'i siler; bahceler subasman altinda,
# istinattan bahceye merdiven; sonunda ev_duzelt.rb ile ev altlari tas kapli dolgu. Orijinal PLANKOTE arazisini gizler (silmez).
# Kaydetmez; Ctrl+Z geri alir.   load Dir.glob("C:/Users/YOGA/OneDrive/*/*/cincin_terrain/p115_yol.rb").first
dir = File.dirname(__FILE__) + "/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  m.start_operation("P115 yol + otopark + yaya yolu", true)
  ents = m.entities
  ents.grep(Sketchup::Group).select { |g| g.name =~ /^(P115_ARAZI|P115_BAHCE|P115_DUVAR|P115_OTOPARK|P115_ETIKET|P115_MERDIVEN|P115_KITLE_TABAN)/ }.each(&:erase!)
  orig = ents.grep(Sketchup::Group).select { |g| g.name.start_with?("ARAZI (PLANKOTE") }
  orig.each { |g| g.hidden = true }
  mk = lambda { |n, r, g, b| x = m.materials[n] || m.materials.add(n); x.color = Sketchup::Color.new(r, g, b); x }
  # SketchUp malzeme kutuphanesinden (.skm) malzeme yukle; bulunamazsa duz renkli yedek
  kutup = lambda do |adlar, yedek, r, g, b|
    adlar.each { |a| x = m.materials[a] || m.materials["[#{a}]"]; return x if x }
    kok = (Sketchup.find_support_file("Materials") rescue nil)
    dosyalar = kok ? Dir.glob(File.join(kok, "**", "*.skm")) : []
    adlar.each do |a|
      f = dosyalar.find { |d| File.basename(d, ".skm").casecmp(a).zero? }
      if f
        x = (m.materials.load(f) rescue nil)
        return x if x
      end
    end
    mk.(yedek, r, g, b)
  end
  # istinat duvarlari: evlerin tasindan (Sandstone Ashlar) farkli, gri-kahve dogal tas
  istinat_tas = kutup.(["Stone Masonry Multi", "Stone Fieldstone", "Stone Coursed Rough", "Stone Masonry Rough"], "ISTINAT_TAS", 128, 118, 105)
  (istinat_tas.texture.size = 1.5.m if istinat_tas.texture) rescue nil
  mats = {
    "arazi" => (m.materials["ARAZI_PLANKOTE_UYDU"] || mk.("ARAZI_PLANKOTE_UYDU", 120, 120, 90)),
    "cim" => mk.("BAHCE_CIM", 96, 150, 60), "asfalt" => mk.("ARAC_YOLU_ASFALT", 70, 70, 75),
    "otopark" => mk.("OTOPARK_ZEMIN", 120, 120, 128), "yaya" => mk.("YAYA_YOLU", 205, 190, 150),
    "kaldirim" => mk.("KALDIRIM", 200, 190, 170),
    "perde_beton" => istinat_tas,
    "perde_tas" => (m.materials["[Stone Sandstone Ashlar Light]"] || mk.("ETEK_DUVAR", 200, 175, 130))
  }
  v = []; tris = Hash.new { |h, k| h[k] = [] }
  File.foreach(dir + "p115y_mesh.txt") do |ln|
    t = ln.split
    if t[0] == "V" then v << t[1..5].map(&:to_f)
    elsif t[0] == "F" then tris[t[4]] << t[1..3].map(&:to_i)
    end
  end
  ga = ents.add_group; ga.name = "P115_ARAZI (bahce, yol, otopark, yaya yolu)"; ga.layer = orig.first ? orig.first.layer : m.layers.add("ARAZI")
  nf = 0
  tris.each do |tag, fs|
    pm = Geom::PolygonMesh.new
    idx = {}
    fs.each do |f3|
      ii = f3.map do |q|
        idx[q] ||= begin
          p = v[q]; i = pm.add_point(Geom::Point3d.new(p[0].m, p[1].m, p[2].m)); pm.set_uv(i, Geom::Point3d.new(p[3], p[4], 0), true) if tag == "arazi"; i
        end
      end
      pm.add_polygon(*ii) unless ii.uniq.length < 3
    end
    sg = ga.entities.add_group; sg.name = tag
    sg.entities.add_faces_from_mesh(pm, Geom::PolygonMesh::AUTO_SOFTEN | Geom::PolygonMesh::SMOOTH_SOFT_EDGES, mats[tag], mats[tag])
    nf += fs.length
  end

  bet = mk.("ISTINAT_BETON", 150, 150, 150); bd = mk.("BAHCE_DUVARI", 175, 170, 160)
  gw = ents.add_group; gw.name = "P115_DUVAR (istinat, basamak, dolgu+korkuluk)"; gw.layer = m.layers.add("ISTINAT_DUVARI")
  # gercek istinat duvari: 30 cm govde (alcak tarafa), 30 cm gomulu taban, ust baslik; dolgu tarafinda +0.9 m korkuluk duvari
  th = 0.30
  wm = Hash.new { |h, k| h[k] = Geom::PolygonMesh.new }; nw = 0
  quad = lambda { |mesh, p| i = p.map { |q| mesh.add_point(q) }; mesh.add_polygon(i[0], i[1], i[2]); mesh.add_polygon(i[0], i[2], i[3]) }
  File.foreach(dir + "p115y_duvar.txt") do |ln|
    t = ln.split; next unless t[0] == "W"
    x0, y0, x1, y1, l0, l1, h0, h1, nx, ny = t[2..11].map(&:to_f); e0 = t[12] == "1"; e1 = t[13] == "1"
    mesh = wm[t[1]]
    p = lambda { |x, y, z| Geom::Point3d.new(x.m, y.m, z.m) }
    a0 = p.(x0, y0, l0); b0 = p.(x1, y1, l1); b1 = p.(x1, y1, h1); a1 = p.(x0, y0, h0)
    c0 = p.(x0 + nx * th, y0 + ny * th, l0); d0 = p.(x1 + nx * th, y1 + ny * th, l1); d1 = p.(x1 + nx * th, y1 + ny * th, h1); c1 = p.(x0 + nx * th, y0 + ny * th, h0)
    begin
      quad.(mesh, [a0, b0, b1, a1]); quad.(mesh, [c0, c1, d1, d0]); quad.(mesh, [a1, b1, d1, c1])
      quad.(mesh, [a0, a1, c1, c0]) if e0
      quad.(mesh, [b0, d0, d1, b1]) if e1
      nw += 1
    rescue
    end
  end
  wm.each { |k, mesh| mm = istinat_tas;   # tum istinat/dolgu duvarlari tas kapli
    gw.entities.add_faces_from_mesh(mesh, Geom::PolygonMesh::AUTO_SOFTEN, mm, mm) if mesh.count_polygons > 0 }

  pts = ->(s, z) { s.split(";").map { |q| x, y = q.split(",").map(&:to_f); Geom::Point3d.new(x.m, y.m, z.m) } }
  go = ents.add_group; go.name = "P115_OTOPARK (park yerleri)"; go.layer = m.layers.add("OTOPARK")
  stm = mk.("OTOPARK_YER", 150, 150, 160); ns = 0
  File.foreach(dir + "p115y_park.txt") do |ln|
    t = ln.split; next unless t[0] == "S"
    begin
      fc = go.entities.add_face(pts.(t[2], t[1].to_f)); fc.reverse! if fc.normal.z < 0
      fc.material = stm; fc.back_material = stm; ns += 1
    rescue
    end
  end
  gm = ents.add_group; gm.name = "P115_MERDIVEN (yaya yolu basamak cizgileri)"; gm.layer = m.layers.add("MERDIVEN")
  File.foreach(dir + "p115y_merdiven.txt") do |ln|
    t = ln.split; next unless t[0] == "M"
    x0, y0, x1, y1, z = t[1..5].map(&:to_f)
    gm.entities.add_line(Geom::Point3d.new(x0.m, y0.m, z.m), Geom::Point3d.new(x1.m, y1.m, z.m)) rescue nil
  end
  # istinattan YAPI1 bahcesine (yesile) inen merdiven: kot farkinin en az oldugu yerde, masif basamaklar
  tas = m.materials["[Stone Sandstone Ashlar Light]"] || mk.("MERDIVEN_TAS", 196, 170, 120)
  gb = ents.add_group; gb.name = "P115_MERDIVEN (istinat -> bahce)"; gb.layer = m.layers.add("MERDIVEN")
  nb = 0
  File.foreach(dir + "p115y_basamak.txt") do |ln|
    t = ln.split; next unless t[0] == "T"
    z0 = t[1].to_f; z1 = t[2].to_f
    sg = gb.entities.add_group
    fc = sg.entities.add_face(pts.(t[3], z0)); fc.reverse! if fc.normal.z < 0
    fc.pushpull((z1 - z0).m)
    sg.entities.grep(Sketchup::Face).each { |q| q.material = tas; q.back_material = tas }
    nb += 1
  end
  ge = ents.add_group; ge.name = "P115_ETIKET"; ge.layer = m.layers.add("YAPI_KOT")
  File.foreach(dir + "p115y_etiket.txt") do |ln|
    t = ln.chomp.split(" ", 5); next unless t[0] == "E"
    ge.entities.add_text(t[4].tr("|", "\n"), Geom::Point3d.new(t[1].to_f.m, t[2].to_f.m, t[3].to_f.m), Geom::Vector3d.new(0, 0, 3.m))
  end
  # bahce duvari: istinat ustunde, 2.5 m bolmeli, kademeli. Tas kapli dikme + sivali alcak duvar + kapak + ahsap yatay citalar
  siva = mk.("BAHCE_DUVARI_SIVA", 236, 232, 222)
  kapak = kutup.(["Stone Granite Light", "Stone Marble Light", "Concrete Polished"], "BAHCE_DUVARI_KAPAK", 205, 203, 198)
  ahsap = kutup.(["Wood Cherry Original", "Wood Floor Light", "Wood Bamboo Medium"], "BAHCE_DUVARI_AHSAP", 122, 86, 55)
  gb2 = ents.add_group; gb2.name = "P115_BAHCE_DUVARI (istinat ustu)"; gb2.layer = m.layers.add("BAHCE_DUVARI")
  kutu = lambda do |p0, p1, yari, z0, z1, mat|
    u = p1 - p0
    return if u.length < 1.mm
    u.normalize!; n = Geom::Vector3d.new(-u.y, u.x, 0); n.length = yari
    pts = [p0.offset(n), p1.offset(n), p1.offset(n.reverse), p0.offset(n.reverse)].map { |q| Geom::Point3d.new(q.x, q.y, z0) }
    sg = gb2.entities.add_group
    f = (sg.entities.add_face(pts) rescue nil)
    unless f
      sg.erase!
      return
    end
    f.reverse! if f.normal.z < 0
    f.pushpull(z1 - z0)
    sg.entities.grep(Sketchup::Face).each { |q| q.material = mat; q.back_material = mat }
  end
  dikme = {}; nbd = 0
  File.foreach(dir + "p115y_bahce_duvari.txt") do |ln|
    t = ln.split; next unless t[0] == "B"
    x0, y0, x1, y1, zb, ox, oy = t[1..7].map(&:to_f)
    off = Geom::Vector3d.new(ox, oy, 0); off.length = 0.15.m           # istinat govdesinin ortasi
    a = Geom::Point3d.new(x0.m, y0.m, 0).offset(off); b = Geom::Point3d.new(x1.m, y1.m, 0).offset(off)
    u = b - a
    next if u.length < 0.5.m
    u.normalize!
    a2 = a.offset(u, 0.20.m); b2 = b.offset(u.reverse, 0.20.m)
    z = zb.m
    kutu.(a2, b2, 0.125.m, z - 0.05.m, z + 0.60.m, siva)                 # alcak duvar 25 cm kalin, 60 cm
    kutu.(a2, b2, 0.165.m, z + 0.60.m, z + 0.66.m, kapak)                # kapak tasi
    4.times { |k| kutu.(a2, b2, 0.025.m, z + (0.76 + k * 0.17).m, z + (0.85 + k * 0.17).m, ahsap) }   # ahsap yatay citalar
    [a, b].each do |q|
      key = [(q.x.to_m * 20).round, (q.y.to_m * 20).round]
      d = (dikme[key] ||= { p: q, u: u, z0: zb, z1: zb })
      d[:z0] = [d[:z0], zb].min; d[:z1] = [d[:z1], zb].max
    end
    nbd += 1
  end
  dikme.each_value do |d|
    q = d[:p]; u = d[:u]
    kutu.(q.offset(u.reverse, 0.20.m), q.offset(u, 0.20.m), 0.20.m, (d[:z0] - 0.05).m, (d[:z1] + 1.55).m, istinat_tas)    # dikme 40x40 (kademede uzun olan)
    kutu.(q.offset(u.reverse, 0.25.m), q.offset(u, 0.25.m), 0.25.m, (d[:z1] + 1.55).m, (d[:z1] + 1.61).m, kapak)          # dikme basligi
  end
  m.commit_operation
  File.write(dir + "p115_yol_result.txt", "OK ucgen=#{nf} duvar=#{nw} park_yeri=#{ns} basamak=#{nb} bahce_duvari_bolme=#{nbd} gizlenen_arazi=#{orig.length}")
  # ev altlari: subasman altindaki acik kalan yerleri tas kapli dolgu blokla kapat (tum KITLE_ evleri)
  m.selection.clear
  load dir + "ev_duzelt.rb"
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "p115_yol_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(2).join("\n")}")
end
