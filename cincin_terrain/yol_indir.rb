# Evin onundeki yolu/zemini subasman (kitle tabani) kotuna indirir: pencere/kapi yolun altinda kalmasin.
# Kullanim (iki tik):
#   1) Evin duvarina tikla (KITLE_ grubu bulunur, tabani = subasman alti kotu).
#   2) Indirilecek yola, evin o cephesinin onunde bir yere tikla (cephe secilir).
# O cephenin onunde TAM mesafesine kadar zemin tam kitle tabanina iner, GECIS mesafesi icinde
# eski kotuna yumusak baglanir; cephe uclarindan da GECIS kadar rampa yapilir. Sadece tabandan
# YUKSEK noktalar indirilir; evin diger cephelerine ve bahceye dokunulmaz.
# Duzenlenen: adi ARAZI veya YOL iceren gruplar (ve icindeki gruplar); dusey yuzlu noktalar (duvar, bordur)
# atlanir. Ctrl+Z ile geri alinir.
#   load Dir.glob("C:/Users/YOGA/OneDrive/*/*/cincin_terrain/yol_indir.rb").first
module CincinYol
  TAM = 4.0 unless defined?(TAM)       # cepheden itibaren tam taban kotunda kalan serit (m) = yol genisligi
  GECIS = 6.0 unless defined?(GECIS)   # eski kota baglanma mesafesi (m)

  def self.alt_noktalar(ents, tr, out)
    ents.each do |e|
      if e.is_a?(Sketchup::Face) then e.vertices.each { |v| out << v.position.transform(tr) }
      elsif e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance) then alt_noktalar(e.definition.entities, tr * e.transformation, out)
      end
    end
  end

  def self.kabuk(pts)
    p = pts.map { |q| [q.x.to_f, q.y.to_f] }.uniq.sort
    cr = ->(o, a, b) { (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]) }
    lo = []; p.each { |q| lo.pop while lo.length >= 2 && cr.(lo[-2], lo[-1], q) <= 0; lo << q }
    up = []; p.reverse.each { |q| up.pop while up.length >= 2 && cr.(up[-2], up[-1], q) <= 0; up << q }
    lo[0...-1] + up[0...-1]
  end

  def self.duzenle(m, ents, tr, ctx, sayac)
    ents.grep(Sketchup::Group).each do |g|
      next if g.name.to_s =~ /^(KITLE_|PERDE_|MERDIVEN|OTOPARK)/
      g.make_unique
      duzenle(m, g.entities, tr * g.transformation, ctx, sayac)
    end
    inv = tr.inverse
    vs = ents.grep(Sketchup::Edge).flat_map(&:vertices).uniq
    tv = []; vec = []
    vs.each do |v|
      # duvar/bordur gibi dusey yuzu olan noktalara dokunma, sadece zemin (yatay-egimli) yuzeyler
      next if v.faces.empty? || v.faces.any? { |f| f.normal.transform(tr).z.abs < 0.3 }
      p = v.position.transform(tr)
      dz = ctx.(p)
      next unless dz
      tv << v; vec << Geom::Vector3d.new(0, 0, dz).transform(inv)
    end
    unless tv.empty?
      ents.transform_by_vectors(tv, vec)
      sayac[0] += tv.length
    end
  end

  def self.kur(ev, tik)
    m = Sketchup.active_model
    pts = []
    alt_noktalar(ev.definition.entities, ev.transformation, pts)
    zb = pts.map(&:z).min
    hull = kabuk(pts.select { |q| q.z < zb + 0.03.m })
    # tiklanan noktaya en yakin cephe
    best = nil
    hull.each_with_index do |a, i|
      b = hull[(i + 1) % hull.length]
      ax = Geom::Point3d.new(a[0], a[1], 0); bx = Geom::Point3d.new(b[0], b[1], 0)
      t = Geom::Point3d.new(tik.x, tik.y, 0)
      u = bx - ax; len = u.length; u.normalize!
      s = [[(t - ax).dot(u), 0].max, len].min
      d = t.distance(ax.offset(u, s))
      best = [d, ax, u, len] if best.nil? || d < best[0]
    end
    _, ax, u, len = best
    dis = Geom::Vector3d.new(u.y, -u.x, 0) # saat yonu tersine kabukta disari
    tam = TAM.m; gec = GECIS.m
    maxd = 0.0
    ctx = lambda do |p|
      return nil unless p.z > zb + 1.mm
      w0 = Geom::Point3d.new(p.x, p.y, 0) - ax
      d = w0.dot(dis)
      return nil if d < -0.05.m || d > tam + gec
      s = w0.dot(u)
      return nil if s < -gec || s > len + gec
      wd = d <= tam ? 1.0 : 1.0 - (d - tam) / gec
      ws = s < 0 ? 1.0 + s / gec : (s > len ? 1.0 - (s - len) / gec : 1.0)
      w = wd * ws
      return nil if w <= 0
      dz = -(p.z - zb) * w
      maxd = [maxd, -dz.to_m].max
      dz
    end
    m.start_operation("Yolu subasmana indir", true)
    sayac = [0]
    m.entities.grep(Sketchup::Group).select { |g| g.name.to_s =~ /ARAZI|YOL/i && g.name.to_s !~ /^(KITLE_|PERDE_)/ }.each do |g|
      g.make_unique
      duzenle(m, g.entities, g.transformation, ctx, sayac)
    end
    m.commit_operation
    UI.messagebox(format("%s cephesi (%.1f m) onunde %d nokta indirildi, en fazla %.2f m.\nTaban kotu %.2f",
                         ev.name, len.to_m, sayac[0], maxd, zb.to_m))
  rescue => e
    m.abort_operation rescue nil
    UI.messagebox("Yol indir HATA: #{e.message}")
  end

  class Arac
    def activate
      @ip = Sketchup::InputPoint.new
      @ev = nil
      Sketchup.status_text = "1) Evin duvarina tikla"
    end

    def onMouseMove(_f, x, y, view)
      @ip.pick(view, x, y)
      view.invalidate
    end

    def draw(view)
      @ip.draw(view) if @ip.valid?
    end

    def onCancel(_r, _v)
      Sketchup.active_model.select_tool(nil)
    end

    def onLButtonDown(_f, x, y, view)
      if @ev.nil?
        ph = view.pick_helper
        ph.do_pick(x, y)
        yol = ph.path_at(0) || []
        @ev = yol.find { |e| e.is_a?(Sketchup::Group) && e.name.to_s =~ /^KITLE_/ }
        if @ev
          Sketchup.status_text = "#{@ev.name} secildi. 2) Indirilecek yola, bu cephenin onunde tikla"
        else
          UI.messagebox("Tiklanan yer bir ev kitlesi (KITLE_) degil. Evin duvarina tiklayin.")
        end
      else
        @ip.pick(view, x, y)
        return unless @ip.valid?
        Sketchup.active_model.select_tool(nil)
        CincinYol.kur(@ev, @ip.position)
      end
    end
  end
end

Sketchup.active_model.select_tool(CincinYol::Arac.new)
