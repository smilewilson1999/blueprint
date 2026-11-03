#!/usr/bin/env python3
"""Record the README demo: a scripted walk through a built blueprint page, saved as a GIF.

Usage:
  python3 tools/record_demo.py examples/saas/index.html out.gif

Needs Playwright with Chromium and ffmpeg. Frames are captured one at a time, so the
page's own CSS animations are slowed to match the capture speed and every frame stands
for exactly 1/FPS of a second; the drawn cursor moves on an eased path, frame by frame.
"""
import pathlib, shutil, subprocess, sys, tempfile, time

from playwright.sync_api import sync_playwright

FPS = 20
WIDTH, HEIGHT, OUT_W = 1180, 980, 1000
CURSOR = """
const c = document.createElement('div');
c.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M4 2.5 L4 19 L8.6 14.8 L11.6 21.3 L14.4 20 L11.5 13.7 L17.8 13.4 Z" fill="#2B2622" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
Object.assign(c.style, {position:'fixed', left:'0', top:'0', zIndex:99999, pointerEvents:'none'});
document.body.appendChild(c);
const st = document.createElement('style');
st.textContent = '@keyframes __ripple { from { transform: translate(-50%,-50%) scale(.3); opacity:.55 } to { transform: translate(-50%,-50%) scale(1.6); opacity:0 } }';
document.head.appendChild(st);
window.__at = (x, y) => { c.style.transform = `translate(${x - 3}px, ${y - 2}px)`; };
window.__ripple = (x, y) => {
  const r = document.createElement('div');
  Object.assign(r.style, {position:'fixed', left:x+'px', top:y+'px', width:'34px', height:'34px', borderRadius:'50%',
    border:'2px solid #B25F28', zIndex:99998, pointerEvents:'none', animation:'__ripple .5s cubic-bezier(.22,1,.36,1) forwards'});
  document.body.appendChild(r); setTimeout(() => r.remove(), 1200);
};
"""

def ease(t):  # ease-in-out cubic
    return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2

def main():
    src, out = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2])
    tmp = pathlib.Path(tempfile.mkdtemp())
    n = [0]
    pos = [WIDTH * .62, 150.0]
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--font-render-hinting=none"])
        page = b.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1.5)
        page.goto(src.as_uri())
        page.wait_for_timeout(800)
        page.evaluate(CURSOR)
        page.evaluate(f"__at({pos[0]}, {pos[1]})")

        # measure how long one capture takes, then slow the page's animations to match
        t0 = time.time()
        for _ in range(5): page.screenshot()
        per_shot = (time.time() - t0) / 5
        cdp = page.context.new_cdp_session(page)
        cdp.send("Animation.enable")
        cdp.send("Animation.setPlaybackRate", {"playbackRate": min(1.0, (1 / FPS) / per_shot)})

        def shot():
            page.screenshot(path=str(tmp / f"f{n[0]:04d}.png"))
            n[0] += 1

        def hold(seconds):
            for _ in range(round(seconds * FPS)): shot()

        def glide(selector, seconds=.7):
            box = page.locator(selector).first.bounding_box()
            tx, ty = box["x"] + box["width"] / 2, box["y"] + min(box["height"] / 2, 30)
            sx, sy = pos
            frames = max(2, round(seconds * FPS))
            for i in range(1, frames + 1):
                k = ease(i / frames)
                x, y = sx + (tx - sx) * k, sy + (ty - sy) * k
                page.evaluate(f"__at({x}, {y})")
                page.mouse.move(x, y)
                shot()
            pos[:] = [tx, ty]

        def click(selector, after):
            glide(selector)
            hold(.15)
            page.evaluate(f"__ripple({pos[0]}, {pos[1]})")
            page.mouse.down(); page.mouse.up()
            hold(after)

        hold(1.0)
        glide("#node-user", .9); hold(.6)
        glide("#node-hono", .8); hold(1.4)              # what does Hono talk to
        glide("#node-stripe", .6); hold(1.0)
        click(".seg button[data-flow=request]", 2.0)    # the request path lights up
        glide("#steps li:nth-child(2)", .7); hold(1.0)  # one step at a time
        glide("#steps li:nth-child(3)", .3); hold(1.0)
        click("#node-hono", 2.2)                        # inspector
        click(".seg button[data-flow=deploy]", 1.8)
        click("#theme", 1.8)                            # dark theme
        click(".seg button[data-flow=all]", 1.2)
        click("#theme", 1.2)
        b.close()

    palette = tmp / "palette.png"
    vf = f"scale={OUT_W}:-1:flags=lanczos"
    frames = ["-framerate", str(FPS), "-i", str(tmp / "f%04d.png")]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *frames,
                    "-vf", f"{vf},palettegen=stats_mode=diff:max_colors=200", str(palette)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *frames, "-i", str(palette),
                    "-lavfi", f"{vf}[x];[x][1:v]paletteuse=dither=sierra2_4a:diff_mode=rectangle", str(out)], check=True)
    shutil.rmtree(tmp)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB, {n[0]} frames at {FPS} fps, capture {per_shot * 1000:.0f} ms/frame)")

if __name__ == "__main__":
    main()
