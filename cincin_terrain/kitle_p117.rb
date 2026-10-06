# P117 kitlelerini (YAPI7/8) 3dmodel3.skp'den alir ve kapi esigi p117_yol.py'nin buldugu esik kotuna (subasman+0.30) gelecek sekilde sadece dusey kaydirir.
# P115 kitlelerine dokunmaz. Sonunda p117_yol.rb'yi calistirir (arazi, yol, duvar, ev altlari).
#   load Dir.glob("C:/Users/YOGA/OneDrive/*/*/cincin_terrain/kitle_p117.rb").first
require 'json'
dir = File.dirname(__FILE__) + "/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  skp = [dir + "../GUNCEL_D5_SKETCHUP/SketchUp/3dmodel3.skp", dir + "3dmodel3.skp", "C:/cincin_terrain/3dmodel3.skp"].find { |f| File.exist?(f) }
  raise "3dmodel3.skp bulunamadi" unless skp
  plan = JSON.parse(File.read(dir + "kitle_plan.json")).select { |p| p["yapi"].start_with?("P117") }
  esik = {}
  File.foreach(dir + "p117y_taban.txt") { |ln| t = ln.split; esik[t[1]] = t[3].to_f if t[0] == "B" }
  m.start_operation("P117 kitleleri", true)
  ents = m.entities
  ents.grep(Sketchup::Group).select { |g| g.name =~ /^KITLE_P117/ }.each { |g_| g_.erase! if g_.valid? }
  lay = m.layers.add("KITLE")
  # 3dmodel3.skp patlatilmaz (explode modelin geometrisiyle birlesip silinmis nesne hatasi veriyordu): tanim icindeki gruplar okunur,
  # secilen evin tanimi modele yeni grup olarak eklenir. Modeldeki baska hicbir seye dokunulmaz.
  src = m.definitions.load(skp)
  groups = []
  topla = lambda do |es, tr, d|
    es.each do |x|
      next unless x.is_a?(Sketchup::Group) || x.is_a?(Sketchup::ComponentInstance)
      t = tr * x.transformation
      bb = Geom::BoundingBox.new
      db = x.definition.bounds
      (0..7).each { |i| bb.add(db.corner(i).transform(t)) }
      groups << [x, t, [bb.min.x, bb.min.y, bb.min.z, bb.max.x, bb.max.y, bb.max.z].map(&:to_m)]
      topla.(x.definition.entities, t, d + 1) if d < 1
    end
  end
  topla.(src.entities, Geom::Transformation.new, 0)
  keep = []; placed = 0; missing = []; log = []
  plan.each do |p|
    b = p["bounds"]
    cand = groups.reject { |x, _, _| keep.include?(x) }.map { |x, t, v| [x, t, v.each_with_index.map { |q, i| (q - b[i]).abs }.max] }.min_by { |_, _, d| d }
    log << "#{p['yapi']}: en yakin sapma=#{cand ? cand[2].round(3) : 'yok'} m (aday #{groups.length})"
    if cand.nil? || cand[2] > 1.0 || esik[p["yapi"]].nil? then missing << p["yapi"]; next end
    x, t, = cand
    dz = esik[p["yapi"]] - p["kapi_alt_kotlar"].first
    g = ents.add_group
    ii = g.entities.add_instance(x.definition, t); ii.material = x.material if x.material
    g.transform!(Geom::Transformation.translation(Geom::Vector3d.new(0, 0, dz.m)))
    placed += 1
    g.name = "KITLE_#{p['yapi']}_#{placed}"; g.layer = lay
    keep << x
  end
  m.definitions.purge_unused
  m.commit_operation
  File.write(dir + "kitle_p117_result.txt", "OK yerlestirilen=#{placed}/#{plan.length} eksik=#{missing.inspect}\n#{log.join("\n")}\nskp=#{skp}")
  UI.messagebox("[betik v4: #{File.expand_path(__FILE__)}]\nP117 kitleleri: #{placed}/#{plan.length} yerlestirildi\n#{log.join("\n")}")
  load dir + "p117_yol.rb" if missing.empty?
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "kitle_p117_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
  UI.messagebox("HATA: #{e.message}\n#{e.backtrace.first(4).join("\n")}\n[betik v4: #{File.expand_path(__FILE__)}]")
end
