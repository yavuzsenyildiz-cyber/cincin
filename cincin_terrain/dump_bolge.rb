# Acik modelin ev cevresini disari yazar (bolge_dump.txt). Duzeltme scriptlerini kesin olculerle yazmak icin.
#   load Dir.glob("C:/Users/YOGA/OneDrive/*/*/cincin_terrain/dump_bolge.rb").first
# Sonra bolge_dump.txt'yi git ile gonderin (git add, commit, push).
dir = File.dirname(__FILE__) + "/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  out = ["MODEL #{m.title}"]
  f3 = ->(p) { format("%.2f,%.2f,%.2f", p.x.to_m, p.y.to_m, p.z.to_m) }
  bb = ->(b) { "#{f3.(b.min)} #{f3.(b.max)}" }
  matn = lambda do |ents|
    h = Hash.new(0)
    ents.grep(Sketchup::Face).each { |f| h[(f.material || f.back_material)&.name || "-"] += f.area }
    h.sort_by { |_, a| -a }.first(3).map { |k, a| "#{k}:#{(a / 1550.0031).round}m2" }.join("|")
  end
  walk = lambda do |ents, tr, d|
    ents.each do |e|
      next unless e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
      t = tr * e.transformation
      b = Geom::BoundingBox.new
      e.definition.bounds.then { |db| (0..7).each { |i| b.add(db.corner(i).transform(t)) } }
      de = e.definition.entities
      out << "#{'  ' * d}#{e.is_a?(Sketchup::Group) ? 'G' : 'C'} \"#{e.name}\" def=\"#{e.definition.name}\" lay=\"#{e.layer.name}\" " \
             "box=#{bb.(b)} faces=#{de.grep(Sketchup::Face).length} mat=#{matn.(de)}"
      walk.(de, t, d + 1) if d < 2 && e.name.to_s !~ /^KITLE_/
    end
  end
  out << "== AGAC (3 seviye; KITLE_ icine girilmez)"
  walk.(m.entities, Geom::Transformation.new, 0)

  out << "== EVLER: taban kotu, taban izi, cevre zemin izgarasi (0.5 m, 8 m)"
  m.entities.grep(Sketchup::Group).select { |g| g.name =~ /^KITLE_/ }.each do |ev|
    pts = []
    col = lambda do |ents, tr|
      ents.each do |e|
        if e.is_a?(Sketchup::Face) then e.vertices.each { |v| pts << v.position.transform(tr) }
        elsif e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance) then col.(e.definition.entities, tr * e.transformation)
        end
      end
    end
    col.(ev.definition.entities, ev.transformation)
    next if pts.empty?
    zb = pts.map(&:z).min
    alt = pts.select { |q| q.z < zb + 0.03.m }.map { |q| [q.x.to_m.round(2), q.y.to_m.round(2)] }.uniq
    b = ev.bounds
    out << "EV #{ev.name} zb=#{zb.to_m.round(3)} box=#{bb.(b)}"
    out << "  TABAN " + alt.map { |x, y| "#{x},#{y}" }.join(";")
    # kapilar
    kap = []
    kw = /kap[iı]|door/i
    scan = lambda do |ents, tr|
      ents.each do |e|
        next unless e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
        t = tr * e.transformation
        if e.definition.name =~ kw || e.name.to_s =~ kw
          bx = Geom::BoundingBox.new; (0..7).each { |i| bx.add(e.definition.bounds.corner(i).transform(t)) }
          kap << bx
        else
          scan.(e.definition.entities, t)
        end
      end
    end
    scan.(ev.definition.entities, ev.transformation)
    kap.each { |k| out << "  KAPI #{bb.(k)}" }
    x0 = b.min.x - 8.m; x1 = b.max.x + 8.m; y0 = b.min.y - 8.m; y1 = b.max.y + 8.m
    out << "  IZGARA x0=#{x0.to_m.round(2)} y0=#{y0.to_m.round(2)} adim=0.5 (satir=y, sutun=x; z, '_'=yok, hit katmani kisaltma)"
    y = y0
    while y <= y1
      row = []
      x = x0
      while x <= x1
        hit = m.raytest([Geom::Point3d.new(x, y, b.max.z + 30.m), Geom::Vector3d.new(0, 0, -1)], true)
        if hit
          top = hit[1].find { |q| q.respond_to?(:name) && !q.name.to_s.empty? }
          tag = top ? top.name.to_s[0, 6].gsub(/\s/, "") : "?"
          row << "#{hit[0].z.to_m.round(2)}:#{tag}"
        else
          row << "_"
        end
        x += 0.5.m
      end
      out << "  R #{y.to_m.round(2)} " + row.join(" ")
      y += 0.5.m
    end
  end
  File.write(dir + "bolge_dump.txt", out.join("\n"))
  UI.messagebox("bolge_dump.txt yazildi (#{out.length} satir). Simdi git add/commit/push yapin.")
rescue => e
  File.write(dir + "bolge_dump.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
  UI.messagebox("HATA: #{e.message}")
end
