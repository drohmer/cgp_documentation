"""Capture the 6 cases of the demo visual-diagnostics (index.html#k) into content/assets/diagnostics/.
Run from the root of the repository, after `.venv/bin/python demos/build.py visual-diagnostics`."""
import functools, http.server, socketserver, sys, threading
from pathlib import Path
sys.path.insert(0, "demos")
import build as demo_build
from playwright.sync_api import sync_playwright

ASSETS = Path("content/assets")
OUT = ASSETS / "diagnostics"
OUT.mkdir(exist_ok=True)
NAMES = ["correct", "null-normals", "inverted-normals", "no-uv", "stale-normals", "transparency-order"]

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
httpd = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ASSETS)))
threading.Thread(target=httpd.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{httpd.server_address[1]}"
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    for k, name in enumerate(NAMES):
        page = b.new_page(viewport={"width": 640, "height": 300})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"{base}/visual-diagnostics-demo/index.html#{k}")
        page.wait_for_selector("#status", state="detached", timeout=30000)
        page.wait_for_timeout(2000)
        demo_build.collapse_gui(page)
        page.screenshot(path=str(OUT / f"{name}.png"), clip={"x": 100, "y": 20, "width": 440, "height": 260})
        print(k, name, "errors:", errors)
        page.close()
    b.close()
httpd.shutdown()
