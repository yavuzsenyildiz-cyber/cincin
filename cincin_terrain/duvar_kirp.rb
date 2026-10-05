# Secili istinat duvarlarinin cimden yukari tasan kismini keser: duvarin ust noktalari,
# iki yanindaki zeminden (cim/platform) YUKSEK olanin kotuna indirilir -> duvar cimle ayni hizada biter.
# Kullanim: kirpilacak duvar(lar)i sec (grup veya bilesen), sonra:
#   load "C:/Users/YOGA/OneDrive/MİMARİ/CİNCİN/cincin_terrain/duvar_kirp.rb"
# Bilesenler once tekil yapilir (make_unique), diger kopyalar etkilenmez. Ctrl+Z ile geri alinir.
dir = File.dirname(__FILE__) + "/"
module CincinDuvar
  YAN = 0.40 # duvar yuzunden zemin okunan mesafe

  def self.zemin(m, pt, atla)
    p = Geom::Point3d.new(pt.x, pt.y, pt.z + 20.m)
    8.times do
      hit = m.raytest([p, Geom::Vector3d.new(0, 0, -1)], true)
      return nil unless hit
      return hit[0].z unless hit[1].any? { |e| atla.include?(e) || (e.respond_to?(:name) && e.name.to_s =~ /^(KITLE_|PERDE_|MERDIVEN)/) }
      p = hit[0].offset(Geom::Vector3d.new(0, 0, -1), 1.mm)
    end
    nil
  end
end

begin
  m = Sketchup.active_model
  sec = m.selection.grep(Sketchup::Group) + m.selection.grep(Sketchup::ComponentInstance)
  raise "Once kirpilacak duvar(lar)i secin" if sec.empty?
  m.start_operation("Duvar ustunu cime indir", true)
  rapor = []
  sec.each do |w|
    w.make_unique if w.is_a?(Sketchup::Group) || w.definition.count_instances > 1
    tr = w.transformation
    db = w.definition.bounds
    lx = (db.max.x - db.min.x) * tr.xaxis.length
    ly = (db.max.y - db.min.y) * tr.yaxis.length
    yan = (lx >= ly ? tr.yaxis : tr.xaxis); yan = Geom::Vector3d.new(yan.x, yan.y, 0); yan.normalize!
    ents = w.definition.entities
    verts = ents.grep(Sketchup::Edge).flat_map(&:vertices).uniq
    zs = verts.map { |v| v.position.transform(tr).z }
    zmid = (zs.min + zs.max) / 2.0
    ust = verts.select { |v| v.position.transform(tr).z > zmid }
    inv = tr.inverse
    tasi_v = []; tasi = []; maxk = 0.0
    ust.each do |v|
      pw = v.position.transform(tr)
      z1 = CincinDuvar.zemin(m, pw.offset(yan, YAN.m), [w])
      z2 = CincinDuvar.zemin(m, pw.offset(yan, -YAN.m), [w])
      gz = [z1, z2].compact.max
      next if gz.nil? || gz >= pw.z - 0.01.m || gz <= zmid
      hedef = Geom::Point3d.new(pw.x, pw.y, gz).transform(inv)
      tasi_v << v; tasi << (hedef - v.position)
      maxk = [maxk, (pw.z - gz).to_m].max
    end
    ents.transform_by_vectors(tasi_v, tasi) unless tasi_v.empty?
    rapor << format("%s: %d ust nokta indirildi, en fazla %.2f m", (w.name.empty? ? w.definition.name : w.name), tasi_v.length, maxk)
  end
  m.commit_operation
  txt = rapor.join("\n")
  File.write(dir + "duvar_kirp_result.txt", "OK\n" + txt)
  UI.messagebox(txt)
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "duvar_kirp_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
  UI.messagebox("HATA: #{e.message}")
end
