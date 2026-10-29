"""marching-cube-edge.svg: a vertex of the marching cubes lies on an edge of the grid, at the
linear interpolation of the field; its normal interpolates the gradients of the two ends.
2D view (marching squares) of the example marching-cubes-interactive.
Usage: python marching-cube-edge.py OUT.svg"""
import math
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
cpu, gpu = PAL['cpu'], PAL['gpu']

# left: samples of a blob field on a grid, the isoline vertices on the edges
NX, NY, H, X0, Y0 = 7, 6, 40, 40, 56
cx, cy, s, iso = X0 + 2.9 * H, Y0 + 2.4 * H, 1.9 * H, 0.5


def f(x, y):
    return math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / s ** 2)


L = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 330" width="700" height="330">
  <style>
    text {{ font-family: Helvetica, Arial, sans-serif; font-size: 15px; fill: #666666; }}
    .in {{ fill: #333; font-size: 14px; }}
    .b {{ font-weight: bold; }}
    .m {{ font-family: Menlo, Consolas, monospace; font-size: 13px; fill: #333; }}
    .ar {{ stroke-width: 2; fill: none; }}
  </style>
  <defs>
    <marker id="ag" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#888888"/></marker>
    <marker id="ao" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{gpu['line']}"/></marker>
  </defs>
  <text x="20" y="24" class="b in">Samples of the field on the grid, vertices on the edges</text>''']
for j in range(NY):
    L.append(f'  <line x1="{X0}" y1="{Y0 + j * H}" x2="{X0 + (NX - 1) * H}" y2="{Y0 + j * H}" stroke="#cccccc"/>')
for i in range(NX):
    L.append(f'  <line x1="{X0 + i * H}" y1="{Y0}" x2="{X0 + i * H}" y2="{Y0 + (NY - 1) * H}" stroke="#cccccc"/>')
pts = []
for j in range(NY):
    for i in range(NX):
        x, y = X0 + i * H, Y0 + j * H
        for di, dj in ((1, 0), (0, 1)):
            if i + di < NX and j + dj < NY:
                x1, y1 = X0 + (i + di) * H, Y0 + (j + dj) * H
                f0, f1 = f(x, y), f(x1, y1)
                if (f0 - iso) * (f1 - iso) < 0:
                    a = (iso - f0) / (f1 - f0)
                    pts.append((x + a * (x1 - x), y + a * (y1 - y)))
pts.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
L.append('  <polygon points="' + ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
         + f'" fill="{cpu["fill"]}" fill-opacity="0.6" stroke="{cpu["line"]}" stroke-width="2"/>')
for j in range(NY):
    for i in range(NX):
        x, y = X0 + i * H, Y0 + j * H
        inside = f(x, y) > iso
        L.append(f'  <circle cx="{x}" cy="{y}" r="4.5" fill="{gpu["line"] if inside else "#ffffff"}" stroke="{gpu["line"]}" stroke-width="1.5"/>')
for x, y in pts:
    L.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{cpu["line"]}"/>')
yl = Y0 + (NY - 1) * H + 30
L.append(f'  <circle cx="{X0}" cy="{yl}" r="4.5" fill="{gpu["line"]}"/><text x="{X0 + 10}" y="{yl + 5}" class="in">f &gt; isovalue</text>')
L.append(f'  <circle cx="{X0 + 120}" cy="{yl}" r="4.5" fill="#fff" stroke="{gpu["line"]}" stroke-width="1.5"/><text x="{X0 + 130}" y="{yl + 5}" class="in">f &lt; isovalue</text>')
L.append(f'  <circle cx="{X0 + 240}" cy="{yl}" r="3.5" fill="{cpu["line"]}"/><text x="{X0 + 250}" y="{yl + 5}" class="in">vertex</text>')

# right: one edge, zoomed
ex0, ex1, ey = 440, 620, 170
f0, f1 = 0.8, 0.3
a = (iso - f0) / (f1 - f0)
px = ex0 + a * (ex1 - ex0)
L.append(f'  <text x="400" y="24" class="b in">One edge, zoomed</text>')
L.append(f'  <line x1="{ex0}" y1="{ey}" x2="{ex1}" y2="{ey}" stroke="#888888" stroke-width="2"/>')
L.append(f'  <circle cx="{ex0}" cy="{ey}" r="6" fill="{gpu["line"]}"/>')
L.append(f'  <circle cx="{ex1}" cy="{ey}" r="6" fill="#fff" stroke="{gpu["line"]}" stroke-width="2"/>')
L.append(f'  <text x="{ex0 - 12}" y="{ey - 22}" class="m" text-anchor="end">k0</text><text x="{ex0 - 12}" y="{ey - 4}" class="m" text-anchor="end">f = 0.8</text>')
L.append(f'  <text x="{ex1 + 12}" y="{ey - 22}" class="m">k1</text><text x="{ex1 + 12}" y="{ey - 4}" class="m">f = 0.3</text>')
L.append(f'  <circle cx="{px:.1f}" cy="{ey}" r="5" fill="{cpu["line"]}"/>')
L.append(f'  <text x="{px:.1f}" y="{ey + 28}" class="m" text-anchor="middle" style="fill:{cpu["text"]}">p</text>')
L.append(f'  <text x="530" y="{ey + 98}" class="in" text-anchor="middle">alpha = (iso - f0) / (f1 - f0) = 0.6</text>')
L.append(f'  <text x="530" y="{ey + 118}" class="in" text-anchor="middle">p = (1 - alpha) k0 + alpha k1</text>')
# gradients (towards larger f), and the normal at p (opposite, interpolated)
for x, (gx, gy), lab in ((ex0, (-25, 55), 'g0'), (ex1, (-45, 40), 'g1')):
    L.append(f'  <line x1="{x}" y1="{ey}" x2="{x + gx}" y2="{ey + gy}" class="ar" stroke="#888888" marker-end="url(#ag)"/>')
    L.append(f'  <text x="{x + gx - 8}" y="{ey + gy + 4}" class="m" text-anchor="end">{lab}</text>')
gx, gy = (1 - a) * -25 + a * -45, (1 - a) * 55 + a * 40
n = math.hypot(gx, gy)
nx, ny = -gx / n * 70, -gy / n * 70
L.append(f'  <line x1="{px:.1f}" y1="{ey}" x2="{px + nx:.1f}" y2="{ey + ny:.1f}" class="ar" stroke="{gpu["line"]}" marker-end="url(#ao)"/>')
L.append(f'  <text x="690" y="{ey + ny - 12:.1f}" class="m" text-anchor="end" style="fill:{gpu["text"]}">n = -normalize((1-alpha) g0 + alpha g1)</text>')
L.append('</svg>')
write_svg(out, L)
