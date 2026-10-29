import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
face = {3: '+y', 1: '-x', 4: '+z', 7: '+x', 10: '-z', 5: '-y'}
fill = {'x': ('#fbe3e1', '#d0605a'), 'y': ('#dff0dc', '#5aa55a'), 'z': ('#e3eefb', '#4a86d0')}
L = []
L.append('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 386" width="700" height="386">
  <style>
    text { font-family: Helvetica, Arial, sans-serif; font-size: 15px; fill: #888; }
    .in { fill: #333; font-size: 14px; }
    .b { font-weight: bold; }
    .m { font-family: Menlo, Consolas, monospace; font-size: 13px; fill: #333; }
    .idx { font-family: Menlo, Consolas, monospace; font-size: 12px; fill: #777; }
    .f { font-size: 22px; font-weight: bold; }
    .ar { stroke: #e07b1a; stroke-width: 2; fill: none; marker-end: url(#ar); }
  </style>
  <defs>
    <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#e07b1a"/></marker>
  </defs>
  <text x="20" y="24" class="b in">image_split_grid(image, 4, 3)</text>
  <text x="20" y="44" class="m">faces[row + 3*column]</text>''')
x0, y0, c = 20, 74, 84
for col in range(4):
    L.append(f'  <text x="{x0+col*c+c/2}" y="{y0-6}" class="idx" text-anchor="middle">column {col}</text>')
for row in range(3):
    L.append(f'  <text x="{x0+4*c+8}" y="{y0+row*c+c/2+4}" class="idx">row {row}</text>')
for col in range(4):
    for row in range(3):
        k = row + 3 * col
        x, y = x0 + col * c, y0 + row * c
        if k in face:
            f = face[k]
            fl, st = fill[f[1]]
            L.append(f'  <rect x="{x}" y="{y}" width="{c}" height="{c}" style="fill:{fl};stroke:{st};stroke-width:1.5"/>')
            L.append(f'  <text x="{x+c/2}" y="{y+c/2+12}" class="f" text-anchor="middle" style="fill:{st}">{f}</text>')
            L.append(f'  <text x="{x+6}" y="{y+16}" class="idx" style="fill:#333">{k}</text>')
        else:
            L.append(f'  <rect x="{x}" y="{y}" width="{c}" height="{c}" style="fill:#f4f4f4;stroke:#ccc;stroke-width:1;stroke-dasharray:4 3"/>')
            L.append(f'  <text x="{x+6}" y="{y+16}" class="idx" style="fill:#aaa">{k}</text>')
L.append(f'  <text x="{x0}" y="{y0+3*c+24}" class="idx">unused squares (dashed) are ignored</text>')

# right: call
rx = 452
L.append(f'  <path d="M{x0+4*c+50},{y0+1.5*c} H{rx-8}" class="ar"/>')
L.append(f'  <text x="{rx}" y="{y0+8}" class="m">skybox.texture.</text>')
L.append(f'  <text x="{rx}" y="{y0+26}" class="m">initialize_cubemap_on_gpu(</text>')
order = [(1, '-x'), (7, '+x'), (5, '-y'), (3, '+y'), (10, '-z'), (4, '+z')]
for i, (k, f) in enumerate(order):
    y = y0 + 40 + i * 30
    fl, st = fill[f[1]]
    L.append(f'  <rect x="{rx+16}" y="{y}" width="96" height="24" rx="3" style="fill:{fl};stroke:{st};stroke-width:1.2"/>')
    L.append(f'  <text x="{rx+64}" y="{y+17}" class="m" text-anchor="middle">faces[{k}]</text>')
    L.append(f'  <text x="{rx+124}" y="{y+17}" class="in b" style="fill:{st}">{f}</text>')
L.append(f'  <text x="{rx}" y="{y0+40+6*30+12}" class="m">);</text>')
L.append(f'  <text x="350" y="374" text-anchor="middle">The cube map is y-up (OpenGL); skybox_rotation tilts it for the z-up scene.</text>')
L.append('</svg>')
write_svg(out, L)
