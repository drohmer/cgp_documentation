"""multiple-cameras-passes.svg: the example multiple-cameras draws the same cube twice in
display_frame(), each time after changing environment.camera_view; both passes write into the
same image (same projection, same depth buffer). Usage: python multiple-cameras-passes.py OUT.svg"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
cam, inp, mut = PAL['camera'], PAL['input'], PAL['muted']
WOOD, WOOD_D, WOOD_L = '#c99a5b', '#9a6d36', '#e2c08f'

L = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 360" width="700" height="360">
  <style>
    text {{ font-family: Helvetica, Arial, sans-serif; font-size: 14px; fill: #333333; }}
    .b {{ font-weight: bold; }}
    .t {{ fill: {cam['text']}; }}
    .s {{ font-size: 13px; fill: #666666; }}
    .m {{ font-family: Menlo, Consolas, monospace; font-size: 12px; fill: #333333; }}
    .box {{ fill: {cam['fill']}; stroke: {cam['stroke']}; stroke-width: 1.4; }}
    .ar {{ stroke: {cam['line']}; stroke-width: 2; fill: none; marker-end: url(#ac); }}
  </style>
  <defs>
    <marker id="ac" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{cam['line']}"/></marker>
  </defs>
  <text x="20" y="24" class="b">display_frame(): the same cube drawn twice, one image</text>''']


def box(y, title, lines, h=104):
    L.append(f'  <rect x="20" y="{y}" width="362" height="{h}" rx="6" class="box"/>')
    L.append(f'  <text x="34" y="{y + 24}" class="b t">{title}</text>')
    for k, s in enumerate(lines):
        L.append(f'  <text x="34" y="{y + 46 + k * 19}" class="m">{s}</text>')


box(44, '1. camera_control (mouse)', [
    'camera_view = V1   (changes with the mouse)',
    'light = position of camera 1',
    'cube: no rotation, at (0,0,0)'])
box(176, '2. camera2_control (look_at every frame)', [
    'camera_view = V2   (eye (8,0.5,0), fixed)',
    'light = (7,1,0)',
    'cube: rotated by timer.t around y, at (0,2.5,0)'])
L.append(f'  <text x="20" y="312" class="s">Same projection P and same depth buffer for both passes:</text>')
L.append(f'  <text x="20" y="331" class="s">nothing is cleared between them.</text>')

# the image
ix, iy, iw, ih = 418, 44, 262, 236
L.append(f'  <rect x="{ix}" y="{iy}" width="{iw}" height="{ih}" fill="#ffffff" stroke="#999999" stroke-width="1.4"/>')
L.append(f'  <text x="{ix + iw / 2}" y="{iy + ih + 22}" class="s" text-anchor="middle">the window: one color and depth buffer</text>')


def cube(cx, cy, s):
    a, b, h = 0.5 * s, 0.28 * s, 0.62 * s
    y0 = cy - s
    top = f'{cx},{y0} {cx + a},{y0 + b} {cx},{y0 + 2 * b} {cx - a},{y0 + b}'
    left = f'{cx - a},{y0 + b} {cx},{y0 + 2 * b} {cx},{y0 + 2 * b + h} {cx - a},{y0 + b + h}'
    right = f'{cx + a},{y0 + b} {cx},{y0 + 2 * b} {cx},{y0 + 2 * b + h} {cx + a},{y0 + b + h}'
    L.append(f'  <polygon points="{top}" fill="{WOOD_L}" stroke="{WOOD_D}" stroke-width="1.2"/>')
    L.append(f'  <polygon points="{left}" fill="{WOOD}" stroke="{WOOD_D}" stroke-width="1.2"/>')
    L.append(f'  <polygon points="{right}" fill="{WOOD_D}" stroke="{WOOD_D}" stroke-width="1.2"/>')


cube(545, 205, 90)
L.append(f'  <rect x="{545 - 26}" y="{iy + 16}" width="52" height="46" fill="{WOOD}" stroke="{WOOD_D}" stroke-width="1.2"/>')
L.append(f'  <line x1="{545 - 9}" y1="{iy + 16}" x2="{545 - 9}" y2="{iy + 62}" stroke="{WOOD_D}"/>')
L.append(f'  <line x1="{545 + 9}" y1="{iy + 16}" x2="{545 + 9}" y2="{iy + 62}" stroke="{WOOD_D}"/>')
L.append(f'  <text x="{545 + 36}" y="{iy + 36}" class="s">pass 2: fixed on</text>')
L.append(f'  <text x="{545 + 36}" y="{iy + 53}" class="s">the screen</text>')
L.append(f'  <text x="{ix + 12}" y="{iy + ih - 14}" class="s">pass 1: follows the mouse</text>')
# arrows from the boxes to the image
L.append(f'  <path d="M382,96 C410,96 420,190 480,190" class="ar"/>')
L.append(f'  <path d="M382,228 C410,228 420,{iy + 39} {545 - 32},{iy + 39}" class="ar"/>')
L.append('</svg>')
write_svg(out, L)
