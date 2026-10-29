"""Frustum (camera space) -> NDC cube, same axonometric view in both panels.
Screen position = x*EX + y*EY + d*ED, with d = depth = -z (camera space) or z (NDC)."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
EX, EY, ED = (1.0, 0.0), (0.0, -1.0), (0.9, -0.45)


def proj(o, s, x, y, d):
    return (o[0] + s * (x * EX[0] + y * EY[0] + d * ED[0]), o[1] + s * (x * EX[1] + y * EY[1] + d * ED[1]))


L = ['''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 372" width="700" height="372">
  <style>
    text { font-family: Helvetica, Arial, sans-serif; font-size: 15px; fill: #888; }
    .in { fill: #333; font-size: 14px; }
    .lab { font-size: 13px; fill: #333; }
    .b { font-weight: bold; }
    .m { font-family: Menlo, Consolas, monospace; font-size: 12px; fill: #333; }
    .e { stroke: #333; stroke-width: 1.6; fill: none; }
    .eh { stroke: #bbb; stroke-width: 1.2; fill: none; stroke-dasharray: 4 3; }
    .fov { stroke: ''' + PAL['camera']['line'] + '''; stroke-width: 1.2; fill: none; }
    .ax { stroke-width: 2; fill: none; }
    .ar { stroke: #555; stroke-width: 2; fill: none; marker-end: url(#ak); }
  </style>
  <defs>
    <marker id="ak" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#555"/></marker>
    <marker id="mx" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#d0605a"/></marker>
    <marker id="my" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5aa55a"/></marker>
    <marker id="mz" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#4a86d0"/></marker>
  </defs>''']

# one color per corner, the same in both panels (n = near plane, f = far plane)
col = {('-', '-', 'n'): '#555555', ('+', '-', 'n'): '#d0605a', ('+', '+', 'n'): '#e0b000', ('-', '+', 'n'): '#5aa55a',
       ('-', '-', 'f'): '#aaaaaa', ('+', '-', 'f'): '#c050c0', ('+', '+', 'f'): '#ffffff', ('-', '+', 'f'): '#30b0c0'}
HIDDEN = ('-', '-', 'f')   # corner behind the others in this view


def box(P):
    edges = []
    for sx in '+-':
        for sy in '+-':
            edges.append(((sx, sy, 'n'), (sx, sy, 'f')))
        for pl in 'nf':
            edges.append(((sx, '+', pl), (sx, '-', pl)))
    for sy in '+-':
        for pl in 'nf':
            edges.append((('+', sy, pl), ('-', sy, pl)))
    for a, b in edges:
        cls = 'eh' if HIDDEN in (a, b) else 'e'
        L.append(f'  <path d="M{P[a][0]:.1f},{P[a][1]:.1f} L{P[b][0]:.1f},{P[b][1]:.1f}" class="{cls}"/>')


def dots(P):
    for k, p in P.items():
        L.append(f'  <circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="5" style="fill:{col[k]};stroke:#333;stroke-width:1.3"/>')


def axes(o, s, length, zsign, offsets):
    for (dx, dy, dd), c, m, lab, (tx, ty) in zip([(1, 0, 0), (0, 1, 0), (0, 0, zsign)], ['#d0605a', '#5aa55a', '#4a86d0'], ['mx', 'my', 'mz'], 'xyz', offsets):
        p = proj(o, s, dx * length, dy * length, dd * length)
        L.append(f'  <path d="M{o[0]:.1f},{o[1]:.1f} L{p[0]:.1f},{p[1]:.1f}" class="ax" style="stroke:{c};marker-end:url(#{m})"/>')
        L.append(f'  <text x="{p[0]+tx:.1f}" y="{p[1]+ty:.1f}" class="lab b" style="fill:{c}">{lab}</text>')


# ---- left: camera space frustum (d = -z)
eye, s = (40, 290), 46
n, f = 1.5, 4.4
h, w = 0.30 * n, 0.40 * n
P = {}
for sx in '+-':
    for sy in '+-':
        for pl, d in (('n', n), ('f', f)):
            k = d / n
            P[(sx, sy, pl)] = proj(eye, s, (w if sx == '+' else -w) * k, (h if sy == '+' else -h) * k, d)
for key in [('+', '+', 'f'), ('-', '+', 'f'), ('+', '-', 'f'), ('-', '-', 'f')]:
    L.append(f'  <path d="M{eye[0]},{eye[1]} L{P[key][0]:.1f},{P[key][1]:.1f}" class="fov"/>')
pa = proj(eye, s, 0, 0, f + 0.7)
L.append(f'  <path d="M{eye[0]},{eye[1]} L{pa[0]:.1f},{pa[1]:.1f}" class="eh" style="stroke:#888"/>')
L.append(f'  <text x="{pa[0]+4:.1f}" y="{pa[1]+4:.1f}" class="lab">-z</text>')
box(P)
dots(P)
axes(eye, s, 0.8, -1, [(-2, 16), (-14, 4), (-4, 16)])
L.append(f'  <circle cx="{eye[0]}" cy="{eye[1]}" r="3.5" style="fill:#333"/>')
q = P[('+', '-', 'n')]
L.append(f'  <text x="{q[0]+14:.1f}" y="{q[1]+22:.1f}" class="m" text-anchor="middle">(w, -h, -n)</text>')
q = P[('+', '+', 'f')]
L.append(f'  <text x="{q[0]:.1f}" y="{q[1]-14:.1f}" class="m" text-anchor="middle">(w f/n, h f/n, -f)</text>')
L.append('  <text x="20" y="24" class="in b">Camera space</text>')
L.append('  <text x="20" y="42" class="lab" style="fill:#888">eye at the origin, looking toward -z</text>')
L.append('  <text x="20" y="338" class="lab">near plane z = -n, far plane z = -f,</text>')
L.append('  <text x="20" y="356" class="lab">h = n tan(theta/2), w = a h</text>')

# ---- arrow
L.append('  <path d="M368,224 H436" class="ar"/>')
L.append('  <text x="402" y="212" class="m" text-anchor="middle">P, then / w</text>')

# ---- right: NDC cube (d = z)
c, s2 = (566, 196), 46
Q = {}
for sx in '+-':
    for sy in '+-':
        for pl, d in (('n', -1), ('f', 1)):
            Q[(sx, sy, pl)] = proj(c, s2, 1 if sx == '+' else -1, 1 if sy == '+' else -1, d)
box(Q)
axes((452, 312), s2, 0.55, 1, [(-2, 16), (-14, 4), (4, -6)])
dots(Q)
lab = {('+', '+', 'n'): ('(1,1,-1)', 8, 18, 'start'), ('+', '+', 'f'): ('(1,1,1)', 0, -12, 'middle'),
       ('-', '-', 'n'): ('(-1,-1,-1)', -10, 4, 'end'), ('+', '-', 'n'): ('(1,-1,-1)', 0, 22, 'middle'),
       ('-', '+', 'n'): ('(-1,1,-1)', -10, 4, 'end'), ('+', '-', 'f'): ('(1,-1,1)', -8, -8, 'end'),
       ('-', '+', 'f'): ('(-1,1,1)', 0, -12, 'middle')}
for k, (t, dx, dy, a) in lab.items():
    q = Q[k]
    L.append(f'  <text x="{q[0]+dx:.1f}" y="{q[1]+dy:.1f}" class="m" text-anchor="{a}">{t}</text>')
L.append('  <text x="460" y="24" class="in b">NDC</text>')
L.append('  <text x="460" y="42" class="lab" style="fill:#888">the cube [-1,1]^3</text>')
L.append('  <text x="460" y="338" class="lab">near plane -> z = -1,</text>')
L.append('  <text x="460" y="356" class="lab">far plane -> z = 1</text>')
L.append('</svg>')
write_svg(out, L)
