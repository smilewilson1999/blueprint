#!/usr/bin/env python3
"""Lay out, route and render a blueprint spec into one self-contained HTML file.

Usage:
  python3 blueprint.py SPEC.json ICONDIR OUT.html [--strict]

SPEC.json describes nodes on a grid, groups by membership, and edges by endpoints
(see references/spec.md). This script places everything in pixels, computes group
boxes from their members, routes every edge orthogonally around node boxes and
group labels, places edge labels where nothing else is, then inlines fonts and
icons. It prints every layout problem it can detect; --strict exits 1 on any.
"""
import base64, html, json, pathlib, re, sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
FONTS = SKILL / "assets" / "fonts"
MIME = {"svg": "image/svg+xml", "png": "image/png", "webp": "image/webp", "jpg": "image/jpeg", "jpeg": "image/jpeg"}

TILE, NODE_W, WIDE_W = 64, 148, 176
COL, ROW, MARGIN, PORT = 184, 232, 48, 7
KINDS = ("primary", "internal", "async", "dev", "vendor")
KIND_ORDER = {k: i for i, k in enumerate(KINDS)}
LEGEND = {"primary": "request path", "internal": "internal call", "async": "async / events",
          "dev": "build & deploy", "vendor": "connection"}
VENDOR = re.compile(r"^(aws|gcp|azure)(-|$)")
CREDITS = {"svgl": "svgl", "devicon": "devicon", "gilbarbara": "gilbarbara/logos", "lucide": "Lucide",
           "aws": "AWS Architecture Icons", "gcp": "Google Cloud product icons",
           "azure": "Azure Public Service Icons", "url": "brand sites"}

TOKEN = re.compile(r"[A-Za-z0-9_-]+")   # class names and icon names go into attributes unescaped

def token(value, what):
    if not TOKEN.fullmatch(str(value)):
        sys.exit(f"{what} {value!r} must be letters, digits, '-' or '_'")
    return value

warnings = []
def warn(msg): warnings.append(msg)
esc = lambda s: html.escape(str(s), quote=True)

def text_w(s, latin, cjk):
    return sum(cjk if ord(c) >= 0x2E80 else latin for c in s)

# ── geometry ─────────────────────────────────────────────────────────────────

class Node:
    def __init__(self, d):
        self.d, self.id = d, d["id"]
        self.name, self.role = d.get("name", d["id"]), d.get("role", "")
        self.w = WIDE_W if d.get("wide") else NODE_W
        col, row = d["at"]
        self.cx, self.top = col * COL, row * ROW
        lines = 2 if text_w(self.name, 7.7, 13.5) > self.w - 10 else 1
        self.label_h = 22 + 18 * lines + (0 if self.role else -16)
        self.label_w = min(self.w, max(text_w(self.name, 7.7, 13.5) if lines == 1 else self.w,
                                       text_w(self.role, 6.4, 10.5)) + 12)

    def move(self, dx, dy): self.cx += dx; self.top += dy
    @property
    def bottom(self): return self.top + 70 + self.label_h
    @property
    def ty(self): return self.top + TILE / 2
    def rects(self):
        """Tile and label text: the two things no edge may pass through."""
        return [(self.cx - TILE / 2, self.top, self.cx + TILE / 2, self.top + TILE),
                (self.cx - self.label_w / 2, self.top + TILE + 4, self.cx + self.label_w / 2, self.bottom)]
    def box(self): return (self.cx - self.w / 2, self.top, self.cx + self.w / 2, self.bottom)
    def port(self, side, off=0):
        """Where an edge leaves or enters. off shifts it along the side, so a two-way pair runs side by side."""
        return {"left": (self.cx - TILE / 2 - PORT, self.ty + off), "right": (self.cx + TILE / 2 + PORT, self.ty + off),
                "top": (self.cx + off, self.top - PORT), "bottom": (self.cx + off, self.bottom + PORT - 2)}[side]

def style_of(g, nested):
    s = g.get("style") or ("zone" if nested else "window")
    return s

def pads(style):
    """(side, top, bottom) padding of a group around its members, and the label band for a nested child."""
    if style == "window": return 22, 64, 24, 46
    if VENDOR.match(style): return 22, 58, 22, 44
    return 18, 46, 20, 36

