# Health AIO 3D body

`body.bin` is the Recovery page's turnable body: a cartoon, not a portrait. It shows where the muscles are and which
region is sore; a realistic body read as uncanny. `tools/make_body_mesh.py` builds it; run it again to change it
(`--weight`, `--muscle`, `--height`, `--proportions`, `--arms`, `--elbows`, `--round`, `--head`).

## Where it comes from

Everything is from the [MakeHuman](https://github.com/makehumancommunity/makehuman) 1.x repository at commit
`a8bc2d54ff0ac92e78ff71431b1023eda42bf482`, released there as CC0 (`LICENSE.ASSETS.md`): the base mesh
(`3dobjs/base.obj`), the macro targets (`targets/macrodetails/`), the default skeleton and its vertex weights
(`rigs/default.mhskel`, `rigs/default_weights.mhw`). No scan of a person, and no AI image.

## What was done to it

- **Build**: a man of 25, lean and fit: MakeHuman's weight dial at 0.25, muscle 0.85, height 0.55, proportions 0.75.
- **Stance**: the elbows straightened from MakeHuman's bent rest pose (8° left), the arms lowered to 16° from
  vertical, by the skeleton's own vertex weights.
- **A toy's build**: the whole skin rounded (25 steps of volume-keeping smoothing), the hands three times as much,
  so they read as mittens; the head a size up (×1.15), as a cartoon's is.
- **No face**: the neck and head are turned into a solid, openings up to about 2 cm closed (the mouth, the eye
  sockets), its distance field blurred by 1.6 cm, and meshed again. Ears, eyes and mouth are gone.
- **Shorts**: from 9 cm above the hip joints to mid-thigh the skin is smoothed like fabric and stands 5 mm proud;
  the page colours it slate.
- **Muscle lines**, the way a fitness chart draws them: in front, the sternum, under the pectorals, the abdomen's
  six blocks, the thighs, kneecaps and shins; behind, the spine, trapezius, shoulder blades, lats, hamstrings and
  the calf's two heads; on each arm the deltoid's V and the line between biceps and triceps. They are drawn in a
  front and a back view, hung from the skeleton's joint heights, and dropped onto the skin, so their places are
  approximate. None on the head, hands or shorts.
- One Catmull-Clark subdivision for round outlines; ambient occlusion baked per vertex from 160 directions.

## Regions

Each vertex carries its two strongest regions among the 31 places soreness is said for (`schema.SORE_REGIONS`) and
"other" (the head, forearms, hands and feet, which are not places), and how much of it is the first. The arms are
what the skeleton weights put on the arm bones: the first 36% of the way to the elbow is the shoulder, split front
and back at the shoulder joint, then the upper arm to the elbow. The neck runs from its base to under the chin in
front and to the skull behind, cut front and back at its middle, the back in halves. The torso is cut front and back
at its own middle, height by height: the chest down to a little under the breast joints, then the abs; behind, the
upper back down to 15 cm above the waist, the lower back to the waist, then the glutes. Below the gluteal fold each
leg is cut in four by the angle round its own middle (front, back, outside, inside), the thigh to the knee, the calf
to the ankle. Edges are softened over about a centimetre. These are hit areas at the granularity people say where it
hurts, and the lines are a guide to where muscles lie: the model cannot show an individual muscle's injury, an organ's state or a recovery time.

## File layout

Little-endian: `"HAB3"`, a uint32 header length, the JSON header (space-padded to 4 bytes), then positions
(int16 x3, padded to 4 bytes; a position is `center + q / 32767 * extent`, metres, soles at y = 0, facing +z, the
person's left at +x), normals (int8 x3 + 0), occlusion and cloth (uint8, + 2 zero bytes), regions (uint8 x4: the
strongest region's index in the header's list, the second's, how much of the two is the first × 255, 0) and
triangles (uint16 x3); then, each block 4-byte aligned, the muscle lines' positions
(int16 x3, as the body's) and triangles (uint16 x3), counted in the header's `lines`. The header also holds, per
region, eight surface points (one per 45° around the body) where the page puts its marker for a region chosen
from the list.
