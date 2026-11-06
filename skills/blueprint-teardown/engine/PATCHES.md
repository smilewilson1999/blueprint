# Patches to the upstream engine

`engine/` is [teardown](https://github.com/jakubkrehel/skills/tree/main/skills/teardown)
by Jakub Krehel (MIT, see `LICENSE` in this folder), copied from commit
[`60bf140`](https://github.com/jakubkrehel/skills/commit/60bf140e43c98b248e6594487384ec967e89d98a)
(2026-11-01).

Everything here is unchanged except what this file lists. To update from upstream,
copy the new files over, reapply these patches, and rerun the checks at the end.

| File | Change |
| --- | --- |
| `SKILL.md` → `TEARDOWN.md` | Renamed, content unchanged, so skill installers don't mistake the engine for a second skill named `teardown` |
| `scripts/test-*.cjs` | Not copied; they test the upstream skill itself |
| `assets/viewer.js` | Three patches, below |
| `assets/viewer.html` | One patch, below |

## 1. Labels on by default (`viewer.js`)

```diff
-  annotate: false,
+  annotate: d.annotate ?? true,
```

A review comment pinned to a part name, such as `SOC DIE`, anchors to that label's
text. With labels off, a reviewer opening the page has no label to find, so the
comment shows as outdated. A drawing can still opt out with `"annotate": false` in
its configuration.

## 2. A lighter transition (`viewer.js`)

```diff
   ease: DrawingFlipbook.easeInOutCubic,
+  frames: 40
```

The exploded and assembled views animate between each other from pre-rendered
frames. Upstream renders 85. The 700 ms transition at 60 fps needs about 42, and
fewer frames are ready sooner: measured on the CoWoS example, the transition was
ready in about 6 s instead of 16 s.

## 3. Fade instead of a jump (`viewer.js`, `viewer.html`)

Until those frames exist, switching views swapped the drawing in one jump. Now the
current view dims to 35% and the new one fades in when it has rendered:

- `viewer.js`: `setView` sets `data-fading` and a `fadeIn` flag when `play()`
  returns false; `render` fades the new drawing in and clears both, also on error.
- `viewer.html`: an opacity transition on `#drawing > svg:first-child`, the dimmed
  `[data-fading]` state, and no transition under `prefers-reduced-motion`.

## Checks after an update

```sh
node engine/scripts/proof.cjs drawing.json proof/ --quick
node engine/scripts/build-viewer.cjs drawing.json dist/index.html
node engine/scripts/check-viewer.cjs dist/index.html check/
```

Then open `dist/index.html`, switch views right after it loads (it should fade),
and again after a few seconds (it should animate).
