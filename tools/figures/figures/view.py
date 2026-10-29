"""View matrix: the same scene in world space (left), with the camera frame (eye, right, up,
back = -front) and its frustum, and in camera space (right), after V = inverse of the camera
frame: the eye at the origin, right/up/back along x/y/z, looking toward -z.
The right panel is drawn with the camera's y axis vertical, as frustum.svg.
Usage: python3 view.py content/assets/view.svg"""
import math
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _ortho3d import (Projector, MARKERS, STYLE, add, sub, mul, dot, cross, normalize, box_faces,
                      draw_box, arrow, label, pts, shade, face_normal)

out = sys.argv[1]
W, H = 700, 330
CUBE, SPHERE = '#f2e88a', '#e07a6e'
TILE = ('#ececec', '#f4ddd3')

# ---------------- scene, in world coordinates (z up)
cube_c, cube_h = (0.45, 0.35, 0.3), 0.3
sphere_c, sphere_r = (-0.55, -0.35, 0.25), 0.25
G, NT = 1.2, 4                                    # ground [-G,G]^2, NT x NT tiles

# camera frame (as camera_orbit / look_at: front toward the target, z up)
eye = (-1.6, -2.1, 1.4)
target = (0.0, 0.0, 0.1)
front = normalize(sub(target, eye))
right = normalize(cross(front, (0, 0, 1)))
up = cross(right, front)
back = mul(front, -1)
fov, aspect, near, far = math.radians(40), 1.4, 0.3, 1.3   # a short frustum: only its start is drawn


def to_camera(p):
    """V p: coordinates in the camera frame (right, up, back)."""
    d = sub(p, eye)
    return (dot(d, right), dot(d, up), dot(d, back))


