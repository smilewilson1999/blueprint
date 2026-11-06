#!/bin/sh
# Render the demo film: dist/cowos-teardown.mp4 (1920×1080, 30 fps).
# Needs Node, Python with Playwright (Chromium), and ffmpeg. Takes a few minutes.
set -e
cd "$(dirname "$0")/.."
cache=film/.cache
rm -rf "$cache" && mkdir -p "$cache" dist

# 1. hidden-line frames from the model, split across six processes
count=$(node -e "console.log(require('./film/timeline.js').COUNT)")
step=$(( (count + 5) / 6 ))
for k in 0 1 2 3 4 5; do
  s=$(( k * step )); e=$(( s + step )); [ "$e" -gt "$count" ] && e=$count
  node film/render-frames.js "$s" "$e" "$cache/raw" > /dev/null &
done
wait

# 2. one framing for the whole film, the terminal and the comments
node film/compose.js "$cache/raw" "$cache/svg"

# 3. SVG to PNG in Chromium, then encode
python3 film/rasterize.py "$PWD/$cache/svg" "$cache/png"
ffmpeg -loglevel error -y -framerate 30 -i "$cache/png/f-%04d.png" \
  -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -movflags +faststart dist/cowos-teardown.mp4
echo "wrote dist/cowos-teardown.mp4"
