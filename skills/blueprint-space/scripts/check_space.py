#!/usr/bin/env python3
"""Exercise an offline space page and rebuild its downloaded JSON."""

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BUILDER = Path(__file__).with_name("space.py")


def export(page, target):
    with page.expect_download() as download:
        page.locator("#export").click()
    download.value.save_as(target)
    return json.loads(target.read_text(encoding="utf-8"))


def rebuild(source, target):
    result = subprocess.run(
        [sys.executable, str(BUILDER), str(source), str(target), "--strict"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0 and "WARN" not in result.stdout, (
        result.stdout + result.stderr
    )


def check_edge_cases(page, original, out):
    model = copy.deepcopy(original)
    names = {}
    for kind in ("rooms", "walls", "doors", "windows", "furniture"):
        for i, item in enumerate(model.get(kind, [])):
            ident = (
                "count"
                if kind == "rooms" and i == 0
                else "row-count"
                if kind == "rooms" and i == 1
                else "list"
                if kind == "furniture" and i == 0
                else f"edge-{kind}-{i}"
            )
            names[item["id"]] = ident
            item["id"] = ident
    for f in model["furniture"]:
        f["room"] = names[f["room"]]
    for opening in model.get("doors", []) + model.get("windows", []):
        opening["wall"] = names[opening["wall"]]
    payload = '</script><img src="https://example.invalid/anchor" onerror="alert(1)">'
    model["title"] = payload
    model["furniture"][0]["name"] = payload
    model["furniture"][0]["rotation"] = -720
    model["metadata"] = {"2": "second", "1": "first", "zero": -0.0}
    source, output = out / "edge-cases.json", out / "edge-cases.html"
    source.write_text(json.dumps(model), encoding="utf-8")
    rebuild(source, output)
    page.goto(output.resolve().as_uri())
    expect(page.locator("#viewport canvas")).to_be_visible()
    ids = page.locator("[id]").evaluate_all(
        "elements => elements.map(element => element.id)"
    )
    assert len(ids) == len(set(ids)), "valid source ids collided with control ids"
    expect(page.locator("h1")).to_have_text(payload)
    assert export(page, out / "edge-export.json") == model
    rebuild(out / "edge-export.json", out / "edge-rebuilt.html")
    assert (out / "edge-rebuilt.html").read_bytes() == output.read_bytes(), (
        "numeric metadata changed an unchanged build"
    )
    page.locator("#edit").click()
    page.locator(".inventory summary").click()
    page.locator("#space-piece-list").click()
    expect(page.locator("#inspector h2")).to_have_text(payload)
    page.locator("#rotate-right").click()
    expect(page.locator("#space-piece-list")).to_have_attribute("data-rotation", "15")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    errors, requests = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000}, accept_downloads=True
        )
        page = context.new_page()
        page.set_default_timeout(10000)
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
        ids = page.locator("[id]").evaluate_all(
            "(elements) => elements.map(element => element.id)"
        )
        assert len(ids) == len(set(ids)), "duplicate DOM ids break review anchors"
        original = json.loads(page.locator("#space-model").text_content())
        room, piece = original.get("rooms", [])[0], original.get("furniture", [])[0]
        label = page.locator(f"#space-room-{room['id']}")
        before = label.bounding_box()
        view = page.locator("#viewport").bounding_box()
        x, y = view["x"] + 40, view["y"] + 80
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + 110, y + 40, steps=12)
        page.mouse.up()
        assert label.bounding_box() != before, (
            "orbit did not change the projected room label"
        )
        page.locator("#fit").click()
        unchanged = args.out / "unchanged.json"
        assert export(page, unchanged) == original, "unchanged export lost fields"
        rebuilt = args.out / "unchanged.html"
        rebuild(unchanged, rebuilt)
        assert rebuilt.read_bytes() == args.html.read_bytes(), (
            "unchanged export changed the build"
        )
        label.click()
        expect(page.locator("#inspector")).to_contain_text(room["name"])
        expect(page.locator("#inspector")).to_contain_text(room["id"])
        page.locator(".inventory summary").click()
        page.locator(f"#space-piece-{piece['id']}").click()
        expect(page.locator("#inspector")).to_contain_text(piece["name"])
        expect(page.locator("#inspector")).to_contain_text(piece["id"])
        page.keyboard.press("v")
        expect(page.locator("#view-plan")).to_have_attribute("aria-pressed", "true")
        page.keyboard.press("e")
        expect(page.locator("#edit")).to_have_attribute("aria-pressed", "true")
        node = page.locator(f"#space-piece-{piece['id']}")
        start = [
            float(node.get_attribute("data-x")),
            float(node.get_attribute("data-z")),
        ]
        point = json.loads(node.get_attribute("data-screen"))
        page.mouse.move(point[0], point[1])
        page.mouse.down()
        page.mouse.move(point[0] + 28, point[1] + 18, steps=12)
        page.mouse.up()
        moved = [
            float(node.get_attribute("data-x")),
            float(node.get_attribute("data-z")),
        ]
        assert moved != start, f"drag did not move {piece['id']}: {start} -> {moved}"
        page.locator("#rotate-right").click()
        expect(node).to_have_attribute(
            "data-rotation", str((piece.get("rotation", 0) + 15) % 360)
        )
        grid = original.get("grid", 0.25)
        assert all(abs(value / grid - round(value / grid)) < 1e-6 for value in moved), (
            "drag did not snap to grid"
        )
        updated = args.out / "exported-space.json"
        exported = export(page, updated)
        assert [f["id"] for f in exported["furniture"]] == [
            f["id"] for f in original["furniture"]
        ]
        changed = next(f for f in exported["furniture"] if f["id"] == piece["id"])
        assert changed["position"] == moved
        expected = copy.deepcopy(original)
        expected["furniture"][0]["position"] = moved
        expected["furniture"][0]["rotation"] = (piece.get("rotation", 0) + 15) % 360
        assert exported == expected, "export changed ids or unrelated source fields"
        output = args.out / "rebuilt.html"
        rebuild(updated, output)
        page.goto(output.resolve().as_uri())
        new_model = json.loads(page.locator("#space-model").text_content())
        assert new_model == exported, "rebuild lost moved position or schema fields"
        page.locator("#theme").click()
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        page.locator("#view-plan").click()
        page.locator("#edit").click()
        page.locator(".inventory summary").click()
        page.locator(f"#space-piece-{piece['id']}").click()
        expect(page.locator("#inspector")).to_contain_text(piece["id"])
        page.screenshot(path=str(args.out / "edited-dark.png"), full_page=True)
        phone = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=1,
        )
        mobile = phone.new_page()
        mobile.on("pageerror", lambda error: errors.append(str(error)))
        mobile.on(
            "request",
            lambda request: (
                requests.append(request.url)
                if not request.url.startswith(("file:", "data:", "blob:"))
                else None
            ),
        )
        mobile.goto(args.html.resolve().as_uri())
        expect(mobile.locator("#viewport canvas")).to_be_visible()
        assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
            "phone overflow"
        )
        box = mobile.locator("#viewport").bounding_box()
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        client = phone.new_cdp_session(mobile)

        def touch(kind, points):
            client.send(
                "Input.dispatchTouchEvent",
                {
                    "type": kind,
                    "touchPoints": [
                        {"x": px, "y": py, "id": i} for i, (px, py) in enumerate(points)
                    ],
                },
            )

        before = mobile.locator("#viewport").get_attribute("data-camera")
        touch("touchStart", [(cx - 70, cy)])
        touch("touchMove", [(cx + 5, cy + 30)])
        touch("touchEnd", [])
        after_orbit = mobile.locator("#viewport").get_attribute("data-camera")
        assert before != after_orbit, "touch orbit did not move camera"
        touch("touchStart", [(cx - 45, cy), (cx + 45, cy)])
        touch("touchMove", [(cx - 80, cy), (cx + 80, cy)])
        touch("touchEnd", [])
        assert (
            mobile.locator("#viewport").get_attribute("data-camera") != after_orbit
        ), "touch pinch did not zoom"
        mobile.screenshot(path=str(args.out / "touch-390.png"), full_page=True)
        check_edge_cases(page, original, args.out)
        browser.close()
    assert not errors, errors
    assert not requests, requests
    print(
        "PASS orbit; V/Plan; E/edit; drag + grid; rotation; room/piece inspector; unchanged export identical HTML; moved export/rebuild + stable ids; theme; touch orbit/pinch at 390px; zero page errors; zero external requests"
    )


if __name__ == "__main__":
    main()
