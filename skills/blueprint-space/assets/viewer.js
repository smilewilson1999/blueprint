const $ = (selector) => document.querySelector(selector);
const model = JSON.parse($("#space-model").textContent);
const root = document.documentElement;
const viewport = $("#viewport");
const rooms = model.rooms || [],
  furniture = model.furniture || [],
  walls = model.walls || [];
const byId = new Map([...rooms, ...furniture].map((item) => [item.id, item]));
const groups = new Map(),
  labels = new Map(),
  rows = new Map(),
  roomRows = new Map();
const palette = [
  "#d8dfce",
  "#d3dee0",
  "#e7d7c5",
  "#ddd1ca",
  "#dce0cf",
  "#e6dfcc",
];
const bounds = new THREE.Box2().setFromPoints(
  model.floor.map((p) => new THREE.Vector2(...p)),
);
const center = bounds.getCenter(new THREE.Vector2());
const span = Math.max(...bounds.getSize(new THREE.Vector2()).toArray());
const grid = model.grid || 0.25;
const scene = new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xffffff, 0x928473, 1.8));
const sun = new THREE.DirectionalLight(0xffffff, 2.5);
sun.position.set(-5, 18, 10);
scene.add(sun);
const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, span * 15);
let renderer;
try {
  renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    preserveDrawingBuffer: true,
  });
} catch (error) {
  $("#render-error").hidden = false;
  $("#render-error").textContent =
    "This 3D view needs WebGL. Open this file in a browser with hardware acceleration enabled.";
  throw error;
}
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
viewport.prepend(renderer.domElement);
renderer.domElement.setAttribute(
  "aria-label",
  "3D space model; room and furniture names are available in the inspector and lists.",
);
let view = "3d",
  editing = false,
  selected = null;
let theta = -0.55,
  phi = 0.72,
  zoom = 1,
  frame = span;
const target = new THREE.Vector3(center.x, 0.35, center.y);
const ray = new THREE.Raycaster(),
  pointer = new THREE.Vector2();
const ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
const world = new THREE.Group();
scene.add(world);
const wallGroup = new THREE.Group();
world.add(wallGroup);
const material = (color) =>
  new THREE.MeshStandardMaterial({ color, roughness: 0.88 });
const materials = {
  wood: material("#c19c76"),
  leg: material("#696d63"),
  seat: material("#82977d"),
  leaf: material("#718461"),
};
const roomMaterials = [],
  wallMaterials = [];
const area = (poly) =>
  Math.abs(
    poly.reduce((n, p, i) => {
      const q = poly[(i + 1) % poly.length];
      return n + p[0] * q[1] - q[0] * p[1];
    }, 0) / 2,
  );
const centroid = (poly) =>
  poly.reduce(
    (p, q) => [p[0] + q[0] / poly.length, p[1] + q[1] / poly.length],
    [0, 0],
  );
const shape = (poly) =>
  new THREE.Shape(poly.map((p) => new THREE.Vector2(p[0], -p[1])));
