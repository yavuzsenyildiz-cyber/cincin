# P115 (en ust parsel) kitle tabanlarini +-0.00 kotuna oturtur: kot = bina kose noktalarindaki tabii zemin ortalamasi (Plansiz Alanlar Imar Yon. md.21/5).
# Kaydetmez; Ctrl+Z geri alir.  load "C:/Users/YOGA/OneDrive/MİMARİ/CİNCİN/cincin_terrain/p115_taban.rb"
dir = File.dirname(__FILE__) + "/"
DATA = [
  ["P115-YAPI1", 6.037, [[24.468,85.132],[50.825,86.699],[51.281,79.023],[46.089,78.714],[45.929,81.399],[29.957,80.449],[30.117,77.764],[24.925,77.455]], "113.80 / 109.74 / 109.35 / 109.93 / 110.04 / 112.26 / 111.56 / 112.18"],
  ["P115-YAPI2", 3.098, [[69.971,87.834],[96.327,89.402],[96.784,81.725],[91.591,81.416],[91.431,84.102],[75.460,83.138],[75.619,80.466],[70.427,80.158]], "108.02 / 110.36 / 108.77 / 108.90 / 109.60 / 107.04 / 106.28 / 106.37"],
  ["P115-YAPI3", -1.150, [[127.037,91.231],[153.394,92.799],[153.850,85.122],[148.658,84.814],[148.498,87.499],[132.526,86.549],[132.686,83.864],[127.494,83.555]], "107.19 / 102.91 / 100.84 / 101.07 / 101.57 / 105.91 / 105.64 / 106.22"]
]
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  m.start_operation("P115 kitle tabanlari", true)
  m.entities.grep(Sketchup::Group).select { |g| g.name.start_with?("P115_KITLE_TABAN") }.each(&:erase!)
  lay = m.layers.add("KITLE_TABAN")
  mat = m.materials["KITLE_TABAN"] || m.materials.add("KITLE_TABAN"); mat.color = Sketchup::Color.new(220, 60, 40)
  g = m.entities.add_group; g.name = "P115_KITLE_TABAN (+-0.00)"; g.layer = lay
  n = 0
  DATA.each do |name, z, fp, kose|
    sg = g.entities.add_group; sg.name = "#{name} +-0.00 = +#{'%.2f' % (z + 105.07)}"
    f = sg.entities.add_face(fp.map { |x, y| Geom::Point3d.new(x.m, y.m, z.m) }); f.reverse! if f.normal.z < 0
    f.material = mat; f.back_material = mat
    cx = fp.map(&:first).sum / fp.length; cy = fp.map(&:last).sum / fp.length
    g.entities.add_text("#{name}
+-0.00 = +#{'%.2f' % (z + 105.07)}
kose tabii zemin: #{kose}", Geom::Point3d.new(cx.m, cy.m, (z + 0.1).m), Geom::Vector3d.new(0, 0, 4.m))
    n += 1
  end
  m.commit_operation
  File.write(dir + "p115_taban_result.txt", "OK taban=#{n}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "p115_taban_result.txt", "ERR #{e.class}: #{e.message}")
end
