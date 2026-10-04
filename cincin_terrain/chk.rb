m = Sketchup.active_model
g = m.entities.grep(Sketchup::Group).find { |q| q.name.start_with?("ARAZI_TESVIYE") }
f = g.entities.grep(Sketchup::Face).first
mat = f.material
uvh = f.get_UVHelper(true, false, m.materials["ARAZI_PLANKOTE_UYDU"].texture.nil? ? nil : Sketchup.create_texture_writer)
v = f.vertices.first.position
s = "mat=#{mat && mat.name} tex=#{mat && mat.texture && mat.texture.filename} size=#{mat && mat.texture && [mat.texture.width, mat.texture.height].inspect} uv=#{uvh.get_front_UVQ(v).to_a.inspect} rstyle=#{m.rendering_options['Texture']} disp=#{m.rendering_options['RenderMode']}"
File.write("C:/Users/YOGA/AppData/Local/Temp/cincin_terrain/chk.txt", s)
