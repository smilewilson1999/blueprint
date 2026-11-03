# blueprint.json

One JSON file describes the whole diagram. You place nodes on a grid and say
who belongs to which group and who talks to whom; `blueprint.py` computes every
pixel, the group boxes, the edge routes and the label positions.

```json
{
  "title": "Acme checkout platform",
  "kicker": "acme / platform / 2026-11",
  "lede": "One or two sentences on what this system does.",
  "footer": "owner: platform team",
  "lang": "en",
  "flows": [{ "id": "request", "label": "Request path" }],
  "groups": [{ "id": "vercel", "label": "Vercel", "icon": "vercel", "meta": "iad1", "contains": ["next", "hono"] }],
  "nodes": [
    { "id": "next", "name": "Next.js", "role": "frontend", "icon": "nextjs", "at": [1, 0],
      "note": "App Router. Renders the storefront.", "link": "https://github.com/acme/web" }
  ],
  "edges": [{ "from": "user", "to": "next", "label": "HTTPS", "kind": "primary", "flow": "request", "step": 1,
              "say": "The browser loads the storefront" }]
}
```

## Top level

| Key | |
|---|---|
| `title` | Page title and `<h1>`. Describes the system, not the request. |
| `kicker` | Optional mono line above the title (`org / area / yyyy-mm`). |
| `lede` | Optional 1–2 sentences beside the title. |
| `footer` | Optional left footer (owner, status). Icon credits fill the right side automatically. |
| `lang` | Label language for `<html lang>`. `ja` makes browsers pick Japanese glyphs. |
| `legend` | Optional rename per edge kind, e.g. `{"primary": "checkout path"}`. Only kinds in use are shown. |
| `highlightPrimary` | Default `true`: tiles on primary edges get an amber border. |

## Nodes

| Key | |
|---|---|
| `id` | Stable id. It becomes `id="node-<id>"`, so keep it across versions: review comments anchor to it. |
| `name` | Official product name (`Amazon S3`, not `S3`). |
| `role` | Short lowercase role in mono (`api routes`, `serverless postgres`). |
| `icon` | Icon name in the icons dir (`<icon>.svg`). |
| `at` | `[col, row]` on the grid. Fractions are fine (`1.5` centers between two columns). |
| `tile` | `""` (light tile), `"dark"` (white or light logos), `"wide"` (wide marks), `"bare"`, `"bare res"` (vendor icons that carry their own square). |
| `wide` | `true` widens the node to 176px for long names. |
| `tileDark` | `true` swaps in `<icon>_dark` on the tile in the dark theme (for bare vendor glyphs such as AWS's General-User). |
| `note` | Shown in the inspector on click: what it does, why it was chosen. One or two sentences. |
| `link` | Optional URL shown in the inspector (repo, dashboard, docs). |

Grid pitch is 184px per column and 232px per row. Keep at least one full
column between nodes on the same row, and leave a whole row free between two
rows of groups (or use `row` values like `0` and `1.3`) when groups would touch.

## Groups

| Key | |
|---|---|
| `id`, `label` | Label in the brand's own casing (`GitHub`, `npm`). |
| `icon` | Square mark for the label (15px). If `<icon>_dark.*` exists it's used in the dark theme automatically. |
| `plate` | `true` puts a light plate behind a label mark with black parts and no dark variant. |
| `contains` | Node ids and group ids. Each id belongs to one group; nest groups for deeper structure. |
| `style` | Default `window` for top-level groups (a small OS window with a title bar) and `zone` for nested ones (dashed). Vendor styles: see `vendors.md`. |
| `tone` | Title bar or zone tint: `amber` (default), `neutral`, `green`, `blue`. Use tone to separate vendors, not to decorate. |
| `meta` | Optional mono text at the right of the title bar (`iad1`, `prod`, `us-east-1`). |

Group boxes are computed from their members. Don't size them by hand; move the
members instead.

## Edges

| Key | |
|---|---|
| `from`, `to` | Node ids. |
| `kind` | `primary` (amber, the one path the reader should follow), `internal` (default), `async` (events, queues, webhooks), `dev` (CI, deploy, git hooks), `vendor` (inside an AWS area). |
| `label` | 1–2 words in mono (`HTTPS`, `SQL`, `checkout`). The node's role carries the detail. |
| `flow` | Flow id. Picking that flow in the toolbar lights up its edges and dims the rest. |
| `step` | Number shown on the edge and in the step list below the canvas. Number the primary path. |
| `say` | Plain sentence for the step list (`The API reads and writes orders`). Defaults to `A to B`. |
| `route` | Optional shape hint when the automatic route reads badly: `straight`, `hv`, `vh`, `vhv`, `hvh`, `under`, `over`, `around`. |
| `id` | Optional. Defaults to `<from>--<to>`. |

A deploy edge whose target is a whole platform points at the most representative
node inside that group, labeled `deploy`.

A two-way pair (a call and its webhook) is fine. When an edge would leave a port
another edge arrives at, the build moves it 16px along that side into its own
lane, so the two never read as one line with two heads.

## What the build checks

`blueprint.py` prints a `WARN` line for each problem it can see, and `--strict`
turns any warning into a failure:

- two nodes overlapping
- groups overlapping, or a node sitting inside a group's box without being in it
- an edge that has to run through a node, across a group label, or on top of another edge
- an edge label with no clear spot

Fix warnings by moving nodes on the grid, not by adding route hints first.
