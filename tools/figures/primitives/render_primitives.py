#!/usr/bin/env python3
"""Draw the meshes exported by export_primitives.cpp as SVG figures (no dependency).

Orthographic view from the direction of the template camera (eye {3,-2,1.5}, z up), light at
the camera, shading close to the default CGP shader (ambient 0.3 + diffuse 0.6, no specular, no
two-sided lighting: back faces are dark), triangle edges drawn to show the sampling, world axes at the
origin (x red, y green, z blue) and the points given as parameters marked in orange.

Usage: python3 render_primitives.py primitives.json OUTPUT_DIR
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from palette import P as PAL  # noqa: E402

# axes drawn with the dark (text) tone of the palette: visible over the light blue shapes
AXIS_COLOR = {'x': PAL['x']['text'], 'y': PAL['y']['text'], 'z': PAL['z']['text']}

EYE = (3.0, -2.0, 1.5)
BASE = (0.62, 0.76, 1.00)       # color of the shapes (the frame keeps its per-vertex colors)
W, H, MARGIN = 520, 200, 22    # wide: the sites scale the figures to the width of the text
# Closed shapes: their back faces are hidden, they are not drawn (smaller files).
CLOSED = {"sphere", "ellipsoid", "torus", "cube", "cubic_grid", "cylinder_closed", "cone", "tetrahedron", "arrow", "frame"}


def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def scale(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def normalize(a):
    n = math.sqrt(dot(a, a))
    return scale(a, 1 / n) if n > 1e-12 else (0.0, 0.0, 0.0)


E = normalize(EYE)                        # direction toward the camera (and the light)
R = normalize(cross(scale(E, -1), (0, 0, 1)))
U = cross(R, scale(E, -1))

# Points passed as parameters (default values), labeled on the figures.
LABELS = {
    "sphere": [("center", (0, 0, 0))],
    "ellipsoid": [("center", (0, 0, 0))],
    "cube": [("center", (0, 0, 0))],
    "cubic_grid": [("p000", (0, 0, 0)), ("p111", (1, 1, 1))],
    "cylinder": [("p0", (0, 0, 0)), ("p1", (0, 0, 1))],
    "cylinder_closed": [("p0", (0, 0, 0)), ("p1", (0, 0, 1))],
    "cone": [("center_of_base", (0, 0, 0))],
    "torus": [("center", (0, 0, 0))],
    "disc": [("center", (0, 0, 0))],
    "grid": [("p00", (0, 0, 0)), ("p10", (1, 0, 0)), ("p11", (1, 1, 0)), ("p01", (0, 1, 0))],
    "quadrangle": [("p00", (0, 0, 0)), ("p10", (1, 0, 0)), ("p11", (1, 1, 0)), ("p01", (0, 1, 0))],
    "triangle": [("p0", (0, 0, 0)), ("p1", (1, 0, 0)), ("p2", (0, 1, 0))],
    "tetrahedron": [("p0", (0, 0, 0)), ("p1", (1, 0, 0)), ("p2", (0, 1, 0)), ("p3", (0, 0, 1))],
    "arrow": [("p0", (0, 0, 0)), ("p1", (1, 0, 0))],
    "frame": [],
}


def project(p):
    return (dot(p, R), -dot(p, U), dot(p, E))


def hexcolor(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(255 * v)))) for v in c)


def render(name, m):
    P, N, C, T = m["position"], m["normal"], m["color"], m["connectivity"]
    items = []    # (depth, svg element)
    for t in T:
        a, b, c = (P[i] for i in t)
        n_vertex = normalize(add(add(N[t[0]], N[t[1]]), N[t[2]]))
        col = tuple(sum(C[i][k] for i in t) / 3 for k in range(3))
        base = col if name == "frame" else tuple(BASE[k] * col[k] for k in range(3))
        if name in CLOSED and dot(n_vertex, E) < -0.25:
            continue
        diffuse = max(dot(n_vertex, E), 0.0)
        spec = 0.0    # no highlight: on flat triangles it lights a single triangle
        shade = tuple(min(1.0, (0.3 + 0.6 * diffuse) * base[k] + spec) for k in range(3))
        fill = hexcolor(shade)
        edge = hexcolor(scale(shade, 0.72))
        pa, pb, pc = project(a), project(b), project(c)
        depth = (pa[2] + pb[2] + pc[2]) / 3
        pts = " ".join(f"{q[0]:.4f},{q[1]:.4f}" for q in (pa, pb, pc))
        items.append((depth, "tri", pts, fill, edge))
    # axes, cut in small pieces sorted with the triangles
    if name != "frame":
        L = 0.6
        for axis, color in (((1, 0, 0), AXIS_COLOR['x']), ((0, 1, 0), AXIS_COLOR['y']), ((0, 0, 1), AXIS_COLOR['z'])):
            K = 24
            for k in range(K):
                q0 = project(scale(axis, L * k / K))
                q1 = project(scale(axis, L * (k + 1) / K))
                items.append(((q0[2] + q1[2]) / 2, "seg", (q0, q1), color, None))
    items.sort(key=lambda it: it[0])

    # fit in the view box
    xs, ys = [], []
    for it in items:
        if it[1] == "tri":
            for pt in it[2].split():
                x, y = map(float, pt.split(","))
                xs.append(x); ys.append(y)
        else:
            for q in it[2]:
                xs.append(q[0]); ys.append(q[1])
    for _, p in LABELS[name]:
        q = project(p); xs.append(q[0]); ys.append(q[1])
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    s = min((W - 2 * MARGIN) / max(x1 - x0, 1e-6), (H - 2 * MARGIN) / max(y1 - y0, 1e-6))
    ox = (W - s * (x1 - x0)) / 2 - s * x0
    oy = (H - s * (y1 - y0)) / 2 - s * y0
    tx = lambda x: ox + s * x
    ty = lambda y: oy + s * y

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           '<style>text{font-family:Menlo,Consolas,monospace;font-size:12px;fill:#666;paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}'
           '.l{fill:' + PAL['gpu']['text'] + '}.a{font-weight:bold}</style>', '<g stroke-width="0.4" stroke-linejoin="round">']
    for it in items:
        if it[1] == "tri":
            pts = []
            for pt in it[2].split():
                x, y = map(float, pt.split(","))
                pts.append(f"{tx(x):.1f},{ty(y):.1f}")
            out.append(f'<polygon points="{" ".join(pts)}" fill="{it[3]}" stroke="{it[4]}"/>')
        else:
            q0, q1 = it[2]
            out.append(f'<line x1="{tx(q0[0]):.1f}" y1="{ty(q0[1]):.1f}" x2="{tx(q1[0]):.1f}" y2="{ty(q1[1]):.1f}" stroke="{it[3]}" stroke-width="1.6"/>')
    out.append("</g>")
    if name != "frame":
        for label, axis, color in (("x", (1, 0, 0), AXIS_COLOR['x']), ("y", (0, 1, 0), AXIS_COLOR['y']), ("z", (0, 0, 1), AXIS_COLOR['z'])):
            q = project(scale(axis, 0.6 + 0.08))
            out.append(f'<text class="a" x="{tx(q[0]):.1f}" y="{ty(q[1]) + 4:.1f}" text-anchor="middle" style="fill:{color}">{label}</text>')
    for label, p in LABELS[name]:
        q = project(p)
        x, y = tx(q[0]), ty(q[1])
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{PAL["gpu"]["line"]}" stroke="#fff" stroke-width="0.8"/>')
        anchor, dx, dy = ("start", 5, -5) if x < W * 0.6 else ("end", -5, -5)
        if label.startswith("center"):      # below left, away from the y axis
            anchor, dx, dy = "end", -5, 13
        out.append(f'<text class="l" x="{x + dx:.1f}" y="{y + dy:.1f}" text-anchor="{anchor}">{label}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    data = json.loads(Path(sys.argv[1]).read_text())
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    for name, m in data.items():
        svg = render(name, m)
        f = outdir / f"{name}.svg"
        f.write_text(svg)
        print(f"{f}  {len(m['position'])} vertices, {len(m['connectivity'])} triangles, {len(svg) // 1024} KB  ({m['call']})")


if __name__ == "__main__":
    main()