def inflate(r, k): return (r[0] - k, r[1] - k, r[2] + k, r[3] + k)
def hits(a, b): return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]
def seg_rect(p, q): return (min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1]))

def seg_hits_rect(p, q, r):
    s = seg_rect(p, q)
    return s[0] < r[2] and s[2] > r[0] and s[1] < r[3] and s[3] > r[1]

def collinear_overlap(a, b):
    (p, q), (r, s) = a, b
    if p[1] == q[1] == r[1] == s[1]:
        lo, hi = max(min(p[0], q[0]), min(r[0], s[0])), min(max(p[0], q[0]), max(r[0], s[0]))
        return hi - lo > 6
    if p[0] == q[0] == r[0] == s[0]:
        lo, hi = max(min(p[1], q[1]), min(r[1], s[1])), min(max(p[1], q[1]), max(r[1], s[1]))
        return hi - lo > 6
    return False

def crowds(a, b):
    """Parallel and closer than 14px over a real stretch: two lines that read as one."""
    (p, q), (r, s) = a, b
    if p[1] == q[1] and r[1] == s[1] and 1 < abs(p[1] - r[1]) < 14:
        return min(max(p[0], q[0]), max(r[0], s[0])) - max(min(p[0], q[0]), min(r[0], s[0])) > 10
    if p[0] == q[0] and r[0] == s[0] and 1 < abs(p[0] - r[0]) < 14:
        return min(max(p[1], q[1]), max(r[1], s[1])) - max(min(p[1], q[1]), min(r[1], s[1])) > 10
    return False

def crosses(a, b):
    (p, q), (r, s) = a, b
    if (p[1] == q[1]) == (r[1] == s[1]):
        return False
    h, v = (a, b) if p[1] == q[1] else (b, a)
    x, y = v[0][0], h[0][1]
    return (min(h[0][0], h[1][0]) < x < max(h[0][0], h[1][0]) and
            min(v[0][1], v[1][1]) < y < max(v[0][1], v[1][1]))

def clean(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) < .5 and abs(p[1] - out[-1][1]) < .5:
            continue
        out.append(p)
    # drop middle points of straight runs
    i = 1
    while i < len(out) - 1:
        a, b, c = out[i - 1], out[i], out[i + 1]
        if (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]):
            out.pop(i)
        else:
            i += 1
    return out

LANE = 16   # how far a port moves along its side to give an edge its own lane

def candidates(A, B, oa=0, ob=0):
    """Orthogonal route shapes from A to B. oa/ob move each end along its side (a lane).
    Each candidate is (shape, points, side at A, side at B)."""
    sx = 1 if B.cx > A.cx else -1
    sy = 1 if B.top > A.top else -1
    a_side, b_side = ("right", "left") if sx > 0 else ("left", "right")
    a_v, b_v = ("bottom", "top") if sy > 0 else ("top", "bottom")
    ax, bx, aty, bty = A.cx + oa, B.cx + ob, A.ty + oa, B.ty + ob
    c = []
    if abs(A.top - B.top) < 1:
        if oa == ob:
            c.append(("straight", [A.port(a_side, oa), B.port(b_side, ob)], a_side, b_side))
        yb = max(A.bottom, B.bottom) + 30
        c.append(("under", [A.port("bottom", oa), (ax, yb), (bx, yb), B.port("bottom", ob)], "bottom", "bottom"))
        ya = min(A.top, B.top) - 30
        c.append(("over", [A.port("top", oa), (ax, ya), (bx, ya), B.port("top", ob)], "top", "top"))
    elif abs(A.cx - B.cx) < 1:
        if oa == ob:
            c.append(("straight", [A.port(a_v, oa), B.port(b_v, ob)], a_v, b_v))
        for side, name in ((1, "right"), (-1, "left")):
            x = A.cx + side * COL / 2
            c.append(("around", [A.port(name, oa), (x, aty), (x, bty), B.port(name, ob)], name, name))
    else:
        c.append(("hv", [A.port(a_side, oa), (bx, aty), B.port(b_v, ob)], a_side, b_v))
        c.append(("vh", [A.port(a_v, oa), (ax, bty), B.port(b_side, ob)], a_v, b_side))
        bands = (B.top - 34, A.bottom + 34) if sy > 0 else (B.bottom + 34, A.top - 34)
        for ym in bands:
            c.append(("vhv", [A.port(a_v, oa), (ax, ym), (bx, ym), B.port(b_v, ob)], a_v, b_v))
        for xm in ((A.cx + B.cx) / 2, B.cx - sx * COL / 2, A.cx + sx * COL / 2):
            c.append(("hvh", [A.port(a_side, oa), (xm, aty), (xm, bty), B.port(b_side, ob)], a_side, b_side))
    # number repeated shapes (vhv0, vhv1) so a route hint can name the exact one
    seen, out = {}, []
    for name, pts, sa, sb in c:
        k = seen.get(name, 0); seen[name] = k + 1
        out.append((f"{name}{k}", clean(pts), sa, sb))
    return out

