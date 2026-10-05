# Otopark araci: bos alanin koselerine sirayla tikla, Enter (veya cift tik) ile bitir.
# Ilk tikladigin kenar (1. -> 2. kose) park siralarinin dizildigi kenardir (genelde duvar/yol kenari).
# Alan icine 2.50 x 5.00 m park yerleri cizilir (beyaz 12 cm cizgi, zeminin 2 cm ustunde);
# derinlik yeterse (>= 16 m) 6 m manevra koridorunun karsisina ikinci sira da konur.
# Sonuc "OTOPARK" grubu, "OTOPARK" katmani. Ctrl+Z ile geri alinir. Esc = iptal.
#   load Dir.glob("C:/Users/YOGA/OneDrive/*/*/cincin_terrain/otopark.rb").first
module CincinOtopark
  EN = 2.50 unless defined?(EN)
  BOY = 5.00 unless defined?(BOY)
  KORIDOR = 6.00 unless defined?(KORIDOR)
  CIZGI = 0.12 unless defined?(CIZGI)

  def self.zemin(m, x, y, z0)
    hit = m.raytest([Geom::Point3d.new(x, y, z0), Geom::Vector3d.new(0, 0, -1)], true)
    hit ? hit[0].z : nil
  end

  def self.kur(pts)
    m = Sketchup.active_model
    poly = pts.map { |p| Geom::Point3d.new(p.x, p.y, 0) }
    a = poly[0]; b = poly[1]
    u = b - a; u.z = 0; raise "Ilk iki kose ayni" if u.length < 1.m
    u.normalize!
    v = Geom::Vector3d.new(-u.y, u.x, 0)
    orta = poly.inject(Geom::Vector3d.new(0, 0, 0)) { |s, p| s + Geom::Vector3d.new(p.x, p.y, 0) }
    orta = Geom::Point3d.new(orta.x / poly.length, orta.y / poly.length, 0)
    v.reverse! if (orta - a).dot(v) < 0
    z0 = pts.map(&:z).max + 30.m
    ic = ->(p) { Geom.point_in_polygon_2D(p, poly, true) }
    uzun = (b - a).length.to_m
    derin = poly.map { |p| (p - a).dot(v) }.max.to_m
    siralar = [[0.3, 1]] # [kenardan uzaklik (m), yon]
    siralar << [0.3 + BOY + KORIDOR, 1] if derin >= 0.3 + 2 * BOY + KORIDOR
    m.start_operation("Otopark", true)
    m.entities.grep(Sketchup::Group).select { |g| g.name == "OTOPARK" }.each(&:erase!)
    g = m.entities.add_group; g.name = "OTOPARK"; g.layer = m.layers.add("OTOPARK")
    beyaz = m.materials["OTOPARK_CIZGI"] || m.materials.add("OTOPARK_CIZGI").tap { |x| x.color = Sketchup::Color.new(245, 245, 240) }
    serit = lambda do |p1, p2|
      d = p2 - p1; d.z = 0; d.normalize!
      w = Geom::Vector3d.new(-d.y, d.x, 0); w.length = CIZGI.m / 2
      z1 = zemin(m, p1.x, p1.y, z0); z2 = zemin(m, p2.x, p2.y, z0)
      return unless z1 && z2
      q1 = Geom::Point3d.new(p1.x, p1.y, z1 + 0.02.m); q2 = Geom::Point3d.new(p2.x, p2.y, z2 + 0.02.m)
      f = g.entities.add_face(q1 + w, q2 + w, q2 - w, q1 - w)
      f.reverse! if f.normal.z < 0
      f.material = beyaz; f.back_material = beyaz
    end
    adet = 0
    siralar.each_with_index do |(off, _), si|
      yer = []
      s = 0.3
      while s + EN <= uzun - 0.3
        k = [[s, off], [s + EN, off], [s + EN, off + BOY], [s, off + BOY]].map { |su, sv| a.offset(u, su.m).offset(v, sv.m) }
        yer << k if k.all?(&ic)
        s += EN
      end
      yer.each_with_index do |k, i|
        serit.(k[0], k[3]) if i.zero? || !yer[i - 1][1].distance(k[0]).zero?
        serit.(k[1], k[2])
        serit.(si.zero? ? k[0] : k[3], si.zero? ? k[1] : k[2]) # arka cizgi (koridorun ters tarafi)
      end
      adet += yer.length
    end
    if adet > 0
      t = a.offset(u, (uzun / 2).m).offset(v, (siralar.length > 1 ? 0.3 + BOY + KORIDOR / 2 : 0.3 + BOY + 1.5).m)
      tz = zemin(m, t.x, t.y, z0)
      g.entities.add_text("OTOPARK #{adet} arac", Geom::Point3d.new(t.x, t.y, (tz || 0) + 0.05.m)) if tz
    end
    m.commit_operation
    UI.messagebox("Otopark: #{adet} park yeri (#{EN} x #{BOY} m), #{siralar.length} sira.\n" \
                  "Alan: kenar #{uzun.round(1)} m, derinlik #{derin.round(1)} m" +
                  (adet.zero? ? "\nPark yeri sigmadi; ilk kenari daha uzun secin." : ""))
  rescue => e
    m.abort_operation rescue nil
    UI.messagebox("Otopark HATA: #{e.message}")
  end

  class Arac
    def activate
      @ip = Sketchup::InputPoint.new
      @pts = []
      Sketchup.status_text = "Otopark alaninin koselerine tikla; ilk kenar = park sirasi kenari. Enter = bitir, Esc = iptal"
    end

    def onMouseMove(_f, x, y, view)
      @ip.pick(view, x, y)
      view.invalidate
    end

    def draw(view)
      @ip.draw(view) if @ip.valid?
      return if @pts.empty?
      view.drawing_color = "red"; view.line_width = 3
      view.draw(GL_LINE_STRIP, @pts + (@ip.valid? ? [@ip.position] : []))
    end

    def onLButtonDown(_f, x, y, view)
      @ip.pick(view, x, y)
      @pts << @ip.position if @ip.valid?
      view.invalidate
    end

    def onLButtonDoubleClick(_f, _x, _y, _view)
      bitir
    end

    def onReturn(_view)
      bitir
    end

    def onCancel(_r, view)
      @pts = []
      Sketchup.active_model.select_tool(nil)
    end

    def bitir
      pts = @pts.each_with_object([]) { |p, o| o << p if o.empty? || o.last.distance(p) > 0.1.m }
      if pts.length < 3
        UI.messagebox("En az 3 kose gerekli")
        return
      end
      Sketchup.active_model.select_tool(nil)
      CincinOtopark.kur(pts)
    end
  end
end

Sketchup.active_model.select_tool(CincinOtopark::Arac.new)
