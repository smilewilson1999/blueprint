#!/usr/bin/env python3
"""Cut a light and a dark render of the same diagram along a diagonal, into one image.

Usage:
  python3 tools/light_dark.py docs/ai.png docs/ai-dark.png docs/light-dark.png

Light keeps the upper left, dark the lower right. Both inputs come from render_png.py,
so they are the same size.
"""
import sys
from PIL import Image, ImageDraw

def main():
    light, dark = Image.open(sys.argv[1]).convert("RGB"), Image.open(sys.argv[2]).convert("RGB")
    w, h = light.size
    top, bottom = w * .62, w * .38          # where the cut meets the top and bottom edges
    mask = Image.new("L", (w * 4, h * 4), 0)  # drawn large, scaled down, for a clean edge
    ImageDraw.Draw(mask).polygon([(top * 4, 0), (w * 4, 0), (w * 4, h * 4), (bottom * 4, h * 4)], fill=255)
    out = Image.composite(dark, light, mask.resize((w, h), Image.LANCZOS))
    out.save(sys.argv[3], optimize=True)
    print(f"wrote {sys.argv[3]} ({w}x{h})")

if __name__ == "__main__":
    main()
