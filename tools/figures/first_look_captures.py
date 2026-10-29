"""Capture the images of the three snippets of the home page (section "A first look") from the
demo first-look (index.html#k shows snippet k) into content/assets/first-look/.
Run from the root of the repository, after `.venv/bin/python demos/build.py first-look`."""
import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

sys.path.insert(0, "demos")
import build as demo_build  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ASSETS = Path("content/assets")
OUT = ASSETS / "first-look"
NAMES = ["shapes", "cube", "terrain"]
VIEW = {"width": 520, "height": 440}
CLIP = {"x": 40, "y": 30, "width": 440, "height": 380}   # the GUI, collapsed, stays out of it


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    OUT.mkdir(exist_ok=True)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ASSETS)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        for k, name in enumerate(NAMES):
            page = browser.new_page(viewport=VIEW)
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{base}/first-look-demo/index.html#{k}")
            page.wait_for_selector("#status", state="detached", timeout=30000)
            page.wait_for_timeout(2000)
            demo_build.collapse_gui(page)
            page.screenshot(path=str(OUT / f"{name}.png"), clip=CLIP)
            print(name, "errors:", errors)
            page.close()
        browser.close()
    httpd.shutdown()


if __name__ == "__main__":
    main()
