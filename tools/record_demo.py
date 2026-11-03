#!/usr/bin/env python3
"""Record the README demo: a scripted walk through a built blueprint page, saved as a GIF.

Usage:
  python3 tools/record_demo.py examples/saas/index.html docs/demo.gif

Needs Playwright with Chromium and ffmpeg. A drawn cursor is injected into the page so
the viewer can see what is being pointed at; the page itself is unchanged.
"""
import pathlib, shutil, subprocess, sys, tempfile

from playwright.sync_api import sync_playwright

CURSOR = """
const c = document.createElement('div');
c.id = '__cursor';
c.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M4 2.5 L4 19 L8.6 14.8 L11.6 21.3 L14.4 20 L11.5 13.7 L17.8 13.4 Z" fill="#2B2622" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
Object.assign(c.style, {position:'fixed', left:'0', top:'0', zIndex: 99999, pointerEvents:'none',
  transition:'transform .55s cubic-bezier(.22,1,.36,1)', transform:'translate(600px, 120px)'});
document.body.appendChild(c);
window.__move = (x, y) => { c.style.transform = `translate(${x}px, ${y}px)`; };
"""

def main():
    src, out = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2])
    tmp = pathlib.Path(tempfile.mkdtemp())
    frame = [0]
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--font-render-hinting=none"])
        page = b.new_page(viewport={"width": 1180, "height": 1090}, device_scale_factor=1.5)
        page.goto(src.as_uri())
        page.wait_for_timeout(800)
        page.evaluate(CURSOR)

        def hold(seconds, fps=12):
            for _ in range(int(seconds * fps)):
                page.screenshot(path=str(tmp / f"f{frame[0]:04d}.png"))
                frame[0] += 1

        def point(selector, settle=0.7):
            box = page.locator(selector).first.bounding_box()
            x, y = box["x"] + box["width"] / 2, box["y"] + min(box["height"] / 2, 32)
            page.evaluate(f"__move({x}, {y})")
            page.mouse.move(x, y)
            hold(settle)

        def click(selector, settle=1.2):
            point(selector, 0.6)
            page.locator(selector).first.click()
            hold(settle)

        hold(1.2)
        point("#node-hono", 1.6)                      # hover: what does Hono talk to
        point("#node-neon", 1.2)
        click(".seg button[data-flow=request]", 2.2)  # the request path lights up
        point("#steps li:nth-child(3)", 1.4)          # one step at a time
        click("#node-hono", 2.2)                      # inspector
        click(".seg button[data-flow=deploy]", 1.8)
        click("#theme", 2.0)                          # dark theme
        click(".seg button[data-flow=all]", 1.4)
        click("#theme", 1.0)
        b.close()

    palette = tmp / "palette.png"
    vf = "scale=1000:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "12", "-i", str(tmp / "f%04d.png"),
                    "-vf", f"{vf},palettegen=stats_mode=diff:max_colors=200", str(palette)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "12", "-i", str(tmp / "f%04d.png"), "-i", str(palette),
                    "-lavfi", f"{vf}[x];[x][1:v]paletteuse=dither=sierra2_4a:diff_mode=rectangle", str(out)], check=True)
    shutil.rmtree(tmp)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB, {frame[0]} frames)")

if __name__ == "__main__":
    main()
