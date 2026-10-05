# Tikla-sil araci: silinecek nesneye tikla, nesnenin model icindeki yolu gosterilir ve sorulur:
#   Evet  = tiklanan yuzu iceren EN ICTEKI grubu/bileseni sil
#   Hayir = sadece tiklanan yuzu sil
#   Iptal = hicbir sey yapma
# Ev kitlesi (KITLE_), arazi (ARAZI), bahce/platform ust gruplari butunuyle SILINMEZ (koruma).
# Esc ile cik. Her silme ayri Ctrl+Z ile geri alinir. Tiklananlar sec_sil_log.txt'ye yazilir.
#   load Dir.glob("C:/Users/YOGA/OneDrive/*/*/cincin_terrain/sec_sil.rb").first
module CincinSil
  KORU = /^(KITLE_|P\d+_ARAZI|ARAZI|BAHCELER|PLATFORM_BAHCE)/ unless defined?(KORU)

  def self.ad(e)
    n = e.respond_to?(:name) ? e.name.to_s : ""
    n = e.definition.name if n.empty? && e.respond_to?(:definition)
    "#{n} [#{e.class.name.split('::').last}]"
  end

  def self.log(txt)
    File.open(File.dirname(__FILE__) + "/sec_sil_log.txt", "a") { |f| f.puts(txt) }
  rescue
    nil
  end

  class Arac
    def activate
      Sketchup.status_text = "Silinecek nesneye tikla (Esc = cik)"
    end

    def onCancel(_r, _v)
      Sketchup.active_model.select_tool(nil)
    end

    def onLButtonDown(_f, x, y, view)
      ph = view.pick_helper
      ph.do_pick(x, y)
      yol = ph.path_at(0)
      return if yol.nil? || yol.empty?
      kaplar = yol.select { |e| e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance) }
      yuz = yol.find { |e| e.is_a?(Sketchup::Face) }
      ic = kaplar.last
      mt = yuz && (yuz.material || yuz.back_material)
      metin = "Yol:\n  " + yol.map { |e| CincinSil.ad(e) }.join("\n  > ") +
              "\nMalzeme: #{mt ? mt.name : '-'}" + "\nKatman: #{(ic || yol.last).layer.name}"
      CincinSil.log(metin.tr("\n", " ") + "\n---")
      korunan = ic.nil? || ic.name.to_s =~ KORU || ic.definition.name.to_s =~ KORU
      soru = metin + "\n\n" +
             (korunan ? "Evet = (korunan grup, silinmez)" : "Evet = en icteki grubu sil: #{CincinSil.ad(ic)}") +
             "\nHayir = sadece tiklanan bu yuzu sil\nIptal = vazgec"
      r = UI.messagebox(soru, MB_YESNOCANCEL)
      m = Sketchup.active_model
      if r == IDYES && !korunan
        m.start_operation("Nesne sil", true)
        ic.erase!
        m.commit_operation
      elsif r == IDNO && yuz
        m.start_operation("Yuz sil", true)
        ents = yuz.parent.entities
        kenar = yuz.edges
        ents.erase_entities([yuz])
        ents.erase_entities(kenar.select { |e| e.valid? && e.faces.empty? })
        m.commit_operation
      end
      view.invalidate
    end
  end
end

Sketchup.active_model.select_tool(CincinSil::Arac.new)
