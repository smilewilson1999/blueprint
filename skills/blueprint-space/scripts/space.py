#!/usr/bin/env python3
"""Build a space.json into one offline HTML page."""

import argparse
import base64
import html
import itertools
import json
import math
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
TYPES = {"desk", "table", "chair", "sofa", "shelf", "counter", "plant"}
EPS = 1e-7


def number(value, label, positive=False):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or abs(value) > 1_000_000
        or (positive and value <= 0)
    ):
        raise ValueError(
            f"{label}: expected a finite {'positive ' if positive else ''}number (maximum magnitude 1000000)"
        )


def vector(value, length, label, positive=False):
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"{label}: expected {length} numbers")
    for item in value:
        number(item, label, positive)


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def edges(poly):
    return zip(poly, poly[1:] + poly[:1])


def on_segment(p, a, b):
    return abs(cross(a, b, p)) < EPS and all(
        min(a[i], b[i]) - EPS <= p[i] <= max(a[i], b[i]) + EPS for i in (0, 1)
    )


def intersects(a, b, c, d, proper=False):
    ab, cd = cross(a, b, c) * cross(a, b, d), cross(c, d, a) * cross(c, d, b)
    if ab < -EPS and cd < -EPS:
        return True
    return not proper and any(
        (
            on_segment(c, a, b),
            on_segment(d, a, b),
            on_segment(a, c, d),
            on_segment(b, c, d),
        )
    )


def inside(p, poly, boundary=True):
    if any(on_segment(p, a, b) for a, b in edges(poly)):
        return boundary
    result = False
    for a, b in edges(poly):
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (
            b[1] - a[1]
        ) + a[0]:
            result = not result
    return result


def contained(poly, container):
    return (
        all(inside(p, container) for p in poly)
        and not any(
            intersects(a, b, c, d, proper=True)
            for a, b in edges(poly)
            for c, d in edges(container)
        )
        and all(
            inside([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], container)
            for a, b in edges(poly)
        )
    )


def interior_samples(poly):
    sign = 1 if sum(a[0] * b[1] - b[0] * a[1] for a, b in edges(poly)) > 0 else -1
    for a, b in edges(poly):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        step = min(length * 1e-5, 1e-5)
        p = [
            (a[0] + b[0]) / 2 - sign * dy / length * step,
            (a[1] + b[1]) / 2 + sign * dx / length * step,
        ]
        if inside(p, poly, boundary=False):
            yield p


def overlap(a, b):
    return (
        any(
            intersects(p, q, r, s, proper=True)
            for p, q in edges(a)
            for r, s in edges(b)
        )
        or any(
            inside(p, b, boundary=False)
            for p in itertools.chain(a, interior_samples(a))
        )
        or any(
            inside(p, a, boundary=False)
            for p in itertools.chain(b, interior_samples(b))
        )
    )


def canonical(value):
    if isinstance(value, dict):
        return {key: canonical(item) for key, item in value.items()}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value) or abs(value) > 9007199254740991:
            raise ValueError(
                "all JSON numbers must be finite and within JavaScript safe integer magnitude"
            )
        return int(value) if value == int(value) else value
    return value


def rectangle(position, size, rotation=0):
    angle = math.radians(rotation)
    c, s = math.cos(angle), math.sin(angle)
    return [
        [position[0] + x * c - z * s, position[1] + x * s + z * c]
        for x, z in [
            (-size[0] / 2, -size[1] / 2),
            (size[0] / 2, -size[1] / 2),
            (size[0] / 2, size[1] / 2),
            (-size[0] / 2, size[1] / 2),
        ]
    ]


def polygon(value, label):
    if not isinstance(value, list) or len(value) < 3:
        raise ValueError(f"{label}: expected a simple polygon with at least 3 vertices")
    for p in value:
        vector(p, 2, label)
    if (
        any(a == b for a, b in edges(value))
        or abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in edges(value))) < EPS
    ):
        raise ValueError(f"{label}: degenerate polygon")
    segments = list(edges(value))
    for i, j in itertools.combinations(range(len(segments)), 2):
        if j == i + 1 or (i == 0 and j == len(segments) - 1):
            continue
        if intersects(*segments[i], *segments[j]):
            raise ValueError(f"{label}: polygon intersects itself")


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: expected nonempty text")