def port_clash(node, side, off, direction, ports):
    """An edge leaving a port another edge arrives at (or the reverse) reads as one line with two heads."""
    return any(n == node and sd == side and abs(o - off) < LANE - 4 and d != direction for n, sd, o, d in ports)

def score(pts, e, nodes, labels, routed):
    s, why = 0.0, []
    segs = list(zip(pts, pts[1:]))
    for i, (p, q) in enumerate(segs):
        for n in nodes:
            if any(seg_hits_rect(p, q, inflate(r, 3)) for r in n.rects()):
                s += 1000; why.append(f"runs through {n.id}")
        for gid, r in labels:
            if seg_hits_rect(p, q, r):
                s += 400; why.append(f"crosses the {gid} label")
        for oe in routed:
            osegs = list(zip(oe["pts"], oe["pts"][1:]))
            for j, o in enumerate(osegs):
                if collinear_overlap((p, q), o):
                    trunk = (oe["from"] == e["from"] and i == 0 and j == 0) or \
                            (oe["to"] == e["to"] and i == len(segs) - 1 and j == len(osegs) - 1)
                    if not trunk:
                        s += 300; why.append(f"runs on top of {oe['id']}")
                elif crosses((p, q), o):
                    s += 6
                elif crowds((p, q), o) and not (oe["from"] == e["to"] and oe["to"] == e["from"]):
                    s += 150; why.append(f"crowds {oe['id']}")
        s += abs(q[0] - p[0]) * .02 + abs(q[1] - p[1]) * .02
    s += 14 * (len(pts) - 2)
    return s, why

def path_d(pts, r=10):
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(1, len(pts) - 1):
        (ax, ay), (bx, by), (cx, cy) = pts[i - 1], pts[i], pts[i + 1]
        k = min(r, abs(bx - ax + by - ay) / 2, abs(cx - bx + cy - by) / 2)
        ux, uy = (bx - ax) / max(abs(bx - ax) + abs(by - ay), 1e-9), (by - ay) / max(abs(bx - ax) + abs(by - ay), 1e-9)
        vx, vy = (cx - bx) / max(abs(cx - bx) + abs(cy - by), 1e-9), (cy - by) / max(abs(cx - bx) + abs(cy - by), 1e-9)
        d += f" L{bx - ux * k:.1f} {by - uy * k:.1f} Q{bx:.1f} {by:.1f} {bx + vx * k:.1f} {by + vy * k:.1f}"
    d += f" L{pts[-1][0]:.1f} {pts[-1][1]:.1f}"
    return d

def place_chip(e, nodes, labels, chips, routed, borders):
    text = e.get("label", "")
    w = text_w(text, 6.4, 10.5) + 16 + (19 if e.get("step") else 0) - (0 if text else 8)
    h = 20
    best = None
    segs = list(zip(e["pts"], e["pts"][1:]))
    for i, (p, q) in enumerate(segs):
        length = abs(q[0] - p[0]) + abs(q[1] - p[1])
        horiz = p[1] == q[1]
        need = (w if horiz else h) + 28
        if length < need:
            continue
        for t in (.5, .35, .65, .22, .78):
            x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
            r = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
            s = -length * .05 - (8 if horiz else 0) + abs(t - .5) * 20
            for n in nodes:
                if any(hits(inflate(nr, 12), r) for nr in n.rects()):
                    s += 1000
            for _, lr in labels:
                if hits(lr, r): s += 400
            for c in chips:
                if hits(inflate(c, 10), r): s += 500
            for g in borders:
                if hits(g, r): s += 60
            for oe in routed:
                if oe is e: continue
                for a, b in zip(oe["pts"], oe["pts"][1:]):
                    if seg_hits_rect(a, b, r): s += 40
            if best is None or s < best[0]:
                best = (s, x, y, r)
    if best is None:
        # no segment is long enough: sit on the longest one anyway and say so
        p, q = max(segs, key=lambda pq: abs(pq[1][0] - pq[0][0]) + abs(pq[1][1] - pq[0][1]))
        x, y = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        best = (1000, x, y, (x - w / 2, y - h / 2, x + w / 2, y + h / 2))
    if best[0] >= 400:
        warn(f"edge {e['id']}: label {text!r} has no clear spot; spread the nodes or shorten the label")
    chips.append(best[3])
    return best[1], best[2]

