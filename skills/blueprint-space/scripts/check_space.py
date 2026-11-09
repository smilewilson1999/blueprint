#!/usr/bin/env python3
"""Exercise an offline space page and rebuild its downloaded JSON."""

import argparse
import copy
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BUILDER = Path(__file__).with_name("space.py")
SPACE_SPEC = importlib.util.spec_from_file_location("space_builder", BUILDER)
SPACE = importlib.util.module_from_spec(SPACE_SPEC)
SPACE_SPEC.loader.exec_module(SPACE)


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


def plan_screen_point(page, anchor_id, x_ref_id, z_ref_id, target, positions):
    def screen(item_id):
        return json.loads(
            page.locator(f"#space-piece-{item_id}").get_attribute("data-screen")
        )

    anchor = screen(anchor_id)
    x_ref = screen(x_ref_id)
    z_ref = screen(z_ref_id)
    anchor_position = positions[anchor_id]
    x_scale = (x_ref[0] - anchor[0]) / (positions[x_ref_id][0] - anchor_position[0])
    z_scale = (z_ref[1] - anchor[1]) / (positions[z_ref_id][1] - anchor_position[1])
    return [
        anchor[0] + (target[0] - anchor_position[0]) * x_scale,
        anchor[1] + (target[1] - anchor_position[1]) * z_scale,
    ]


def polygon_bounds(polygon):
    xs, zs = zip(*polygon)
    return min(xs), min(zs), max(xs), max(zs)


def bounds_overlap(first, second):
    return (
        first[0] < second[2]
        and first[2] > second[0]
        and first[1] < second[3]
        and first[3] > second[1]
    )


def find_cross_room_case(model):
    rooms = model.get("rooms", [])
    furniture = model.get("furniture", [])
    if len(rooms) < 2:
        return None, "the model has fewer than two rooms"
    if not furniture:
        return None, "the model has no furniture to move"
    grid = model.get("grid", 0.25)
    walls = model.get("walls", [])
    doors = model.get("doors", [])
    footprints = {
        item["id"]: SPACE.rectangle(
            item["position"], item["size"], item.get("rotation", 0)
        )
        for item in furniture
    }
    wall_clearances = [SPACE.wall_rectangle(wall) for wall in walls]
    for door in doors:
        wall = next((item for item in walls if item["id"] == door["wall"]), None)
        if wall:
            wall_clearances.append(
                SPACE.wall_rectangle(
                    wall,
                    door["offset"],
                    door["offset"] + door["width"],
                    2 * door["width"],
                )
            )
    clearance_bounds = [polygon_bounds(item) for item in wall_clearances]
    furniture_bounds = {
        ident: polygon_bounds(footprint) for ident, footprint in footprints.items()
    }
    for piece in furniture:
        source_room = piece["room"]
        for room in rooms:
            if room["id"] == source_room:
                continue
            outline = room["outline"]
            xs, zs = zip(*outline)
            angle = math.radians(piece.get("rotation", 0))
            half_width = (
                abs(piece["size"][0] * math.cos(angle))
                + abs(piece["size"][1] * math.sin(angle))
            ) / 2
            half_depth = (
                abs(piece["size"][0] * math.sin(angle))
                + abs(piece["size"][1] * math.cos(angle))
            ) / 2
            min_x = math.ceil((min(xs) + half_width) / grid)
            max_x = math.floor((max(xs) - half_width) / grid)
            min_z = math.ceil((min(zs) + half_depth) / grid)
            max_z = math.floor((max(zs) - half_depth) / grid)
            candidates = (max_x - min_x + 1) * (max_z - min_z + 1)
            if candidates <= 0:
                continue
            multiple = max(1, math.ceil(math.sqrt(candidates / 100_000)))
            search_grid = grid * multiple
            min_x = math.ceil((min(xs) + half_width) / search_grid)
            max_x = math.floor((max(xs) - half_width) / search_grid)
            min_z = math.ceil((min(zs) + half_depth) / search_grid)
            max_z = math.floor((max(zs) - half_depth) / search_grid)
            for ix in range(min_x, max_x + 1):
                for iz in range(min_z, max_z + 1):
                    position = [round(ix * search_grid, 6), round(iz * search_grid, 6)]
                    footprint = SPACE.rectangle(
                        position, piece["size"], piece.get("rotation", 0)
                    )
                    if not SPACE.contained(footprint, outline):
                        continue
                    if not SPACE.contained(footprint, model["floor"]):
                        continue
                    footprint_bounds = polygon_bounds(footprint)
                    if any(
                        bounds_overlap(footprint_bounds, furniture_bounds[ident])
                        and SPACE.overlap(footprint, other)
                        for ident, other in footprints.items()
                        if ident != piece["id"]
                    ):
                        continue
                    if any(
                        bounds_overlap(footprint_bounds, bounds)
                        and SPACE.overlap(footprint, wall)
                        for wall, bounds in zip(wall_clearances, clearance_bounds)
                    ):
                        continue
                    return {
                        "piece": piece,
                        "room": room,
                        "position": position,
                    }, None
    return None, "no grid-snapped free spot fits a piece in another room"


