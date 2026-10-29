"""Self-check of the Starlight prototype: screenshots + filter + search.
Usage: ROOT/.venv/bin/python tests/check.py [base_url]   (dist/ must be served, e.g. port 4391)
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:4391"
SHOTS = Path(__file__).resolve().parent.parent / "shots"
SHOTS.mkdir(exist_ok=True)
PAGES = {
    "home": "/",
    "camera": "/understand/camera-and-matrices/",
    "howto": "/how-to/draw-a-mesh/",
    "vec3": "/reference/vec3/",
}
SEARCH_BTN = "site-search button[data-open-modal]"
SEARCH_INPUT = "#starlight__search input.pagefind-ui__search-input"
ok = True


def check(cond, msg):
    global ok
    print(("PASS " if cond else "FAIL ") + msg)
    ok = ok and cond


with sync_playwright() as p:
    b = p.chromium.launch()
    for mode, kw in {
        "light": dict(viewport={"width": 1400, "height": 900}, color_scheme="light"),
        "dark": dict(viewport={"width": 1400, "height": 900}, color_scheme="dark"),
        "mobile": dict(viewport={"width": 390, "height": 844}, color_scheme="light", device_scale_factor=2, is_mobile=True, has_touch=True),
    }.items():
        ctx = b.new_context(**kw)
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        for name, url in PAGES.items():
            page.goto(BASE + url, wait_until="networkidle")
            # trigger lazy-loaded images before the full-page capture
            page.evaluate("async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 30)); } window.scrollTo(0, 0); }")
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(SHOTS / f"{name}-{mode}.png"), full_page=(name != "vec3"))
            if name == "vec3":
                page.screenshot(path=str(SHOTS / f"{name}-{mode}-full.png"), full_page=True)
                page.evaluate("document.getElementById('takes-transform').scrollIntoView()")
                page.screenshot(path=str(SHOTS / f"{name}-{mode}-fns.png"))
                page.evaluate("window.scrollTo(0,0)")
            sw = page.evaluate("document.documentElement.scrollWidth")
            check(sw <= kw["viewport"]["width"], f"{mode} {name}: no horizontal scroll (scrollWidth={sw})")
        check(not errors, f"{mode}: no JS errors {errors[:2]}")
        ctx.close()

    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()
    page.goto(BASE + "/reference/vec3/", wait_until="networkidle")
    total = page.locator(".fn-entry").count()
    page.fill("#fn-filter", "cross")
    visible = page.locator(".fn-entry:visible").count()
    names = page.eval_on_selector_all(".fn-entry:visible", "els => els.map(e => e.dataset.name)")
    check(0 < visible < total and "cross" in names, f"filter 'cross': {visible}/{total} visible {names}")
    hidden_groups = page.locator(".fn-group[hidden]").count()
    check(hidden_groups > 0, f"filter hides empty groups ({hidden_groups} hidden)")
    page.screenshot(path=str(SHOTS / "vec3-filter.png"))
    page.fill("#fn-filter", "")
    check(page.locator(".fn-entry:visible").count() == page.locator(".fn-list:visible .fn-entry").count(), "filter reset")

    for q, expect in [("norm", "/reference/vec3/"), ("cross", "/reference/vec3/"), ("uniform", "/understand/camera-and-matrices/"), ("perspective", "/understand/camera-and-matrices/")]:
        page.goto(BASE + "/", wait_until="networkidle")
        page.click(SEARCH_BTN)
        page.fill(SEARCH_INPUT, q)
        page.wait_for_selector(".pagefind-ui__result", timeout=8000)
        page.wait_for_timeout(600)
        links = page.eval_on_selector_all(".pagefind-ui__result a", "els => els.map(e => e.getAttribute('href'))")
        check(any(l.startswith(expect) for l in links), f"search '{q}' -> {links[:6]}")
        if q == "norm":
            page.screenshot(path=str(SHOTS / "search-norm.png"))

    # Deep link from search lands on the entry
    page.goto(BASE + "/reference/vec3/#fn-cross--vec3-const-vec3-const", wait_until="networkidle")
    check(page.locator("#fn-cross--vec3-const-vec3-const").is_visible(), "deep link anchor visible")

    # Demo is lazy: no iframe before click, iframe after
    page.goto(BASE + "/understand/camera-and-matrices/", wait_until="networkidle")
    check(page.locator(".cgp-demo iframe").count() == 0, "demo not loaded on page load")
    page.click(".cgp-demo__poster")
    page.wait_for_timeout(4000)
    check(page.locator(".cgp-demo iframe").count() == 1, "demo iframe after click")
    page.locator(".cgp-demo").screenshot(path=str(SHOTS / "demo-loaded.png"))
    b.close()

print("ALL OK" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
