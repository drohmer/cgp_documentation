"""multipass-passes.svg: the passes of the multipass_structure of the examples image-filter,
image-filter-effects (scene -> fbo_pass_1 -> quad_pass_2 -> window) and image-filters-chain
(... quad_pass_2 -> fbo_pass_2 -> quad_pass_3 -> window).
Usage: python multipass-passes.py OUT.svg"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from palette import P as PAL, write_svg  # noqa: E402
out = sys.argv[1]
code, gpu, fixed, muted = PAL['code'], PAL['gpu'], PAL['fixed'], PAL['muted']

W, BW, BH = 700, 140, 104
COL = [20, 195, 370, 545]
YA, YB = 70, 262          # top of lane A (all examples) and lane B (chain only)

L = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 450" width="{W}" height="450">
  <style>
    text {{ font-family: Helvetica, Arial, sans-serif; font-size: 13px; fill: #333333; }}
    .t {{ font-weight: bold; font-size: 14px; }}
    .h {{ font-weight: bold; font-size: 14px; fill: {muted['text']}; }}
    .m {{ font-family: Menlo, Consolas, monospace; font-size: 12px; fill: #333333; }}
    .s {{ font-size: 12px; fill: {muted['text']}; }}
  </style>
  <defs>
    <marker id="ag" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{gpu['line']}"/></marker>
    <marker id="ak" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#555555"/></marker>
  </defs>''']


def box(x, y, c, title, lines, mono_title=True):
    L.append(f'  <rect x="{x}" y="{y}" width="{BW}" height="{BH}" rx="6" fill="{c["fill"]}" stroke="{c["stroke"]}" stroke-width="1.5"/>')
    cls = 'm t' if mono_title else 't'
    L.append(f'  <text x="{x + 10}" y="{y + 22}" class="{cls}" style="fill:{c["text"]}">{title}</text>')
    for k, (txt, cl) in enumerate(lines):
        L.append(f'  <text x="{x + 10}" y="{y + 46 + 19 * k}" class="{cl}">{txt}</text>')


def arrow(x1, y1, x2, y2, color='#555555', mk='ak'):
    L.append(f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2" marker-end="url(#{mk})"/>')


# headers of the passes
L.append(f'  <text x="{COL[0]}" y="{YA - 14}" class="h">pass 1</text>')
L.append(f'  <text x="{COL[2]}" y="{YA - 14}" class="h">pass 2</text>')
L.append(f'  <text x="{COL[3]}" y="{YB - 14}" class="h">pass 3 (chain only)</text>')

# lane A
box(COL[0], YA, code, 'the scene', [('draw(shape, ...)', 'm'), ('for every shape,', 's'), ('usual shaders', 's')], False)
box(COL[1], YA, gpu, 'fbo_pass_1', [('color texture', ''), ('+ depth buffer', '')])
box(COL[2], YA, code, 'quad_pass_2', [('full-screen quad', ''), ('shader of pass 2:', 's'), ('filter 1', 's')])
box(COL[3], YA, fixed, 'window', [('the image seen', ''), ('on screen', '')], False)
# lane B
box(COL[2], YB, gpu, 'fbo_pass_2', [('color texture', ''), ('+ depth buffer', '')])
box(COL[3], YB, code, 'quad_pass_3', [('full-screen quad', ''), ('shader of pass 3:', 's'), ('filter 2', 's')])

ym = YA + BH // 2
# draw into (orange): the output goes into a texture
arrow(COL[0] + BW, ym, COL[1] - 4, ym, gpu['line'], 'ag')
L.append(f'  <text x="{COL[0] + BW + 17}" y="{ym - 8}" class="s" text-anchor="middle">into</text>')
# texture read (dark): the texture is the input of the quad
arrow(COL[1] + BW, ym, COL[2] - 4, ym)
L.append(f'  <text x="{COL[1] + BW + 17}" y="{ym - 8}" class="s" text-anchor="middle">read</text>')
# quad_pass_2 -> window (one filter)
arrow(COL[2] + BW, ym, COL[3] - 4, ym)
# quad_pass_2 -> fbo_pass_2 (chain)
xm = COL[2] + BW // 2
arrow(xm, YA + BH, xm, YB - 4, gpu['line'], 'ag')
L.append(f'  <text x="{xm + 8}" y="{(YA + BH + YB) // 2 + 4}" class="s">into (chain)</text>')
# fbo_pass_2 -> quad_pass_3 -> window
ymb = YB + BH // 2
arrow(COL[2] + BW, ymb, COL[3] - 4, ymb)
L.append(f'  <text x="{COL[2] + BW + 17}" y="{ymb - 8}" class="s" text-anchor="middle">read</text>')
xw = COL[3] + BW // 2
arrow(xw, YB, xw, YA + BH + 4)

# explanation
ty = YB + BH + 40
L.append(f'  <text x="{COL[0]}" y="{ty}">image-filter, image-filter-effects: quad_pass_2 is drawn to the window (two passes).</text>')
L.append(f'  <text x="{COL[0]}" y="{ty + 20}">image-filters-chain: quad_pass_2 is drawn into fbo_pass_2, then quad_pass_3 to the window.</text>')
L.append(f'  <text x="{COL[0]}" y="{ty + 40}" class="s">Orange arrow: draw into the texture of an FBO. Dark arrow: the next quad reads this texture.</text>')

# lane B legend on the left: what the chain adds
L.append(f'  <text x="{COL[0]}" y="{YB + 30}" class="s">The chain inserts a second</text>')
L.append(f'  <text x="{COL[0]}" y="{YB + 48}" class="s">FBO and a third quad between</text>')
L.append(f'  <text x="{COL[0]}" y="{YB + 66}" class="s">the first filter and the window.</text>')
L.append('</svg>')
write_svg(out, L)
