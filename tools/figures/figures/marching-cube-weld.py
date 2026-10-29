"""marching-cube-weld.svg: two neighbor cells of the grid create a vertex on their common edge.
The low-level marching_cube (vector of positions) keeps two copies (triangle soup); the version
that returns a mesh keys the vertices by their edge (k0, k1) and stores one shared vertex, whose
normal is then averaged over the triangles around it (normal_per_vertex).
2D view (marching squares) of the example marching-cubes-simple.
Usage: python marching-cube-weld.py OUT.svg"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
cpu, gpu, muted = PAL['cpu'], PAL['gpu'], PAL['muted']
H = 110

L = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 300" width="700" height="300">
  <style>
    text {{ font-family: Helvetica, Arial, sans-serif; font-size: 14px; fill: #333333; }}
    .b {{ font-weight: bold; }}
    .s {{ font-size: 13px; fill: #666666; }}
    .m {{ font-family: Menlo, Consolas, monospace; font-size: 12.5px; fill: #333; }}
  </style>
  <defs>
    <marker id="ao" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{gpu['line']}"/></marker>
  </defs>''']


def panel(x0, y0, welded):
    # two cells side by side, common vertical edge between nodes k0 (bottom) and k1 (top)
    xs, ys = [x0, x0 + H, x0 + 2 * H], [y0, y0 + H]
    for y in ys:
        L.append(f'<line x1="{xs[0]}" y1="{y}" x2="{xs[2]}" y2="{y}" stroke="#cccccc" stroke-width="1.5"/>')
    for x in xs:
        L.append(f'<line x1="{x}" y1="{ys[0]}" x2="{x}" y2="{ys[1]}" stroke="#cccccc" stroke-width="1.5"/>')
    L.append(f'<line x1="{xs[1]}" y1="{ys[0]}" x2="{xs[1]}" y2="{ys[1]}" stroke="#888888" stroke-width="2.5"/>')
    # isoline crossing the two cells: left piece and right piece meet on the common edge
    vx, vy = xs[1], y0 + 0.45 * H
    a, b = (x0, y0 + 0.8 * H), (xs[2], y0 + 0.2 * H)
    off = 0 if welded else 5
    L.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{vx - off}" y2="{vy}" stroke="{cpu["line"]}" stroke-width="3"/>')
    L.append(f'<line x1="{vx + off}" y1="{vy}" x2="{b[0]}" y2="{b[1]}" stroke="{cpu["line"]}" stroke-width="3"/>')
    # nodes inside (filled) / outside (empty)
    for x, y, inside in ((xs[0], ys[0], False), (xs[1], ys[0], False), (xs[2], ys[0], False),
                         (xs[0], ys[1], True), (xs[1], ys[1], True), (xs[2], ys[1], True)):
        L.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{gpu["line"] if inside else "#ffffff"}" stroke="{gpu["line"]}" stroke-width="1.5"/>')
    L.append(f'<text x="{xs[1] + 8}" y="{ys[1] + 18}" class="m">k0</text>')
    L.append(f'<text x="{xs[1] + 8}" y="{ys[0] - 8}" class="m">k1</text>')
    if welded:
        L.append(f'<circle cx="{vx}" cy="{vy}" r="5.5" fill="{cpu["line"]}"/>')
        # normal of the shared vertex: average of the two neighbor faces, pointing outward (up)
        L.append(f'<line x1="{vx}" y1="{vy}" x2="{vx - 15}" y2="{vy - 50}" stroke="{gpu["line"]}" stroke-width="2" marker-end="url(#ao)"/>')
        L.append(f'<text x="{vx - 22}" y="{vy - 36}" class="s" text-anchor="end">one normal</text>')
    else:
        for dx in (-off, off):
            L.append(f'<circle cx="{vx + dx}" cy="{vy}" r="4.5" fill="{cpu["line"]}"/>')
        L.append(f'<text x="{vx + 12}" y="{vy - 30}" class="s">two copies</text>')


L.append('<text x="20" y="28" class="b">Triangle soup (low-level marching_cube)</text>')
L.append('<text x="20" y="46" class="s">each cell adds its own vertices</text>')
panel(40, 100, False)
L.append('<text x="380" y="28" class="b">mesh returned by marching_cube</text>')
L.append('<text x="380" y="46" class="s">one vertex per edge (k0, k1) of the grid</text>')
panel(400, 100, True)
L.append(f'<text x="40" y="250" class="s">the two triangles do not share the vertex:</text>')
L.append(f'<text x="40" y="268" class="s">normals must come from elsewhere (gradient)</text>')
L.append(f'<text x="400" y="250" class="s">shared vertex: fill_empty_field averages</text>')
L.append(f'<text x="400" y="268" class="s">the normals of the triangles around it</text>')
L.append('</svg>')
write_svg(out, L)
