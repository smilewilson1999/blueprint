#!/usr/bin/env node
// Compose raw frames into fixed-framing 16:9 SVGs: node film/compose.js RAWDIR OUTDIR
// Every raw frame was fitted to the sheet on its own. Map each one back to camera space
// (paper = offset + scale * cam) and then onto one shared scale, so nothing jumps.
const fs = require('node:fs'), path = require('node:path');
const {frame, COUNT} = require('./timeline.js');
const SHEET = require('../../../skills/blueprint-teardown/engine/assets/sheet.js');

const [rawDir, outDir] = process.argv.slice(2);
fs.mkdirSync(outDir, {recursive: true});
const W = 528, H = 297;                                     // 16:9 in sheet millimetres
const AREA = {x0: 238, x1: 512, y0: 20, y1: 272};           // right of the terminal
const TERM = {x: 18, y: 62, w: 206, h: 170};                // the agent session, left, centered on the drawing

const raws = [];
for (let i = 0; i < COUNT; i++) {
  const r = JSON.parse(fs.readFileSync(path.join(rawDir, `raw-${String(i).padStart(4, '0')}.json`), 'utf8'));
  const b = r.bounds, [ox, oy] = r.offset, s = r.scale;
  r.cam = [(b.x - ox) / s, (b.y - oy) / s, (b.x + b.width - ox) / s, (b.y + b.height - oy) / s];
  raws.push(r);
}
// a following camera: fit each frame, widen toward the end so the labels have room,
// then smooth both scale and center so the dolly never jitters
const LABEL_ROOM = 52;                                      // sheet mm per side the labels need
const fits = raws.map((r, i) => {
  const room = frame(i).room * LABEL_ROOM / r.scale;
  const c = [r.cam[0] - room, r.cam[1], r.cam[2] + room, r.cam[3]];
  const fs = Math.min((AREA.x1 - AREA.x0) / (c[2] - c[0]), (AREA.y1 - AREA.y0) / (c[3] - c[1]));
  return {S: Math.min(fs, 3.2), cx: (c[0] + c[2]) / 2, cy: (c[1] + c[3]) / 2};
});
// the widest frame so far bounds the scale, so the camera only ever pulls back
for (let i = 1; i < fits.length; i++) fits[i].S = Math.min(fits[i].S, fits[i - 1].S);
const smooth = (key, w = 9) => fits.map((_, i) => {
  let sum = 0, n = 0;
  for (let j = Math.max(0, i - w); j <= Math.min(fits.length - 1, i + w); j++) { sum += fits[j][key]; n++; }
  return sum / n;
});
const SS = smooth('S'), CX = smooth('cx'), CY = smooth('cy');
const view = i => ({S: SS[i], O: [(AREA.x0 + AREA.x1) / 2 - SS[i] * CX[i], (AREA.y0 + AREA.y1) / 2 - SS[i] * CY[i]]});

const PART = {   // Cafe OS materials: stroke, fill
  lid: ['#A0561E', '#EFDFCC'], tim: ['#8C7A2E', '#F5F0DC'], soc: ['#6A4FC4', '#E6E0F7'],
  hbm: ['#1E7D74', '#D2EBE7'], ubump: ['#A27419', '#F2E3BC'], interposer: ['#2C6DB0', '#D9E7F5'],
  c4: ['#A27419', '#F2E3BC'], substrate: ['#227A4C', '#D5EBDD'], bga: ['#A27419', '#F2E3BC'],
};
const font = f => path.resolve(__dirname, '..', f);
const style = `
@font-face{font-family:Inter;font-weight:100 900;src:url("file://${font('node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2')}") format("woff2")}
@font-face{font-family:Plex;src:url("file://${font('../../skills/blueprint/assets/fonts/IBMPlexMono-400.woff2')}") format("woff2")}
path{fill:none;stroke:#2B2622;stroke-linejoin:round}
${Object.entries(PART).map(([id, [s, f]]) => `g[data-item="${id}"] path{stroke:${s}}[data-fill="${id}"]{fill:${f};stroke:none}`).join('')}
[data-annotations] path{stroke:#8F8A80}[data-annotations] [data-ink-fill]{fill:#5B544B;stroke:none}
text[data-annotation]{fill:#2B2622;font-family:Inter;font-weight:550;letter-spacing:.02em}
.t{font:5.2px Plex,Menlo,monospace;fill:#E8E3D9;white-space:pre}
.t .p{fill:#DB8A52}.t .dot{fill:#94A97C}.t .r{fill:#A39C90}.t .l{fill:#EBA877;text-decoration:underline}
.bar{font:3.9px Plex,Menlo,monospace;fill:#8C857A}
.note{font:3.3px Plex,Menlo,monospace;fill:#8F8A80;letter-spacing:.04em}
.who{font:620 3.7px Inter;fill:#2B2622}.role{font:2.9px Plex,Menlo,monospace;fill:#8F8A80}
.body{font:3.6px Inter;fill:#2B2622}.reply{font:3px Inter;fill:#6F8259;font-weight:560}
.ini{font:650 3.1px Inter;fill:#fff}
`;
const esc = s => s.replaceAll('&', '&amp;').replaceAll('<', '&lt;');

