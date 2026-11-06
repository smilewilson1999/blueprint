#!/usr/bin/env python3
"""Render the README cover (light and dark): the architecture diagram in front, the
exploded CoWoS teardown behind it, one window each.

Usage:
  python3 tools/cover.py docs/hero.png docs/hero-dark.png docs/teardown.png docs/teardown-dark.png docs/cover.png

Writes docs/cover.png and docs/cover-dark.png. Needs Playwright with Chromium and Pillow.
"""
import base64, io, pathlib, sys

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "skills" / "blueprint" / "assets" / "fonts"
W, H = 1600, 820

def b64(p): return base64.b64encode(pathlib.Path(p).read_bytes()).decode()

def drawing_only(path):
    """The teardown viewer screenshot without its toolbar, cropped to the drawing."""
    im = Image.open(path).convert("RGB")
    body = im.crop((0, 0, im.width, int(im.height * .86)))
    bg = body.getpixel((4, 4))
    box = ImageChops.difference(body, Image.new("RGB", body.size, bg)).convert("L").point(lambda v: 255 if v > 18 else 0).getbbox()
    pad = 24
    crop = body.crop((box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad))
    buf = io.BytesIO(); crop.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode(), '#%02x%02x%02x' % bg

PAGE = """<!doctype html><html data-theme="{theme}"><meta charset="utf-8"><style>
@font-face {{ font-family: Inter; font-weight: 100 900; src: url(data:font/woff2;base64,{inter}) format("woff2"); }}
@font-face {{ font-family: Plex; font-weight: 400; src: url(data:font/woff2;base64,{mono}) format("woff2"); }}
:root {{ --bg:#F4F1EA; --ink:#2B2622; --ink2:#6F695F; --ink3:#8F8A80; --amber:#B25F28; --amber-ink:#8A4A1B;
  --chip:#FFFFFF; --chip-line:#E3DED3; --glow:rgba(214,132,74,.30); --glow2:rgba(124,147,166,.16); --dot:rgba(43,38,34,.10);
  --win-bar:#F6EFE2; --win-line:#E8DCC4; --win-bg:#F7F7F4; --shadow:rgba(60,40,20,.28); --grain:.05; }}
[data-theme=dark] {{ --bg:#15110E; --ink:#F2ECE3; --ink2:#B3ACA0; --ink3:#8C857A; --amber:#DB8A52; --amber-ink:#EBA877;
  --chip:#211C18; --chip-line:#3A322B; --glow:rgba(219,138,82,.30); --glow2:rgba(124,147,166,.12); --dot:rgba(242,236,227,.07);
  --win-bar:#2E2722; --win-line:#4A3D30; --win-bg:#1E1A17; --shadow:rgba(0,0,0,.7); --grain:.09; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{w}px; height:{h}px; overflow:hidden; background:var(--bg); font-family:Inter; color:var(--ink);
  -webkit-font-smoothing:antialiased; position:relative; }}
.glow {{ position:absolute; inset:0;
  background: radial-gradient(900px 600px at 82% -8%, var(--glow), transparent 62%),
              radial-gradient(700px 520px at -6% 108%, var(--glow2), transparent 60%); }}
.dots {{ position:absolute; inset:0; background-image: radial-gradient(var(--dot) 1px, transparent 1.3px); background-size: 22px 22px;
  -webkit-mask-image: radial-gradient(1100px 700px at 30% 50%, #000 20%, transparent 75%); }}
.grain {{ position:absolute; inset:-50%; opacity:var(--grain); mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }}
.copy {{ position:absolute; left:104px; top:50%; transform:translateY(-50%); width:560px; }}
.pill {{ display:inline-flex; align-items:center; gap:10px; height:30px; padding:0 14px 0 12px; border-radius:15px;
  border:1px solid var(--chip-line); background:color-mix(in oklab, var(--chip) 70%, transparent);
  font: 400 13px/1 Plex; color:var(--ink2); letter-spacing:.01em; }}
.pill i {{ width:7px; height:7px; border-radius:50%; background:var(--amber); box-shadow:0 0 0 4px color-mix(in oklab, var(--amber) 22%, transparent); }}
.word {{ margin-top:28px; font-size:112px; font-weight:620; letter-spacing:-0.055em; line-height:.92; }}
.word span {{ color:var(--amber); }}
.line {{ margin-top:26px; font-size:29px; font-weight:450; letter-spacing:-0.02em; line-height:1.28; color:var(--ink2); }}
.line b {{ color:var(--ink); font-weight:560; }}
.cmd {{ margin-top:40px; display:inline-flex; align-items:center; gap:14px; height:48px; padding:0 20px; border-radius:12px;
  background:var(--chip); border:1px solid var(--chip-line); font: 400 15px/1 Plex; color:var(--ink);
  box-shadow: 0 1px 0 rgba(255,255,255,.04) inset, 0 10px 30px -18px var(--shadow); }}
.cmd em {{ font-style:normal; color:var(--amber); }}
.stage {{ position:absolute; right:236px; top:262px; perspective:2400px; }}
.stage2 {{ position:absolute; right:58px; top:52px; perspective:2400px; }}
.win2 {{ width:372px; border-radius:16px; overflow:hidden; background:{tdbg}; border:1px solid var(--win-line);
  transform: rotateY(-16deg) rotateX(6deg) rotateZ(1deg); transform-origin: 100% 50%; opacity:.97;
  box-shadow: 0 2px 0 rgba(255,255,255,.05) inset, 0 50px 100px -40px var(--shadow), 0 24px 50px -30px var(--shadow); }}
.win2 img {{ display:block; width:100%; }}
.win {{ width:720px; border-radius:16px; overflow:hidden; background:var(--win-bg); border:1px solid var(--win-line);
  transform: rotateY(-16deg) rotateX(6deg) rotateZ(1deg); transform-origin: 100% 50%;
  box-shadow: 0 2px 0 rgba(255,255,255,.05) inset, 0 60px 120px -40px var(--shadow), 0 30px 60px -30px var(--shadow); position:relative; }}
.bar {{ height:40px; display:flex; align-items:center; gap:8px; padding:0 16px; background:var(--win-bar); border-bottom:1px solid var(--win-line); }}
.bar i {{ width:11px; height:11px; border-radius:50%; background:var(--win-line); }}
.bar .t {{ margin-left:10px; font-size:13.5px; font-weight:560; color:var(--ink); }}
.bar .v {{ margin-left:auto; font: 400 12px/1 Plex; color:var(--amber-ink); padding:4px 8px; border-radius:6px; border:1px solid var(--win-line); }}
.win img {{ display:block; width:100%; }}
.pin {{ position:absolute; left:{px}px; top:{py}px; width:30px; height:30px; flex:none; border-radius:15px 15px 15px 3px; background:var(--amber); color:#fff;
  display:grid; place-items:center; font-size:13px; font-weight:600; box-shadow:0 0 0 3px var(--win-bg), 0 8px 18px -6px var(--shadow); }}
.card {{ position:absolute; left:{cx}px; top:{cy}px; width:236px; padding:11px 13px 12px; border-radius:12px; background:var(--chip); border:1px solid var(--chip-line);
  box-shadow: 0 18px 40px -16px var(--shadow); }}
.card .who {{ font: 400 11px/1 Plex; color:var(--ink3); }}
.card .who b {{ font-family:Inter; font-size:12px; font-weight:600; color:var(--ink); margin-right:4px; }}
.card p {{ margin-top:7px; font-size:13.5px; line-height:1.42; color:var(--ink); }}
</style>
<body>
<div class="glow"></div><div class="dots"></div><div class="grain"></div>
<div class="copy">
  <div class="pill"><i></i>two agent skills · reviewed on artifact.cafe</div>
  <div class="word">blueprint<span>.</span></div>
  <div class="line">Diagrams and teardowns<br><b>your team can actually review.</b></div>
  <div class="cmd"><em>$</em> npx skills add smilewilson1999/blueprint</div>
</div>
<div class="stage2"><div class="win2">
  <div class="bar"><i></i><i></i><i></i><span class="t">CoWoS package</span><span class="v">teardown</span></div>
  <img src="data:image/png;base64,{td}">
</div></div>
<div class="stage"><div class="win">
  <div class="bar"><i></i><i></i><i></i><span class="t">Acme checkout platform</span><span class="v">v2</span></div>
  <img src="data:image/png;base64,{img}">
  <div class="pin">M</div><div class="card"><div class="who"><b>Maya</b> guest · on Neon</div>
    <p>Should checkout reads go to a replica before launch?</p></div>
</div></div>
</body></html>"""

def main():
    light, dark, td_light, td_dark, out = sys.argv[1:6]
    out = pathlib.Path(out)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--font-render-hinting=none"])
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1.5)
        for theme, img, td, path in (("light", light, td_light, out), ("dark", dark, td_dark, out.with_name(out.stem + "-dark" + out.suffix))):
            td_img, td_bg = drawing_only(td)
            # the comment pin sits on Neon; positions scale with the 720 px window
            pg.set_content(PAGE.format(theme=theme, w=W, h=H, img=b64(img), td=td_img, tdbg=td_bg, inter=b64(FONTS / "Inter.woff2"),
                                       mono=b64(FONTS / "IBMPlexMono-400.woff2"), px=640, py=110, cx=402, cy=36))
            pg.wait_for_timeout(500)
            pg.screenshot(path=str(path))
            print(f"wrote {path}")
        b.close()

if __name__ == "__main__":
    main()
