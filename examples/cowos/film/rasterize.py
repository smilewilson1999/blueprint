"""Rasterize composed film frames with Chromium: python3 film/rasterize.py SVGDIR PNGDIR"""
import glob, os, sys

from playwright.sync_api import sync_playwright

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
files = sorted(glob.glob(os.path.join(src, "f-*.svg")))
with sync_playwright() as p:
    browser = p.chromium.launch(args=["--font-render-hinting=none"])
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    for f in files:
        page.goto("file://" + os.path.abspath(f))
        page.wait_for_timeout(60)  # let the embedded fonts settle
        page.screenshot(path=os.path.join(out, os.path.basename(f).replace(".svg", ".png")))
    browser.close()
print(f"{len(files)} frames")
