#!/usr/bin/env python3
"""
Build the WebGL demos (demos/<name>/) with Emscripten, then capture a poster image of each.

Output: content/assets/<name>-demo/ (index.html, project.js/.wasm/.data, poster.png).
Progress is printed and written to build/demos/build.log (CGP_DEMO_BUILD_DIR to use another
build directory, e.g. one per parallel worker).

Usage:  .venv/bin/python demos/build.py [name ...]          (default: every demo)
        .venv/bin/python demos/build.py --no-poster [name ...]
        .venv/bin/python demos/build.py --poster-only [name ...]   (no compilation, ~4 s each)
Needs:  the Emscripten SDK (emcmake on the PATH, or ~/emsdk), and Playwright for the posters.
"""

import functools
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BUILD = Path(os.environ.get("CGP_DEMO_BUILD_DIR", ROOT / "build" / "demos"))   # one per parallel worker
ASSETS = ROOT / "content" / "assets"
LOG = BUILD / "build.log"


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def emsdk_env():
    env = dict(os.environ)
    if shutil.which("emcmake"):
        return env
    emsdk = Path.home() / "emsdk"
    paths = [emsdk / "upstream" / "emscripten", emsdk]
    env["PATH"] = os.pathsep.join(str(p) for p in paths) + os.pathsep + env["PATH"]
    if not shutil.which("emcmake", path=env["PATH"]):
        sys.exit("emcmake not found: activate the Emscripten SDK (source ~/emsdk/emsdk_env.sh)")
    return env


def run(cmd, env):
    log("$ " + " ".join(cmd))
    with open(LOG, "a", encoding="utf-8") as fh:
        p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in p.stdout:
            fh.write(line)
            if line.startswith("[") and "%]" in line[:7]:      # cmake progress "[ 42%] ..."
                print("  " + line.rstrip()[:110], flush=True)
            elif "error" in line.lower():
                print("  " + line.rstrip(), flush=True)
        if p.wait() != 0:
            log(f"FAILED ({p.returncode}), see {LOG}")
            sys.exit(p.returncode)


def demo_names():
    return sorted(d.name for d in HERE.iterdir() if (d / "scene.cpp").exists())


# The CGP window "GUI" (cgp-2027/src/application.cpp: ImGui::Begin("GUI", ...), no position
# given) opens at the ImGui default position (60, 60) in CSS pixels; its collapse arrow is the
# first thing of its title bar, about 12 px right and 9 px below that corner (font scale 1).
GUI_COLLAPSE_ARROW = (72, 69)
GUI_PANEL_PROBE = (66, 96, 230, 140)   # box inside the open panel (fps text line and below)


