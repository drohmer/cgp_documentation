"""multi-texture-blend.svg: the fragment shader of the example multi-texture reads two textures at
the same uv, fades the second one (cracks) to white along v, and multiplies the two colors.
Usage: python multi-texture-blend.py OUT.svg"""
import math
import os
import random
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
gpu, muted, uniform = PAL['gpu'], PAL['muted'], PAL['uniform']
BRICK, MORTAR, CRACK = '#b0573e', '#e9e2da', '#2b2b2b'   # content colors of the two images
S, Y0 = 150, 70


def bricks(x0, y0, uid):
    L = [f'<clipPath id="c{uid}"><rect x="{x0}" y="{y0}" width="{S}" height="{S}"/></clipPath>',
         f'<g clip-path="url(#c{uid})"><rect x="{x0}" y="{y0}" width="{S}" height="{S}" fill="{MORTAR}"/>']
    h, w = S / 6, S / 3
    for j in range(6):
        off = 0 if j % 2 == 0 else -w / 2
        for i in range(4):
            L.append(f'<rect x="{x0 + off + i * w + 2:.1f}" y="{y0 + j * h + 2:.1f}" width="{w - 4:.1f}" height="{h - 4:.1f}" fill="{BRICK}"/>')
    L.append('</g>')
    return L


def cracks(x0, y0, uid, fade):
    rnd = random.Random(3)
    L = [f'<clipPath id="c{uid}"><rect x="{x0}" y="{y0}" width="{S}" height="{S}"/></clipPath>',
         f'<g clip-path="url(#c{uid})">']
    for _ in range(16):
        x, y = x0 + rnd.uniform(0, S), y0 + rnd.uniform(0, S)
        a = rnd.uniform(0, 6.3)
        pts = [(x, y)]
        for _ in range(9):
            a += rnd.uniform(-0.7, 0.7)
            x += 11 * math.cos(a)
            y += 11 * math.sin(a)
            pts.append((x, y))
        L.append('<polyline points="' + ' '.join(f'{a:.1f},{b:.1f}' for a, b in pts)
                 + f'" fill="none" stroke="{CRACK}" stroke-width="1.6"/>')
    L.append('</g>')
    if fade:   # the cracks fade out along v: visible at the bottom (v = 0), gone at the top (v = 1)
        L.insert(1, f'<mask id="m{uid}"><rect x="{x0}" y="{y0}" width="{S}" height="{S}" fill="url(#fade)"/></mask>')
        L[2] = L[2].replace('<g ', f'<g mask="url(#m{uid})" ')
    return L


L = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 300" width="700" height="300">
  <style>
    text {{ font-family: Helvetica, Arial, sans-serif; font-size: 14px; fill: #333333; }}
    .b {{ font-weight: bold; }}
    .s {{ font-size: 13px; fill: #666666; }}
    .m {{ font-family: Menlo, Consolas, monospace; font-size: 12.5px; fill: #333; }}
    .op {{ font-size: 26px; fill: #666666; }}
  </style>
  <defs>
    <linearGradient id="fade" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#000000"/>
    </linearGradient>
  </defs>''']
cols = [(30, 'image_texture', 'brick.png, unit 0'),
        (275, 'image_texture_2', 'crack.png, unit 1'),
        (520, 'product', 'color of the object')]
for x, title, sub in cols:
    L.append(f'<text x="{x}" y="30" class="b">{title}</text>')
    L.append(f'<text x="{x}" y="48" class="s">{sub}</text>')
L += bricks(30, Y0, 'a')
L.append(f'<rect x="275" y="{Y0}" width="{S}" height="{S}" fill="#ffffff"/>')
L += cracks(275, Y0, 'b', True)
L += bricks(520, Y0, 'c')
L += cracks(520, Y0, 'd', True)
for x in (30, 275, 520):
    L.append(f'<rect x="{x}" y="{Y0}" width="{S}" height="{S}" fill="none" stroke="{gpu["stroke"]}" stroke-width="2"/>')
L.append(f'<text x="{(30 + S + 275) / 2:.0f}" y="{Y0 + S / 2 + 9}" class="op" text-anchor="middle">x</text>')
L.append(f'<text x="{(275 + S + 520) / 2:.0f}" y="{Y0 + S / 2 + 9}" class="op" text-anchor="middle">=</text>')
# v axis of the fade
ax = 275 + S + 10
L.append(f'<text x="{ax}" y="{Y0 + 12}" class="s">v = 1</text>')
L.append(f'<text x="{ax}" y="{Y0 + S}" class="s">v = 0</text>')
L.append(f'<text x="275" y="{Y0 + S + 26}" class="m">mix with white, weight</text>')
L.append(f'<text x="275" y="{Y0 + S + 44}" class="m">fragment.uv.y</text>')
L.append(f'<text x="520" y="{Y0 + S + 26}" class="s">cracks at the bottom,</text>')
L.append(f'<text x="520" y="{Y0 + S + 44}" class="s">clean bricks at the top</text>')
L.append('</svg>')
write_svg(out, L)