// where each label's dot sits on its part, in this frame's paper coordinates
function anchors(markup) {
  const out = {};
  for (const [, cx, cy, name] of markup.matchAll(/<circle data-ink-fill="" cx="([\d.]+)" cy="([\d.]+)"[^>]*\/><text[^>]*>([^<]+)<\/text>/g)) out[name] = [+cx, +cy];
  return out;
}
const CARD = {W: 76, H: 23};
// card offset from its pin, chosen so cards sit over open space and clear the labels
const PLACE = {'HBM STACKS': [-86, -50], 'THERMAL INTERFACE MATERIAL': [-50, -38], 'SILICON INTERPOSER': [12, 8]};
const pop = a => { const t = Math.min(1, a / .35); return 1 + 2.2 * (t - 1) ** 3 + 1.2 * (t - 1) ** 2; };   // back-out
function comments(f, at, place) {
  return f.comments.map(c => {
    const a = at[c.part]; if (!a) return '';
    const [x, y] = place(a), [dx, dy] = PLACE[c.part];
    const k = pop(c.age), cardIn = Math.min(1, Math.max(0, (c.age - .12) / .3)), lift = 4 * (1 - cardIn);
    const cx = x + dx, cy = y + dy + lift, h = CARD.H + (c.replied > 0 ? 6 : 0);
    return `<g>
<g transform="translate(${x.toFixed(2)} ${y.toFixed(2)}) scale(${k.toFixed(3)})"><circle cx="4" cy="-4" r="4.4" fill="#F7F7F4"/><rect x="0" y="-4" width="4" height="4" fill="#B25F28"/><circle cx="4" cy="-4" r="3.6" fill="#B25F28"/><text class="ini" x="4" y="-2.9" text-anchor="middle">${c.who[0]}</text></g>
<g opacity="${cardIn.toFixed(3)}" filter="url(#shadow)">
<rect x="${cx}" y="${cy}" width="${CARD.W}" height="${h}" rx="3" fill="#FFFFFF" stroke="#E3DED3" stroke-width=".3"/>
<text class="who" x="${cx + 5}" y="${cy + 7}">${esc(c.who)}<tspan class="role" dx="2">${esc(c.role)}</tspan></text>
<text class="body" x="${cx + 5}" y="${cy + 13.4}">${esc(c.text[0])}</text><text class="body" x="${cx + 5}" y="${cy + 18.6}">${esc(c.text[1])}</text>
${c.replied > 0 ? `<g opacity="${c.replied.toFixed(3)}"><line x1="${cx + 5}" x2="${cx + CARD.W - 5}" y1="${cy + 22.2}" y2="${cy + 22.2}" stroke="#EAE8E3" stroke-width=".3"/><circle cx="${cx + 6.4}" cy="${cy + 25.6}" r="1.1" fill="#6F8259"/><text class="reply" x="${cx + 9}" y="${cy + 26.6}">Claude replied</text></g>` : ''}
</g></g>`;
  }).join('\n');
}

