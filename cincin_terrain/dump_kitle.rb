# 3dmodel3.skp acikken calistir: kitleleri ve kapi/giris nesnelerini kitle_dump.json'a yazar.
#   load "C:/cincin_terrain/dump_kitle.rb"
require 'json'
dir = File.dirname(__FILE__) + "/"
begin
  m = Sketchup.active_model
  m.close_active while m.active_path
  kw = /kap[iı]|door|giri[sş]|entr|portal/i
  out = { title: m.title, layers: m.layers.map(&:name), masses: [], doors: [], defs: Hash.new(0) }
  wbox = lambda do |e, tw|
    b = e.definition.bounds
    c = (0..7).map { |i| b.corner(i).transform(tw) }
    xs = c.map { |p| p.x.to_m }; ys = c.map { |p| p.y.to_m }; zs = c.map { |p| p.z.to_m }
    [xs.min, ys.min, zs.min, xs.max, ys.max, zs.max].map { |v| v.round(3) }
  end
  walk = lambda do |ents, tp, path, depth|
    ents.each do |e|
      next unless e.is_a?(Sketchup::Group) || e.is_a?(Sketchup::ComponentInstance)
      tw = tp * e.transformation
      dn = e.definition.name.to_s; iname = e.name.to_s
      out[:defs][dn] += 1
      rec = { path: path.join(" > "), def: dn, name: iname, layer: e.layer.name, bounds: wbox.(e, tw),
              axes_x: [tw.xaxis.x, tw.xaxis.y].map { |v| v.round(4) } }
      if depth == 0
        out[:masses] << rec if e.is_a?(Sketchup::Group) || dn !~ kw
      end
      out[:doors] << rec if dn =~ kw || iname =~ kw || e.layer.name =~ kw
      walk.(e.definition.entities, tw, path + [dn], depth + 1) if depth < 3
    end
  end
  walk.(m.entities, Geom::Transformation.new, [], 0)
  out[:defs] = out[:defs].sort_by { |_, v| -v }.first(60).to_h
  File.write(dir + "kitle_dump.json", JSON.pretty_generate(out))
  File.write(dir + "kitle_dump_result.txt", "OK masses=#{out[:masses].length} doors=#{out[:doors].length} defs=#{out[:defs].length}")
rescue => e
  File.write(dir + "kitle_dump_result.txt", "ERR #{e.class}: #{e.message}\n#{e.backtrace.first(3).join("\n")}")
end