def validate(model):
    if not isinstance(model, dict):
        raise TypeError("space.json must be an object")
    canonical(model)
    text(model.get("title"), "title")
    if model.get("units") != "m":
        raise ValueError("units must be m (metres)")
    polygon(model.get("floor"), "floor")
    if "grid" in model:
        number(model["grid"], "grid", True)
    for key in ("lede", "kicker", "footer", "lang"):
        if key in model:
            text(model[key], key)
    ids = set()
    for kind in ("rooms", "walls", "doors", "windows", "furniture"):
        if not isinstance(model.get(kind, []), list):
            raise TypeError(f"{kind} must be an array")
        for obj in model.get(kind, []):
            if not isinstance(obj, dict):
                raise TypeError(f"{kind}: expected an object")
            ident = obj.get("id")
            if (
                not isinstance(ident, str)
                or not re.fullmatch(r"[a-zA-Z0-9_-]+", ident)
                or ident in ids
            ):
                raise ValueError(f"{kind}: invalid or duplicate id {ident!r}")
            ids.add(ident)
            if "note" in obj:
                text(obj["note"], f"{ident}.note")
            if kind in ("rooms", "furniture"):
                text(obj.get("name"), f"{ident}.name")
                if "color" in obj and not re.fullmatch(
                    r"#[0-9A-Fa-f]{6}", str(obj["color"])
                ):
                    raise ValueError(f"{ident}.color: expected #RRGGBB")
            if kind == "rooms":
                polygon(obj.get("outline"), ident)
                if "label" in obj:
                    vector(obj["label"], 2, f"{ident}.label")
            elif kind == "walls":
                for key in ("start", "end"):
                    vector(obj.get(key), 2, f"{ident}.{key}")
                if obj["start"] == obj["end"]:
                    raise ValueError(f"{ident}: wall has zero length")
                for key in ("height", "thickness"):
                    number(obj.get(key), f"{ident}.{key}", True)
            elif kind in ("doors", "windows"):
                text(obj.get("wall"), f"{ident}.wall")
                for key in ("width", "height"):
                    number(obj.get(key), f"{ident}.{key}", True)
                number(obj.get("offset"), f"{ident}.offset")
                if kind == "windows":
                    number(obj.get("sill"), f"{ident}.sill")
                    if obj["sill"] < 0:
                        raise ValueError(f"{ident}.sill must be nonnegative")
            else:
                if obj.get("type") not in TYPES:
                    raise ValueError(
                        f"{ident}.type must be one of {', '.join(sorted(TYPES))}"
                    )
                text(obj.get("room"), f"{ident}.room")
                vector(obj.get("position"), 2, f"{ident}.position")
                vector(obj.get("size"), 3, f"{ident}.size", True)
                number(obj.get("rotation", 0), f"{ident}.rotation")


def wall_rectangle(wall, start=0, end=None, depth=None):
    a, b = wall["start"], wall["end"]
    length = math.dist(a, b)
    end = length if end is None else end
    return rectangle(
        [a[i] + (b[i] - a[i]) * (start + end) / (2 * length) for i in (0, 1)],
        [end - start, depth or wall["thickness"]],
        math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])),
    )