// an agent session: prompts type out with a block cursor, tool lines land whole
function terminal(f) {
  const {x, y, w, h} = TERM, LH = 8.2, CH = 3.12, left = x + 10;   // CH: one mono character
  const rows = [];
  let row = y + 27;
  for (const l of f.lines) {
    const fade = Math.min(1, l.age / 0.18).toFixed(3);
    if (l.kind === 'prompt') {
      if (rows.length) row += 5;
      rows.push(`<text class="t" x="${left}" y="${row.toFixed(2)}"><tspan class="p">&gt; </tspan>${esc(l.shown)}</text>`);
      if (l.typing) rows.push(`<rect x="${(left + CH * (2 + l.shown.length)).toFixed(2)}" y="${(row - 4.3).toFixed(2)}" width="2.8" height="5.6" fill="#E8E3D9"/>`);
      row += LH + 1.5;
    } else if (l.kind === 'tool') {
      rows.push(`<text class="t" x="${left}" y="${row.toFixed(2)}" opacity="${fade}"><tspan class="dot">⏺ </tspan>${esc(l.text)}</text>`);
      row += LH * 0.85;
    } else {
      rows.push(`<text class="t r" x="${left + CH}" y="${row.toFixed(2)}" opacity="${fade}"><tspan>⎿  </tspan><tspan class="${l.link ? 'l' : 'r'}">${esc(l.text)}</tspan></text>`);
      row += LH;
    }
  }
  // an idle prompt with a blinking cursor whenever nothing is typing
  if (!f.lines.some(l => l.typing)) {
    if (f.lines.length) row += 5;
    const on = Math.floor(f.t * 2) % 2 === 0;
    rows.push(`<text class="t" x="${left}" y="${row.toFixed(2)}"><tspan class="p">&gt; </tspan></text>`);
    if (on) rows.push(`<rect x="${(left + CH * 2).toFixed(2)}" y="${(row - 4.3).toFixed(2)}" width="2.8" height="5.6" fill="#E8E3D9" opacity=".85"/>`);
  }
  // scroll like a real terminal once the session outgrows the window
  const scroll = Math.max(0, row - (y + h - 9));
  return `<g>
<clipPath id="term-clip"><rect x="${x}" y="${y + 14.2}" width="${w}" height="${h - 14.2}"/></clipPath>
<rect x="${x}" y="${y + 1.6}" width="${w}" height="${h}" rx="5" fill="#2B2622" opacity=".10"/>
<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="5" fill="#26221E"/>
<circle cx="${x + 8}" cy="${y + 7}" r="1.5" fill="#4A4038"/><circle cx="${x + 13}" cy="${y + 7}" r="1.5" fill="#4A4038"/><circle cx="${x + 18}" cy="${y + 7}" r="1.5" fill="#4A4038"/>
<text class="bar" x="${x + w / 2}" y="${y + 8.4}" text-anchor="middle">claude · ~/cowos</text>
<line x1="${x}" x2="${x + w}" y1="${y + 14}" y2="${y + 14}" stroke="#3A322B" stroke-width=".3"/>
<g clip-path="url(#term-clip)"><g transform="translate(0 ${(-scroll).toFixed(2)})">${rows.join('\n')}</g></g>
</g>`;
}

for (let i = 0; i < COUNT; i++) {
  const f = frame(i), r = raws[i], {S, O} = view(i), k = S / r.scale;
  // line weights are sheet millimetres after scaling, so divide them by this frame's zoom
  const lines = Object.entries(SHEET.linework.technical).map(([role, w]) => `[data-line-role="${role}"]{stroke-width:${(w * 1.25 / k).toFixed(4)};stroke-linecap:${SHEET.linecap(role)}}`).join('');
  const markup = r.markup.replace('<g data-annotations', `<g opacity="${f.labels.toFixed(3)}" data-annotations`);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 ${W} ${H}"><style>${style}${lines}</style>
<defs><filter id="shadow" x="-20%" y="-30%" width="140%" height="180%"><feDropShadow dx="0" dy="1.6" stdDeviation="2.2" flood-color="#3C2814" flood-opacity=".16"/></filter></defs>
<rect width="${W}" height="${H}" fill="#F7F7F4"/>
<g transform="translate(${O[0].toFixed(3)} ${O[1].toFixed(3)}) scale(${k.toFixed(6)}) translate(${(-r.offset[0]).toFixed(3)} ${(-r.offset[1]).toFixed(3)})">${markup}</g>
${terminal(f)}
<text class="note" x="512" y="284" text-anchor="end">CONCEPT · NOT TO SCALE</text>
${comments(f, anchors(r.markup), ([px, py]) => [O[0] + k * (px - r.offset[0]), O[1] + k * (py - r.offset[1])])}
</svg>`;
  fs.writeFileSync(path.join(outDir, `f-${String(i).padStart(4, '0')}.svg`), svg);
}
console.log(`composed ${COUNT} frames, zoom ${SS[0].toFixed(2)} → ${SS[COUNT - 1].toFixed(2)}`);
