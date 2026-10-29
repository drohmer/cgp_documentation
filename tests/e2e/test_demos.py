#!/usr/bin/env python3
"""
End-to-end tests of the WebGL demos, on both built sites.

For every page of content/ holding `<!-- demo: NAME -->` markers, and every prototype of
tests/e2e/protos.json:
  - the page shows one demo figure per marker;
  - the poster image of the demo (content/assets/NAME-demo/poster.png, if any) is served;
  - a click loads the demo in an iframe, whose CGP program starts (the loading status is
    removed by Module.onRuntimeInitialized) within 40 s, without JavaScript error.
Software WebGL (SwiftShader): no GPU needed. About 5 s per demo and per site.

Usage:  .venv/bin/python tests/e2e/test_demos.py [proto ...]
"""

import functools
import http.server
import json
import re
import socketserver
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTENT = ROOT / "content"
CONFIG = json.load(open(HERE / "protos.json", encoding="utf-8"))
DEMO = re.compile(r"<!--\s*demo:\s*([\w-]+)\s*-->")
# harmless messages: glfwSwapInterval called before the main loop exists (the prebuilt
# `projection` demo, compiled from older sources; the program runs normally)
IGNORED = re.compile(r"emscripten_set_main_loop_timing: Cannot set timing mode")

# how each prototype names a page and shows a demo
SITES = {
    "lhtml": {"url": "/{rel}/index.html", "figure": "figure.demo", "poster": ".demo-poster",
              "poster_url": "/assets/{name}-demo/poster.png"},
    "starlight": {"url": "/{rel}/", "figure": ".cgp-demo", "poster": ".cgp-demo__poster",
                  "poster_url": "/demos/{name}/poster.png"},
}


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def pages_with_demos():
    out = []
    for md in sorted(CONTENT.rglob("*.md")):
        names = DEMO.findall(md.read_text(encoding="utf-8"))
        if names:
            out.append((md.relative_to(CONTENT).as_posix()[:-3], names))
    return out


def run_site(name, browser, pages, problems):
    site = SITES[name]
    handler = functools.partial(Quiet, directory=str(ROOT / CONFIG[name]["dist"]))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        for rel, names in pages:
            for k, demo in enumerate(names):
                ctx = browser.new_context(viewport={"width": 1300, "height": 900})
                page = ctx.new_page()
                errors = []
                page.on("console", lambda m: m.type == "error" and errors.append(m.text))
                page.on("pageerror", lambda e: errors.append(str(e)))
                t0 = time.time()
                page.goto(base + site["url"].format(rel=rel), wait_until="networkidle")
                figs = page.locator(site["figure"])
                status = []
                if figs.count() != len(names):
                    status.append(f"{figs.count()} demo figure(s) for {len(names)} marker(s)")
                if (CONTENT / "assets" / f"{demo}-demo" / "poster.png").exists():
                    r = page.request.get(base + site["poster_url"].format(name=demo))
                    if r.status != 200:
                        status.append(f"poster HTTP {r.status}")
                if figs.count() > k:
                    figs.nth(k).locator(site["poster"]).click()
                    try:
                        frame_el = figs.nth(k).locator("iframe")
                        frame_el.wait_for(timeout=5000)
                        frame = frame_el.content_frame
                        # demos/index.html removes #status when the runtime is initialized;
                        # the older demos (no #status) only need a canvas
                        frame.locator("canvas").wait_for(timeout=10000)
                        if frame.locator("#status").count():
                            frame.locator("#status").wait_for(state="detached", timeout=40000)
                        page.wait_for_timeout(1500)
                    except Exception as e:
                        status.append(f"not started: {type(e).__name__}")
                status += [f"JS error: {e[:120]}" for e in errors if not IGNORED.search(e)]
                verdict = "ok" if not status else "KO " + "; ".join(status)
                print(f"  {rel:45} {demo:28} {time.time() - t0:5.1f}s {verdict}", flush=True)
                if status:
                    problems.append(f"{name} {rel} {demo}: {'; '.join(status)}")
                ctx.close()
    finally:
        httpd.shutdown()


def main():
    names = sys.argv[1:] or list(SITES)
    pages = pages_with_demos()
    print(f"{sum(len(n) for _, n in pages)} demo marker(s) in {len(pages)} page(s)")
    problems = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        for n in names:
            print(f"== {n}", flush=True)
            run_site(n, browser, pages, problems)
        browser.close()
    print(f"\n{len(problems)} problem(s)")
    for pb in problems:
        print("  " + pb)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
