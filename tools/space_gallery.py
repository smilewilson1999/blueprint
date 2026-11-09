#!/usr/bin/env python3
"""Render Juniper Commons as a drawing-only 3D and Plan README gallery tile.

Usage:
  python3 tools/space_gallery.py
"""

import base64
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/blueprint-space"
SIZE = (2400, 1000)
DRAWING_STYLE = """
#viewport {
  position: fixed;
  inset: 0 auto auto 0;
  width: 1200px;
  height: 900px;
  background: var(--paper);
  border: 0;
  outline: 0;
  z-index: 10;
}
.view-tools, .scale { display: none; }
.room-label, .room-label.compact {
  font-size: 30px;
  padding: 8px 12px;
}
.room-label small { font-size: 18px; }
"""


def check_image(image, background, size):
    assert image.size == size, f"expected {size}, got {image.size}"
    for index in range(2):
        half = image.crop((index * size[0] // 2, 0, (index + 1) * size[0] // 2, 900))
        difference = ImageChops.difference(
            half.convert("RGB"), Image.new("RGB", half.size, background)
        )
        bounds = difference.convert("L").point(lambda value: 255 if value > 12 else 0)
        box = bounds.getbbox()
        assert box is not None, f"half {index + 1} is empty"
        left, top, right, bottom = box
        assert right - left > half.width * 0.6, f"half {index + 1} is too small"
        assert bottom - top > half.height * 0.5, f"half {index + 1} is too small"
        assert min(left, top, half.width - right, half.height - bottom) >= 24, (
            f"half {index + 1} touches the edge"
        )


def check_labels(page, names):
    labels = page.locator("#labels .room-label").evaluate_all(
        """labels => labels.map(label => {
          const rect = label.getBoundingClientRect();
          const viewport = label.parentElement.getBoundingClientRect();
          return {
            name: label.querySelector('span').textContent,
            visible: getComputedStyle(label).visibility === 'visible',
            inside: rect.left >= viewport.left && rect.right <= viewport.right &&
                    rect.top >= viewport.top && rect.bottom <= viewport.bottom
          };
        })"""
    )
    assert sorted(label["name"] for label in labels) == sorted(names)
    assert all(label["visible"] and label["inside"] for label in labels), labels


def read_image(data):
    return Image.open(BytesIO(data)).convert("RGB")


def render(html):
    names = [
        room["name"]
        for room in json.loads(
            (ROOT / "examples/juniper-commons/space.json").read_text()
        )["rooms"]
    ]
    mono = base64.b64encode(
        (SKILL / "assets/fonts/IBMPlexMono-400.woff2").read_bytes()
    ).decode()
    errors, requests = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1200, "height": 1000},
            device_scale_factor=1,
            color_scheme="light",
        )
        composition = browser.new_page(
            viewport={"width": SIZE[0], "height": SIZE[1]}, device_scale_factor=1
        )
        for tab in (page, composition):
            tab.on("pageerror", lambda error: errors.append(str(error)))
            tab.on(
                "request",
                lambda request: (
                    requests.append(request.url)
                    if not request.url.startswith(("file:", "data:", "blob:"))
                    else None
                ),
            )
        page.goto(html.as_uri())
        expect(page.locator("#viewport canvas")).to_be_visible()
        page.add_style_tag(content=DRAWING_STYLE)
        page.evaluate("document.fonts.ready")
        for theme in ("light", "dark"):
            if page.locator("html").get_attribute("data-theme") != theme:
                page.locator("#theme").evaluate("button => button.click()")
            colors = page.evaluate("""() => {
              const style = getComputedStyle(document.documentElement);
              return ['--paper', '--muted'].map(key => style.getPropertyValue(key).trim());
            }""")
            figures = []
            for view, caption in (("3d", "3D"), ("plan", "Plan")):
                page.locator(f"#view-{view}").evaluate("button => button.click()")
                page.evaluate("""() => new Promise(resolve => {
                  requestAnimationFrame(() => requestAnimationFrame(resolve));
                })""")
                page.locator("#fit").evaluate("button => button.click()")
                check_labels(page, names)
                capture = page.locator("#viewport").screenshot()
                encoded = base64.b64encode(capture).decode()
                figures.append(
                    f'<figure><img src="data:image/png;base64,{encoded}">'
                    f"<figcaption>{caption}</figcaption></figure>"
                )
            composition.set_content(
                f"""<!doctype html><html><head><style>
                @font-face {{ font-family: Mono;
                  src: url(data:font/woff2;base64,{mono}) format('woff2'); }}
                * {{ box-sizing: border-box; }}
                body {{ margin: 0; width: 2400px; height: 1000px;
                  display: flex; background: {colors[0]}; }}
                figure {{ margin: 0; width: 1200px; }}
                img {{ display: block; width: 1200px; height: 900px; }}
                figcaption {{ margin-top: 24px; text-align: center;
                  font: 26px/1.5 Mono, monospace; color: {colors[1]}; }}
                </style></head><body>{"".join(figures)}</body></html>"""
            )
            composition.evaluate("document.fonts.ready")
            image = read_image(composition.screenshot())
            check_image(image, colors[0], SIZE)
            if errors or requests:
                raise RuntimeError(
                    f"page errors: {errors}; external requests: {requests}"
                )
            suffix = "-dark" if theme == "dark" else ""
            target = ROOT / f"docs/space-gallery{suffix}.png"
            image.save(target, optimize=True)
            print(f"wrote {target.relative_to(ROOT)} (2400x1000; both halves checked)")
        browser.close()


def main():
    check = ROOT / "check"
    check.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="space-gallery-", dir=check) as temporary:
        html = Path(temporary) / "index.html"
        subprocess.run(
            [
                sys.executable,
                str(SKILL / "scripts/space.py"),
                str(ROOT / "examples/juniper-commons/space.json"),
                str(html),
                "--strict",
            ],
            check=True,
        )
        render(html)


if __name__ == "__main__":
    main()
