"""Small 3D helpers shared by model.py and view.py: vectors, an orthographic projector for a
z-up scene, flat-shaded convex polyhedra (back faces culled) and SVG snippets.

Projector: the viewer looks at the scene from the direction (azimuth, elevation); screen x is
the horizontal right vector, screen y points down (SVG). depth() grows toward the viewer, so
drawing in increasing depth order is a painter's algorithm."""
import math


def add(a, b): return tuple(x + y for x, y in zip(a, b))
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def mul(a, s): return tuple(x * s for x in a)
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a): return math.sqrt(dot(a, a))
def normalize(a): return mul(a, 1 / norm(a))


def matvec(M, p):
    """M given as three rows."""
    return tuple(dot(r, p) for r in M)


def rot_axis(axis, angle):
    """Rows of the rotation matrix of the given angle around a unit axis (Rodrigues)."""
    x, y, z = normalize(axis)
    c, s, C = math.cos(angle), math.sin(angle), 1 - math.cos(angle)
    return ((c + x * x * C, x * y * C - z * s, x * z * C + y * s),
            (y * x * C + z * s, c + y * y * C, y * z * C - x * s),
            (z * x * C - y * s, z * y * C + x * s, c + z * z * C))


def matmul(A, B):
    Bt = list(zip(*B))
    return tuple(tuple(dot(r, c) for c in Bt) for r in A)


class Projector:
    def __init__(self, origin, scale, azimuth_deg, elevation_deg):
        a, e = math.radians(azimuth_deg), math.radians(elevation_deg)
        self.d = (math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))   # toward the viewer
        self.r = normalize((-math.sin(a), math.cos(a), 0.0))
        self.u = cross(self.d, self.r)
        self.o, self.s = origin, scale

    def __call__(self, p):
        return (self.o[0] + self.s * dot(p, self.r), self.o[1] - self.s * dot(p, self.u))

    def depth(self, p):
        return dot(p, self.d)

    def visible(self, normal):
        return dot(normal, self.d) > 1e-9


def pts(P, points):
    return ' '.join(f'{x:.1f},{y:.1f}' for x, y in (P(p) for p in points))


def shade(hex_color, k):
    """Color scaled by k (k < 1 darker)."""
    c = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{max(0, min(255, int(v * k))):02x}' for v in c)


LIGHT = normalize((0.3, -0.5, 1.0))   # fixed shading direction (world / pseudo-world)


def box_faces(corner_fn):
    """The 6 faces of a box as lists of 4 points, outward orientation (counter-clockwise seen
    from outside). corner_fn(i, j, k), i, j, k in {0, 1}, gives the corners."""
    c = corner_fn
    return [[c(0, 0, 0), c(0, 1, 0), c(1, 1, 0), c(1, 0, 0)],   # bottom
            [c(0, 0, 1), c(1, 0, 1), c(1, 1, 1), c(0, 1, 1)],   # top
            [c(0, 0, 0), c(1, 0, 0), c(1, 0, 1), c(0, 0, 1)],   # y = 0
            [c(0, 1, 0), c(0, 1, 1), c(1, 1, 1), c(1, 1, 0)],   # y = 1
            [c(0, 0, 0), c(0, 0, 1), c(0, 1, 1), c(0, 1, 0)],   # x = 0
            [c(1, 0, 0), c(1, 1, 0), c(1, 1, 1), c(1, 0, 1)]]   # x = 1


def face_normal(f):
    return normalize(cross(sub(f[1], f[0]), sub(f[2], f[0])))


def draw_box(L, P, faces, color, light=LIGHT, stroke='#555'):
    for f in faces:
        n = face_normal(f)
        if P.visible(n):
            k = 0.78 + 0.22 * max(0.0, dot(n, light))
            L.append(f'  <polygon points="{pts(P, f)}" style="fill:{shade(color, k)};stroke:{stroke};stroke-width:1.3;stroke-linejoin:round"/>')


MARKERS = '''    <marker id="ak" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#555"/></marker>
    <marker id="mx" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#d0605a"/></marker>
    <marker id="my" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5aa55a"/></marker>
    <marker id="mz" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#4a86d0"/></marker>'''

STYLE = '''    text { font-family: Helvetica, Arial, sans-serif; font-size: 15px; fill: #888; }
    .in { fill: #333; font-size: 15px; }
    .lab { font-size: 14px; fill: #333; }
    .sub { font-size: 14px; fill: #888; }
    .b { font-weight: bold; }
    .m { font-family: Menlo, Consolas, monospace; font-size: 13px; fill: #333; }
    .ar { stroke: #555; stroke-width: 2; fill: none; marker-end: url(#ak); }'''

AXIS = [('#d0605a', 'mx'), ('#5aa55a', 'my'), ('#4a86d0', 'mz')]


def arrow(L, P, a, b, k, width=2.2):
    c, m = AXIS[k]
    pa, pb = P(a), P(b)
    L.append(f'  <path d="M{pa[0]:.1f},{pa[1]:.1f} L{pb[0]:.1f},{pb[1]:.1f}" style="stroke:{c};stroke-width:{width};fill:none;marker-end:url(#{m})"/>')


def label(L, xy, text, cls='lab', color=None, anchor='start', dx=0, dy=0):
    style = f' style="fill:{color}"' if color else ''
    L.append(f'  <text x="{xy[0] + dx:.1f}" y="{xy[1] + dy:.1f}" class="{cls}" text-anchor="{anchor}"{style}>{text}</text>')
