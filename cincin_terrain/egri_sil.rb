# Eş yukselti egrilerini (kontur cizgilerini) modelden siler.
#   load "C:/cincin_terrain/egri_sil.rb"
# Silinenler:
#   a) Adi kontur/contour/egri/esyukselti/isohips/topo iceren katmanlardaki tum kenarlar
#   b) Hicbir yuzeye bagli olmayan (serbest) ve YATAY (iki ucu ayni kotta) kenarlar
# Yuzeye bagli kenarlara, mavi parsel/sinir cizgilerine (yatay olmayanlar), KITLE_/MERDIVEN gruplarina dokunmaz.
# Sonuc egri_sil_result.txt'ye yazilir; Ctrl+Z ile geri alinir.
dir = File.dirname(__FILE__) + "/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  kat = /kontur|contour|e[gğ]ri|e[sş].?y[uü]kselti|isohips|topo/i
  atla = /^(KITLE_|MERDIVEN)/
  sil = {}
  gezilen = {}
  tara = lambda do |ents|
    ents.each do |e|
      if e.is_a?(Sketchup::Edge)
        katman = e.layer.name =~ kat
        serbest_yatay = e.faces.empty? && (e.start.position.z - e.end.position.z).abs < 1.mm
        (sil[ents] ||= []) << e if katman || serbest_yatay
      elsif e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
        next if e.name =~ atla || e.definition.name =~ atla
        d = e.definition
        next if gezilen[d]
        gezilen[d] = true
        tara.(d.entities)
      end
    end
  end
  tara.(m.entities)
  m.start_operation("Es yukselti egrilerini sil", true)
  n = 0
  sil.each do |ents, list|
    list = list.select(&:valid?)
    n += list.length
    ents.erase_entities(list) unless list.empty?
  end
  # Bos kalan kontur katmanlarini da kaldir
  bos = m.layers.select { |l| l.name =~ kat }
  adlar = bos.map(&:name)
  bos.each { |l| m.layers.remove(l) rescue nil }
  m.commit_operation
  File.write(dir + "egri_sil_result.txt", "OK silinen kenar=#{n} kaldirilan katman=#{adlar.inspect}")
  UI.messagebox("Silinen egri kenari: #{n}")
rescue => e
  begin; Sketchup.active_model.abort_operation; rescue; end
  File.write(dir + "egri_sil_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
