"""billboard-discard.svg: the foliage of the example transparent-billboards is made of textured
quads; the fragment shader discards the pixels whose texture alpha is below 0.5, so the kept
pixels are opaque (color and depth written, no blending, no sorting) and the discarded ones
leave the scene behind visible.
Usage: python billboard-discard.py OUT.svg"""
import math
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
gpu, code, muted = PAL['gpu'], PAL['code'], PAL['muted']
LEAF = '#4f7a3a'    # content color: the needles of the pine texture


def frond(x0, y0, s, flip=False):
    """A pine frond in a square of size s whose top-left corner is (x0, y0): a stem and needles."""
    L = []
    sx, sy, ex, ey = x0 + 0.12 * s, y0 + 0.85 * s, x0 + 0.9 * s, y0 + 0.2 * s
    L.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{LEAF}" stroke-width="3"/>')
    n = 11
    for k in range(1, n):
        t = k / n
        px, py = sx + t * (ex - sx), sy + t * (ey - sy)
        ln = 0.26 * s * (1 - 0.6 * t)
        for a in (55, -55):
            ang = math.atan2(ey - sy, ex - sx) + math.radians(a + (25 if a > 0 else -25))
            L.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px + ln * math.cos(ang):.1f}" y2="{py + ln * math.sin(ang):.1f}" stroke="{LEAF}" stroke-width="2.4" stroke-linecap="round"/>')
    return L


def checker(x0, y0, s, n=8):
    L = [f'<rect x="{x0}" y="{y0}" width="{s}" height="{s}" fill="#ffffff"/>']
    c = s / n
    for j in range(n):
        for i in range(n):
            if (i + j) % 2:
                L.append(f'<rect x="{x0 + i * c:.1f}" y="{y0 + j * c:.1f}" width="{c:.1f}" height="{c:.1f}" fill="#e6e6e6"/>')
    return L


S = 150
L = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 262" width="700" height="262">
  <style>
    text {{ font-family: Helvetica, Arial, sans-serif; font-size: 14px; fill: #333333; }}
    .b {{ font-weight: bold; }}
    .s {{ font-size: 13px; fill: #666666; }}
    .m {{ font-family: Menlo, Consolas, monospace; font-size: 12.5px; fill: #333; }}
  </style>
  <defs>
    <marker id="ag" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{muted['line']}"/></marker>
  </defs>''']

# 1. the texture, with its transparent background shown as a checkerboard
x1, y1 = 30, 60
L.append(f'<text x="{x1}" y="30" class="b">1. Texture (pine.png)</text>')
L.append(f'<text x="{x1}" y="48" class="s">checkerboard = alpha 0</text>')
L += checker(x1, y1, S)
L += frond(x1, y1, S)
L.append(f'<rect x="{x1}" y="{y1}" width="{S}" height="{S}" fill="none" stroke="{gpu["stroke"]}" stroke-width="2"/>')

# 2. the test in the fragment shader
bx, by, bw, bh = 228, 95, 220, 82
L.append(f'<text x="{bx}" y="30" class="b">2. Fragment shader</text>')
L.append(f'<text x="{bx}" y="48" class="s">once per pixel of the quad</text>')
L.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="6" fill="{code["fill"]}" stroke="{code["stroke"]}" stroke-width="1.5"/>')
L.append(f'<text x="{bx + 12}" y="{by + 24}" class="m" xml:space="preserve">if (color_image_texture.a</text>')
L.append(f'<text x="{bx + 12}" y="{by + 42}" class="m" xml:space="preserve">    &lt; 0.5)</text>')
L.append(f'<text x="{bx + 12}" y="{by + 62}" class="m" xml:space="preserve">  discard;</text>')
L.append(f'<line x1="{x1 + S + 8}" y1="{y1 + S / 2}" x2="{bx - 6}" y2="{y1 + S / 2}" stroke="{muted["line"]}" stroke-width="2" marker-end="url(#ag)"/>')
L.append(f'<text x="{bx}" y="{by + bh + 28}" class="s">alpha &gt;= 0.5: shaded, color</text>')
L.append(f'<text x="{bx}" y="{by + bh + 46}" class="s">and depth written (opaque)</text>')
L.append(f'<text x="{bx}" y="{by + bh + 70}" class="s">alpha &lt; 0.5: nothing written</text>')

# 3. the result over what is behind
x3, y3 = 500, 60
L.append(f'<text x="{x3}" y="30" class="b">3. Result on screen</text>')
L.append(f'<text x="{x3}" y="48" class="s">over the trunk behind it</text>')
L.append(f'<rect x="{x3}" y="{y3}" width="{S}" height="{S}" fill="#f4f4f4"/>')
L.append(f'<rect x="{x3 + 62}" y="{y3}" width="26" height="{S}" fill="#8a6a4e"/>')
L += frond(x3, y3, S)
L.append(f'<rect x="{x3}" y="{y3}" width="{S}" height="{S}" fill="none" stroke="{gpu["stroke"]}" stroke-width="2" stroke-dasharray="6 4"/>')
L.append(f'<line x1="{bx + bw + 6}" y1="{y1 + S / 2}" x2="{x3 - 8}" y2="{y1 + S / 2}" stroke="{muted["line"]}" stroke-width="2" marker-end="url(#ag)"/>')
L.append(f'<text x="{x3}" y="{y3 + S + 24}" class="s">border of the quad: invisible</text>')
L.append(f'<text x="{x3}" y="{y3 + S + 42}" class="s">no blending, no sorting</text>')
L.append('</svg>')
write_svg(out, L)
