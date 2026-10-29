"""Shared color palette of the CGP documentation figures.

The meaning of each color and the contrast checks are in tools/figures/README.md.
Every concept has up to four values:
  fill   light tint for the background of a box,
  inner  lighter tint for a box nested in a filled box (GPU buffers only),
  stroke border of a box,
  line   arrows, curves, markers, dots (>= 3:1 on white),
  text   labels and titles in that color (>= 4.5:1 on white and on the fill).

Usage from a generator in figures/ or primitives/:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from palette import P
    P['cpu']['text']
"""

P = {
    # memory and processors
    'cpu':     dict(fill='#e3eefb', stroke='#6b9bd8', line='#4a86d0', text='#2b66ad'),
    'gpu':     dict(fill='#fdebd6', inner='#fff7ec', stroke='#e0912f', line='#e07b1a', text='#a85000'),
    # data sent to the shaders
    'uniform': dict(fill='#eee5f8', stroke='#9c6ade', line='#9c6ade', text='#7b48c4'),
    'vbo':     dict(fill='#fff7ec', stroke='#e0912f', line='#e07b1a', text='#a85000'),  # = GPU buffer
    # stages and code
    'code':    dict(fill='#dff0dc', stroke='#5aa55a', line='#5aa55a', text='#2a7330'),  # shaders, your scene
    'fixed':   dict(fill='#ececec', stroke='#999999', line='#999999', text='#333333'),  # fixed function, library
    # coordinate spaces and the matrices that lead to them
    'local':   dict(fill='#f4f9cf', stroke='#a8b04a', line='#a8b04a', text='#6f6400'),  # M
    'world':   dict(fill='#ececec', stroke='#999999', line='#999999', text='#333333'),
    'camera':  dict(fill='#dcf1f3', stroke='#3a9aa5', line='#2a8f99', text='#1a6b73'),  # V, camera frame
    'clip':    dict(fill='#fbe4ec', stroke='#c9567f', line='#c9567f', text='#a3305e'),  # P, clip, NDC
    # axes
    'x':       dict(fill='#fbe3e1', line='#d0605a', text='#b3261e'),
    'y':       dict(fill='#dff0dc', line='#5aa55a', text='#2a7330'),
    'z':       dict(fill='#e3eefb', line='#4a86d0', text='#2b66ad'),
    # events and states
    'input':   dict(fill='#fce4ee', line='#d6407a', text='#c2185b'),  # mouse, keyboard
    'error':   dict(fill='#fbe3e1', line='#d9534f', text='#b3261e'),  # warning, forbidden path
    'light':   dict(fill='#fdf3dc', line='#e0a030', text='#8a5a00'),  # light source
    # neutrals
    'ink':     dict(text='#333333'),
    'muted':   dict(text='#666666', line='#888888'),  # secondary text / guide lines
}

# Older mid tones used as text color -> text tone of the same concept.
# Used by recolor.py on the hand-drawn SVGs (text elements and text-only CSS rules only).
TEXT_MAP = {
    '#4a86d0': P['cpu']['text'], '#6b9bd8': P['cpu']['text'], '#4a90c2': P['cpu']['text'],
    '#4a90d9': P['cpu']['text'],
    '#e07b1a': P['gpu']['text'], '#e0912f': P['gpu']['text'], '#d9822b': P['gpu']['text'],
    '#c8650f': P['gpu']['text'], '#efa760': P['gpu']['text'], '#e0823d': P['gpu']['text'],
    '#9c6ade': P['uniform']['text'],
    '#43a047': P['code']['text'], '#5aa55a': P['code']['text'], '#4caf50': P['code']['text'],
    '#2e7d32': P['code']['text'], '#5a9a4a': P['code']['text'],
    '#d0605a': P['error']['text'], '#d9534f': P['error']['text'], '#e05050': P['error']['text'],
    '#c0504d': P['error']['text'], '#e03030': P['error']['text'],
    '#888': P['muted']['text'], '#888888': P['muted']['text'], '#8a8a8a': P['muted']['text'],
    '#999': P['muted']['text'], '#999999': P['muted']['text'], '#9a9a9a': P['muted']['text'],
    '#aaa': P['muted']['text'], '#aaaaaa': P['muted']['text'], '#808080': P['muted']['text'],
    '#777': P['muted']['text'],
    '#b0951c': P['local']['text'], '#a8b04a': P['local']['text'],
    '#2a8f99': P['camera']['text'],
    '#e0a030': P['light']['text'], '#c07a10': P['light']['text'],
}

# Near-duplicate line colors of the hand-drawn plots -> palette line color (everywhere).
LINE_MAP = {
    '#4a90c2': P['cpu']['line'],
    '#d9822b': P['gpu']['line'],
    '#8a8a8a': P['muted']['line'],
    '#808080': P['muted']['line'],
    '#43a047': P['code']['line'],
}


def write_svg(path, lines):
    """Join the lines of a generated SVG, pass the text colors through TEXT_MAP, write it."""
    from recolor import recolor
    svg, warnings = recolor('\n'.join(lines) + '\n')
    for w in warnings:
        print(f'{path}: warning: {w}')
    open(path, 'w').write(svg)
