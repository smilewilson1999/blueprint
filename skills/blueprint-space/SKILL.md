---
name: blueprint-space
description: "Create interactive 3D and Plan prototypes of physical spaces: offices, co-working floors, shops, showrooms and venues, from a short space.json in metres. Use for space planning, floor plans, room layouts or furniture arrangements, in any language. Orbit, inspect named rooms and pieces, edit furniture on a grid and export the updated JSON, in one offline HTML page for review on artifact.cafe (plus PNGs). For software architecture and request paths use blueprint; for exploded objects and layered internals use blueprint-teardown."
license: MIT (see LICENSE); three.js is MIT (see assets/vendor/LICENSE); bundled fonts are SIL OFL 1.1
compatibility: Python 3.9+; viewing needs a browser with WebGL; PNGs and browser checks also need Python Playwright with Chromium
---

# blueprint-space

Turns `space.json` into one offline page in the Cafe OS style: warm paper,
muted room colors, bundled Inter and IBM Plex Mono, light and dark themes.
Reviewers can orbit in 3D, switch to Plan, select any room or furniture piece,
and quote its real text name and stable id. Edit layout moves and rotates
furniture; Export JSON saves the same schema for the next build.

## Which skill

| The user wants to show | Use |
| --- | --- |
| How services, APIs and data stores connect; a request path | `blueprint` |
| How a physical object is built: layers, parts, how they fit | `blueprint-teardown` |
| A physical space: rooms, floor plan, furniture placement | `blueprint-space` |

This skill covers space prototypes. It does not draw UI wireframes or product
flows. Unless the user supplied measured drawings, state that dimensions are
invented. The model is a layout study, not a construction drawing.

## Workflow

1. Settle the space: floor, rooms, walls, openings and furniture
2. Write `space.json`: read `references/spec.md`
3. Build: `scripts/space.py`, fix every `WARN`
4. Check interactions and the JSON round trip
5. Render light and dark PNGs in both views and look at them
6. Publish to artifact.cafe for review when authorized (or deliver HTML / PNG)

Commands below run from the project directory, with the installed skill's
scripts called by path. Replace `/path/to/blueprint-space` with the installed
skill directory. This keeps `dist/`, `check/` and PNGs in the project rather
than inside the skill package. The builder needs only Python's standard
library. Three.js **0.170.0** is vendored unchanged with its MIT license in
`assets/vendor/`; fonts and the module are embedded, with no CDN at view time.

## Step 1: Content

Choose a floor outline and named room zones in metres. Add walls explicitly:
room boundaries describe zones and do not automatically become walls. Add
doors and windows on their wall segments. Pick furniture types and dimensions
that leave room for circulation and door clearance.

For an underspecified brief, choose a coherent layout and record the
assumptions in the lede, footer or object notes. Use a fictional name and no
real address unless the user supplies one.

## Step 2: Spec

Read `references/spec.md`, then write only `space.json`. Positions are `[x, z]`
on the floor; furniture sizes are `[width, depth, height]`. Rotation is clockwise
in Plan, in degrees. All room, wall, opening and furniture ids are globally
unique. Keep ids and names stable when the part is unchanged: reviewers use
them to identify their comments.

## Step 3: Build

```bash
python3 /path/to/blueprint-space/scripts/space.py space.json dist/index.html --strict
```

Fix every `WARN`: overlaps, furniture outside its room or floor, furniture
crossing walls, blocked doors, unknown references and invalid openings. Invalid
schema always fails. `--strict` also fails on layout warnings and writes no new
HTML; an older output file may still exist. Change the JSON and rebuild rather
than editing the generated page. Keep `dist/` for `index.html` only; checks and
PNGs stay outside it.

Wall heights remain in the source; 3D displays a cutaway capped at 1.2 m and
Plan displays wall footprints. Windows appear within the visible cutaway.

## Step 4: Check it

```bash
python3 /path/to/blueprint-space/scripts/check_space.py dist/index.html check/
```

For a furnished space, this exercises orbit, V/Plan, E/edit, dragging the first
piece, 15° rotation, grid snapping, room and piece inspectors, a model-derived
cross-room move with room-count refresh and strict export/rebuild, theme
switching, and touch orbit/pinch at 390 px. It rejects page errors and external
requests. It downloads an unchanged JSON and requires its rebuilt HTML to be
identical, then downloads edited JSON and requires moved positions, room
assignments and ids to survive rebuilding. If the model has one room or no
free grid-snapped cross-room spot, the cross-room case is reported as skipped;
the other checks still run. `check/` holds the downloaded files and browser
proofs.

Controls: drag empty space to orbit in 3D or pan in Plan; right-drag or
Shift-drag pans in 3D; scroll or pinch zooms; Fit / `0` reframes. One finger
orbits, two fingers pinch and pan inside the viewport. In Edit layout (`E`),
drag furniture, use the inspector's rotation buttons or `R` / Shift-R, or move
the selected piece by one grid step with arrow keys. `V` changes views.

Edits are held in the page until Export JSON downloads `space.json`. Export
before closing or rebuilding. Edits can create overlaps: run the strict build
on the downloaded file to check clearances before using it as the next source.
Keep that exported file; rebuilding the old source would discard the changes.

## Step 5: Look at it

```bash
python3 /path/to/blueprint-space/scripts/render_png.py dist/index.html space.png --view both
python3 /path/to/blueprint-space/scripts/render_png.py dist/index.html phone.png --view both --width 390 --height 844
```

Each command writes four files: light and dark 3D, and `-plan` / `-plan-dark`.
`--scale 2` increases resolution; `--view 3d` (default) or `--view plan` renders
only that pair. Read every image. Check readable room labels, visible furniture
and openings, clear circulation, theme contrast and usable controls at 390 px.
On small screens, zoom in for individual pieces and use the room/furniture
lists below the drawing. Build outputs and proof images belong outside the
installed skill folder.

## Step 6: Deliver

**Default delivery, when publishing is authorized: review on artifact.cafe.**
Publish only the `dist/` folder with the artifact-cafe skill or CLI
(`npx artifact-cafe@latest publish dist`), using the space title. Keep `check/`
and PNGs outside the published folder. Share the review URL. Reviewers can
comment on names, ids and inspector text without an account. If publishing is
outside the authorized scope, deliver the local HTML and PNGs instead.

When comments come back, update `space.json` (starting with the exported file
if the layout was edited), rebuild and publish the next version into the same
artifact. Preserve ids and names for unchanged parts, and reply to each thread
with what changed. Comments belong to the version on which they were made;
stable names and anchors help locate the part in the next version.

The HTML works offline. Keep JSON beside it as the editable source of truth.
