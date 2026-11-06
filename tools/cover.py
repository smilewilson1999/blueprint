#!/usr/bin/env python3
"""Render the README cover (light and dark): a centered, symmetric layout. The title on top,
the architecture window floating in the middle, and along the bottom a watermark: the CoWoS
package exploded sideways into one row of parts, outlines only (tools/cover-mark.js).

Usage:
  node tools/cover-mark.js docs/cover-mark.svg
  python3 tools/cover.py docs/hero.png docs/hero-dark.png docs/cover-mark.svg docs/cover.png

Writes docs/cover.png and docs/cover-dark.png. Needs Playwright with Chromium.
"""
import base64, pathlib, sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "skills" / "blueprint" / "assets" / "fonts"
W, H = 1600, 880

def b64(p): return base64.b64encode(pathlib.Path(p).read_bytes()).decode()

PAGE = """<!doctype html><html data-theme="{theme}"><meta charset="utf-8"><style>
@font-face {{ font-family: Inter; font-weight: 100 900; src: url(data:font/woff2;base64,{inter}) format("woff2"); }}
@font-face {{ font-family: Plex; font-weight: 400; src: url(data:font/woff2;base64,{mono}) format("woff2"); }}
:root {{ --bg:#F4F1EA; --ink:#2B2622; --ink2:#6F695F; --amber:#B25F28; --amber-ink:#8A4A1B;
  --chip:#FFFFFF; --chip-line:#E3DED3; --glow:rgba(214,132,74,.22);
  --win-bar:#F6EFE2; --win-line:#E8DCC4; --win-bg:#F7F7F4; --shadow:rgba(60,40,20,.30);
  --mark:.20; --mark-blend:multiply; --mark-filter:none; }}
[data-theme=dark] {{ --bg:#15110E; --ink:#F2ECE3; --ink2:#B3ACA0; --amber:#DB8A52; --amber-ink:#EBA877;
  --chip:#211C18; --chip-line:#3A322B; --glow:rgba(219,138,82,.20);
  --win-bar:#2E2722; --win-line:#4A3D30; --win-bg:#1E1A17; --shadow:rgba(0,0,0,.75);
  --mark:.24; --mark-blend:screen; --mark-filter:invert(1) sepia(.35); }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{w}px; height:{h}px; overflow:hidden; background:var(--bg); font-family:Inter; color:var(--ink);
  -webkit-font-smoothing:antialiased; position:relative; }}
.glow {{ position:absolute; inset:0; background: radial-gradient(1100px 520px at 50% -12%, var(--glow), transparent 70%); }}
.mark {{ position:absolute; left:50%; bottom:22px; width:1480px; margin-left:-740px; opacity:var(--mark);
  mix-blend-mode:var(--mark-blend); filter:var(--mark-filter); pointer-events:none;
  -webkit-mask-image: linear-gradient(90deg, transparent 0, #000 9%, #000 91%, transparent 100%); }}
.head {{ position:absolute; left:0; right:0; top:44px; text-align:center; }}
.pill {{ display:inline-flex; align-items:center; gap:10px; height:28px; padding:0 14px 0 12px; border-radius:14px;
  border:1px solid var(--chip-line); background:color-mix(in oklab, var(--chip) 70%, transparent);
  font: 400 12.5px/1 Plex; color:var(--ink2); letter-spacing:.01em; }}
.pill i {{ width:6px; height:6px; border-radius:50%; background:var(--amber); }}
.word {{ margin-top:16px; font-size:84px; font-weight:620; letter-spacing:-0.055em; line-height:.95; }}
.word span {{ color:var(--amber); }}
.line {{ margin-top:14px; font-size:21px; font-weight:450; letter-spacing:-0.015em; color:var(--ink2); }}
.line b {{ color:var(--ink); font-weight:560; }}
.win {{ position:absolute; left:50%; top:262px; width:{ww}px; margin-left:-{wh}px; border-radius:16px;
  background:var(--win-bg); border:1px solid var(--win-line);
  box-shadow: 0 -1px 0 rgba(255,255,255,.05) inset, 0 40px 120px -30px var(--shadow), 0 18px 50px -24px var(--shadow); }}
.bar {{ height:40px; border-radius:15px 15px 0 0; display:flex; align-items:center; gap:8px; padding:0 16px; background:var(--win-bar); border-bottom:1px solid var(--win-line); }}
.bar i {{ width:11px; height:11px; border-radius:50%; background:var(--win-line); }}
.bar .t {{ margin-left:10px; font-size:13.5px; font-weight:560; color:var(--ink); }}
.bar .v {{ margin-left:auto; font: 400 12px/1 Plex; color:var(--amber-ink); padding:4px 8px; border-radius:6px; border:1px solid var(--win-line); }}
.win img {{ display:block; width:100%; border-radius:0 0 15px 15px; }}
.pin {{ position:absolute; left:{px}px; top:{py}px; width:30px; height:30px; border-radius:15px 15px 15px 3px; background:var(--amber); color:#fff;
  display:grid; place-items:center; font-size:13px; font-weight:600; box-shadow:0 0 0 3px var(--win-bg), 0 8px 18px -6px var(--shadow); }}
.card {{ position:absolute; left:{cx}px; top:{cy}px; width:214px; padding:11px 13px 12px; border-radius:12px; background:var(--chip); border:1px solid var(--chip-line);
  box-shadow: 0 18px 40px -16px var(--shadow); }}
.card .who {{ font: 400 11px/1 Plex; color:var(--ink2); }}
.card .who b {{ font-family:Inter; font-size:12px; font-weight:600; color:var(--ink); margin-right:4px; }}
.card p {{ margin-top:6px; font-size:12.5px; line-height:1.42; color:var(--ink); }}
</style>
<body>
<div class="glow"></div>
<img class="mark" src="data:image/svg+xml;base64,{mark}" alt="">
<div class="head">
  <div class="pill"><i></i>two agent skills · reviewed on artifact.cafe</div>
  <div class="word">blueprint<span>.</span></div>
  <div class="line">Diagrams and teardowns <b>your team can actually review.</b></div>
</div>
<div class="win">
  <div class="bar"><i></i><i></i><i></i><span class="t">Acme checkout platform</span><span class="v">v2</span></div>
  <img src="data:image/png;base64,{img}">
  <div class="pin">M</div><div class="card"><div class="who"><b>Maya</b> guest · on Neon</div>
    <p>Should checkout reads go to a replica before launch?</p></div>
</div>
</body></html>"""

def main():
    light, dark, mark, out = sys.argv[1:5]
    out = pathlib.Path(out)
    ww = 760
    # Neon's logo spans x 1648–1714, y 256–322 in the 1924 px hero render. The pin sits on the
    # tile's top-right corner; the card hangs above and to the right, clear of every logo.
    k = ww / 1924
    nx, ny = 1714 * k, 40 + 236 * k
    pin = dict(px=round(nx) - 2, py=round(ny) - 22, cx=round(nx) + 22, cy=round(ny) - 92)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--font-render-hinting=none"])
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1.5)
        for theme, img, path in (("light", light, out), ("dark", dark, out.with_name(out.stem + "-dark" + out.suffix))):
            pg.set_content(PAGE.format(theme=theme, w=W, h=H, img=b64(img), mark=b64(mark), ww=ww, wh=ww // 2, **pin,
                                       inter=b64(FONTS / "Inter.woff2"), mono=b64(FONTS / "IBMPlexMono-400.woff2")))
            pg.wait_for_timeout(500)
            pg.screenshot(path=str(path))
            print(f"wrote {path}")
        b.close()

if __name__ == "__main__":
    main()
