# 3dmodel3.skp'deki bina kitlelerini CINCIN_arazi_KOTLANDIRMA.skp'ye alir; kapi esigi platform+subasman kotuna gelecek sekilde sadece dusey kaydirir.
# Kapilara ve kitle yonune dokunmaz. Gerekli: C:/cincin_terrain/3dmodel3.skp (Turkce harfsiz yola kopyalanmis olmali).
#   load "C:/cincin_terrain/kitle_yerlestir.rb"
require 'json'
dir = File.dirname(__FILE__) + "/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  raise "Once CINCIN_arazi_KOTLANDIRMA.skp acik olmali (acik: #{m.title})" unless m.title.include?("KOTLANDIRMA")
  skp = dir + "3dmodel3.skp"
  raise "3dmodel3.skp bulunamadi: #{skp}" unless File.exist?(skp)
  plan = JSON.parse(File.read(dir + "kitle_plan.json"))
  m.start_operation("Kitleleri yerlestir", true)
  ents = m.entities
  ents.grep(Sketchup::Group).select { |g| g.name =~ /^KITLE_/ }.each(&:erase!)
  lay = m.layers.add("KITLE")
  defn = m.definitions.load(skp)
  inst = ents.add_instance(defn, Geom::Transformation.new)
  parts = inst.explode
  groups = parts.select { |e| e.valid? && e.is_a?(Sketchup::Group) }
  keep = []; placed = 0; missing = []
  plan.each do |p|
    b = p["bounds"]
    g = groups.find do |x|
      next false unless x.valid? && !keep.include?(x)
      bx = x.bounds
      v = [bx.min.x, bx.min.y, bx.min.z, bx.max.x, bx.max.y, bx.max.z].map(&:to_m)
      v.each_with_index.all? { |val, i| (val - b[i]).abs < 0.05 }
    end
    if g.nil? then missing << p["yapi"]; next end
    g.transform!(Geom::Transformation.translation(Geom::Vector3d.new(0, 0, p["dz"].m)))
    placed += 1
    g.name = "KITLE_#{p['yapi']}_#{placed}"; g.layer = lay
    keep << g
  end
  (parts.select(&:valid?) - keep).each { |e| e.erase! if e.valid? }
  m.definitions.purge_unused
  m.commit_operation
  vw = m.active_view
  vw.camera = Sketchup::Camera.new(Geom::Point3d.new(85.m, -40.m, 60.m), Geom::Point3d.new(85.m, 65.m, 0), Geom::Vector3d.new(0, 0, 1))
  vw.write_image(dir + "kitle_view.png", 1600, 1000, true, 0.0)
  File.write(dir + "kitle_result.txt", "OK yerlestirilen=#{placed}/#{plan.length} eksik=#{missing.inspect}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "kitle_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