# ── build ────────────────────────────────────────────────────────────────────

def icon_tok(name): return f"%%ICON_{name}%%"

def label_html(g, icondir, cls):
    icon = g.get("icon")
    img = ""
    if icon:
        plate = ' class="plate"' if g.get("plate") else ""
        if any(icondir.glob(f"{icon}_dark.*")):
            img = (f'<img class="lt" src="{icon_tok(icon)}" alt=""><img class="dk" src="{icon_tok(icon + "_dark")}" alt="">')
        else:
            img = f'<img{plate} src="{icon_tok(icon)}" alt="">'
    meta = f'<span class="g-meta">{esc(g["meta"])}</span>' if g.get("meta") else ""
    return f'<div class="{cls}">{img}<span class="g-name">{esc(g.get("label", g["id"]))}</span>{meta}</div>'

def main():
    args = sys.argv[1:]
    strict = "--strict" in args
    args = [a for a in args if a != "--strict"]
    if len(args) != 3:
        print(__doc__); sys.exit(1)
    spec = json.loads(pathlib.Path(args[0]).read_text(encoding="utf-8"))
    icondir, out = pathlib.Path(args[1]), pathlib.Path(args[2])

    for d in spec["nodes"]:
        token(d["id"], "node id")
        for t in d.get("tile", "").split(): token(t, "tile class")
        if d.get("icon"): token(d["icon"], "icon")
        if d.get("link") and not re.match(r"https?://", d["link"]):
            sys.exit(f"node {d['id']}: link must start with http:// or https://")
    for g in spec.get("groups", []):
        token(g["id"], "group id")
        for k in ("style", "tone", "icon"):
            if g.get(k): token(g[k], f"group {k}")
    for e in spec.get("edges", []):
        if e.get("id"): token(e["id"], "edge id")
        if e.get("flow"): token(e["flow"], "edge flow")
    for f in spec.get("flows", []):
        token(f["id"], "flow id")
    nodes = [Node(d) for d in spec["nodes"]]
    by = {n.id: n for n in nodes}
    if len(by) != len(nodes):
        sys.exit("duplicate node id")
    groups = {g["id"]: g for g in spec.get("groups", [])}
    parent = {}
    for g in groups.values():
        for m in g.get("contains", []):
            if m not in by and m not in groups:
                sys.exit(f"group {g['id']} contains unknown id {m!r}")
            if m in parent:
                sys.exit(f"{m!r} is in two groups ({parent[m]}, {g['id']}); nest the groups instead")
            parent[m] = g["id"]

    def ancestors(x):
        out = []
        while x in parent:
            x = parent[x]; out.append(x)
        return out

    rect = {}
    def align(gids):
        """Sibling groups side by side share top and bottom edges, the way a row of subnets is drawn."""
        for a in gids:
            for b in gids:
                if a >= b: continue
                ra, rb = rect[a], rect[b]
                overlap = min(ra[3], rb[3]) - max(ra[1], rb[1])
                if overlap > .5 * min(ra[3] - ra[1], rb[3] - rb[1]) and not hits(ra, rb):
                    top, bottom = min(ra[1], rb[1]), max(ra[3], rb[3])
                    rect[a] = (ra[0], top, ra[2], bottom); rect[b] = (rb[0], top, rb[2], bottom)

    def grect(gid):
        if gid in rect: return rect[gid]
        g = groups[gid]
        st = style_of(g, gid in parent)
        px, pt, pb, band = pads(st)
        kids = [m for m in g.get("contains", []) if m in groups]
        for m in kids: grect(m)
        align(kids)
        exts = []
        for m in g.get("contains", []):
            if m in by:
                n = by[m]; b = n.box()
                exts.append((b[0] - px, n.top - pt, b[2] + px, b[3] + pb))
            else:
                c = rect[m]
                exts.append((c[0] - 14, c[1] - band, c[2] + 14, c[3] + 14))
        if not exts:
            sys.exit(f"group {gid} is empty")
        rect[gid] = (min(e[0] for e in exts), min(e[1] for e in exts), max(e[2] for e in exts), max(e[3] for e in exts))
        return rect[gid]
    for gid in groups: grect(gid)
    align([g for g in groups if g not in parent])

    # translate so the drawing starts at MARGIN
    xs0 = [n.box()[0] for n in nodes] + [r[0] for r in rect.values()]
    ys0 = [n.top for n in nodes] + [r[1] for r in rect.values()]
    dx, dy = MARGIN - min(xs0), MARGIN - min(ys0)
    for n in nodes: n.move(dx, dy)
    rect = {k: (r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy) for k, r in rect.items()}

    # group labels are obstacles for edges and chips
    labels = []
    for gid, r in rect.items():
        g = groups[gid]
        lw = text_w(g.get("label", gid), 7.4, 12.5) + (24 if g.get("icon") else 0) + 16
        st = style_of(g, gid in parent)
        if VENDOR.match(st) and st in ("aws", "aws-vpc", "aws-region", "aws-private", "aws-public"):
            labels.append((gid, (r[0], r[1], r[0] + lw + 24, r[1] + 32)))
        else:
            labels.append((gid, (r[0] + 6, r[1] + 4, r[0] + lw + 12, r[1] + 30)))

    # layout checks
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if hits(a.box(), b.box()):
                warn(f"nodes {a.id} and {b.id} overlap; move one of them")
    ids = list(rect)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if a in ancestors(b) or b in ancestors(a):
                continue
            if hits(rect[a], rect[b]):
                warn(f"groups {a} and {b} overlap; leave more grid space between their members")
        for n in nodes:
            if a not in ancestors(n.id) and hits(inflate(n.box(), -4), rect[a]):
                warn(f"node {n.id} sits inside group {a}'s box but isn't in it")
    for gid in ids:
        p = parent.get(gid)
        if p and not (rect[p][0] <= rect[gid][0] and rect[gid][2] <= rect[p][2] and rect[p][1] <= rect[gid][1] and rect[gid][3] <= rect[p][3]):
            warn(f"group {gid} sticks out of {p}")

    # route edges, primary first
    edges = []
    for i, e in enumerate(spec.get("edges", [])):
        e = dict(e)
        if e["from"] not in by or e["to"] not in by:
            sys.exit(f"edge {e['from']}->{e['to']} names an unknown node")
        e.setdefault("kind", "internal")
        if e["kind"] not in KINDS:
            sys.exit(f"edge {e['from']}->{e['to']}: kind must be one of {', '.join(KINDS)}")
        e["id"] = e.get("id") or f"{e['from']}--{e['to']}"
        e["_i"] = i
        edges.append(e)
    routed, ports = [], []
    for e in sorted(edges, key=lambda e: (KIND_ORDER[e["kind"]], e["_i"])):
        A, B = by[e["from"]], by[e["to"]]
        scored = []
        for oa in (0, LANE, -LANE):
            for ob in (0, LANE, -LANE):
                cands = candidates(A, B, oa, ob)
                if e.get("route"):
                    cands = [c for c in cands if c[0].startswith(e["route"])] or cands
                for name, pts, sa, sb in cands:
                    s, why = score(pts, e, nodes, labels, routed)
                    s += 3 * (oa != 0) + 3 * (ob != 0)
                    if port_clash(A.id, sa, oa, "out", ports) or port_clash(B.id, sb, ob, "in", ports):
                        s += 250; why = why + ["shares a port with an edge going the other way"]
                    scored.append((s, why, name, pts, (A.id, sa, oa), (B.id, sb, ob)))
        s, why, e["shape"], pts, pa, pb = min(scored, key=lambda t: t[0])
        if s >= 250:
            warn(f"edge {e['id']}: {'; '.join(dict.fromkeys(why))}. Move a node or add a grid column/row")
        ports += [(*pa, "out"), (*pb, "in")]
        e["pts"] = pts
        routed.append(e)

    chips = []
    borders = [b for r in rect.values() for b in ((r[0], r[1] - 1, r[2], r[1] + 1), (r[0], r[3] - 1, r[2], r[3] + 1),
                                                   (r[0] - 1, r[1], r[0] + 1, r[3]), (r[2] - 1, r[1], r[2] + 1, r[3]))]
    for e in sorted(edges, key=lambda e: (KIND_ORDER[e["kind"]], e["_i"])):
        if e.get("label") or e.get("step"):
            e["chip"] = place_chip(e, nodes, labels, chips, routed, borders)

    # canvas size
    xs = [n.box()[2] for n in nodes] + [r[2] for r in rect.values()] + [p[0] for e in edges for p in e["pts"]]
    ys = [n.bottom for n in nodes] + [r[3] for r in rect.values()] + [p[1] for e in edges for p in e["pts"]]
    W, H = int(max(xs) + MARGIN), int(max(ys) + MARGIN)

    # ── emit ──
    order = sorted(rect, key=lambda g: len(ancestors(g)))
    ghtml = []
    for gid in order:
        g, r = groups[gid], rect[gid]
        st = style_of(g, gid in parent)
        cls = ["group"]
        if VENDOR.match(st):
            base = st.split("-")[0]
            cls += [base] + ([st] if st != base else [])
        else:
            cls.append(st)
        if g.get("tone"): cls.append(f"tone-{g['tone']}")
        inner = label_html(g, icondir, "g-bar" if st == "window" else "g-label")
        ghtml.append(f'      <div class="{" ".join(cls)}" id="group-{esc(gid)}" data-group="{esc(gid)}" '
                     f'style="left:{r[0]:.0f}px;top:{r[1]:.0f}px;width:{r[2]-r[0]:.0f}px;height:{r[3]-r[1]:.0f}px">{inner}</div>')

    ehtml, chtml = [], []
    for e in sorted(edges, key=lambda e: -KIND_ORDER[e["kind"]]):
        k = e["kind"]
        dash = " dev" if k == "vendor" and e.get("dev") else ""
        d = path_d(e["pts"])
        ehtml.append(f'        <path class="e k-{k}{dash}" data-edge="{esc(e["id"])}" d="{d}" marker-end="url(#ar-{k})"/>')
        ehtml.append(f'        <path class="pulse" data-edge="{esc(e["id"])}" d="{d}"/>')
        if "chip" in e:
            x, y = e["chip"]
            step = f'<span class="step">{int(e["step"])}</span>' if e.get("step") else ""
            chtml.append(f'      <span class="chip k-{k}" data-edge="{esc(e["id"])}" style="left:{x:.0f}px;top:{y:.0f}px">'
                         f'{step}{esc(e.get("label", ""))}</span>')

    primary_nodes = {x for e in edges if e["kind"] == "primary" for x in (e["from"], e["to"])}
    nhtml = []
    for n in nodes:
        d = n.d
        tile = " ".join(["tile"] + d.get("tile", "").split())
        cls = "node primary" if n.id in primary_nodes and spec.get("highlightPrimary", True) else "node"
        role = f'<span class="role"><span>{esc(n.role)}</span></span>' if n.role else ""
        icon = d.get("icon")
        if icon and d.get("tileDark"):
            img = f'<img class="lt" src="{icon_tok(icon)}" alt=""><img class="dk" src="{icon_tok(icon + "_dark")}" alt="">'
        else:
            img = f'<img src="{icon_tok(icon)}" alt="">' if icon else ""
        aria = esc(f"{n.name}{', ' + n.role if n.role else ''}")
        nhtml.append(f'      <div class="{cls}" id="node-{esc(n.id)}" data-node="{esc(n.id)}" tabindex="0" role="button" '
                     f'aria-label="{aria}" style="left:{n.cx - n.w / 2:.0f}px;top:{n.top:.0f}px;width:{n.w}px">'
                     f'<span class="{tile}">{img}</span><span class="name"><span>{esc(n.name)}</span></span>{role}</div>')

    used = sorted({e["kind"] for e in edges}, key=KIND_ORDER.get)
    names = {**LEGEND, **spec.get("legend", {})}
    legend = "".join(
        f'<span><svg viewBox="0 0 28 8"><path class="e k-{k}" d="M0 4 H22" marker-end="url(#ar-{k})"/></svg>{esc(names[k])}</span>'
        for k in used)
    flows = spec.get("flows", [])
    tabs = "".join([f'<button type="button" data-flow="all" aria-pressed="true">All</button>'] +
                   [f'<button type="button" data-flow="{esc(f["id"])}" aria-pressed="false">{esc(f["label"])}</button>' for f in flows])

    model = {
        "nodes": [{"id": n.id, "name": n.name, "role": n.role, "note": n.d.get("note", ""), "link": n.d.get("link", ""),
                   "path": " / ".join(groups[g].get("label", g) for g in reversed(ancestors(n.id)))} for n in nodes],
        "edges": [{k: e[k] for k in ("id", "from", "to", "kind", "label", "flow", "step", "say") if k in e} for e in edges],
        "flows": [{"id": f["id"], "label": f["label"]} for f in flows],
    }

    manifest = icondir / "manifest.json"
    used_icons = {n.d.get("icon") for n in nodes} | {g.get("icon") for g in groups.values()}
    sources = []
    if manifest.exists():
        m = json.loads(manifest.read_text())
        for k in sorted(used_icons - {None}):
            src = m.get(k, {}).get("source", "generic")
            label = CREDITS.get(src, src)
            if label not in sources: sources.append(label)
    credit = (f"icons: {esc(' / '.join(sources))} · " if sources else "") + \
             'made with <a href="https://github.com/smilewilson1999/blueprint" target="_blank" rel="noopener">blueprint</a>'

    tpl = (SKILL / "assets" / "template.html").read_text(encoding="utf-8")
    fill = {
        "LANG": esc(spec.get("lang", "en")),
        "TITLE": esc(spec.get("title", "Architecture")),
        "KICKER": f'<div class="kicker">{esc(spec["kicker"])}</div>' if spec.get("kicker") else "",
        "LEDE": f'<p class="lede">{esc(spec["lede"])}</p>' if spec.get("lede") else "",
        "FLOW_TABS": tabs, "W": str(W), "H": str(H),
        "GROUPS": "\n".join(ghtml), "EDGES": "\n".join(ehtml), "CHIPS": "\n".join(chtml), "NODES": "\n".join(nhtml),
        "LEGEND": legend, "FOOT_LEFT": esc(spec.get("footer", "")), "FOOT_RIGHT": credit,
        "MODEL": json.dumps(model, ensure_ascii=False).replace("</", "<\\/"),
    }
    page = re.sub(r"\{\{([A-Z_]+)\}\}", lambda mt: fill[mt.group(1)], tpl)

    # inline fonts and icons
    for tok, fn in (("FONT_INTER", "Inter.woff2"), ("FONT_MONO_400", "IBMPlexMono-400.woff2"), ("FONT_MONO_500", "IBMPlexMono-500.woff2")):
        page = page.replace(f"%%{tok}%%", base64.b64encode((FONTS / fn).read_bytes()).decode())
    for f in sorted(icondir.iterdir()):
        ext = f.suffix.lstrip(".").lower()
        if ext in MIME and icon_tok(f.stem) in page:
            page = page.replace(icon_tok(f.stem), f"data:{MIME[ext]};base64,{base64.b64encode(f.read_bytes()).decode()}")
    left = sorted(set(re.findall(r"%%ICON_([A-Za-z0-9_-]+)%%", page)))
    if left:
        sys.exit(f"missing icon files in {icondir}: {', '.join(left)} (fetch them with fetch_icons.py)")

    out.write_text(page, encoding="utf-8")
    for w in warnings: print(f"WARN {w}")
    print(f"built {out} ({len(page) // 1024} KB, canvas {W}x{H}, {len(nodes)} nodes, {len(edges)} edges, {len(warnings)} warnings)")
    if strict and warnings:
        sys.exit(1)

if __name__ == "__main__":
    main()
