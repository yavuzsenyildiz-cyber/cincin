# Ev kitlelerinin altini duzeltir:
#   1) Kirmizi "YAPI_SUBASMAN (+0.50)" ve "BINA_OTURUM" gruplarini siler (kitlelerin kendi 50 cm subasmani var).
#   2) Kitle tabaninin altinda arazi/yol asagi dustugu her yerde perde duvar kurar: dis yuzu kitle
#      kenariyla ayni hizada, 25 cm kalin, zemine 30 cm gomulu, evin kaplama malzemesiyle (tas) kapli.
# Secim bossa adi KITLE_ ile baslayan tum gruplara uygulanir; ev grubu/gruplari seciliyse sadece onlara.
#   load "C:/Users/YOGA/OneDrive/MİMARİ/CİNCİN/cincin_terrain/ev_duzelt.rb"
# Sonuc ev_duzelt_result.txt'ye yazilir. Ctrl+Z ile tek adimda geri alinir.
dir = File.dirname(__FILE__) + "/"
module CincinEv
  KALINLIK = 0.25 unless defined?(KALINLIK)
  GOMME = 0.30 unless defined?(GOMME)
  ADIM = 0.50 unless defined?(ADIM)
  ERISIM = 2.50 unless defined?(ERISIM) # kenardan disari bakilan mesafe (m)
  ERISIM_N = 10 unless defined?(ERISIM_N)
  ESIK = 0.30 unless defined?(ESIK) # bundan az dususte perde kurma (m)

  # BINA_OTURUM malzemeli ya da duz kirmizi (220,60,40 civari, dokusuz) yuzler
  def self.kirmizi?(mt)
    return false unless mt
    return true if mt.name =~ /OTURUM|SUBASMAN/i
    c = mt.color
    mt.texture.nil? && (c.red - 220).abs < 25 && (c.green - 60).abs < 30 && (c.blue - 40).abs < 30
  end

  # Tum modelde kirmizi yuzleri sil; bosalan grup/bilesenleri de sil. Silinen yuz sayisi ve yerleri doner.
  def self.kirmizi_sil(ents, yol, rapor, gezilen = {})
    yuz = ents.grep(Sketchup::Face).select { |f| kirmizi?(f.material) || kirmizi?(f.back_material) }
    unless yuz.empty?
      kenar = yuz.flat_map(&:edges).uniq
      ents.erase_entities(yuz)
      ents.erase_entities(kenar.select { |e| e.valid? && e.faces.empty? })
      rapor[yol.empty? ? "(model)" : yol] += yuz.length
    end
    (ents.grep(Sketchup::Group) + ents.grep(Sketchup::ComponentInstance)).each do |g|
      next unless g.valid?
      next if g.name.to_s =~ /^KITLE_/ # evin icindeki esyalara dokunma
      d = g.definition
      next if gezilen[d]
      gezilen[d] = true
      ad = g.name.to_s.empty? ? d.name : g.name
      kirmizi_sil(d.entities, yol.empty? ? ad : "#{yol} > #{ad}", rapor, gezilen)
      g.erase! if g.valid? && d.entities.grep(Sketchup::Face).empty? && d.entities.grep(Sketchup::Group).empty? && d.entities.grep(Sketchup::ComponentInstance).empty?
    end
  end

  def self.alt_noktalar(ents, tr, out)
    ents.each do |e|
      case e
      when Sketchup::Face
        e.vertices.each { |v| out << v.position.transform(tr) }
      when Sketchup::Group, Sketchup::ComponentInstance
        alt_noktalar(e.definition.entities, tr * e.transformation, out)
      end
    end
  end

  def self.kabuk(pts)
    p = pts.map { |q| [q.x.to_f, q.y.to_f] }.uniq.sort
    return p if p.length < 3
    cr = ->(o, a, b) { (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]) }
    lo = []; p.each { |q| lo.pop while lo.length >= 2 && cr.(lo[-2], lo[-1], q) <= 0; lo << q }
    up = []; p.reverse.each { |q| up.pop while up.length >= 2 && cr.(up[-2], up[-1], q) <= 0; up << q }
    lo[0...-1] + up[0...-1] # saat yonu tersine
  end

  def self.malzeme(ents, alan = Hash.new(0))
    ents.each do |e|
      if e.is_a?(Sketchup::Face)
        mt = e.material
        alan[mt] += e.area if mt && mt.texture && mt.alpha > 0.99
      elsif e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
        malzeme(e.definition.entities, alan)
      end
    end
    alan
  end

  # (x,y) noktasinda z0'dan asagi ilk zemin: kitleler ve perdeler atlanir
  def self.zemin(m, x, y, z0, atla)
    p = Geom::Point3d.new(x, y, z0)
    6.times do
      hit = m.raytest([p, Geom::Vector3d.new(0, 0, -1)], true)
      return nil unless hit
      return [hit[0].z, hit[1].map { |e| e.respond_to?(:name) && !e.name.to_s.empty? ? e.name : e.class.name.split('::').last }.join(' > ')] unless hit[1].any? { |e| atla.include?(e) || (e.respond_to?(:name) && e.name.to_s =~ /^(KITLE_|PERDE_|MERDIVEN)/) }
      p = hit[0].offset(Geom::Vector3d.new(0, 0, -1), 1.mm)
    end
    nil
  end
end

begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  m.start_operation("Ev alti duzelt (subasman sil + perde)", true)
  ents = m.entities

  kirmizi = ents.grep(Sketchup::Group).select { |g| g.name =~ /^(YAPI_SUBASMAN|BINA_OTURUM)/ }
  silinen = Hash.new(0)
  kirmizi.each { |g| silinen[g.name] += 1; g.erase! }
  CincinEv.kirmizi_sil(ents, "", silinen)

  sec = m.selection.grep(Sketchup::Group) + m.selection.grep(Sketchup::ComponentInstance)
  evler = sec.empty? ? ents.grep(Sketchup::Group).select { |g| g.name =~ /^KITLE_/ } : sec
  raise "Ev grubu bulunamadi (KITLE_ ile baslayan grup yok, bir sey de secili degil)" if evler.empty?

  ents.grep(Sketchup::Group).select { |g| g.name =~ /^PERDE_/ && evler.any? { |e| g.name == "PERDE_#{e.name}" } }.each(&:erase!)
  lay = m.layers.add("PERDE_DUVAR")
  rapor = []
  evler.each do |ev|
    pts = []
    CincinEv.alt_noktalar(ev.definition.entities, ev.transformation, pts)
    next if pts.empty?
    zb = pts.map(&:z).min
    alt = pts.select { |q| q.z < zb + 0.03.m }
    hull = CincinEv.kabuk(alt)
    next if hull.length < 3
    tas = CincinEv.malzeme(ev.definition.entities).max_by { |_, a| a }&.first
    tas ||= m.materials["ETEK_DUVAR"] || m.materials.add("ETEK_DUVAR").tap { |x| x.color = Sketchup::Color.new(200, 175, 130) }
    gp = ents.add_group; gp.name = "PERDE_#{ev.name}"; gp.layer = lay
    kenar = 0; hmax = 0.0; tani = []
    hull.each_with_index do |a, i|
      b = hull[(i + 1) % hull.length]
      dx = b[0] - a[0]; dy = b[1] - a[1]; len = Math.hypot(dx, dy)
      next if len < 0.10.m
      dis = Geom::Vector3d.new(dy / len, -dx / len, 0) # saat yonu tersine kabukta disari
      n = [(len.to_m / CincinEv::ADIM).ceil, 1].max
      # Duvarin dibi: kenardan disari ERISIM mesafesi icindeki en alcak zemin (sev/sevli dolgu yerine yola kadar iner)
      ilk = nil
      alts = (0..n).map do |k|
        x = a[0] + dx * k / n; y = a[1] + dy * k / n
        zs = (0..CincinEv::ERISIM_N).map do |j|
          d = 0.05 + j * CincinEv::ERISIM / CincinEv::ERISIM_N
          r = CincinEv.zemin(m, x + dis.x * d.m, y + dis.y * d.m, zb + 0.20.m, [ev])
          ilk ||= r if j.zero? && k == n / 2
          r && r[0]
        end.compact
        gz = zs.min
        gz = zb if gz.nil? || gz > zb
        [x, y, gz]
      end
      h = alts.map { |q| (zb - q[2]).to_m }.max
      tani << format("  kenar %d (%.1f m): taban %.2f, dibe kadar %.2f m, ilk zemin %s", i + 1, len.to_m, zb.to_m, h,
                     ilk ? format("%.2f [%s]", ilk[0].to_m, ilk[1]) : "yok")
      next if h < CincinEv::ESIK
      hmax = [hmax, h].max
      ust = [Geom::Point3d.new(a[0], a[1], zb), Geom::Point3d.new(b[0], b[1], zb)]
      dip = alts.reverse.map { |x, y, gz| Geom::Point3d.new(x, y, [gz - CincinEv::GOMME.m, zb - 0.05.m].min) }
      sg = gp.entities.add_group
      f = sg.entities.add_face(ust + dip)
      next unless f
      f.pushpull(f.normal.dot(dis) > 0 ? -CincinEv::KALINLIK.m : CincinEv::KALINLIK.m)
      sg.entities.grep(Sketchup::Face).each { |q| q.material = tas; q.back_material = tas }
      kenar += 1
    end
    gp.erase! if kenar.zero?
    rapor << format("%s: %d kenarda perde, en yuksek %.2f m, malzeme %s", ev.name, kenar, hmax, tas.name)
    rapor.concat(tani)
  end
  m.commit_operation
  kirmizimsi = m.materials.select { |x| c = x.color; c.red > 150 && c.red > c.green * 1.8 && c.red > c.blue * 1.8 }
                          .map { |x| "#{x.name}(#{x.color.red},#{x.color.green},#{x.color.blue}#{x.texture ? ',doku' : ''})" }
  kr = silinen.empty? ? "kirmizi bulunamadi; kirmizimsi malzemeler: #{kirmizimsi.join(', ')}" : silinen.map { |k, v| "  #{k}: #{v}" }.join("\n")
  txt = "Kirmizi silinen:\n#{kr}\nEv (#{sec.empty? ? 'tum KITLE_' : 'secili'}): #{evler.length}\n" +
        (rapor.empty? ? "perde gerekmedi" : rapor.join("\n"))
  File.write(dir + "ev_duzelt_result.txt", txt)
  UI.messagebox(txt)
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "ev_duzelt_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
  UI.messagebox("HATA: #{e.message}")
end