def frustum_corners(dist):
    h = dist * math.tan(fov / 2)
    w = aspect * h
    return [(sx * w, sy * h, -dist) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def from_camera(q):
    return add(eye, add(add(mul(right, q[0]), mul(up, q[1])), mul(back, q[2])))


L = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <style>
{STYLE}
    .fr {{ stroke: {PAL["camera"]["line"]}; stroke-width: 1.2; fill: none; }}
    .frf {{ stroke: {PAL["camera"]["line"]}; stroke-width: 1.2; fill: {PAL["camera"]["line"]}; fill-opacity: 0.06; }}
  </style>
  <defs>
{MARKERS}
    <radialGradient id="sph" cx="0.35" cy="0.35" r="0.75"><stop offset="0" stop-color="#fbe3df"/><stop offset="1" stop-color="{SPHERE}"/></radialGradient>
  </defs>''']


def draw_scene(P, T, sphere_shrink=1.0):
    """Ground, cube and sphere; T maps a world point to the coordinates drawn by P."""
    for i in range(NT):
        for j in range(NT):
            a, b = -G + 2 * G * i / NT, -G + 2 * G * j / NT
            c = 2 * G / NT
            quad = [T((a, b, 0)), T((a + c, b, 0)), T((a + c, b + c, 0)), T((a, b + c, 0))]
            L.append(f'  <polygon points="{pts(P, quad)}" style="fill:{TILE[(i + j) % 2]};stroke:#d0d0d0;stroke-width:0.6"/>')
    objs = [(P.depth(T(cube_c)), 'cube'), (P.depth(T(sphere_c)), 'sphere')]
    for _, o in sorted(objs):
        if o == 'cube':
            faces = box_faces(lambda i, j, k: T(add(cube_c, ((2 * i - 1) * cube_h, (2 * j - 1) * cube_h, (2 * k - 1) * cube_h))))
            draw_box(L, P, faces, CUBE)
        else:
            c = P(T(sphere_c))
            L.append(f'  <circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{P.s * sphere_r:.1f}" style="fill:url(#sph);stroke:#a6564c;stroke-width:1"/>')


def draw_frustum(P, T, apex):
    fc = [T(from_camera(q)) for q in frustum_corners(far)]
    a = P(apex)
    for q in fc:
        b = P(q)
        L.append(f'  <path d="M{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f}" class="fr"/>')
    L.append(f'  <polygon points="{pts(P, fc)}" class="frf"/>')
    # line of sight, from the eye to the target (-z in camera space)
    b = P(T(target))
    L.append(f'  <path d="M{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f}" style="stroke:#888;stroke-width:1.2;stroke-dasharray:4 3;fill:none"/>')


def fit(az, el, scale, T, box):
    """Projector whose drawing (ground, eye, frustum) is centered in box = (x0, y0, x1, y1)."""
    P = Projector((0, 0), scale, az, el)
    key = [T((x, y, 0)) for x in (-G, G) for y in (-G, G)] + [T(eye)] + [T(add(eye, mul(v, 0.95))) for v in (up, right, back)]
    key += [T(from_camera(q)) for q in frustum_corners(far)]
    xs, ys = zip(*(P(k) for k in key))
    cx, cy = (box[0] + box[2]) / 2 - (min(xs) + max(xs)) / 2, (box[1] + box[3]) / 2 - (min(ys) + max(ys)) / 2
    return Projector((cx, cy), scale, az, el)


# ================= left panel: world space
ident = lambda p: p
P1 = fit(-70, 28, 60, ident, (70, 64, 316, 290))
draw_scene(P1, ident)
draw_frustum(P1, ident, eye)
# world frame
o = (0, 0, 0)
for k, e in enumerate([(0.9, 0, 0), (0, 0.9, 0), (0, 0, 0.9)]):
    arrow(L, P1, o, e, k, width=2)
L.append(f'  <circle cx="{P1(o)[0]:.1f}" cy="{P1(o)[1]:.1f}" r="3" style="fill:#333"/>')
label(L, P1((0.9, 0, 0)), 'x', 'lab b', '#d0605a', dx=4, dy=14)
label(L, P1((0, 0.9, 0)), 'y', 'lab b', '#5aa55a', anchor='end', dx=-4, dy=-4)
label(L, P1((0, 0, 0.9)), 'z', 'lab b', '#4a86d0', dx=6, dy=4)
# camera frame at the eye
CL = 0.75
for k, (v, name) in enumerate([(right, 'right'), (up, 'up'), (back, 'back')]):
    arrow(L, P1, eye, add(eye, mul(v, CL)), k, width=2.4)
e1 = P1(eye)
L.append(f'  <circle cx="{e1[0]:.1f}" cy="{e1[1]:.1f}" r="5" style="fill:{PAL["camera"]["line"]};stroke:#333;stroke-width:1.2"/>')
label(L, P1(add(eye, mul(right, CL))), 'right', 'lab b', '#d0605a', dx=4, dy=16)
label(L, P1(add(eye, mul(up, CL))), 'up', 'lab b', '#5aa55a', dx=6, dy=0)
label(L, P1(add(eye, mul(back, CL))), 'back', 'lab b', '#4a86d0', anchor='end', dx=-6, dy=-2)
label(L, P1(add(eye, mul(back, CL))), '= -front', 'lab', '#4a86d0', anchor='end', dx=-6, dy=14)
label(L, e1, 'eye', 'lab b', PAL['camera']['text'], anchor='end', dx=-6, dy=20)
L.append('  <text x="20" y="26" class="in b">World space</text>')
L.append('  <text x="20" y="45" class="sub">the camera is a frame placed in the scene</text>')
L.append('  <text x="20" y="314" class="sub">camera frame: eye, right, up, back</text>')

# ================= middle arrows
L.append('  <path d="M334,160 H390" class="ar"/>')
L.append('  <text x="362" y="150" class="m b" text-anchor="middle">V</text>')
L.append('  <path d="M390,196 H334" class="ar" style="stroke:#aaa;marker-end:url(#ak)"/>')
L.append('  <text x="362" y="218" class="m" text-anchor="middle" style="fill:#888">V^-1</text>')

# ================= right panel: camera space, drawn with y up (pseudo world: (x, -z, y))
pseudo = lambda q: (q[0], -q[2], q[1])
T2 = lambda p: pseudo(to_camera(p))
P2 = fit(-58, 18, 70, T2, (420, 64, 690, 290))
draw_scene(P2, T2)
draw_frustum(P2, T2, (0, 0, 0))
# camera axes = canonical axes
for k, e in enumerate([(CL, 0, 0), (0, CL, 0), (0, 0, CL)]):
    arrow(L, P2, (0, 0, 0), pseudo(e), k, width=2.4)
e2 = P2((0, 0, 0))
L.append(f'  <circle cx="{e2[0]:.1f}" cy="{e2[1]:.1f}" r="5" style="fill:{PAL["camera"]["line"]};stroke:#333;stroke-width:1.2"/>')
label(L, P2(pseudo((CL, 0, 0))), 'right (1,0,0)', 'lab b', '#d0605a', dx=4, dy=16)
label(L, P2(pseudo((0, CL, 0))), 'up (0,1,0)', 'lab b', '#5aa55a', anchor='end', dx=-6, dy=4)
label(L, P2(pseudo((0, 0, CL))), 'back (0,0,1)', 'lab b', '#4a86d0', anchor='end', dx=-6, dy=4)
label(L, e2, 'eye (0,0,0)', 'lab b', PAL['camera']['text'], anchor='end', dx=-8, dy=-8)
L.append('  <text x="400" y="26" class="in b">Camera space</text>')
L.append('  <text x="400" y="45" class="sub">after V: the eye at the origin, looking toward -z</text>')
L.append('  <text x="400" y="314" class="m">V = inverse(camera frame)</text>')
L.append('</svg>')
write_svg(out, L)