def screen_references(model, anchor_id):
    positions = {item["id"]: item["position"] for item in model["furniture"]}
    anchor = positions[anchor_id]
    x_ref = next(
        (item for item in model["furniture"] if item["position"][0] != anchor[0]), None
    )
    z_ref = next(
        (item for item in model["furniture"] if item["position"][1] != anchor[1]), None
    )
    if not x_ref or not z_ref:
        return None
    return positions, x_ref["id"], z_ref["id"]


def assert_labels_disjoint(page, context):
    labels = page.locator(".room-label").evaluate_all(
        """
        elements => elements
          .filter(element => getComputedStyle(element).visibility !== 'hidden')
          .map(element => {
            const rect = element.getBoundingClientRect();
            return {left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, text: element.innerText};
          })
        """
    )
    for index, first in enumerate(labels):
        for second in labels[index + 1 :]:
            overlap = (
                first["left"] < second["right"]
                and first["right"] > second["left"]
                and first["top"] < second["bottom"]
                and first["bottom"] > second["top"]
            )
            assert not overlap, (
                f"{context}: labels overlap: {first['text']!r} / {second['text']!r}"
            )


def assert_piece_centres_on_canvas(page, context):
    pieces = page.locator(".piece-row").evaluate_all(
        "elements => elements.map(element => ({id: element.id, point: JSON.parse(element.dataset.screen)}))"
    )
    for piece in pieces:
        x, y = piece["point"]
        element = page.evaluate(
            "point => { const element = document.elementFromPoint(...point); return {tag: element?.tagName, id: element?.id}; }",
            [x, y],
        )
        assert element["tag"] == "CANVAS", (
            f"{context}: {piece['id']} centre hit {element} instead of canvas"
        )


def assert_visible_labels_in_rooms(page, model, context):
    rooms = {room["id"]: room["outline"] for room in model.get("rooms", [])}
    viewport = page.locator("#viewport").bounding_box()
    labels = page.locator(".room-label").evaluate_all(
        """
        elements => elements
          .filter(element => getComputedStyle(element).visibility !== 'hidden')
          .map(element => {
            const rect = element.getBoundingClientRect();
            return {
              id: element.dataset.room,
              point: JSON.parse(element.dataset.floorPoint),
              screen: JSON.parse(element.dataset.screen),
              center: [(rect.left + rect.right) / 2, (rect.top + rect.bottom) / 2],
              rect: {left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom},
            };
          })
        """
    )
    for label in labels:
        assert label["id"] in rooms, f"{context}: unknown room label {label['id']}"
        assert SPACE.inside(label["point"], rooms[label["id"]]), (
            f"{context}: label {label['id']} floor point left its room"
        )
        assert all(
            abs(actual - expected) <= 1
            for actual, expected in zip(label["center"], label["screen"])
        ), f"{context}: label {label['id']} center does not match its floor projection"
        assert (
            label["rect"]["left"] >= viewport["x"] - 1
            and label["rect"]["right"] <= viewport["x"] + viewport["width"] + 1
            and label["rect"]["top"] >= viewport["y"] - 1
            and label["rect"]["bottom"] <= viewport["y"] + viewport["height"] + 1
        ), f"{context}: label {label['id']} is clipped by the viewport"


