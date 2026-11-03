#!/usr/bin/env python3
"""Open a built blueprint page in a real browser window and walk the real macOS cursor
through the demo, for a screen recorder (Screen Studio, QuickTime) to capture.

Usage:
  python3 tools/drive_cursor.py examples/saas/index.html [--go-file /tmp/bp-go] [--check]

1. The window opens and waits. Point the recorder at it and start recording.
2. Create the go file (touch /tmp/bp-go) or press Enter: the tour starts 2s later.
--check opens the window, prints its size and the page height, and closes.
3. The window stays open until you press Ctrl-C, so the recording can end on a still frame.

Needs Playwright with Chromium, pyobjc-framework-Quartz, and Accessibility permission for
the app running this script. Don't touch the mouse during the tour.
"""
import os, pathlib, sys, threading, time

import Quartz
from playwright.sync_api import sync_playwright

WIN_X, WIN_Y, WIN_W, WIN_H = 150, 40, 1220, 930

def post(kind, x, y):
    ev = Quartz.CGEventCreateMouseEvent(None, kind, (x, y), Quartz.kCGMouseButtonLeft)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

def cursor():
    p = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
    return p.x, p.y

def ease(t):
    return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2

def glide(x, y, seconds):
    sx, sy = cursor()
    steps = max(2, int(seconds * 120))
    for i in range(1, steps + 1):
        k = ease(i / steps)
        post(Quartz.kCGEventMouseMoved, sx + (x - sx) * k, sy + (y - sy) * k)
        time.sleep(seconds / steps)

def click():
    x, y = cursor()
    post(Quartz.kCGEventLeftMouseDown, x, y); time.sleep(.07)
    post(Quartz.kCGEventLeftMouseUp, x, y)

def main():
    args = sys.argv[1:]
    go = "/tmp/bp-go"
    if "--go-file" in args:
        i = args.index("--go-file"); go = args[i + 1]; del args[i:i + 2]
    check = "--check" in args
    args = [a for a in args if a != "--check"]
    src = pathlib.Path(args[0]).resolve().as_uri()
    if os.path.exists(go): os.remove(go)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            "", headless=False, no_viewport=True, ignore_default_args=["--enable-automation"],
            args=[f"--app={src}", f"--window-position={WIN_X},{WIN_Y}", f"--window-size={WIN_W},{WIN_H}",
                  "--hide-scrollbars", "--disable-infobars", "--font-render-hinting=none"])
        page = ctx.pages[0] if ctx.pages else ctx.wait_for_event("page")
        page.wait_for_load_state()
        page.wait_for_timeout(600)
        # fit the whole page in the window; the recorder can zoom back in
        page.evaluate("""() => { const h = document.documentElement;
          const z = Math.min(1, (innerHeight - 8) / h.scrollHeight); h.style.zoom = z; return z; }""")
        page.wait_for_timeout(200)

        def origin():
            # top-left of the page's viewport in screen points
            return page.evaluate("[window.screenX + (window.outerWidth - window.innerWidth) / 2,"
                                 " window.screenY + window.outerHeight - window.innerHeight]")

        def to(selector, seconds=.8):
            ox, oy = origin()
            b = page.locator(selector).first.bounding_box()
            glide(ox + b["x"] + b["width"] / 2, oy + b["y"] + min(b["height"] / 2, 30), seconds)

        def press(selector, after):
            to(selector); time.sleep(.2); click(); time.sleep(after)

        print(f"window open: {page.evaluate('[innerWidth, innerHeight]')} css px. "
              f"Start recording, then `touch {go}` or press Enter.", flush=True)
        if check:
            print("zoom:", page.evaluate("document.documentElement.style.zoom"),
                  "fits:", page.evaluate("document.documentElement.scrollHeight <= innerHeight"),
                  "hono box:", page.locator("#node-hono").bounding_box(), flush=True)
            ctx.close(); return
        if sys.stdin.isatty():
            threading.Thread(target=lambda: (sys.stdin.readline(), open(go, "w").close()), daemon=True).start()
        while not os.path.exists(go):
            time.sleep(.1)
        os.remove(go)
        ox, oy = origin()
        post(Quartz.kCGEventMouseMoved, ox + 760, oy + 60)
        time.sleep(2)

        to("#node-user", 1.0); time.sleep(.8)
        to("#node-hono", .9); time.sleep(1.6)          # what does Hono talk to
        to("#node-stripe", .7); time.sleep(1.2)
        press(".seg button[data-flow=request]", 2.2)   # the request path lights up
        to("#steps li:nth-child(2)", .8); time.sleep(1.1)
        to("#steps li:nth-child(3)", .4); time.sleep(1.1)
        press("#node-hono", 2.6)                       # inspector
        press(".seg button[data-flow=deploy]", 2.0)
        press("#theme", 2.2)                           # dark theme
        press(".seg button[data-flow=all]", 1.4)
        press("#theme", 1.2)
        glide(ox + 900, oy + 120, 1.0)
        print("tour done. Stop the recording, then Ctrl-C here.", flush=True)
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            pass
        ctx.close()

if __name__ == "__main__":
    main()
