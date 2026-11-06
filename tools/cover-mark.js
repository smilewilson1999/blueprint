#!/usr/bin/env node
// Render the cover watermark: the CoWoS package exploded sideways into one level row of
// parts, outlines only. node tools/cover-mark.js OUT.svg
// Uses the example's own model and the teardown engine, so the drawing is the real model.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const engine = path.join(root, 'skills/blueprint-teardown/engine/assets');
const context = {console, structuredClone};
context.self = context;
vm.createContext(context);
for (const f of ['sheet.js', 'geometry.js', 'projection.js']) vm.runInContext(fs.readFileSync(path.join(engine, f), 'utf8'), context);
vm.runInContext(fs.readFileSync(path.join(root, 'examples/cowos/model.js'), 'utf8'), context);

const camera = {azimuth: -118, elevation: 32, roll: 0};
// left to right, bottom of the stack to the top; the SoC and its HBM stacks share a slot
const SLOT = {bga: 0, substrate: 1, c4: 2, interposer: 3, ubump: 4, soc: 5, hbm: 5, tim: 6, lid: 7};
const PITCH = 70, RISE = 0;                                  // model mm between slots, along the camera's right; RISE lifts each slot

let captured = null;
const real = context.TechnicalProjection.render;
context.TechnicalProjection.render = (parts, options) => (captured = {parts, options}, {});
context.DrawingModels.cowos({hbmPerSide: 2, dramLayers: 8}, {explosion: 1, isolated: null, fill: false, annotate: false, camera});
context.TechnicalProjection.render = real;

const a = camera.azimuth * Math.PI / 180, right = [-Math.sin(a), Math.cos(a), 0];
for (const p of captured.parts) {
  const k = (SLOT[p.id] - 3.5) * PITCH;
  p.explosion = [right[0] * k, right[1] * k, SLOT[p.id] * RISE];
}
const r = real(captured.parts, {...captured.options, explosion: 1, fitExplosion: 1, camera});

// outlines and edges only: drop vias, DRAM layer lines and other fine detail
const keep = new Set(['outline', 'edge']);
const markup = r.markup.replace(/<path data-line-role="(\w+)"[^>]*\/>/g, (m, role) => keep.has(role) ? m : '');
const b = r.bounds, pad = 2;
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${(b.x - pad).toFixed(2)} ${(b.y - pad).toFixed(2)} ${(b.width + 2 * pad).toFixed(2)} ${(b.height + 2 * pad).toFixed(2)}">`
  + `<style>path{fill:none;stroke:#202020;stroke-linejoin:round;stroke-linecap:round}[data-line-role="outline"]{stroke-width:.30}[data-line-role="edge"]{stroke-width:.18}</style>`
  + markup + '</svg>';
fs.writeFileSync(process.argv[2], svg);
console.log(`wrote ${process.argv[2]}: ${b.width.toFixed(0)} × ${b.height.toFixed(0)} mm, aspect ${(b.width / b.height).toFixed(2)}`);
