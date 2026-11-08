# space.json

One JSON object describes a single floor. Units are metres, with `[x, z]` on
the floor: x increases rightward and z downward in Plan. Height is y in 3D.
The builder validates the source and embeds it without adding schema fields.
Extra fields, including `metadata`, survive export; they do not affect drawing.

```json
{
  "title": "Willow studio",
  "kicker": "concept / layout 01",
  "lede": "A fictional studio with invented dimensions.",
  "footer": "Layout study",
  "lang": "en",
  "units": "m",
  "grid": 0.25,
  "floor": [[0, 0], [8, 0], [8, 6], [0, 6]],
  "rooms": [{"id": "work", "name": "Work room", "outline": [[0, 0], [8, 0], [8, 6], [0, 6]], "label": [4, 1], "color": "#dce2d2"}],
  "walls": [{"id": "north", "start": [0, 0], "end": [8, 0], "height": 2.8, "thickness": 0.15}],
  "doors": [{"id": "entry", "wall": "north", "offset": 1, "width": 1.1, "height": 2.1}],
  "windows": [{"id": "glazing", "wall": "north", "offset": 3, "width": 3, "height": 1.4, "sill": 0.7}],
  "furniture": [{"id": "desk-01", "name": "Writing desk", "type": "desk", "room": "work", "position": [4, 3], "size": [1.4, 0.7, 0.75], "rotation": 0}]
}
```

## Top level

| Key | Meaning |
| --- | --- |
| `title` | Required nonempty page title. |
| `units` | Required; exactly `"m"`. |
| `floor` | Required simple polygon with at least three `[x, z]` vertices, in either winding. No repeated closing vertex, self intersections or holes. Concave outlines are supported. |
| `rooms`, `walls`, `doors`, `windows`, `furniture` | Arrays, default `[]`. |
| `grid` | Positive snap interval; default `0.25` m. |
| `kicker`, `lede`, `footer` | Optional nonempty text for context and assumptions. |
| `lang` | Optional HTML language, default `en`. Non-Latin glyphs use local system fonts. |
| `metadata` | Optional project information, preserved without interpretation. |

All numeric values must be finite. Geometry values have magnitude at most
1,000,000. All numbers, including extra metadata, must have magnitude at most
9,007,199,254,740,991 so browser export can preserve them. Integral floats and
negative zero are normalized during building; whitespace and number spelling
are not preserved. The model and resulting build survive an unchanged export.

## Stable ids and text

Every room, wall, door, window and furniture piece requires a globally unique
`id` using letters, digits, `_` or `-`. Rooms and furniture require a nonempty
real text `name`; either may have `note` and a six-digit `#RRGGBB` `color`.
Notes appear in the inspector. Walls and openings may also carry notes, which
are preserved in exports. Names and ids render through text nodes or escaped
HTML; source text is never interpreted as markup.

Room labels have `id="space-room-<id>"`; the room list uses `space-zone-<id>` and
furniture uses `space-piece-<id>`. Each name is available without relying on text
painted into WebGL. Clicking the actual furniture or its list entry opens the
same inspector, with its id, dimensions, position and rotation.

## Rooms

| Key | Meaning |
| --- | --- |
| `outline` | Required simple polygon, as for `floor`. Room zones must fit inside the floor and have no area overlaps; shared edges are fine. |
| `label` | Optional `[x, z]` label anchor inside the room. Defaults to the mean of its vertices; set explicitly for concave zones. |

Rooms color the floor; their outlines do not create walls. Unassigned floor
area is circulation. Room membership is explicit through furniture's `room`.

## Walls and openings

| Object | Required fields |
| --- | --- |
| Wall | `id`, `start: [x, z]`, `end: [x, z]`, positive `height` and `thickness`. The segment runs along the wall's centreline and must have nonzero length. |
| Door | `id`, `wall` (wall id), `offset`, positive `width` and `height`. The opening starts `offset` metres from the wall's `start`, measured along it. |
| Window | Same as a door, plus nonnegative `sill` (height of the opening's bottom). |

Openings must fit horizontally and vertically within their wall and may not
overlap each other in both dimensions. Reversing a wall's endpoints reverses
its offset direction. Doors are open passages with a threshold. The blocked
door check reserves a rectangle spanning its width along the wall and one
door width on each side, a conservative clearance zone rather than a swing
simulation. Window glazing occupies the opening, with wall below the sill.

3D caps drawn wall height at 1.2 m to reveal the interior; Plan uses 0.1 m wall
footprints, with blue window markers. Full heights remain in the JSON and validation. These are drawing
conventions, not edits to the model. Only the part of a window within the
cutaway is visible.

## Furniture

| Key | Meaning |
| --- | --- |
| `type` | `desk`, `table`, `chair`, `sofa`, `shelf`, `counter` or `plant`. |
| `room` | Required room id. |
| `position` | Required `[x, z]` footprint centre on the floor. |
| `size` | Required positive `[width, depth, height]` in metres. |
| `rotation` | Optional degrees clockwise in Plan around its centre; default `0`. |

All types use the same rectangular footprint for checks. Desk/table tops,
chair/sofa seats, shelves and potted plants are procedural shapes, not imported
models. Desks include a small monitor for readability; footprint size describes
the desk and height its worktop. Use names and notes for individual purpose.

Edit layout snaps moved centres to `grid` and rotates in 15° increments. When a
move or rotation ends, the viewer assigns the piece to the room whose outline
contains its footprint centre. If no room contains that centre, the previous
`room` is retained so a strict build reports the out-of-room placement. Editing
supports dragging in both views, with floor-plane intersection, or arrow keys.
Export includes all source objects and extra fields, changing positions,
rotations and room assignment only when editing changed them. Camera, view,
theme and selection are presentation state and are not exported.

## Build warnings and limits

The CLI prints `WARN` for schema errors and fails without producing new HTML.
For a structurally valid model it checks:

- room/floor containment and room overlaps
- explicit label anchors outside their room
- rotated furniture footprints outside the floor or assigned room
- furniture overlaps and intersections with wall footprints
- blocked door clearance rectangles
- unknown room or wall references
- openings outside their wall or overlapping another opening

Without `--strict`, layout warnings are reported and HTML is still written;
with `--strict`, any warning fails and no new HTML is written. Fix the source
and rebuild to zero `WARN`. A furniture footprint across an opening still
intersects the wall centreline and is flagged; passages should remain empty.
This is a layout check, not an assessment of accessibility, occupancy, egress
or building codes. Multiple floors, curved walls and elevation changes are
outside this schema.
