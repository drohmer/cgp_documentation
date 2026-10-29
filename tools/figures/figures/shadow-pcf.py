"""shadow-pcf.svg: the 5 x 5 samples of the shadow map read by ShadowCalculation (example
shadow-mapping), half a texel apart, and the fraction of them in shadow.
Usage: python shadow-pcf.py OUT.svg"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
cpu, gpu = PAL['cpu'], PAL['gpu']

T, X0, Y0 = 60, 40, 60          # texel size in px, origin of the 4 x 4 texels
L = ['''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 340" width="700" height="340">
  <style>
    text { font-family: Helvetica, Arial, sans-serif; font-size: 15px; fill: #666666; }
    .in { fill: #333; font-size: 14px; }
    .b { font-weight: bold; }
    .m { font-family: Menlo, Consolas, monospace; font-size: 13px; fill: #333; }
  </style>
  <text x="20" y="28" class="b in">Texels of the shadow map around the pixel</text>''']
# texels: the right column is "closer to the light" (an occluder): darker
for j in range(4):
    for i in range(4):
        occl = i >= 2
        L.append(f'  <rect x="{X0 + i * T}" y="{Y0 + j * T}" width="{T}" height="{T}" '
                 f'fill="{"#bdbdbd" if occl else "#f4f4f4"}" stroke="#999999"/>')
L.append(f'  <text x="{X0 + 3 * T}" y="{Y0 + 4 * T + 22}" class="in" text-anchor="middle">occluder in front</text>')
L.append(f'  <text x="{X0 + T}" y="{Y0 + 4 * T + 22}" class="in" text-anchor="middle">nothing in front</text>')
# the pixel projected at the center, samples at 0.5 * (x, y) texel, x, y in -2..2
cx, cy = X0 + 2 * T - 6, Y0 + 2 * T
shadowed = 0
for y in range(-2, 3):
    for x in range(-2, 3):
        sx, sy = cx + 0.5 * x * T, cy + 0.5 * y * T
        s = sx >= X0 + 2 * T
        shadowed += s
        L.append(f'  <circle cx="{sx:.1f}" cy="{sy:.1f}" r="5" fill="{gpu["line"] if s else "#ffffff"}" '
                 f'stroke="{gpu["line"]}" stroke-width="1.5"/>')
L.append(f'  <rect x="{cx - T - 8}" y="{cy - T - 8}" width="{2 * T + 16}" height="{2 * T + 16}" fill="none" '
         f'stroke="{cpu["line"]}" stroke-width="2" stroke-dasharray="6 4"/>')
# right: legend and result
x0 = 340
L.append(f'  <text x="{x0}" y="90" class="in">25 samples, half a texel apart:</text>')
L.append(f'  <text x="{x0}" y="112" class="m">projCoords.xy + 0.5*vec2(x, y)*texelSize</text>')
L.append(f'  <text x="{x0}" y="134" class="m">x, y = -2 .. 2</text>')
L.append(f'  <circle cx="{x0 + 6}" cy="166" r="5" fill="{gpu["line"]}"/><text x="{x0 + 20}" y="171" class="in">depth of the pixel - bias &gt; depth stored: in shadow</text>')
L.append(f'  <circle cx="{x0 + 6}" cy="192" r="5" fill="#fff" stroke="{gpu["line"]}" stroke-width="1.5"/><text x="{x0 + 20}" y="197" class="in">lit</text>')
L.append(f'  <text x="{x0}" y="236" class="in">shadow = {shadowed} / 25 = {shadowed / 25:.2f}: the diffuse and specular</text>')
L.append(f'  <text x="{x0}" y="256" class="in">terms are multiplied by 1 - shadow. Near the border of</text>')
L.append(f'  <text x="{x0}" y="276" class="in">a shadow the fraction goes from 0 to 1 over about two</text>')
L.append(f'  <text x="{x0}" y="296" class="in">texels: a soft edge instead of a staircase.</text>')
L.append('</svg>')
write_svg(out, L)
