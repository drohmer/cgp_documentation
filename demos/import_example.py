"""Import a CGP example of github.com/drohmer/epita_ani3d_lab_code-2027 (folder examples/) as a
demo folder demos/<name>/, to be built by demos/build.py.

    .venv/bin/python demos/import_example.py examples/02_marching_cubes/02_marching_cube_dynamic marching-cubes-interactive

Copies what differs from the cgp-2027 template project (see README.md, "Content of a demo
folder"): src/ files other than main.cpp, application.* and environment.* when identical to the
template (sub-folders kept), the shaders that differ from the default ones, and assets/
(as they are: reduce the large ones by hand, then note it in origin.txt). Writes origin.txt.
Files are downloaded with `gh api` (public repository, no clone). Refuses to overwrite an
existing demo folder.
"""
import subprocess
import sys
from pathlib import Path

REPO = "drohmer/epita_ani3d_lab_code-2027"
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parents[1] / "cgp-2027"


def gh(*args) -> bytes:
    r = subprocess.run(["gh", "api", *args], capture_output=True, check=True)
    return r.stdout


def main(example: str, name: str) -> int:
    out = HERE / name
    if out.exists():
        print(f"ERROR {out} exists")
        return 1
    tree = gh(f"repos/{REPO}/git/trees/HEAD?recursive=1", "--jq",
              '.tree[] | select(.type=="blob") | .path').decode().split()
    files = [p for p in tree if p.startswith(example + "/")]
    copied, skipped = [], []
    for path in files:
        rel = path[len(example) + 1:]
        top = rel.split("/")[0]
        if top not in ("src", "shaders", "assets"):
            continue
        data = gh(f"repos/{REPO}/contents/{path}", "-H", "Accept: application/vnd.github.raw")
        if top == "src":
            rel = rel[len("src/"):]
            same = TEMPLATE / "src" / rel
            if "/" not in rel and same.exists() and (same.read_bytes() == data or rel in (
                    "main.cpp", "application.cpp", "application.hpp")):
                skipped.append(path)   # template file (application.cpp: the template one has the web fixes)
                continue
        elif top == "shaders":
            same = TEMPLATE / rel
            if same.exists() and same.read_bytes() == data:
                skipped.append(path)
                continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        copied.append((rel, len(data)))
    sha = gh(f"repos/{REPO}/commits/HEAD", "--jq", ".sha").decode().strip()
    (out / "origin.txt").write_text(
        f"Origin: CGP example of github.com/{REPO}\n({example}, commit {sha[:7]}), unchanged.\n",
        encoding="utf-8")
    for rel, size in copied:
        print(f"  {size:9d}  {rel}")
    print(f"{len(copied)} files copied to {out.relative_to(HERE.parent)}, {len(skipped)} identical to the template")
    big = sum(s for r, s in copied if r.startswith("assets/"))
    if big > 3_000_000:
        print(f"WARNING assets: {big / 1e6:.1f} MB (> 3 MB): reduce them, and say how in origin.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]) if len(sys.argv) == 3 else print(__doc__) or 1)
