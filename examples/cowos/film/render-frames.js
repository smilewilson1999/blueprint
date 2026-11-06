#!/usr/bin/env node
// Render raw frames: node film/render-frames.js START END OUTDIR
// Each frame is the model's own hidden-line render, with every part lifted by its own
// progress. Writes {markup, scale, offset} per frame; compose.js fixes the framing.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const {frame} = require('./timeline.js');

const root = path.resolve(__dirname, '..');
const context = {console, structuredClone};
context.self = context;
vm.createContext(context);
for (const f of ['sheet.js', 'geometry.js', 'projection.js'])
  vm.runInContext(fs.readFileSync(path.join(root, '../../skills/blueprint-teardown/engine/assets', f), 'utf8'), context);
vm.runInContext(fs.readFileSync(path.join(root, 'model.js'), 'utf8'), context);

const realRender = context.TechnicalProjection.render;
const [start, end, out] = [Number(process.argv[2]), Number(process.argv[3]), process.argv[4]];
fs.mkdirSync(out, {recursive: true});

for (let i = start; i < end; i++) {
  const f = frame(i);
  // let the model build its parts, then take them before it renders
  let captured = null;
  context.TechnicalProjection.render = (parts, options) => (captured = {parts, options}, {});
  context.DrawingModels.cowos({hbmPerSide: 2, dramLayers: f.dramLayers}, {explosion: 1, isolated: null, fill: true, annotate: f.annotate, camera: f.camera});
  context.TechnicalProjection.render = realRender;
  for (const p of captured.parts) p.explosion = p.explosion.map(v => v * f.progress[p.id]);
  const r = realRender(captured.parts, {...captured.options, explosion: 1, fitExplosion: 1});
  fs.writeFileSync(path.join(out, `raw-${String(i).padStart(4, '0')}.json`), JSON.stringify({markup: r.markup, scale: r.scale, offset: r.offset, bounds: r.bounds}));
  process.stdout.write('.');
}
process.stdout.write('\n');
