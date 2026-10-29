"""instancing-procedural-blade.svg: in the example instancing-procedural, the vertex shader places
each blade from gl_InstanceID only (left, top view of the domain of the offsets), then bends it
with a wind displacement proportional to the height z (right, side view).
Usage: python instancing-procedural-blade.py OUT.svg"""
import math
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
code, cam, px, py, mut = PAL['code'], PAL['camera'], PAL['x'], PAL['y'], PAL['muted']
GRASS, GRASS_D = '#8cc63f', '#4e7d1e'

L = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 370" width="700" height="370">
  <style>
    text {{ font-family: Helvetica, Arial, sans-serif; font-size: 14px; fill: #333333; }}
    .b {{ font-weight: bold; }}
    .s {{ font-size: 13px; fill: #666666; }}
    .m {{ font-family: Menlo, Consolas, monospace; font-size: 12px; fill: #333333; }}
  </style>
  <defs>
    <marker id="ag" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{mut['line']}"/></marker>
    <marker id="ax" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{px['line']}"/></marker>
    <marker id="ay" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{py['line']}"/></marker>
    <marker id="ac" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{cam['line']}"/></marker>
  </defs>
  <text x="20" y="24" class="b">Where: offset from gl_InstanceID (top view)</text>
  <text x="400" y="24" class="b">How: wind bends the blade (side view)</text>''']

# ---- left: top view, world units -> pixels
S = 9.0                      # pixels per unit
OX, OY = 110, 250            # pixel position of the world origin
def P(x, y):
    return OX + S * x, OY - S * y


x0, y0 = P(0, 14)
x1, y1 = P(20, -6)
L.append(f'  <rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="{code["fill"]}" stroke="{code["stroke"]}" stroke-width="1.4" stroke-dasharray="5 3"/>')
# a few blades seen from the top (short segments with random orientation)
import random
random.seed(3)
for _ in range(60):
    bx, by = random.uniform(0.5, 19.5), random.uniform(-5.5, 13.5)
    a = random.uniform(0, math.pi)
    cx, cy = P(bx, by)
    dx, dy = 4 * math.cos(a), 4 * math.sin(a)
    L.append(f'  <line x1="{cx - dx:.1f}" y1="{cy - dy:.1f}" x2="{cx + dx:.1f}" y2="{cy + dy:.1f}" stroke="{GRASS_D}" stroke-width="1.6"/>')
# axes
ax0, ay0 = P(-8, 0)
L.append(f'  <line x1="{ax0}" y1="{OY}" x2="{P(23, 0)[0]}" y2="{OY}" stroke="{px["line"]}" stroke-width="1.6" marker-end="url(#ax)"/>')
L.append(f'  <text x="{P(23, 0)[0] - 4}" y="{OY + 18}" class="b" style="fill:{px["text"]}">x</text>')
L.append(f'  <line x1="{OX}" y1="{P(0, -2.5)[1]}" x2="{OX}" y2="{P(0, 17)[1]}" stroke="{py["line"]}" stroke-width="1.6" marker-end="url(#ay)"/>')
L.append(f'  <text x="{OX - 16}" y="{P(0, 17)[1] + 8}" class="b" style="fill:{py["text"]}">y</text>')
# tree at the origin, camera at (0,-6) looking at it
L.append(f'  <circle cx="{OX}" cy="{OY}" r="6" fill="#b08a5a" stroke="#6b4f2a" stroke-width="1.2"/>')
L.append(f'  <text x="{OX - 10}" y="{OY - 10}" class="s" text-anchor="end">palm tree (0,0)</text>')
cx, cy = P(0, -6)
L.append(f'  <circle cx="{cx}" cy="{cy}" r="5" fill="{cam["line"]}"/>')
L.append(f'  <line x1="{cx}" y1="{cy - 6}" x2="{cx}" y2="{cy - 30}" stroke="{cam["line"]}" stroke-width="2" marker-end="url(#ac)"/>')
L.append(f'  <text x="{cx - 10}" y="{cy + 5}" class="s" text-anchor="end" style="fill:{cam["text"]}">camera (0,-6)</text>')
# extents
L.append(f'  <text x="{(x0 + x1) / 2}" y="{y0 - 8}" class="m" text-anchor="middle">x in [0, 20 s)</text>')
L.append(f'  <text x="{x1 + 8}" y="{(y0 + y1) / 2 - 6}" class="m">y in</text>')
L.append(f'  <text x="{x1 + 8}" y="{(y0 + y1) / 2 + 10}" class="m">[-6 s,</text>')
L.append(f'  <text x="{x1 + 8}" y="{(y0 + y1) / 2 + 26}" class="m">14 s)</text>')
L.append(f'  <text x="20" y="335" class="s">s = scaling_grass (slider Scale), drawn here for s = 1;</text>')
L.append(f'  <text x="20" y="353" class="s">the angle of the blade around z also comes from rand(id).</text>')

# ---- right: side view of one blade, root fixed, tip displaced by z * wind
GX, GY, H = 470, 300, 210      # root (pixels), height of the blade (1 unit)
L.append(f'  <line x1="400" y1="{GY}" x2="680" y2="{GY}" stroke="#999999" stroke-width="1.4"/>')
L.append(f'  <text x="680" y="{GY + 18}" class="s" text-anchor="end">ground z = 0</text>')
W = 26
# undeformed quad
L.append(f'  <polygon points="{GX - W},{GY} {GX + W},{GY} {GX + W},{GY - H} {GX - W},{GY - H}" fill="none" stroke="{mut["line"]}" stroke-width="1.4" stroke-dasharray="5 3"/>')
# deformed: displacement = z * wind, wind horizontal: shear proportional to z
D = 95   # pixels of displacement at z = 1
pts = f'{GX - W},{GY} {GX + W},{GY} {GX + W + D},{GY - H} {GX - W + D},{GY - H}'
L.append(f'  <polygon points="{pts}" fill="{GRASS}" fill-opacity="0.75" stroke="{GRASS_D}" stroke-width="1.6"/>')
L.append(f'  <line x1="{GX + W + 4}" y1="{GY - H}" x2="{GX + W + D - 4}" y2="{GY - H}" stroke="{mut["line"]}" stroke-width="2" marker-end="url(#ag)"/>')
L.append(f'  <text x="{GX + W + D / 2}" y="{GY - H - 10}" class="m" text-anchor="middle">1 x wind</text>')
L.append(f'  <line x1="{GX + W + 4}" y1="{GY - H / 2}" x2="{GX + W + D / 2 - 4}" y2="{GY - H / 2}" stroke="{mut["line"]}" stroke-width="2" marker-end="url(#ag)"/>')
L.append(f'  <text x="{GX + W + D / 2 + 6}" y="{GY - H / 2 + 4}" class="m">0.5 x wind</text>')
L.append(f'  <text x="{GX}" y="{GY + 18}" class="s" text-anchor="middle">root: z = 0, fixed</text>')
L.append(f'  <text x="400" y="335" class="m">p = p + p.z * wind(p, time)</text>')
L.append(f'  <text x="400" y="353" class="s">the tips move, the roots stay on the ground</text>')
L.append('</svg>')
write_svg(out, L)