def layout_warnings(model):
    warnings = []
    rooms = {r["id"]: r for r in model.get("rooms", [])}
    walls = {w["id"]: w for w in model.get("walls", [])}
    openings = model.get("doors", []) + model.get("windows", [])
    furniture = model.get("furniture", [])
    footprints = {
        f["id"]: rectangle(f["position"], f["size"], f.get("rotation", 0))
        for f in furniture
    }
    for room in rooms.values():
        if not contained(room["outline"], model["floor"]):
            warnings.append(f"room {room['id']} outside floor")
        if "label" in room and not inside(room["label"], room["outline"]):
            warnings.append(f"room {room['id']} label outside room")
    for a, b in itertools.combinations(rooms.values(), 2):
        if overlap(a["outline"], b["outline"]):
            warnings.append(f"rooms {a['id']} and {b['id']} overlap")
    for opening in openings:
        wall = walls.get(opening["wall"])
        if not wall:
            warnings.append(f"{opening['id']}: unknown wall {opening['wall']}")
        elif (
            opening["offset"] < 0
            or opening["offset"] + opening["width"]
            > math.dist(wall["start"], wall["end"]) + EPS
            or opening.get("sill", 0) + opening["height"] > wall["height"] + EPS
        ):
            warnings.append(f"opening {opening['id']} outside wall {wall['id']}")
    for a, b in itertools.combinations(openings, 2):
        if (
            a["wall"] == b["wall"]
            and min(a["offset"] + a["width"], b["offset"] + b["width"])
            > max(a["offset"], b["offset"]) + EPS
            and min(a.get("sill", 0) + a["height"], b.get("sill", 0) + b["height"])
            > max(a.get("sill", 0), b.get("sill", 0)) + EPS
        ):
            warnings.append(f"openings {a['id']} and {b['id']} overlap")
    for f in furniture:
        poly = footprints[f["id"]]
        room = rooms.get(f["room"])
        if not room:
            warnings.append(f"{f['id']}: unknown room {f['room']}")
        elif not contained(poly, room["outline"]):
            warnings.append(f"{f['id']} outside room {room['id']}")
        if not contained(poly, model["floor"]):
            warnings.append(f"{f['id']} outside floor")
        for wall in walls.values():
            if overlap(poly, wall_rectangle(wall)):
                warnings.append(f"{f['id']} intersects wall {wall['id']}")
        for door in model.get("doors", []):
            wall = walls.get(door["wall"])
            if wall and overlap(
                poly,
                wall_rectangle(
                    wall,
                    door["offset"],
                    door["offset"] + door["width"],
                    2 * door["width"],
                ),
            ):
                warnings.append(f"{f['id']} blocks door {door['id']}")
    for a, b in itertools.combinations(furniture, 2):
        if overlap(footprints[a["id"]], footprints[b["id"]]):
            warnings.append(f"furniture {a['id']} and {b['id']} overlap")
    return warnings


def build(model):
    validate(model)
    model = canonical(model)
    warnings = layout_warnings(model)
    assets = SKILL / "assets"
    encode = lambda path: base64.b64encode(path.read_bytes()).decode("ascii")
    values = {
        key.upper(): html.escape(model.get(key, ""), quote=True)
        for key in ("title", "kicker", "lede", "footer")
    }
    values.update(
        LANG=html.escape(model.get("lang", "en"), quote=True),
        MODEL=json.dumps(
            model, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026"),
        THREE=encode(assets / "vendor/three.module.min.js"),
        LICENSE=html.escape((assets / "vendor/LICENSE").read_text(encoding="utf-8")),
        VIEWER=(assets / "viewer.js").read_text(encoding="utf-8"),
        STYLE=(assets / "style.css").read_text(encoding="utf-8"),
        INTER=encode(assets / "fonts/Inter.woff2"),
        MONO=encode(assets / "fonts/IBMPlexMono-400.woff2"),
    )
    template = (assets / "template.html").read_text(encoding="utf-8")
    return re.sub(
        r"\{\{([A-Z_]+)\}\}", lambda match: values[match[1]], template
    ), warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument(
        "--strict", action="store_true", help="fail without writing HTML on any WARN"
    )
    args = parser.parse_args()
    try:
        model = json.loads(args.spec.read_text(encoding="utf-8"))
        page, warnings = build(model)
    except (TypeError, ValueError, OSError) as error:
        print(f"WARN {error}")
        return 1
    for warning in warnings:
        print(f"WARN {warning}")
    if args.strict and warnings:
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding="utf-8")
    print(
        f"built {args.out} ({len(page.encode()) // 1024} KB, {len(warnings)} warnings)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
