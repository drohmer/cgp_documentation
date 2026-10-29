"""camera-2d-displacement-plane.svg: camera_controller_2d_displacement moves the camera along the
front direction projected on the plane orthogonal to the rotation axis (normalized), so looking
down does not move the eye toward the ground. Side view. Usage: python camera-2d-displacement-plane.py OUT.svg"""
import math
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
cam, py, mut, err = PAL['camera'], PAL['y'], PAL['muted'], PAL['error']

L = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 270" width="700" height="270">
  <style>
    text {{ font-family: Helvetica, Arial, sans-serif; font-size: 14px; fill: #333333; }}
    .b {{ font-weight: bold; }}
    .s {{ font-size: 13px; fill: #666666; }}
    .m {{ font-family: Menlo, Consolas, monospace; font-size: 12px; fill: #333333; }}
  </style>
  <defs>
    <marker id="ac" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{cam['line']}"/></marker>
    <marker id="ay" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{py['line']}"/></marker>
    <marker id="ag" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{mut['line']}"/></marker>
  </defs>
  <text x="20" y="24" class="b">Side view: the keys move the eye in the plane orthogonal to the up axis</text>''']

EX, EY = 160, 120           # eye
GY = 210                    # ground (y = -0.5)
L.append(f'  <line x1="20" y1="{GY}" x2="680" y2="{GY}" stroke="#999999" stroke-width="1.4"/>')
L.append(f'  <text x="680" y="{GY + 20}" class="s" text-anchor="end">ground, y = -0.5</text>')
L.append(f'  <line x1="20" y1="{EY}" x2="680" y2="{EY}" stroke="{mut["line"]}" stroke-width="1" stroke-dasharray="4 4"/>')
L.append(f'  <text x="680" y="{EY - 8}" class="s" text-anchor="end">height of the eye, kept constant (y = 0 at start)</text>')
# up axis
L.append(f'  <line x1="{EX}" y1="{EY}" x2="{EX}" y2="{EY - 80}" stroke="{py["line"]}" stroke-width="2" marker-end="url(#ay)"/>')
L.append(f'  <text x="{EX - 8}" y="{EY - 70}" class="m" text-anchor="end" style="fill:{py["text"]}">axis_of_rotation (y)</text>')
# front, looking down
a = math.radians(-30)
fl = 170
fx, fy = EX + fl * math.cos(a), EY - fl * math.sin(a)
L.append(f'  <line x1="{EX}" y1="{EY}" x2="{fx:.1f}" y2="{fy:.1f}" stroke="{cam["line"]}" stroke-width="2" marker-end="url(#ac)"/>')
L.append(f'  <text x="{fx + 8:.1f}" y="{fy - 8:.1f}" class="m" style="fill:{cam["text"]}">front (camera looks down)</text>')
# projection
pl = fl * math.cos(a)
L.append(f'  <line x1="{fx:.1f}" y1="{fy:.1f}" x2="{fx:.1f}" y2="{EY}" stroke="{mut["line"]}" stroke-width="1" stroke-dasharray="3 3"/>')
L.append(f'  <line x1="{EX}" y1="{EY}" x2="{EX + fl:.1f}" y2="{EY}" stroke="{cam["line"]}" stroke-width="3" marker-end="url(#ac)"/>')
L.append(f'  <text x="{EX + fl + 10:.1f}" y="{EY + 18}" class="m" style="fill:{cam["text"]}">move_front: projected, normalized</text>')
# eye
L.append(f'  <circle cx="{EX}" cy="{EY}" r="7" fill="{cam["line"]}"/>')
L.append(f'  <text x="{EX - 14}" y="{EY - 10}" class="s" text-anchor="end">eye</text>')
L.append(f'  <text x="20" y="250" class="m">move_front = front - dot(front, up) * up, then divided by its norm</text>')
L.append('</svg>')
write_svg(out, L)
