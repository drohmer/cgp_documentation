"""NDC cube with a triangle -> viewport (pixels) + depth buffer. Same cabinet view as frustum.py."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
EX, EY, ED = (1.0, 0.0), (0.0, -1.0), (0.6, -0.35)


def proj(o, s, x, y, d):
    return (o[0] + s * (x * EX[0] + y * EY[0] + d * ED[0]), o[1] + s * (x * EX[1] + y * EY[1] + d * ED[1]))


L = ['''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 340" width="700" height="340">
  <style>
    text { font-family: Helvetica, Arial, sans-serif; font-size: 15px; fill: #888; }
    .in { fill: #333; font-size: 14px; }
    .lab { font-size: 13px; fill: #333; }
    .b { font-weight: bold; }
    .m { font-family: Menlo, Consolas, monospace; font-size: 12px; fill: #333; }
    .e { stroke: #333; stroke-width: 1.6; fill: none; }
    .eh { stroke: #bbb; stroke-width: 1.2; fill: none; stroke-dasharray: 4 3; }
    .tri { fill: ''' + PAL['clip']['fill'] + '''; stroke: ''' + PAL['clip']['line'] + '''; stroke-width: 1.8; }
    .grid { stroke: #d5d5d5; stroke-width: 1; }
    .ar { stroke: #555; stroke-width: 2; fill: none; marker-end: url(#ak); }
    .ax { stroke-width: 2; fill: none; }
  </style>
  <defs>
    <marker id="ak" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#555"/></marker>
    <marker id="mx" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#d0605a"/></marker>
    <marker id="my" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5aa55a"/></marker>
    <marker id="mz" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#4a86d0"/></marker>
  </defs>''']

tri = [(-0.6, -0.3, 0.1), (0.6, 0.55, -0.1), (0.25, -0.75, 0.0)]

# ---- left: NDC cube
c, s = (170, 180), 60
Q = {}
for sx in (1, -1):
    for sy in (1, -1):
        for sz in (1, -1):
            Q[(sx, sy, sz)] = proj(c, s, sx, sy, sz)
hidden = (-1, -1, 1)
edges = []
for a in Q:
    for b in Q:
        if a < b and sum(1 for i in range(3) if a[i] != b[i]) == 1:
            edges.append((a, b))
for a, b in edges:
    if hidden in (a, b):
        L.append(f'  <path d="M{Q[a][0]:.1f},{Q[a][1]:.1f} L{Q[b][0]:.1f},{Q[b][1]:.1f}" class="eh"/>')
pts = ' '.join(f'{p[0]:.1f},{p[1]:.1f}' for p in (proj(c, s, *v) for v in tri))
L.append(f'  <polygon points="{pts}" class="tri"/>')
for a, b in edges:
    if hidden not in (a, b):
        L.append(f'  <path d="M{Q[a][0]:.1f},{Q[a][1]:.1f} L{Q[b][0]:.1f},{Q[b][1]:.1f}" class="e"/>')
for k, (t, dx, dy, an) in {(-1, -1, -1): ('(-1,-1,-1)', 0, 20, 'middle'), (1, 1, 1): ('(1,1,1)', 0, -10, 'middle'),
                           (1, -1, -1): ('(1,-1,-1)', 0, 20, 'middle')}.items():
    q = Q[k]
    L.append(f'  <text x="{q[0]+dx:.1f}" y="{q[1]+dy:.1f}" class="m" text-anchor="{an}">{t}</text>')
o = (300, 300)
for (dx, dy, dd), col, m, lab, (tx, ty) in zip([(1, 0, 0), (0, 1, 0), (0, 0, 1)], ['#d0605a', '#5aa55a', '#4a86d0'], ['mx', 'my', 'mz'], 'xyz', [(-2, 16), (-14, 4), (4, -6)]):
    p = proj(o, s, dx * 0.45, dy * 0.45, dd * 0.45)
    L.append(f'  <path d="M{o[0]},{o[1]} L{p[0]:.1f},{p[1]:.1f}" class="ax" style="stroke:{col};marker-end:url(#{m})"/>')
    L.append(f'  <text x="{p[0]+tx:.1f}" y="{p[1]+ty:.1f}" class="lab b" style="fill:{col}">{lab}</text>')
L.append('  <text x="20" y="24" class="in b">NDC (after the division by w)</text>')

# ---- arrow
L.append('  <path d="M352,186 H420" class="ar"/>')
L.append('  <text x="386" y="174" class="lab" text-anchor="middle">viewport</text>')

# ---- right: window
wx, wy, W, H = 440, 70, 240, 180
L.append(f'  <rect x="{wx}" y="{wy}" width="{W}" height="{H}" style="fill:#fff;stroke:#555;stroke-width:1.5"/>')
for k in range(1, 12):
    L.append(f'  <path d="M{wx+k*W/12:.1f},{wy} V{wy+H}" class="grid"/>')
for k in range(1, 9):
    L.append(f'  <path d="M{wx},{wy+k*H/9:.1f} H{wx+W}" class="grid"/>')
pts = ' '.join(f'{wx+(x+1)/2*W:.1f},{wy+(1-y)/2*H:.1f}' for x, y, z in tri)
L.append(f'  <polygon points="{pts}" class="tri"/>')
L.append(f'  <text x="{wx}" y="{wy+H+18}" class="m">(0,0)</text>')
L.append(f'  <text x="{wx+W}" y="{wy-8}" class="m" text-anchor="end">(width, height)</text>')
L.append(f'  <text x="{wx-6}" y="{wy-8}" class="in b">window (pixels)</text>')
L.append(f'  <text x="{wx}" y="{wy+H+44}" class="lab">x, y: pixel position in the window</text>')
L.append(f'  <text x="{wx}" y="{wy+H+62}" class="lab">z: kept in the depth buffer</text>')
L.append('</svg>')
write_svg(out, L)
