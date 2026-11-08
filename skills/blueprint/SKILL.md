---
name: blueprint
description: "Create premium, interactive architecture diagrams of tech stacks, system architectures, infra layouts and service topologies, with real brand logos, grouped windows, numbered request flows and orthogonal edges, delivered as one self-contained HTML file that publishes to artifact.cafe for review (plus PNGs). Use this skill whenever the user asks for an architecture / system / stack / infra diagram, a tech-stack overview, a service topology, a cloud-vendor-style diagram, a diagram to get feedback on, or wants tech logos arranged into a picture of how their services connect, in any language, even if they don't name an output format and even if the tools involved aren't cloud services. For physical spaces, floor plans and furniture layouts use blueprint-space; for exploded physical objects and layered internals use blueprint-teardown."
license: MIT (see LICENSE); bundled fonts are SIL OFL 1.1
compatibility: Python 3.9+ and network access to fetch logos; PNG output also needs Playwright with Chromium
---

# blueprint

Turns a short JSON description of a system into an interactive architecture
page in the Cafe OS style: warm paper, real logos on light tiles, groups drawn
as small OS windows, one amber request path with numbered steps, flow tabs, an
inspector, and light and dark themes. The HTML is the source of truth. It is
built to be reviewed on artifact.cafe, where every node name is real text a
reviewer can quote and every node has a stable id.

## Which skill

| The user wants to show | Use |
| --- | --- |
| How services, APIs and data stores connect; a request path | `blueprint` |
| How a physical object is built: layers, parts, how they fit | `blueprint-teardown` |
| A physical space: rooms, floor plan, furniture placement | `blueprint-space` |

## Workflow

1. Settle the content: nodes, groups, edges, flows
2. Fetch icons: `scripts/fetch_icons.py`
3. Write `blueprint.json`: read `references/spec.md`
4. Build: `scripts/blueprint.py`, fix every `WARN`
5. Render PNGs and look at them
6. Publish to artifact.cafe for review (or deliver the HTML / PNG)

## Step 1: Content

From the user's list of technologies, decide:

- **Nodes**: one per technology, with its official name and a short lowercase role (`api routes`, `sqlite db`), plus a one-sentence `note` on what it does here when you know it.
- **Groups**: a box around things that share a runtime, vendor or repo. Nest one level; deeper gets noisy.
- **Edges**: `primary` for the one path a reader should follow (number it with `step`), `internal` for other calls, `async` for events, queues and webhooks, `dev` for CI and deploys.
- **Flows**: when the system has more than one story (request path, nightly sync, deploy), give each a flow so the reader can switch between them.

If the user gave only a flat list, infer sensible groups and flows from what the
tools are. Ask only when a tool is ambiguous enough that the diagram would be
wrong either way.

## Step 2: Icons

```bash
python3 scripts/fetch_icons.py <icons-dir> nextjs hono neon "actions:githubactions" "betterauth:better-auth" "orpc=https://orpc.unnoq.com/logo.webp"
python3 scripts/fetch_icons.py <icons-dir> "cron:lucide/clock" "queue:lucide/list-ordered"
```

Spec forms: `name`, `name:slug`, `name=URL`, `name:lucide/<icon>`, and the
vendor forms `name:aws/<Name>`, `name:gcp/<Product>`, `name:azure/<Name>`. The
script tries svgl, then devicon, then gilbarbara/logos, writes `manifest.json`,
saves `<name>_dark` when the brand has a dark-theme mark, and flags white fills.

- **Never recolor a logo.** If it's white or too light for a light tile, use `"tile": "dark"`. The `white_fill` flag is a heuristic: glance at the SVG first.
- **Official marks only.** When every source misses, find the official file in the project's repo or site and pass it as `name=URL`.
- **Abstract concepts get Lucide pictograms** (`devenv:lucide/terminal`, `cron:lucide/clock`), never text in a tile or emoji. Generic people and machines: copy a glyph from `assets/generic/` into the icons dir.
- **Vendor sub-products** without their own mark (Cloudflare D1, R2) reuse the vendor logo; the name carries the distinction.
- **Group-label icons are 15px**: use the brand's square mark, never a wordmark.
- **AWS, Google Cloud and Azure** use their vendors' own icons and drawing rules inside their area. Read `references/vendors.md` before drawing one.

## Step 3: Spec

Write `blueprint.json` per `references/spec.md`. Place nodes on a grid with
`at: [col, row]`, in reading order: the request enters on the left or top and
the primary path runs in a straight line where it can. Keep node `id`s stable
between versions; comments on the review page attach to them.

## Step 4: Build

```bash
python3 scripts/blueprint.py blueprint.json <icons-dir> index.html
```

The build lays everything out, routes edges around nodes and group labels,
inlines the fonts and icons, and prints a `WARN` line for each overlap,
collision or crowded label it finds. Fix warnings by moving nodes on the grid,
then rebuild. Don't hand-edit the generated HTML: change the spec.

## Step 5: Look at it

```bash
python3 scripts/render_png.py index.html diagram.png --scale 2
```

This writes `diagram.png` and `diagram-dark.png` (canvas only; `--selector .page`
for the whole page). Read both images. Check:

- the primary path reads left to right (or top to bottom) without doubling back
- no edge crosses label text and no label chip sits on a node or a window title bar
- every icon is visible in both themes, including group-label marks in dark
- groups don't touch each other and nothing sticks out of its group

If Japanese text renders with Chinese glyphs, the host is missing a Japanese
font: the script prints a fix.

## Step 6: Deliver

**Default: publish for review on artifact.cafe.** The HTML is one
self-contained file, so publish the folder that holds `index.html` with the
artifact-cafe skill or CLI (`npx artifact-cafe@latest publish <dir>`), using the
diagram's title as the artifact title. Share the review URL. Reviewers can
comment on any node name, role, edge label or step without an account.

When comments come back, change `blueprint.json`, rebuild, and publish the next
version into the same artifact. Keep node ids and names stable where the
component is unchanged: comments belong to the version they were made on, and
an unchanged anchor is what lets a thread be found again in the next one.
Reply to each thread with what changed.

Also on request:

- **PNG**: the `render_png.py` pair, for Slack, slides or a README.
- **HTML**: the built file itself; it works offline.

The footer credits the icon sources from `manifest.json` automatically. Brand
logos remain the trademarks of their owners.