def _panel_share(page, box):
    """Share of the pixels of box that look like the ImGui panel (dark grey, low saturation).
    The WebGL canvas cannot be read back: a screenshot of the box is decoded in the page."""
    import base64
    x0, y0, x1, y1 = box
    png = page.screenshot(clip={"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0})
    return page.evaluate("""async (b64) => {
        const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
        const c = new OffscreenCanvas(img.width, img.height), g = c.getContext('2d');
        g.drawImage(img, 0, 0);
        const d = g.getImageData(0, 0, img.width, img.height).data;
        let dark = 0;
        for (let i = 0; i < d.length; i += 4) {
            const mx = Math.max(d[i], d[i + 1], d[i + 2]), mn = Math.min(d[i], d[i + 1], d[i + 2]);
            if (mx < 70 && mx - mn < 14) dark++;
        }
        return dark / (d.length / 4);
    }""", base64.b64encode(png).decode())


def collapse_gui(page):
    """Collapse the ImGui window before the poster is taken, so that the scene is not hidden
    behind the sliders (illustration review C11). A real click on the collapse arrow: the mouse
    is moved first so that ImGui sees it over the arrow on the next frames, then pressed and
    released a few frames apart. Returns (share of panel pixels before, after) for the log."""
    before = _panel_share(page, GUI_PANEL_PROBE)
    x, y = GUI_COLLAPSE_ARROW
    page.mouse.move(x, y)
    page.wait_for_timeout(200)
    page.mouse.down()
    page.wait_for_timeout(120)
    page.mouse.up()
    page.wait_for_timeout(200)
    # then drag the collapsed title bar to the bottom-right corner: ImGui clamps it there with
    # only about 19 x 19 px visible, under the dark gradient of the poster in the pages
    page.mouse.move(x + 18, y)
    page.wait_for_timeout(100)
    page.mouse.down()
    vw, vh = page.viewport_size["width"], page.viewport_size["height"]
    for k in range(1, 11):
        page.mouse.move(x + 18 + (vw - 2 - x - 18) * k / 10, y + (vh - 2 - y) * k / 10)
        page.wait_for_timeout(60)
    page.mouse.up()
    page.mouse.move(vw / 2, vh - 2)      # no hover highlight left on the title bar
    page.wait_for_timeout(500)
    after = _panel_share(page, GUI_PANEL_PROBE)
    return before, after


def capture_posters(names):
    """Run each demo in headless Chromium (software WebGL) and save poster.png."""
    from playwright.sync_api import sync_playwright

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(Quiet, directory=str(ASSETS))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    failed = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        for name in names:
            page = browser.new_page(viewport={"width": 800, "height": 500})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: m.type == "error" and errors.append(m.text))
            page.goto(f"{base}/{name}-demo/index.html")
            try:
                page.wait_for_selector("#status", state="detached", timeout=30000)
            except Exception:
                errors.append("runtime not initialized after 30 s")
            page.wait_for_timeout(2500)     # let a few frames run (animations)
            before, after = collapse_gui(page)
            gui = f"  GUI panel pixels {before:.0%} -> {after:.0%}"
            if after > 0.5:
                gui += "  WARNING: the GUI panel looks still open"
            out = ASSETS / f"{name}-demo" / "poster.png"
            fixed = HERE / name / "poster.png"     # a scene that shows nothing before interaction
            if fixed.exists():                     # (sketching) keeps a poster captured by hand
                shutil.copyfile(fixed, out)
            else:
                page.screenshot(path=str(out))
            log(f"poster {name}: {out.relative_to(ROOT)}{gui}" + (f"  ERRORS: {errors[:3]}" if errors else ""))
            if errors:
                failed.append(name)
            page.close()
        browser.close()
    httpd.shutdown()
    return failed


def main():
    args = sys.argv[1:]
    poster = "--no-poster" not in args
    names = [a for a in args if not a.startswith("--")] or demo_names()
    # --poster-only also accepts a demo built elsewhere (content/assets/projection-demo/)
    unknown = set(names) - set(demo_names()) - (
        {n for n in names if (ASSETS / f"{n}-demo" / "project.wasm").exists()} if "--poster-only" in args else set())
    if unknown:
        sys.exit(f"unknown demo(s): {sorted(unknown)}")
    BUILD.mkdir(parents=True, exist_ok=True)
    LOG.write_text("", encoding="utf-8")
    t0 = time.time()
    if "--poster-only" in args:     # demos already built in content/assets/<name>-demo/
        missing = [n for n in names if not (ASSETS / f"{n}-demo" / "project.wasm").exists()]
        if missing:
            sys.exit(f"not built yet (run without --poster-only): {missing}")
        log(f"posters only: {', '.join(names)}")
        failed = capture_posters(names)
        log(f"done in {time.time() - t0:.0f} s" + (f"; demos with errors: {failed}" if failed else ""))
        sys.exit(1 if failed else 0)
    env = emsdk_env()
    # The demo of a how-to page runs the code of the page: its scene is regenerated from the
    #  template and the page (tests/recipes/run_recipes.py), only assets/ and shaders/ are its own.
    sys.path.insert(0, str(ROOT / "tests" / "recipes"))
    import run_recipes
    generated = [n for n in names if n in run_recipes.recipes()]
    for n in generated:
        run_recipes.write_demo_scene(n, HERE / n)
    log(f"scenes generated from their page: {', '.join(generated) or 'none'}")
    log(f"building {len(names)} demo(s): {', '.join(names)}")
    run(["emcmake", "cmake", "-S", str(HERE), "-B", str(BUILD), "-DCMAKE_BUILD_TYPE=Release",
         f"-DDEMO_LIST={';'.join(names)}"], env)
    run(["cmake", "--build", str(BUILD), "-j", str(os.cpu_count() or 4)], env)
    for n in names:
        size = sum(f.stat().st_size for f in (ASSETS / f"{n}-demo").glob("project.*"))
        log(f"built {n}-demo ({size / 1e6:.1f} MB)")
    failed = capture_posters(names) if poster else []
    log(f"done in {time.time() - t0:.0f} s" + (f"; demos with errors: {failed}" if failed else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
