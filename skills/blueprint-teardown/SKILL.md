---
name: blueprint-teardown
description: "Create exploded technical illustrations of physical things and layered build-ups, such as semiconductor packages (CoWoS, InFO, flip-chip BGA, HBM stacks), boards, devices and their internals, or a concept drawn as stacked plates, as an interactive page with assembled and exploded views, part labels, color, SVG/PNG/PDF downloads, and review on artifact.cafe. Use this skill when the user asks for a teardown, exploded view, cutaway, package or chip structure, stack-up, or how a physical object is built, in any language. For services, request flows and cloud architecture, use the blueprint skill instead."
license: MIT (see LICENSE); the engine is teardown by Jakub Krehel, MIT (see engine/LICENSE)
compatibility: Node 22+ with npm; Chrome or Chromium for proofs and checks
---

# blueprint-teardown

Builds one 3D model from plain parameters, projects it with hidden lines removed,
and packages a single HTML page: assembled and exploded views with a smooth
transition, part labels, parameter sliders, coloring, and SVG, PNG and PDF
downloads. The page is published to artifact.cafe, where reviewers comment on any
part by name without an account.

The drawing engine is [teardown](https://github.com/jakubkrehel/skills/tree/main/skills/teardown)
by Jakub Krehel, in `engine/` with the small changes listed in `engine/PATCHES.md`.

## Which skill

| The user wants to show | Use |
| --- | --- |
| How services, APIs and data stores connect; a request path | `blueprint` |
| How a physical object is built: layers, parts, how they fit | `blueprint-teardown` |
| A concept with no physical form, explained as layers (display pixels, an interface stack) | `blueprint-teardown`, as stacked plates |

## Workflow

1. **Set up the project.** Copy this skill's `engine/assets/` and `engine/scripts/`
   into the project's `tools/teardown/`, then
   `npm install jspdf svg2pdf.js @fontsource-variable/inter`. The engine's own docs
   use the `tools/teardown/` paths from here on.
2. **Follow `engine/TEARDOWN.md`** for the drawing itself, steps 1–6: the evidence
   record, choosing views, one model, inking, proofing and packaging. Read the
   reference files it names at each step; they live beside it in `engine/`.
3. **Apply the rules below** while you do.
4. **Publish for review** (below).

## Rules this skill adds

- **Name parts as a reader labels them** (`Copper lid`, `HBM stacks`), and keep part
  IDs and names the same across versions. Labels are on by default, and review
  comments anchor to them: a renamed part leaves its comments outdated.
- **Say what is invented.** Unless the user supplied real drawings or dimensions,
  the drawing is a concept. Keep the configuration's `concept` flag on, and say in
  its `description` what is estimated and whether an axis is exaggerated. A chip
  package is unreadable at true thickness, so stretching the vertical axis is
  normal; say so.
- **Color by material**, so a reader can tell parts apart at a glance. In
  `colors.hues` (OKLab hue angles), roughly: copper 55, gold or solder 85, organic
  substrate 150, memory 185, silicon 245, logic die 290. Fill the large plates and
  leave small repeated features as linework.
- **Keep repeated small features light.** Hundreds of bumps or balls at the default
  lathe resolution make every view slow and the transition late. Use 12–16
  segments for features a few millimetres across; they still read round.
- **Expose the parameters people argue about** as sliders: stack height, die count,
  layer count. Derive every dependent size from them so the model stays coherent at
  each extreme.

## Publish for review

The built `dist/index.html` is one self-contained file. Publish its folder with the
artifact-cafe skill or CLI (`npx artifact-cafe@latest publish dist`), with the
drawing's title as the artifact title and version notes as bullets. A new artifact
is unlisted: anyone with the link can open and comment, no account. Say so when you
share the link.

When comments come back, change the model or configuration, rebuild, and publish the
next version into the same artifact. Reply to each thread with what changed.

The page works inside the review frame: rendering, the view transition, labels and
downloads were tested there.

## Demo film (optional)

For a launch video or a deck, the repository's `examples/cowos/film/` renders the
same model frame by frame into an MP4: parts lifting off one by one, a following
camera, an agent session typing on the left and review comments landing on the
parts. Copy it and edit `timeline.js` for another drawing.
