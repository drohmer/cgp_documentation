"""Model matrix: a unit cube in its local frame (left) placed in the world by
model = translation * rotation * scaling (right), its local frame carried along.
Usage: python3 model.py content/assets/model.svg"""
import math
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ortho3d import (Projector, MARKERS, STYLE, add, mul, matvec, matmul, rot_axis, box_faces,
                      draw_box, arrow, label, pts)

out = sys.argv[1]
W, H = 700, 330
CUBE = '#f2e88a'
L = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <style>
{STYLE}
  </style>
  <defs>
{MARKERS}
  </defs>''']

# ---- left: local space, the unit cube [0,1]^3
P1 = Projector((150, 236), 84, -120, 24)
draw_box(L, P1, box_faces(lambda i, j, k: (i, j, k)), CUBE)
o = (0, 0, 0)
for k, e in enumerate([(1.45, 0, 0), (0, 1.55, 0), (0, 0, 1.45)]):
    arrow(L, P1, o, e, k)
label(L, P1((1.45, 0, 0)), 'x', 'lab b', '#d0605a', dx=-2, dy=18)
label(L, P1((0, 1.55, 0)), 'y', 'lab b', '#5aa55a', dx=-6, dy=-8)
label(L, P1((0, 0, 1.45)), 'z', 'lab b', '#4a86d0', dx=8, dy=6)
for p, t, dx, dy, a in [((0, 0, 0), '(0,0,0)', -8, 18, 'end'), ((1, 0, 0), '(1,0,0)', 0, 22, 'middle'),
                        ((0, 1, 0), '(0,1,0)', -10, 18, 'end'), ((1, 1, 1), '(1,1,1)', 8, -6, 'start')]:
    q = P1(p)
    L.append(f'  <circle cx="{q[0]:.1f}" cy="{q[1]:.1f}" r="3" style="fill:#333"/>')
    label(L, q, t, 'm', anchor=a, dx=dx, dy=dy)
L.append('  <text x="20" y="26" class="in b">Local space</text>')
L.append('  <text x="20" y="45" class="sub">the mesh as created: a unit cube</text>')

# ---- arrow
L.append('  <path d="M262,170 H322" class="ar"/>')
L.append('  <text x="292" y="158" class="m b" text-anchor="middle">M</text>')
L.append('  <text x="292" y="194" class="sub" text-anchor="middle">model</text>')

# ---- right: world space
P2 = Projector((496, 240), 84, -120, 24)
G = 1.25
L.append(f'  <polygon points="{pts(P2, [(-G, -G, 0), (G, -G, 0), (G, G, 0), (-G, G, 0)])}" style="fill:#f1f1f1;stroke:#bbb;stroke-width:1"/>')
for t in [-G + i * G / 2.5 for i in range(1, 5)]:
    for a, b in [((t, -G, 0), (t, G, 0)), ((-G, t, 0), (G, t, 0))]:
        pa, pb = P2(a), P2(b)
        L.append(f'  <path d="M{pa[0]:.1f},{pa[1]:.1f} L{pb[0]:.1f},{pb[1]:.1f}" style="stroke:#ddd;stroke-width:1"/>')
# world frame
for k, e in enumerate([(0.9, 0, 0), (0, 0.9, 0), (0, 0, 0.9)]):
    arrow(L, P2, o, e, k)
L.append(f'  <circle cx="{P2(o)[0]:.1f}" cy="{P2(o)[1]:.1f}" r="3.5" style="fill:#333"/>')
label(L, P2((0.9, 0, 0)), 'x', 'lab b', '#d0605a', dx=-2, dy=18)
label(L, P2((0, 0.9, 0)), 'y', 'lab b', '#5aa55a', dx=-6, dy=-8)
label(L, P2((0, 0, 0.9)), 'z', 'lab b', '#4a86d0', dx=8, dy=6)

# model = translation * rotation * scaling (same order as affine: p -> R s p + t)
s = 0.7
R = rot_axis((0, 0, 1), math.radians(35))
t = (1.25, 0.85, 0.4)


def model(p):
    return add(matvec(R, mul(p, s)), t)


# translation, dashed from the world origin to the local origin
pa, pb = P2(o), P2(t)
L.append(f'  <path d="M{pa[0]:.1f},{pa[1]:.1f} L{pb[0]:.1f},{pb[1]:.1f}" style="stroke:#999;stroke-width:1.4;stroke-dasharray:5 4;fill:none"/>')
draw_box(L, P2, box_faces(lambda i, j, k: model((i, j, k))), CUBE)
# local frame of the cube, carried by the model matrix
for k, e in enumerate([(1.45, 0, 0), (0, 1.55, 0), (0, 0, 1.45)]):
    arrow(L, P2, t, model(e), k, width=1.8)
L.append(f'  <circle cx="{pb[0]:.1f}" cy="{pb[1]:.1f}" r="3" style="fill:#333"/>')
q = P2(model((1, 1, 1)))
label(L, q, 'M (1,1,1)', 'm', dx=8, dy=-4)
q = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
label(L, q, 'translation', 'sub', dx=10, dy=8)

L.append('  <text x="362" y="26" class="in b">World space</text>')
L.append('  <text x="362" y="45" class="sub">model: translation, rotation, scaling</text>')
L.append('  <text x="362" y="316" class="m">p_world = M p_local</text>')
L.append('  <text x="20" y="316" class="sub">corners given in local coordinates</text>')
L.append('</svg>')
write_svg(out, L)
