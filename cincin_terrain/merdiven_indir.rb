# Ust kottan (istinat duvari ustu) eve inen duz merdiven kurar.
#   load "C:/cincin_terrain/merdiven_indir.rb"
# Kullanim (iki tik):
#   1) Ust kotta, duvarin ust kenarina tikla. Bir KENARA (edge) tiklarsan o kenarin EN ALCAK ucu
#      alinir -> merdiven en az yukseklikten baslar. Bir yuzeye tiklarsan tiklanan nokta alinir.
#   2) Evin onundeki cime (alt kota) tikla. Merdiven bu yone dogru iner; alt kot bu noktanin z'sidir.
# Rihtim <= 17 cm, basamak 30 cm, genislik 1.20 m. 2 m'den fazla yukseklikte ortada 1.20 m sahanlik.
# Sonuc "MERDIVEN_EVE_INIS" grubu, "MERDIVEN" katmani. Ctrl+Z ile geri alinir.
module CincinMerdiven
  RIHTIM_MAX = 0.17
  BASAMAK    = 0.30
  GENISLIK   = 1.20
  SAHANLIK   = 1.20
  SAHANLIK_H = 2.00

  def self.m(v)
    v.to_f.m
  end

  def self.kur(ust, alt)
    mdl = Sketchup.active_model
    h = (ust.z - alt.z).to_m
    raise "Ust nokta alt noktadan yuksek olmali (fark #{h.round(2)} m)" if h < 0.10
    yon = Geom::Vector3d.new(alt.x - ust.x, alt.y - ust.y, 0)
    raise "Iki nokta ayni yerde" if yon.length < 1.mm
    yon.normalize!
    yan = yon.cross(Z_AXIS); yan.normalize!

    n = (h / RIHTIM_MAX).ceil
    r = h / n
    sahanlik_i = h > SAHANLIK_H ? n / 2 : nil
    kosu = (n - 1) * BASAMAK + (sahanlik_i ? SAHANLIK - BASAMAK : 0)
    yatay = Math.hypot((alt.x - ust.x).to_m, (alt.y - ust.y).to_m)

    mdl.start_operation("Merdiven eve inis", true)
    mdl.entities.grep(Sketchup::Group).select { |g| g.name == "MERDIVEN_EVE_INIS" }.each(&:erase!)
    g = mdl.entities.add_group
    g.name = "MERDIVEN_EVE_INIS"
    g.layer = mdl.layers.add("MERDIVEN")
    ents = g.entities
    mat = mdl.materials["Merdiven_Tas"] || mdl.materials.add("Merdiven_Tas").tap { |x| x.color = Sketchup::Color.new(196, 170, 120) }

    pt = lambda { |s, w, z| ust.offset(yon, m(s)).offset(yan, m(w)).tap { |p| p.z = alt.z + m(z) } }
    kutu = lambda do |s0, s1, z0, z1|
      a = [pt.(s0, -GENISLIK / 2, z0), pt.(s1, -GENISLIK / 2, z0), pt.(s1, GENISLIK / 2, z0), pt.(s0, GENISLIK / 2, z0)]
      sg = ents.add_group  # her blok ayri grup: komsu bloklarin yuzleri birbirine karismasin
      f = sg.entities.add_face(a)
      f.reverse! if f.normal.z < 0
      f.pushpull(m(z1 - z0))
      sg.entities.grep(Sketchup::Face).each { |x| x.material = mat }
    end

    # Her basamak alt kota kadar dolu blok (masif merdiven); i=0 ust kottan bir rihtim asagisi.
    s = 0.0
    (0...n - 1).each do |i|
      ust_z = h - (i + 1) * r
      d = (sahanlik_i && i == sahanlik_i) ? SAHANLIK : BASAMAK
      kutu.(s, s + d, 0.0, ust_z)
      s += d
    end
    mdl.commit_operation
    msg = format("Merdiven: yukseklik %.2f m, %d rihtim x %.1f cm, basamak %d cm, kosu %.2f m%s",
                 h, n, r * 100, (BASAMAK * 100).round, kosu, sahanlik_i ? " (sahanlikli)" : "")
    msg += format("\nUYARI: secilen iki nokta arasi yatay %.2f m, merdiven kosusu %.2f m.", yatay, kosu) if kosu > yatay + 0.05
    puts msg
    UI.messagebox(msg)
  rescue => e
    mdl.abort_operation rescue nil
    UI.messagebox("Merdiven HATA: #{e.message}")
  end

  class Arac
    def activate
      @ip = Sketchup::InputPoint.new
      @ust = nil
      Sketchup.status_text = "1) Ust kottaki duvar ust kenarina tikla (kenar = en alcak ucu alinir)"
    end

    def onMouseMove(_f, x, y, view)
      @ip.pick(view, x, y)
      view.tooltip = @ip.tooltip
      view.invalidate
    end

    def draw(view)
      @ip.draw(view) if @ip.valid?
    end

    def onLButtonDown(_f, x, y, view)
      @ip.pick(view, x, y)
      return unless @ip.valid?
      p = @ip.position
      if @ust.nil?
        ed = @ip.edge
        if ed
          tr = @ip.transformation
          a = ed.start.position.transform(tr); b = ed.end.position.transform(tr)
          p = a.z <= b.z ? a : b
        end
        @ust = p
        Sketchup.status_text = format("Ust kot alindi (z=%.2f). 2) Evin onundeki cime tikla", p.z.to_m)
      else
        CincinMerdiven.kur(@ust, p)
        Sketchup.active_model.select_tool(nil)
      end
    end
  end
end

Sketchup.active_model.select_tool(CincinMerdiven::Arac.new)