function box(parent, size, at, mat) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), mat);
  mesh.position.set(...at);
  parent.add(mesh);
  return mesh;
}
const slabMaterial = material("#c6bead");
const baseMaterial = material("#e9e3d6");
const floorMaterials = [
  [slabMaterial, "#c6bead", "#514a41"],
  [baseMaterial, "#e9e3d6", "#2b2824"],
];
const slab = new THREE.Mesh(
  new THREE.ExtrudeGeometry(shape(model.floor), {
    depth: 0.18,
    bevelEnabled: false,
  }),
  slabMaterial,
);
slab.rotation.x = -Math.PI / 2;
slab.position.y = -0.2;
world.add(slab);
const base = new THREE.Mesh(
  new THREE.ShapeGeometry(shape(model.floor)),
  baseMaterial,
);
base.rotation.x = -Math.PI / 2;
base.position.y = -0.015;
world.add(base);
function makeButton(className, parent, item, ident) {
  const button = document.createElement("button");
  button.className = className;
  button.id = ident;
  button.setAttribute("aria-pressed", "false");
  const name = document.createElement("span");
  name.textContent = item.name;
  button.append(name);
  button.addEventListener("click", () => inspect(item.id));
  parent.append(button);
  return button;
}
rooms.forEach((room, i) => {
  const color = room.color || palette[i % palette.length];
  const mat = material(color);
  roomMaterials.push([mat, color]);
  const floor = new THREE.Mesh(
    new THREE.ShapeGeometry(shape(room.outline)),
    mat,
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = 0.002;
  floor.userData.id = room.id;
  world.add(floor);
  const label = makeButton(
    "room-label",
    $("#labels"),
    room,
    `space-room-${room.id}`,
  );
  label.dataset.room = room.id;
  const meta = document.createElement("small");
  meta.className = "room-area";
  meta.textContent = `${area(room.outline).toFixed(0)} m²`;
  label.append(meta);
  labels.set(room.id, label);
  const row = makeButton(
    "room-row",
    $("#room-list"),
    room,
    `space-zone-${room.id}`,
  );
  row.style.setProperty("--color", color);
  const swatch = document.createElement("i");
  swatch.className = "swatch";
  row.firstChild.prepend(swatch);
  const size = document.createElement("small");
  size.textContent = `${area(room.outline).toFixed(0)} m²`;
  row.append(size);
  const pieceCount = document.createElement("small");
  pieceCount.className = "room-piece-count";
  pieceCount.dataset.room = room.id;
  row.append(pieceCount);
  roomRows.set(room.id, pieceCount);
});
function refreshRoomCounts() {
  rooms.forEach((room) => {
    const count = furniture.filter((piece) => piece.room === room.id).length;
    const element = roomRows.get(room.id);
    element.textContent = `${count} piece${count === 1 ? "" : "s"}`;
  });
}
function makeWalls() {
  while (wallGroup.children.length) {
    const child = wallGroup.children[0];
    child.geometry?.dispose();
    wallGroup.remove(child);
  }
  wallMaterials.splice(0).forEach((mat) => mat.dispose());
  const wallMat = material(
    root.dataset.theme === "dark" ? "#81796c" : "#d4cbbb",
  );
  const glassMat = new THREE.MeshStandardMaterial({
    color: "#95b8bd",
    transparent: true,
    opacity: 0.5,
    roughness: 0.25,
  });
  const doorMat = material("#b68c61"),
    planGlassMat = material("#71979e");
  wallMaterials.push(wallMat, glassMat, doorMat, planGlassMat);
  walls.forEach((wall) => {
    const [x, z] = wall.start,
      dx = wall.end[0] - x,
      dz = wall.end[1] - z;
    const length = Math.hypot(dx, dz),
      height = view === "plan" ? 0.1 : Math.min(wall.height, 1.2);
    const openings = [...(model.doors || []), ...(model.windows || [])].filter(
      (o) => o.wall === wall.id,
    );
    const cuts = [
      ...new Set([
        0,
        length,
        ...openings.flatMap((o) => [
          Math.max(0, o.offset),
          Math.min(length, o.offset + o.width),
        ]),
      ]),
    ].sort((a, b) => a - b);
    function segment(a, b, bottom, top, mat) {
      if (b <= a || top <= bottom) return;
      const mesh = box(
        wallGroup,
        [b - a, top - bottom, wall.thickness],
        [
          x + (dx * (a + b)) / (2 * length),
          (top + bottom) / 2,
          z + (dz * (a + b)) / (2 * length),
        ],
        mat,
      );
      mesh.rotation.y = -Math.atan2(dz, dx);
    }
    for (let i = 0; i < cuts.length - 1; i++) {
      const a = cuts[i],
        b = cuts[i + 1],
        mid = (a + b) / 2;
      const opening = openings.find(
        (o) => mid > o.offset && mid < o.offset + o.width,
      );
      if (!opening) segment(a, b, 0, height, wallMat);
      else {
        const sill = opening.sill || 0;
        segment(a, b, 0, Math.min(sill, height), wallMat);
        segment(a, b, sill + opening.height, height, wallMat);
        const isWindow = (model.windows || []).includes(opening);
        if (isWindow && view === "plan")
          segment(a, b, height + 0.01, height + 0.04, planGlassMat);
        else if (isWindow)
          segment(
            a,
            b,
            sill,
            Math.min(sill + opening.height, height),
            glassMat,
          );
        else segment(a, b, 0.01, 0.035, doorMat);
      }
    }
  });
}
function makeFurniture(f) {
  const group = new THREE.Group();
  group.userData.id = f.id;
  const [w, d, h] = f.size;
  const wood = f.color ? material(f.color) : materials.wood;
  const seat = f.color ? wood : materials.seat;
  const legs = (height, spread = 0.42) => {
    for (const x of [-1, 1])
      for (const z of [-1, 1])
        box(
          group,
          [0.055, height, 0.055],
          [x * w * spread, height / 2, z * d * spread],
          materials.leg,
        );
  };
  if (f.type === "desk" || f.type === "table") {
    box(group, [w, 0.07, d], [0, h - 0.035, 0], wood);
    legs(h - 0.07);
    if (f.type === "desk") {
      box(group, [w * 0.3, 0.04, d * 0.3], [0, h + 0.02, 0], materials.leg);
      box(
        group,
        [w * 0.32, h * 0.35, 0.04],
        [0, h * 1.2, -d * 0.2],
        materials.leg,
      );
    }
  } else if (f.type === "chair") {
    box(group, [w, h * 0.1, d], [0, h * 0.5, 0], seat);
    box(group, [w, h * 0.45, d * 0.12], [0, h * 0.78, -d * 0.44], seat);
    legs(h * 0.45, 0.35);
  } else if (f.type === "sofa") {
    box(group, [w, h * 0.48, d], [0, h * 0.32, 0], seat);
    box(group, [w, h * 0.46, d * 0.2], [0, h * 0.77, -d * 0.4], seat);
    for (const x of [-1, 1])
      box(group, [w * 0.08, h * 0.5, d], [x * w * 0.46, h * 0.58, 0], seat);
  } else if (f.type === "plant") {
    const pot = new THREE.Mesh(
      new THREE.CylinderGeometry(w * 0.35, w * 0.26, h * 0.35, 16),
      wood,
    );
    pot.position.y = h * 0.175;
    group.add(pot);
    const leaves = new THREE.Mesh(
      new THREE.SphereGeometry(1, 12, 10),
      materials.leaf,
    );
    leaves.scale.set(w / 2, h * 0.33, d / 2);
    leaves.position.y = h * 0.65;
    group.add(leaves);
  } else if (f.type === "shelf") {
    for (const x of [-1, 1])
      box(group, [0.05, h, d], [x * (w / 2 - 0.025), h / 2, 0], wood);
    for (let i = 0; i < 4; i++)
      box(group, [w, 0.05, d], [0, 0.025 + (i * (h - 0.05)) / 3, 0], wood);
  } else box(group, [w, h, d], [0, h / 2, 0], wood);
  group.position.set(f.position[0], 0, f.position[1]);
  group.rotation.y = -THREE.MathUtils.degToRad(f.rotation || 0);
  world.add(group);
  groups.set(f.id, group);
  const row = makeButton(
    "piece-row",
    $("#piece-list"),
    f,
    `space-piece-${f.id}`,
  );
  const id = document.createElement("small");
  id.textContent = f.id;
  row.append(id);
  rows.set(f.id, row);
}
furniture.forEach(makeFurniture);
const highlight = new THREE.BoxHelper(new THREE.Object3D(), 0xb25f28);
highlight.visible = false;
scene.add(highlight);
function project(point) {
  const p = point.clone().project(camera);
  return [
    ((p.x + 1) * viewport.clientWidth) / 2,
    ((1 - p.y) * viewport.clientHeight) / 2,
  ];
}
function labelCandidates(room) {
  const outline = room.outline;
  const centre = centroid(outline);
  const raw = room.label ? [room.label] : [centre];
  if (room.label) raw.push(centre);
  outline.forEach((point) => {
    raw.push([
      point[0] * 0.55 + centre[0] * 0.45,
      point[1] * 0.55 + centre[1] * 0.45,
    ]);
  });
  outline.forEach((point, index) => {
    const next = outline[(index + 1) % outline.length];
    const midpoint = [(point[0] + next[0]) / 2, (point[1] + next[1]) / 2];
    raw.push([
      midpoint[0] * 0.65 + centre[0] * 0.35,
      midpoint[1] * 0.65 + centre[1] * 0.35,
    ]);
  });
  const xs = outline.map((point) => point[0]);
  const zs = outline.map((point) => point[1]);
  [0.25, 0.5, 0.75].forEach((x) =>
    [0.25, 0.5, 0.75].forEach((z) =>
      raw.push([
        Math.min(...xs) + (Math.max(...xs) - Math.min(...xs)) * x,
        Math.min(...zs) + (Math.max(...zs) - Math.min(...zs)) * z,
      ]),
    ),
  );
  const seen = new Set();
  return raw.filter((point) => {
    const key = point.map((value) => value.toFixed(6)).join(",");
    if (seen.has(key) || !pointInRoom(point, outline)) return false;
    seen.add(key);
    return true;
  });
}
function placeRoomLabels() {
  const overlapArea = (first, second) => {
    const width =
      Math.min(first.right, second.right) - Math.max(first.left, second.left);
    const height =
      Math.min(first.bottom, second.bottom) - Math.max(first.top, second.top);
    return width > 0 && height > 0 ? width * height : 0;
  };
  const furnitureRects = furniture.map((piece) => {
    const angle = THREE.MathUtils.degToRad(piece.rotation || 0);
    const floorCorners = [
      [-piece.size[0] / 2, -piece.size[1] / 2],
      [piece.size[0] / 2, -piece.size[1] / 2],
      [piece.size[0] / 2, piece.size[1] / 2],
      [-piece.size[0] / 2, piece.size[1] / 2],
    ];
    const corners = floorCorners.flatMap(([x, z]) =>
      [0.08, piece.size[2]].map((height) =>
        project(
          new THREE.Vector3(
            piece.position[0] + x * Math.cos(angle) - z * Math.sin(angle),
            height,
            piece.position[1] + x * Math.sin(angle) + z * Math.cos(angle),
          ),
        ),
      ),
    );
    return {
      left: Math.min(...corners.map(([x]) => x)),
      right: Math.max(...corners.map(([x]) => x)),
      top: Math.min(...corners.map(([, y]) => y)),
      bottom: Math.max(...corners.map(([, y]) => y)),
    };
  });
  const measurements = new Map();
  rooms.forEach((room) => {
    const label = labels.get(room.id);
    const measure = label.cloneNode(true);
    measure.removeAttribute("id");
    measure.classList.remove("compact");
    measure.style.visibility = "hidden";
    measure.style.left = "0px";
    measure.style.top = "0px";
    $("#labels").append(measure);
    const areaLabel = measure.querySelector(".room-area");
    if (areaLabel) areaLabel.hidden = false;
    const full = measure.getBoundingClientRect();
    if (areaLabel) areaLabel.hidden = true;
    measure.classList.add("compact");
    const name = measure.getBoundingClientRect();
    measure.remove();
    measurements.set(room.id, {
      full: { width: full.width, height: full.height },
      name: { width: name.width, height: name.height },
    });
  });
  const occupied = [];
  const ordered = [...rooms].sort(
    (first, second) => area(second.outline) - area(first.outline),
  );
  ordered.forEach((room) => {
    const label = labels.get(room.id);
    const areaLabel = label.querySelector(".room-area");
    let chosen = null;
    for (const compact of [false, true]) {
      const size = measurements.get(room.id)[compact ? "name" : "full"];
      for (const point of labelCandidates(room)) {
        const [x, y] = project(new THREE.Vector3(point[0], 0.08, point[1]));
        const bounds = {
          left: x - size.width / 2,
          right: x + size.width / 2,
          top: y - size.height / 2,
          bottom: y + size.height / 2,
        };
        if (
          bounds.left < 0 ||
          bounds.right > viewport.clientWidth ||
          bounds.top < 0 ||
          bounds.bottom > viewport.clientHeight ||
          occupied.some((other) => overlapArea(bounds, other))
        )
          continue;
        const furnitureOverlap = furnitureRects.reduce(
          (total, other) => total + overlapArea(bounds, other),
          0,
        );
        if (!chosen || furnitureOverlap < chosen.furnitureOverlap) {
          chosen = { point, x, y, bounds, compact, furnitureOverlap };
        }
      }
      if (chosen) break;
    }
    if (chosen) {
      label.style.visibility = "visible";
      label.style.left = `${chosen.x}px`;
      label.style.top = `${chosen.y}px`;
      label.dataset.floorPoint = JSON.stringify(chosen.point);
      const viewportRect = viewport.getBoundingClientRect();
      label.dataset.screen = JSON.stringify([
        chosen.x + viewportRect.left,
        chosen.y + viewportRect.top,
      ]);
      label.classList.toggle("compact", chosen.compact);
      if (areaLabel) areaLabel.hidden = chosen.compact;
      occupied.push(chosen.bounds);
    } else {
      label.style.visibility = "hidden";
      label.dataset.floorPoint = "";
      label.dataset.screen = "";
    }
  });
}
function render() {
  const aspect = viewport.clientWidth / viewport.clientHeight;
  camera.left = (-frame * aspect) / (2 * zoom);
  camera.right = -camera.left;
  camera.top = frame / (2 * zoom);
  camera.bottom = -camera.top;
  camera.position
    .copy(target)
    .add(
      view === "plan"
        ? new THREE.Vector3(0, span * 3, 0)
        : new THREE.Vector3(
            Math.sin(theta) * Math.sin(phi),
            Math.cos(phi),
            Math.cos(theta) * Math.sin(phi),
          ).multiplyScalar(span * 3),
    );
  camera.up.set(0, view === "plan" ? 0 : 1, view === "plan" ? -1 : 0);
  camera.lookAt(target);
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld();
  renderer.render(scene, camera);
  placeRoomLabels();
  const rect = viewport.getBoundingClientRect();
  furniture.forEach((f) => {
    const row = rows.get(f.id),
      [x, y] = project(
        new THREE.Vector3(f.position[0], f.size[2] / 2, f.position[1]),
      );
    row.dataset.x = f.position[0];
    row.dataset.z = f.position[1];
    row.dataset.rotation = f.rotation || 0;
    row.dataset.screen = JSON.stringify([x + rect.left, y + rect.top]);
  });
  viewport.dataset.camera = [theta, phi, zoom, target.x, target.z]
    .map((n) => n.toFixed(5))
    .join(",");
  viewport.dataset.view = view;
  $(".scale span").style.width =
    `${(2 * zoom * viewport.clientHeight) / frame}px`;
}
function fit() {
  target.set(center.x, 0.35, center.y);
  zoom = 1;
  frame = span * 1.6;
  render();
  const points = model.floor.flatMap((p) => [
    new THREE.Vector3(p[0], 0, p[1]),
    new THREE.Vector3(p[0], 1.4, p[1]),
  ]);
  const projected = points.map((p) =>
    p.applyMatrix4(camera.matrixWorldInverse),
  );
  const width =
    Math.max(...projected.map((p) => p.x)) -
    Math.min(...projected.map((p) => p.x));
  const height =
    Math.max(...projected.map((p) => p.y)) -
    Math.min(...projected.map((p) => p.y));
  frame =
    Math.max(height, (width * viewport.clientHeight) / viewport.clientWidth) *
    1.22;
  render();
}
function text(parent, tag, value, className = "") {
  const el = document.createElement(tag);
  el.textContent = value;
  el.className = className;
  parent.append(el);
  return el;
}
function inspect(id) {
  selected = id;
  const item = byId.get(id),
    isPiece = groups.has(id),
    panel = $("#inspector");
  panel.replaceChildren();
  for (const el of document.querySelectorAll(
    ".room-label,.room-row,.piece-row",
  ))
    el.setAttribute(
      "aria-pressed",
      String(
        el.id === `space-room-${id}` ||
          el.id === `space-zone-${id}` ||
          el.id === `space-piece-${id}`,
      ),
    );
  $("#selection-kind").textContent = isPiece ? item.type : "room";
  text(
    panel,
    "p",
    isPiece ? byId.get(item.room)?.name || item.room : "Named zone",
    "eyebrow",
  );
  text(panel, "h2", item.name);
  text(panel, "p", item.id, "stable-id");
  if (item.note) text(panel, "p", item.note);
  const dl = document.createElement("dl");
  panel.append(dl);
  const pairs = isPiece
    ? [
        ["Size", `${item.size.join(" × ")} m`],
        ["Position", `${item.position.join(", ")} m`],
        ["Rotation", `${item.rotation || 0}°`],
      ]
    : [
        ["Area", `${area(item.outline).toFixed(1)} m²`],
        ["Pieces", furniture.filter((f) => f.room === id).length],
      ];
  pairs.forEach(([label, value]) => {
    text(dl, "dt", label);
    text(dl, "dd", value);
  });
  $("#edit-controls").hidden = !editing || !isPiece;
  highlight.visible = isPiece;
  if (isPiece) highlight.setFromObject(groups.get(id));
  render();
}
function setView(value) {
  view = value;
  $("#view-3d").setAttribute("aria-pressed", String(view === "3d"));
  $("#view-plan").setAttribute("aria-pressed", String(view === "plan"));
  $("#view-title").textContent =
    `Spatial study / ${view === "plan" ? "Plan" : "3D"}`;
  makeWalls();
  fit();
  hints();
}
function hints() {
  $("#hint").textContent = editing
    ? `Edit layout · drag furniture · R to rotate · ${grid} m grid · export to save`
    : view === "plan"
      ? "Drag to pan · scroll or pinch to zoom · select a room or piece"
      : "Drag to orbit · right-drag to pan · scroll or pinch to zoom";
}
function setEditing() {
  editing = !editing;
  viewport.classList.toggle("editing", editing);
  $("#edit").setAttribute("aria-pressed", String(editing));
  $("#edit-controls").hidden = !editing || !groups.has(selected);
  hints();
}
function movePiece(f, position, rotation) {
  f.position = position;
  if (rotation !== undefined) f.rotation = rotation;
  const group = groups.get(f.id);
  group.position.set(position[0], 0, position[1]);
  group.rotation.y = -THREE.MathUtils.degToRad(f.rotation || 0);
  $("#status").textContent = "Unsaved layout · Export JSON to keep changes";
  inspect(f.id);
}
function pointOnSegment(point, start, end) {
  const cross =
    (point[1] - start[1]) * (end[0] - start[0]) -
    (point[0] - start[0]) * (end[1] - start[1]);
  if (Math.abs(cross) > 1e-7) return false;
  return (
    point[0] >= Math.min(start[0], end[0]) - 1e-7 &&
    point[0] <= Math.max(start[0], end[0]) + 1e-7 &&
    point[1] >= Math.min(start[1], end[1]) - 1e-7 &&
    point[1] <= Math.max(start[1], end[1]) + 1e-7
  );
}
function pointInRoom(point, outline) {
  let inside = false;
  for (let i = 0, j = outline.length - 1; i < outline.length; j = i++) {
    const start = outline[i];
    const end = outline[j];
    if (pointOnSegment(point, start, end)) return true;
    if (start[1] > point[1] !== end[1] > point[1]) {
      const x =
        ((end[0] - start[0]) * (point[1] - start[1])) / (end[1] - start[1]) +
        start[0];
      if (point[0] < x) inside = !inside;
    }
  }
  return inside;
}
function finishPieceChange(f) {
  const current = rooms.find((candidate) => candidate.id === f.room);
  const room =
    (current && pointInRoom(f.position, current.outline) && current) ||
    rooms.find(
      (candidate) =>
        candidate.id !== f.room && pointInRoom(f.position, candidate.outline),
    );
  if (room) f.room = room.id;
  refreshRoomCounts();
  inspect(f.id);
}
function rotate(delta) {
  if (!editing || !groups.has(selected)) return;
  const f = byId.get(selected);
  movePiece(f, f.position, ((((f.rotation || 0) + delta) % 360) + 360) % 360);
  finishPieceChange(f);
}
function setTheme(value) {
  root.dataset.theme = value;
  $("#theme").setAttribute("aria-pressed", String(value === "dark"));
  floorMaterials.forEach(([mat, light, dark]) =>
    mat.color.set(value === "dark" ? dark : light),
  );
  roomMaterials.forEach(([mat, color]) => {
    mat.color.set(color);
    if (value === "dark") mat.color.multiplyScalar(0.16);
  });
  makeWalls();
  render();
}
function groundPoint(x, y) {
  const rect = viewport.getBoundingClientRect();
  pointer.set(
    ((x - rect.left) / rect.width) * 2 - 1,
    (-(y - rect.top) / rect.height) * 2 + 1,
  );
  ray.setFromCamera(pointer, camera);
  return ray.ray.intersectPlane(ground, new THREE.Vector3());
}
function hit(x, y) {
  groundPoint(x, y);
  const hits = ray.intersectObjects([...groups.values()], true);
  if (hits.length) {
    let obj = hits[0].object;
    while (obj && !obj.userData.id) obj = obj.parent;
    return obj?.userData.id;
  }
  const floors = world.children.filter((child) => child.userData.id);
  return ray.intersectObjects(floors, false)[0]?.object.userData.id;
}
const pointers = new Map();
let gesture = null;
const midpoint = () => {
  const p = [...pointers.values()];
  return [(p[0].x + p[1].x) / 2, (p[0].y + p[1].y) / 2];
};
const distance = () => {
  const p = [...pointers.values()];
  return Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
};
viewport.addEventListener("pointerdown", (event) => {
  if (
    event.target.closest(".view-tools") ||
    (event.pointerType !== "touch" && event.target.closest("button"))
  )
    return;
  event.preventDefault();
  viewport.focus({ preventScroll: true });
  viewport.setPointerCapture(event.pointerId);
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  if (pointers.size === 2) {
    const active = gesture;
    if (active?.kind === "piece" && active.id) {
      finishPieceChange(byId.get(active.id));
    }
    gesture = { kind: "pinch", distance: distance(), mid: midpoint() };
    return;
  }
  const hitId = hit(event.clientX, event.clientY);
  const id = hitId;
  const p = groundPoint(event.clientX, event.clientY);
  if (id) inspect(id);
  gesture = {
    kind:
      editing && groups.has(id)
        ? "piece"
        : view === "plan" || event.button === 2 || event.shiftKey
          ? "pan"
          : "orbit",
    x: event.clientX,
    y: event.clientY,
    id,
    point: p,
    start: groups.has(id) ? [...byId.get(id).position] : null,
  };
});
function pan(dx, dy) {
  const units = frame / (zoom * viewport.clientHeight);
  const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
  const up = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 1);
  target.addScaledVector(right, -dx * units);
  target.addScaledVector(up, dy * units);
  target.y = 0.35;
}
viewport.addEventListener("pointermove", (event) => {
  if (!pointers.has(event.pointerId) || !gesture) return;
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  if (gesture.kind === "pinch" && pointers.size === 2) {
    const d = distance(),
      mid = midpoint();
    zoom = THREE.MathUtils.clamp(
      (zoom * d) / Math.max(gesture.distance, 1),
      0.35,
      8,
    );
    pan(mid[0] - gesture.mid[0], mid[1] - gesture.mid[1]);
    gesture = { kind: "pinch", distance: d, mid };
  } else if (gesture.kind === "piece") {
    const p = groundPoint(event.clientX, event.clientY);
    if (p && gesture.point) {
      const snap = (n) => Math.round(n / grid) * grid;
      movePiece(byId.get(gesture.id), [
        Number(snap(gesture.start[0] + p.x - gesture.point.x).toFixed(6)),
        Number(snap(gesture.start[1] + p.z - gesture.point.z).toFixed(6)),
      ]);
    }
  } else {
    const dx = event.clientX - gesture.x,
      dy = event.clientY - gesture.y;
    if (gesture.kind === "pan") pan(dx, dy);
    else {
      theta -= dx * 0.008;
      phi = THREE.MathUtils.clamp(phi + dy * 0.006, 0.12, 1.35);
    }
    gesture.x = event.clientX;
    gesture.y = event.clientY;
  }
  render();
});
function endPointer(event) {
  const active = gesture;
  pointers.delete(event.pointerId);
  if (viewport.hasPointerCapture(event.pointerId))
    viewport.releasePointerCapture(event.pointerId);
  gesture = null;
  if (active?.kind === "piece" && active.id) {
    finishPieceChange(byId.get(active.id));
  }
}
viewport.addEventListener("pointerup", endPointer);
viewport.addEventListener("pointercancel", endPointer);
viewport.addEventListener("contextmenu", (event) => event.preventDefault());
viewport.addEventListener(
  "wheel",
  (event) => {
    const nextZoom = THREE.MathUtils.clamp(
      zoom * Math.exp(-Math.max(-120, Math.min(120, event.deltaY)) * 0.003),
      0.35,
      8,
    );
    if (Math.abs(nextZoom - zoom) < 1e-7) return;
    event.preventDefault();
    zoom = nextZoom;
    render();
  },
  { passive: false },
);
$("#view-3d").addEventListener("click", () => setView("3d"));
$("#view-plan").addEventListener("click", () => setView("plan"));
$("#edit").addEventListener("click", setEditing);
$("#rotate-left").addEventListener("click", () => rotate(-15));
$("#rotate-right").addEventListener("click", () => rotate(15));
$("#theme").addEventListener("click", () =>
  setTheme(root.dataset.theme === "dark" ? "light" : "dark"),
);
$("#zoom-in").addEventListener("click", () => {
  zoom = Math.min(8, zoom * 1.25);
  render();
});
$("#zoom-out").addEventListener("click", () => {
  zoom = Math.max(0.35, zoom / 1.25);
  render();
});
$("#fit").addEventListener("click", fit);
$("#export").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(model, null, 2) + "\n"], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = url;
  a.download = "space.json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  $("#status").textContent =
    "Exported space.json · rebuild to check clearances";
});
document.addEventListener("keydown", (event) => {
  if (
    event.ctrlKey ||
    event.metaKey ||
    event.altKey ||
    /INPUT|TEXTAREA|SELECT/.test(event.target.tagName) ||
    event.target.isContentEditable
  )
    return;
  const key = event.key.toLowerCase();
  if (key === "v") setView(view === "3d" ? "plan" : "3d");
  else if (key === "e") setEditing();
  else if (key === "r") rotate(event.shiftKey ? -15 : 15);
  else if (key === "0") fit();
  else if (editing && groups.has(selected) && key.startsWith("arrow")) {
    event.preventDefault();
    const f = byId.get(selected),
      p = [...f.position];
    if (key === "arrowleft") p[0] -= grid;
    if (key === "arrowright") p[0] += grid;
    if (key === "arrowup") p[1] -= grid;
    if (key === "arrowdown") p[1] += grid;
    movePiece(
      f,
      p.map((n) => Number(n.toFixed(6))),
    );
    finishPieceChange(f);
  }
});
$("#area").textContent = `${area(model.floor).toFixed(0)} m² / metres`;
$("#room-count").textContent = String(rooms.length);
$("#piece-count").textContent = String(furniture.length);
$("#summary").textContent =
  `${rooms.length} named zones · ${furniture.length} pieces · ${grid} m snap grid`;
refreshRoomCounts();
new ResizeObserver(() => {
  renderer.setSize(viewport.clientWidth, viewport.clientHeight);
  fit();
}).observe(viewport);
const systemTheme = matchMedia("(prefers-color-scheme: dark)");
setTheme(systemTheme.matches ? "dark" : "light");
let manualTheme = false;
$("#theme").addEventListener("click", () => {
  manualTheme = true;
});
systemTheme.addEventListener("change", (event) => {
  if (!manualTheme) setTheme(event.matches ? "dark" : "light");
});
fit();
