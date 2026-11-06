// Demo timeline: one source of truth for what every frame shows, on both sides.
// Left, an agent session in a terminal; right, the drawing doing what was asked.
const FPS = 30, SECONDS = 20.5;
const ease = t => t <= 0 ? 0 : t >= 1 ? 1 : t < .5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2;
const clamp01 = t => Math.max(0, Math.min(1, t));

// parts lift off from the top of the stack down; BGA balls drop last
const ORDER = ['lid', 'tim', 'soc', 'hbm', 'ubump', 'interposer', 'c4', 'substrate', 'bga'];
const START = {lid: 3.0, tim: 3.3, soc: 3.6, hbm: 3.6, ubump: 3.9, interposer: 4.2, c4: 4.5, substrate: 0, bga: 4.8};
const LIFT_SECONDS = 1.8;

// the session: prompts type out, tool lines appear whole
const SESSION = [
  {at: 0.4, type: 1.6, kind: 'prompt', text: 'Draw an exploded view of a CoWoS package'},
  {at: 2.2, kind: 'tool', text: 'Write(model.js)'},
  {at: 2.35, kind: 'result', text: '9 parts, 2 parameters'},
  {at: 2.7, kind: 'tool', text: 'Bash(node proof.cjs drawing.json)'},
  {at: 2.85, kind: 'result', text: '21 sheets, every part visible'},
  {at: 6.9, type: 1.2, kind: 'prompt', text: 'Make the HBM stacks 16-high'},
  {at: 8.3, kind: 'tool', text: 'Update(model.js)'},
  {at: 8.45, kind: 'result', text: 'dramLayers 8 → 16'},
  {at: 9.6, type: 1.3, kind: 'prompt', text: 'Label the parts and publish it'},
  {at: 11.1, kind: 'tool', text: 'Bash(npx artifact-cafe publish dist)'},
  {at: 11.7, kind: 'result', text: 'artifact.cafe/a/cowos-package-teardown', link: true},
  {at: 15.7, kind: 'tool', text: 'Bash(npx artifact-cafe comments)'},
  {at: 15.85, kind: 'result', text: '3 open threads on v1'},
  {at: 16.4, type: 1.1, kind: 'prompt', text: 'Reply to each thread'},
  {at: 17.8, kind: 'tool', text: 'Reply(3 threads)'},
  {at: 17.95, kind: 'result', text: 'Answered on the review page'},
];

// reviewers on the published page; illustrative people, no real company
const COMMENTS = [
  {at: 12.6, part: 'HBM STACKS', who: 'Mei', role: 'Packaging engineer', text: ['16-high puts the stacks above the SoC.', 'Do we need a deeper lid cavity?'], reply: 18.0},
  {at: 13.6, part: 'THERMAL INTERFACE MATERIAL', who: 'Ken', role: 'Thermal lead', text: ['TIM is our biggest thermal knob.', 'Can we call out its thickness here?'], reply: 18.2},
  {at: 14.6, part: 'SILICON INTERPOSER', who: 'Lena', role: 'Product marketing', text: ['This is the slide for the launch deck.', 'Keep the interposer front and center.'], reply: 18.4},
];

function frame(i) {
  const t = i / FPS;
  const progress = Object.fromEntries(ORDER.map(id => [id, id === 'substrate' ? 0 : ease((t - START[id]) / LIFT_SECONDS)]));
  const dramLayers = t < 8.5 ? 8 : t < 9.1 ? 12 : 16;
  const azimuth = -146 + 34 * ease(t / 11.2);             // slow orbit, settles before the labels
  const labels = clamp01((t - 11.2) / 0.7);
  const room = ease((t - 10.4) / 1.0);                     // camera makes room for the labels
  const lines = SESSION.filter(l => t >= l.at).map(l => ({
    ...l, shown: l.type ? l.text.slice(0, Math.round(l.text.length * clamp01((t - l.at) / l.type))) : l.text,
    typing: !!l.type && t < l.at + l.type,
    age: t - l.at,
  }));
  const comments = COMMENTS.filter(c => t >= c.at).map(c => ({...c, age: t - c.at, replied: clamp01((t - c.reply) / 0.3)}));
  return {i, t, progress, dramLayers, camera: {azimuth, elevation: 26, roll: 0}, annotate: labels > 0, labels, room, lines, comments};
}

module.exports = {FPS, SECONDS, COUNT: Math.round(FPS * SECONDS), frame};
