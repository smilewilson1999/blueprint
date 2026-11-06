# Evidence: CoWoS-style 2.5D package

**Intended use:** an explanatory exploded illustration of how a 2.5D advanced package
(CoWoS-style, as used by AI accelerators) is built up layer by layer. For a README,
slides and review on artifact.cafe. Output: landscape A3 sheet (420 × 297 mm), viewed
in the bundled page at screen size; SVG, PNG and PDF downloads.

**This is a concept drawing.** No product's drawings or dimensions were supplied. The
build-up order follows public descriptions of CoWoS-S packages; every dimension is
invented for legibility. The vertical axis is exaggerated several times over, because
at true proportion the dies, bumps and interposer are too thin to draw.

| Feature group | Evidence kind | How it is drawn |
| --- | --- | --- |
| Build-up order: BGA → substrate → C4 → interposer → micro-bumps → dies → TIM → lid | Public descriptions of the package type (concept) | One part per layer, stacked on one explosion axis |
| Organic package substrate | Concept | Rounded square plate; internal routing layers omitted |
| BGA solder balls | Concept | Spheres on a square grid under the substrate; real ball count (thousands) reduced to a readable grid |
| C4 bumps | Concept | Short cylinders on the same grid as the interposer's TSVs |
| Silicon interposer | Concept | Plate sized from the dies above it; through-silicon vias shown as circles on its top face, one per C4 bump |
| Micro-bumps | Concept | Fine-pitch cylinders under each die only |
| SoC die | Concept | One plate in the center of the interposer |
| HBM stacks | Concept | One column per side; each stack is a base die plus N DRAM layers, the layers drawn as lines on its sides. Count per side and layer count are parameters |
| Thermal interface material | Concept | Thin plate over all dies |
| Copper lid | Concept | Top plate plus a perimeter wall that sits on the substrate |
| Underfill, molding, passives, stiffener, routing layers | Hidden or unspecified construction | Omitted |

## Rebuild and proof

```sh
npm install
npm run proof      # assembled and exploded proofs in proof/
npm run build      # dist/index.html
npm run check      # headless check of the built page
npm run film       # optional: dist/cowos-teardown.mp4, needs Python Playwright and ffmpeg
```
