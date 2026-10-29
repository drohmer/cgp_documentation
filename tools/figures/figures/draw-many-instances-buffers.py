import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
INS, LP = PAL['vbo'], PAL['vbo']['line']
L = ['''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 372" width="700" height="372">
  <style>
    text { font-family: Helvetica, Arial, sans-serif; font-size: 15px; fill: #888; }
    .in { fill: #333; font-size: 14px; }
    .lab { font-size: 13px; }
    .b { font-weight: bold; }
    .m { font-family: Menlo, Consolas, monospace; font-size: 12px; fill: #333; }
    .buf { fill: #fff7ec; stroke: #e0912f; stroke-width: 1.2; }
    .ins { fill: ''' + INS['fill'] + '''; stroke: ''' + INS['stroke'] + '''; stroke-width: 1.2; }
    .sh { fill: #dff0dc; stroke: #5aa55a; stroke-width: 1.2; }
    .lk { stroke: #e0912f; stroke-width: 1.2; stroke-dasharray: 3 3; fill: none; }
    .lp { stroke: ''' + LP + '''; stroke-width: 2; fill: none; marker-end: url(#ap); }
  </style>
  <defs>
    <marker id="ap" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="''' + LP + '''"/></marker>
  </defs>''']
x0, w = 130, 48
L.append('  <text x="20" y="24" class="in b">per-vertex buffer: location 0, divisor 0 (one value per vertex)</text>')
L.append('  <text x="20" y="60" class="m">vbo_position</text>')
for j in range(8):
    x = x0 + j * w
    L.append(f'  <rect x="{x}" y="40" width="{w}" height="30" class="buf"/>')
    L.append(f'  <text x="{x+w/2}" y="60" class="m" text-anchor="middle">v{j}</text>')
ry = [150, 220]
L.append(f'  <text x="{x0+4*w}" y="{ry[0]-14}" class="lab" text-anchor="middle">vertex shader runs: vertex_position + instance_position</text>')
for j in range(8):
    x = x0 + j * w + w / 2
    L.append(f'  <path d="M{x},70 V{ry[0]-26}" class="lk"/>')
for i, y in enumerate(ry):
    L.append(f'  <text x="20" y="{y+16}" class="in b">instance {i}</text>')
    L.append(f'  <text x="20" y="{y+34}" class="lab">gl_InstanceID={i}</text>')
    for j in range(8):
        x = x0 + j * w
        L.append(f'  <rect x="{x+3}" y="{y}" width="{w-6}" height="40" rx="3" class="sh"/>')
        L.append(f'  <text x="{x+w/2}" y="{y+16}" class="m" text-anchor="middle">v{j}</text>')
        L.append(f'  <text x="{x+w/2}" y="{y+33}" class="m" text-anchor="middle" style="fill:{PAL["vbo"]["text"]}">p{i}</text>')
L.append(f'  <text x="20" y="300" class="lab">... and so on, up to instance N_instances - 1</text>')
# per-instance column
cx, cw = 576, 80
L.append(f'  <text x="690" y="96" class="in b" text-anchor="end">per-instance buffer:</text>')
L.append(f'  <text x="690" y="114" class="lab" text-anchor="end">location 4, divisor 1</text>')
L.append(f'  <text x="690" y="130" class="m" text-anchor="end">instance_positions</text>')
cells = [(ry[0], 'p0'), (ry[1], 'p1')]
for y, c in cells:
    L.append(f'  <rect x="{cx}" y="{y}" width="{cw}" height="40" class="ins"/>')
    L.append(f'  <text x="{cx+cw/2}" y="{y+25}" class="m" text-anchor="middle">{c}</text>')
    L.append(f'  <path d="M{cx},{y+20} H{x0+8*w+4}" class="lp"/>')
L.append(f'  <rect x="{cx}" y="260" width="{cw}" height="22" class="ins" style="stroke-dasharray:3 3"/>')
L.append(f'  <text x="{cx+cw/2}" y="276" class="m" text-anchor="middle">...</text>')
L.append(f'  <rect x="{cx}" y="282" width="{cw}" height="40" class="ins"/>')
L.append(f'  <text x="{cx+cw/2}" y="307" class="m" text-anchor="middle">p5999</text>')
L.append(f'  <text x="350" y="360" text-anchor="middle">draw(grass, environment, N_instances): one call, 8 x N_instances vertex shader runs.</text>')
L.append('</svg>')
write_svg(out, L)
