"""Subset the monospace font of the docs theme (Source Code Pro) to the characters the
documentation uses, into the CGP overlay of the theme (theme/fonts/...), which replaces the
full fonts of lhtml-site when build.py assembles _build/theme.

Each full weight is about 70 KB; the subset keeps Basic Latin, Latin-1 and a few
typographic signs (the files of content/ are ASCII, accents allowed): about 15 KB. A
character outside the subset falls back to the monospace font of the system.

Only the faces that the pages use (font.css: 400, 600, 700 -> Regular, Semibold, Bold, and the
italic of 400, It) are written. Run it again after an update of the fonts of lhtml-site:

    .venv/bin/pip install fonttools brotli      # only to run this script
    .venv/bin/python renderers/lhtml/scripts/subset_fonts.py
"""
from pathlib import Path

import lhtml_site
from fontTools import subset

HERE = Path(__file__).resolve().parents[1]
SOURCE = Path(lhtml_site.__file__).parent / 'themes' / 'docs' / 'fonts' / 'source_code_pro' / 'WOFF2' / 'TTF'
OUT = HERE / 'theme' / 'fonts' / 'source_code_pro' / 'WOFF2' / 'TTF'
FILES = ['SourceCodePro-Regular.ttf.woff2', 'SourceCodePro-Semibold.ttf.woff2', 'SourceCodePro-Bold.ttf.woff2',
         'SourceCodePro-It.ttf.woff2']
# Basic Latin, Latin-1, dashes, quotes, ellipsis, bullet, arrows, math signs of the pages
UNICODES = 'U+0020-007E,U+00A0-00FF,U+2013-2014,U+2018-201D,U+2022,U+2026,U+2190-2193,U+2212,U+2264-2265,U+00D7'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src, dst = SOURCE / name, OUT / name
        subset.main([str(src), f'--unicodes={UNICODES}', '--flavor=woff2', '--layout-features=*', '--drop-tables+=SVG',
                     f'--output-file={dst}'])
        print(f'{name}: {src.stat().st_size // 1024} KB -> {dst.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()
