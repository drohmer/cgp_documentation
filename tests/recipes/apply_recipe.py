"""Apply the C++ snippets of a how-to page literally to a copy of the CGP template.

Each ```cpp block of the page is split on header comments of the form
    // scene.hpp - <action>
    // scene.cpp - <action>
and every segment is applied according to its action. Segments without such a header
(signatures, excerpts, variations) are ignored. Usage:
    python apply_recipe.py PAGE.md PROJECT_DIR [--skip N,M] [--only N,M]
N = index of the segment (0-based, in page order), printed by the script.
"""
import re
import sys
from pathlib import Path

HEADER = re.compile(r'^// (scene\.hpp|scene\.cpp) - (.+?)\s*$')


def segments(md):
    out = []
    for block in re.findall(r'```cpp\n(.*?)```', md, flags=re.S):
        cur = None
        for line in block.splitlines():
            m = HEADER.match(line)
            if m:
                cur = [m.group(1), m.group(2), []]
                out.append(cur)
            elif cur is not None:
                cur[2].append(line)
    return [(f, a, '\n'.join(lines).strip('\n') + '\n') for f, a, lines in out]


def insert_before(text, anchor, code):
    i = text.index(anchor)
    i = text.rfind('\n', 0, i) + 1
    return text[:i] + code + '\n' + text[i:]


def insert_after_line(text, anchor, code):
    i = text.index(anchor)
    j = text.index('\n', i) + 1
    return text[:j] + code + text[j:]


def replace_function(text, name, code):
    start = text.index(f'void scene_structure::{name}()')
    end = text.index('\n}', start) + 2
    return text[:start] + code.rstrip('\n') + text[end:]


def replace_struct(text, name, code):
    start = text.index(f'struct {name} {{')
    end = text.index('\n};', start) + 3
    return text[:start] + code.rstrip('\n') + text[end:]


def apply(seg, hpp, cpp):
    f, action, code = seg
    a = action.lower()
    if 'already in the template' in a:
        norm = lambda x: re.sub(r'\s+', '', re.sub(r'//.*|/\*.*?\*/', '', x))
        target = norm(hpp if f == 'scene.hpp' else cpp)
        for line in code.splitlines():
            if norm(line) and norm(line) not in target:
                print(f'    WARNING: not in the template: {line.strip()}')
        return hpp, cpp
    if f == 'scene.hpp':
        if a == 'add in scene_structure':
            hpp = insert_after_line(hpp, 'mesh_drawable global_frame;', code)
        elif a == 'add in gui_parameters':
            hpp = insert_after_line(hpp, 'bool display_frame = false;', code)
        elif a == 'add before scene_structure':
            hpp = insert_before(hpp, '// The structure of the custom scene', code)
        elif a == 'replace gui_parameters':
            hpp = replace_struct(hpp, 'gui_parameters', code)
        elif a.startswith('replace the line '):
            old = re.search(r'`([^`]+)`', action).group(1)
            assert old in hpp, old
            hpp = hpp.replace(old, code.strip(), 1)
        else:
            raise ValueError(f'unknown action {action!r}')
    else:
        m = re.match(r'replace (\w+)\(\)$', a)
        if a == 'add before initialize()':
            cpp = insert_before(cpp, '// Main initialization function', code)
        elif a == 'replace the camera_control.look_at call in initialize()':
            cpp, n = re.subn(r'camera_control\.look_at\(.*?\);', lambda _: code.strip(), cpp, count=1, flags=re.S)
            assert n == 1
        elif a.startswith('add at the end of initialize()') or a.startswith('in initialize(), instead of'):
            cpp = insert_before(cpp, 'std::cout << "End function scene_structure::initialize()"', code)
        elif a == 'add in display_frame(), before timer.update()':
            start = cpp.index('void scene_structure::display_frame()')
            end = cpp.index('\n}', start)
            i = cpp.rindex('timer.update();', start, end)
            i = cpp.rfind('\n', 0, i) + 1
            cpp = cpp[:i] + code + '\n' + cpp[i:]
        elif a == 'add in display_gui()':
            cpp = insert_after_line(cpp, 'ImGui::Checkbox("Frame", &gui.display_frame);', code)
        elif a == 'add at the end of the file':
            cpp = cpp.rstrip('\n') + '\n\n' + code
        elif m:
            cpp = replace_function(cpp, m.group(1), code)
        else:
            raise ValueError(f'unknown action {action!r}')
    return hpp, cpp


def main():
    page, proj = Path(sys.argv[1]), Path(sys.argv[2])
    skip, only = set(), None
    args = sys.argv[3:]
    for k in range(0, len(args), 2):
        ids = {int(x) for x in args[k + 1].split(',')}
        if args[k] == '--skip':
            skip = ids
        elif args[k] == '--only':
            only = ids
    hpp_p, cpp_p = proj / 'src/scene.hpp', proj / 'src/scene.cpp'
    hpp, cpp = hpp_p.read_text(), cpp_p.read_text()
    for k, seg in enumerate(segments(page.read_text())):
        used = k not in skip and (only is None or k in only)
        print(f'  [{k}] {"apply" if used else "skip "} {seg[0]} - {seg[1]}')
        if used:
            hpp, cpp = apply(seg, hpp, cpp)
    hpp_p.write_text(hpp)
    cpp_p.write_text(cpp)


if __name__ == '__main__':
    main()