def assert_layout_state(page, model, context):
    assert_piece_centres_on_canvas(page, context)
    assert_visible_labels_in_rooms(page, model, context)
    assert_labels_disjoint(page, context)


def check_label_layouts(browser, html, model, errors, requests):
    for width, height in ((1440, 1000), (1024, 900), (390, 844), (360, 800)):
        context = browser.new_context(
            viewport={"width": width, "height": height},
            is_mobile=width < 500,
            has_touch=width < 500,
            device_scale_factor=1,
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
        page.goto(html.resolve().as_uri())
        expect(page.locator("#viewport canvas")).to_be_visible()
        page.evaluate("document.fonts.ready")
        assert_layout_state(page, model, f"{width} 3D load")
        page.mouse.move(width / 2, height / 2)
        page.mouse.wheel(0, 10000)
        assert_layout_state(page, model, f"{width} 3D wheel-out")
        page.set_viewport_size({"width": width - 16, "height": height})
        page.wait_for_timeout(50)
        assert_layout_state(page, model, f"{width} 3D resize")
        if width == 360:
            page.locator("#zoom-in").click()
            assert_layout_state(page, model, "360 3D zoom-in")
            page.locator("#theme").click()
            assert_layout_state(page, model, "360 3D theme toggle")
            page.locator("#theme").click()
        page.keyboard.press("v")
        expect(page.locator("#view-plan")).to_have_attribute("aria-pressed", "true")
        assert_layout_state(page, model, f"{width} Plan load")
        page.mouse.move((width - 16) / 2, height / 2)
        page.mouse.wheel(0, 10000)
        assert_layout_state(page, model, f"{width} Plan wheel-out")
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(50)
        assert_layout_state(page, model, f"{width} Plan resize")
        context.close()


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
    model["metadata"] = {"z-second": "second", "a-first": "first", "zero": -0.0}
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
        original = json.loads(page.locator("#space-model").text_content())
        check_label_layouts(browser, args.html, original, errors, requests)
        assert_layout_state(page, original, "desktop 3D")
        ids = page.locator("[id]").evaluate_all(
            "(elements) => elements.map(element => element.id)"
        )
        assert len(ids) == len(set(ids)), "duplicate DOM ids break review anchors"
        room, piece = original.get("rooms", [])[0], original.get("furniture", [])[0]
        room_row = page.locator(f"#space-zone-{room['id']}")
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
        room_row.click()
        expect(page.locator("#inspector")).to_contain_text(room["name"])
        expect(page.locator("#inspector")).to_contain_text(room["id"])
        page.locator(".inventory summary").click()
        page.locator(f"#space-piece-{piece['id']}").click()
        expect(page.locator("#inspector")).to_contain_text(piece["name"])
        expect(page.locator("#inspector")).to_contain_text(piece["id"])
        page.keyboard.press("v")
        expect(page.locator("#view-plan")).to_have_attribute("aria-pressed", "true")
        assert_layout_state(page, original, "desktop Plan")
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
        cross_case, cross_skip = find_cross_room_case(exported)
        if cross_case is None:
            print(f"NOTE cross-room case skipped: {cross_skip}")
            cross_result = f"cross-room case skipped ({cross_skip})"
        else:
            cross_piece = cross_case["piece"]
            cross_room = cross_case["room"]
            references = screen_references(exported, cross_piece["id"])
            if references is None:
                print(
                    "NOTE cross-room case skipped: no independent Plan screen references"
                )
                cross_result = (
                    "cross-room case skipped (no independent Plan screen references)"
                )
            else:
                positions, x_ref_id, z_ref_id = references
                cross_start = json.loads(
                    page.locator(f"#space-piece-{cross_piece['id']}").get_attribute(
                        "data-screen"
                    )
                )
                cross_target = plan_screen_point(
                    page,
                    cross_piece["id"],
                    x_ref_id,
                    z_ref_id,
                    cross_case["position"],
                    positions,
                )
                page.mouse.move(cross_start[0], cross_start[1])
                page.mouse.down()
                page.mouse.move(cross_target[0], cross_target[1], steps=16)
                page.mouse.up()
                cross_json = args.out / "cross-room.json"
                cross_exported = export(page, cross_json)
                cross_changed = next(
                    item
                    for item in cross_exported["furniture"]
                    if item["id"] == cross_piece["id"]
                )
                assert cross_changed["position"] == cross_case["position"], (
                    cross_changed
                )
                assert cross_changed["room"] == cross_room["id"], cross_changed
                expected_changed = copy.deepcopy(cross_piece)
                expected_changed["position"] = cross_case["position"]
                expected_changed["room"] = cross_room["id"]
                assert cross_changed == expected_changed, cross_changed
                before_other_pieces = {
                    item["id"]: item
                    for item in exported["furniture"]
                    if item["id"] != cross_piece["id"]
                }
                for item in cross_exported["furniture"]:
                    if item["id"] != cross_piece["id"]:
                        assert item == before_other_pieces[item["id"]], item["id"]
                expect(page.locator("#inspector .eyebrow")).to_have_text(
                    cross_room["name"]
                )
                expected_count = sum(
                    item["room"] == cross_room["id"]
                    for item in cross_exported["furniture"]
                )
                expect(
                    page.locator(f"#space-zone-{cross_room['id']} .room-piece-count")
                ).to_have_text(
                    f"{expected_count} piece" + ("s" if expected_count != 1 else "")
                )
                page.locator(f"#space-zone-{cross_room['id']}").click()
                pieces_label = page.locator("#inspector dl dt").filter(
                    has_text="Pieces"
                )
                pieces_value = pieces_label.locator("xpath=following-sibling::dd[1]")
                assert pieces_value.inner_text().strip() == str(expected_count), (
                    pieces_value.inner_text(),
                    expected_count,
                )
                cross_rebuilt = args.out / "cross-room.html"
                rebuild(cross_json, cross_rebuilt)
                page.goto(cross_rebuilt.resolve().as_uri())
                cross_model = json.loads(page.locator("#space-model").text_content())
                assert cross_model == cross_exported, (
                    "cross-room export lost the reassigned room"
                )
                cross_result = (
                    f"cross-room move/rebuild passed ({cross_piece['id']} -> "
                    f"{cross_room['id']}, {cross_case['position']})"
                )
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
        mobile.evaluate("document.fonts.ready")
        assert_layout_state(mobile, original, "phone 3D")
        mobile.keyboard.press("v")
        expect(mobile.locator("#view-plan")).to_have_attribute("aria-pressed", "true")
        assert_layout_state(mobile, original, "phone Plan")
        mobile.keyboard.press("v")
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
        phone360 = browser.new_context(
            viewport={"width": 360, "height": 800},
            is_mobile=True,
            has_touch=True,
            device_scale_factor=1,
        )
        mobile360 = phone360.new_page()
        mobile360.on("pageerror", lambda error: errors.append(str(error)))
        mobile360.on(
            "request",
            lambda request: (
                requests.append(request.url)
                if not request.url.startswith(("file:", "data:", "blob:"))
                else None
            ),
        )
        mobile360.goto(args.html.resolve().as_uri())
        expect(mobile360.locator("#viewport canvas")).to_be_visible()
        mobile360.evaluate("document.fonts.ready")
        assert_layout_state(mobile360, original, "phone 360 3D")
        mobile360.keyboard.press("v")
        expect(mobile360.locator("#view-plan")).to_have_attribute(
            "aria-pressed", "true"
        )
        assert_layout_state(mobile360, original, "phone 360 Plan")
        assert mobile360.evaluate(
            "document.documentElement.scrollWidth <= innerWidth"
        ), "phone 360 overflow"
        mobile360.close()
        phone360.close()
        check_edge_cases(page, original, args.out)
        browser.close()
    assert not errors, errors
    assert not requests, requests
    print(
        "PASS orbit; V/Plan; E/edit; drag + grid; rotation; room/piece inspector; unchanged export identical HTML; moved export/rebuild + stable ids; "
        f"{cross_result}; theme; canvas piece centres + in-room disjoint labels at 1440/1024/390/360 in 3D and Plan after load/wheel/resize; touch orbit/pinch at 390px; zero page errors; zero external requests"
    )


if __name__ == "__main__":
    main()
