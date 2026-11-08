#!/usr/bin/env python3
"""Render a space page in light and dark, in 3D and/or Plan."""

import argparse
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--scale", type=float, default=1)
    parser.add_argument("--view", choices=("3d", "plan", "both"), default="3d")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    errors, requests = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": args.width, "height": args.height},
            device_scale_factor=args.scale,
        )
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "request",
            lambda request: (
                requests.append(request.url)
                if not request.url.startswith(("file:", "data:", "blob:"))
                else None
            ),
        )
        page.goto(args.html.resolve().as_uri())
        expect(page.locator("#viewport canvas")).to_be_visible()
        page.evaluate("document.fonts.ready")
        views = ("3d", "plan") if args.view == "both" else (args.view,)
        for view in views:
            page.locator(f"#view-{view}").click()
            for theme in ("light", "dark"):
                if page.locator("html").get_attribute("data-theme") != theme:
                    page.locator("#theme").click()
                page.locator("#theme").blur()
                page.mouse.move(0, 0)
                suffix = ("-plan" if view == "plan" else "") + (
                    "-dark" if theme == "dark" else ""
                )
                target = args.out.with_name(args.out.stem + suffix + args.out.suffix)
                page.screenshot(path=str(target), full_page=True)
                print(f"rendered {target}")
        browser.close()
    if errors or requests:
        raise RuntimeError(f"page errors: {errors}; external requests: {requests}")


if __name__ == "__main__":
    main()
