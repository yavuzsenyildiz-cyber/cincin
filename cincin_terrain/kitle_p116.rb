# P116 kitlelerini (YAPI4/5/6) 3dmodel3.skp'den alir ve kapi esigi p116_yol.py'nin buldugu esik kotuna (subasman+0.30) gelecek sekilde sadece dusey kaydirir.
# P115 kitlelerine dokunmaz. Sonunda p116_yol.rb'yi calistirir (arazi, yol, duvar, ev altlari).
#   load Dir.glob("C:/Users/YOGA/OneDrive/*/*/cincin_terrain/kitle_p116.rb").first
require 'json'
dir = File.dirname(__FILE__) + "/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  skp = [dir + "../GUNCEL_D5_SKETCHUP/SketchUp/3dmodel3.skp", dir + "3dmodel3.skp", "C:/cincin_terrain/3dmodel3.skp"].find { |f| File.exist?(f) }
  raise "3dmodel3.skp bulunamadi" unless skp
  plan = JSON.parse(File.read(dir + "kitle_plan.json")).select { |p| p["yapi"].start_with?("P116") }
  esik = {}
  File.foreach(dir + "p116y_taban.txt") { |ln| t = ln.split; esik[t[1]] = t[3].to_f if t[0] == "B" }
  m.start_operation("P116 kitleleri", true)
  ents = m.entities
  ents.grep(Sketchup::Group).select { |g| g.name =~ /^KITLE_P116/ }.each(&:erase!)
  lay = m.layers.add("KITLE")
  inst = ents.add_instance(m.definitions.load(skp), Geom::Transformation.new)
  parts = inst.explode
  groups = parts.select { |e| e.valid? && e.is_a?(Sketchup::Group) }
  keep = []; placed = 0; missing = []; log = []
  plan.each do |p|
    b = p["bounds"]
    bd = lambda { |x| bx = x.bounds; [bx.min.x, bx.min.y, bx.min.z, bx.max.x, bx.max.y, bx.max.z].map(&:to_m) }
    cand = groups.select { |x| x.valid? && !keep.include?(x) }.map { |x| [x, bd.(x).each_with_index.map { |v, i| (v - b[i]).abs }.max] }.min_by { |_, d| d }
    g = (cand && cand[1] < 1.0) ? cand[0] : nil
    log << "#{p['yapi']}: en yakin sapma=#{cand ? cand[1].round(3) : 'yok'} (grup sayisi #{groups.length})"
    if g.nil? || esik[p["yapi"]].nil? then missing << p["yapi"]; next end
    dz = esik[p["yapi"]] - p["kapi_alt_kotlar"].first
    g.transform!(Geom::Transformation.translation(Geom::Vector3d.new(0, 0, dz.m)))
    placed += 1
    g.name = "KITLE_#{p['yapi']}_#{placed}"; g.layer = lay
    keep << g
  end
  (parts.select(&:valid?) - keep).each { |e| e.erase! if e.valid? }
  m.definitions.purge_unused
  m.commit_operation
  File.write(dir + "kitle_p116_result.txt", "OK yerlestirilen=#{placed}/#{plan.length} eksik=#{missing.inspect}\n#{log.join("\n")}\nskp=#{skp}")
  UI.messagebox("P116 kitleleri: #{placed}/#{plan.length} yerlestirildi\n#{log.join("\n")}")
  load dir + "p116_yol.rb" if missing.empty?
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "kitle_p116_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
  UI.messagebox("HATA: #{e.message}")
end
