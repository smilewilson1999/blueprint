// CoWoS-style 2.5D package, concept geometry. Units are invented "mm"; z is exaggerated.
self.DrawingModels ??= {};
self.DrawingModels.cowos = (parameters, options) => {
  const G = TechnicalGeometry;
  const hbmPerSide = parameters.hbmPerSide, dramLayers = parameters.dramLayers;
  if (!Number.isInteger(hbmPerSide) || hbmPerSide < 1 || hbmPerSide > 3) throw Error('HBM stacks per side must be 1–3');
  if (!Number.isInteger(dramLayers) || dramLayers < 4 || dramLayers > 16 || dramLayers % 4) throw Error('DRAM layers must be 4, 8, 12 or 16');

  // ── plain data: footprints and heights, all derived from the two parameters ──
  const SUB = 60, SUB_T = 3;                        // substrate square and thickness
  const SOC = [22, 26], DIE_GAP = 1.5;              // SoC footprint (x, y), gap to HBM
  const HBM = [8, 11], HBM_GAP = 1.5;               // one HBM stack footprint
  const BASE_T = 0.45, DRAM_T = 0.14;               // HBM base die and DRAM layer thickness
  const hbmX = SOC[0] / 2 + DIE_GAP + HBM[0] / 2;   // column center, each side
  const column = hbmPerSide * HBM[1] + (hbmPerSide - 1) * HBM_GAP;
  const INT = [2 * (hbmX + HBM[0] / 2) + 4, Math.max(SOC[1], column) + 4];
  const z = {};                                     // assembled heights, bottom up
  z.subTop = SUB_T;
  z.c4Top = z.subTop + 0.8;
  z.intTop = z.c4Top + 1.2;
  z.ubTop = z.intTop + 0.5;
  const hbmH = BASE_T + dramLayers * DRAM_T, socH = 1.6;
  z.dieTop = z.ubTop + Math.max(hbmH, socH);
  z.timTop = z.dieTop + 0.1 + 0.6;
  z.lidTop = z.timTop + 0.1 + 1.6;
  const LID = 58, WALL = 3;                         // lid outer size and wall thickness

  // grids: the TSV / C4 grid is shared, so every via sits on its bump
  const grid = (w, h, pitch, margin) => {
    const nx = Math.floor((w - 2 * margin) / pitch) + 1, ny = Math.floor((h - 2 * margin) / pitch) + 1;
    const out = [];
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++)
      out.push([(i - (nx - 1) / 2) * pitch, (j - (ny - 1) / 2) * pitch]);
    return out;
  };
  const C4_PITCH = 3.2, UB_PITCH = 2;
  const c4Grid = grid(INT[0], INT[1], C4_PITCH, 1.6);
  const hbmCenters = [];
  for (const side of [-1, 1]) for (let k = 0; k < hbmPerSide; k++)
    hbmCenters.push([side * hbmX, (k - (hbmPerSide - 1) / 2) * (HBM[1] + HBM_GAP)]);

  // a short vertical cylinder or a sphere, built on a piece and merged into its part
  const cylinder = (target, [x, y], z0, h, r) => {
    const s = G.piece();
    G.lathe(s, [[0, 0], [0, r], [h, r], [h, 0]], {segments: 12});
    G.transform(s, {origin: [x, y, z0], ...G.along('z')});
    G.merge(target, s);
  };
  const ball = (target, [x, y], zc, r) => {
    const s = G.piece(), prof = [];
    for (let i = 0; i <= 8; i++) { const a = Math.PI * i / 8; prof.push([-r * Math.cos(a), r * Math.sin(a)]); }
    G.lathe(s, prof, {segments: 16, creaseAngle: 60});
    G.transform(s, {origin: [x, y, zc], ...G.along('z')});
    G.merge(target, s);
  };
  const plate = (target, [cx, cy], [w, h], z0, z1, radius = 0) =>
    G.box(target, [cx - w / 2, cy - h / 2, z0], [cx + w / 2, cy + h / 2, z1], radius ? {radius} : {});

  // ── parts, bottom up; explosion is a pure lift along z ──
  const bga = G.part('bga', 'BGA solder balls');
  for (const p of grid(SUB, SUB, 4.4, 3.6)) ball(bga, p, -1.05, 1.05);

  const substrate = G.part('substrate', 'Organic substrate');
  plate(substrate, [0, 0], [SUB, SUB], 0, z.subTop, 1.5);

  const c4 = G.part('c4', 'C4 bumps');
  for (const p of c4Grid) cylinder(c4, p, z.subTop + 0.02, 0.76, 0.55);

  const interposer = G.part('interposer', 'Silicon interposer');
  plate(interposer, [0, 0], INT, z.c4Top + 0.02, z.intTop);
  for (const [x, y] of c4Grid) G.circle(interposer, [x, y, z.intTop + 0.01], 0.32, [0, 0, 1], {segments: 16, role: 'detail'});

  const ubump = G.part('ubump', 'Micro-bumps');
  const footprints = [[[0, 0], SOC], ...hbmCenters.map(c => [c, HBM])];
  for (const [[cx, cy], [w, h]] of footprints)
    for (const [x, y] of grid(w, h, UB_PITCH, 1.2)) cylinder(ubump, [cx + x, cy + y], z.intTop + 0.02, 0.46, 0.3);

  const soc = G.part('soc', 'SoC die');
  plate(soc, [0, 0], SOC, z.ubTop + 0.02, z.ubTop + socH);

  const hbm = G.part('hbm', 'HBM stacks');
  for (const [cx, cy] of hbmCenters) {
    const z0 = z.ubTop + 0.02;
    plate(hbm, [cx, cy], HBM, z0, z0 + hbmH);
    // DRAM layer boundaries as lines around the stack, just proud of its sides
    const e = 0.02, x0 = cx - HBM[0] / 2 - e, x1 = cx + HBM[0] / 2 + e, y0 = cy - HBM[1] / 2 - e, y1 = cy + HBM[1] / 2 + e;
    for (let k = 0; k < dramLayers; k++) {
      const zz = z0 + BASE_T + k * DRAM_T;
      G.polyline(hbm, [[x0, y0, zz], [x1, y0, zz], [x1, y1, zz], [x0, y1, zz]], {closed: true, role: k ? 'texture' : 'detail'});
    }
  }

  const tim = G.part('tim', 'Thermal interface material');
  plate(tim, [0, 0], [INT[0] - 3, INT[1] - 3], z.dieTop + 0.1, z.timTop, 0.8);

  const lid = G.part('lid', 'Copper lid');
  plate(lid, [0, 0], [LID, LID], z.timTop + 0.1, z.lidTop, 2.5);
  const wall = G.piece();
  G.extrude(wall, G.roundedRectangle(LID, LID, 2.5), {depth: z.timTop + 0.1 - z.subTop - 0.02,
    holes: [G.roundedRectangle(LID - 2 * WALL, LID - 2 * WALL, 1.2)]});
  G.transform(wall, {origin: [0, 0, z.subTop + 0.02]});
  G.merge(lid, wall);

  const lift = {bga: -16, substrate: 0, c4: 12, interposer: 24, ubump: 40, soc: 54, hbm: 54, tim: 70, lid: 96};
  const parts = [lid, tim, soc, hbm, ubump, interposer, c4, substrate, bga];
  for (const p of parts) p.explosion = [0, 0, lift[p.id]];

  return TechnicalProjection.render(parts, {...options, camera: options.camera ?? {azimuth: -118, elevation: 26, roll: 0}});
};
