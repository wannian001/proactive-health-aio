# Recovery overview / 身体状态与恢复

The Recovery route (`#recovery`) opens with a selectable illustrated regional body map,
two stacked horizontal cards (soreness and energy), cardio fitness and related
sleep, HRV, resting-heart-rate and training-load records. The morning check-in,
14-day regional history and after-training analyses remain below it.

恢复页顶部为部位地图、上下排列的酸痛与精力横卡、心肺趋势和相关记录。
早上打卡、14 天记录与练后分析仍在下方。人体插画可左右切换正面、左右侧面和背面，大小固定；
点击只选择部位，明确选择酸痛等级后仍需在打卡区保存。

## Meaning and missing data

- Soreness keeps the existing **0–3** scale. The main reading is the maximum
  recorded regional level, accompanied by affected regions/count, not a mean.
  No check-in for the selected day remains unknown; old soreness is not promoted
  to a current reading. A completed existing check-in treats omitted regions as
  not sore, matching the current CSV contract.
- Energy keeps the original **0–5** self-report. Zero is valid. A previous-day
  rating carries its date and an explicit previous-day label; it is never derived
  from HRV, sleep, the morning feeling or the after-training composite.
- Neither metric has a validated recovery forecast. The estimate reads
  **Not yet estimable / 暂无法估计** and the outer track stays empty/dashed. No
  invented target, recovery percentage or countdown is shown.
- Cardio uses `body.cardio()` unchanged, including the median, actual estimates,
  historical cutoff, comparison and freshness. It is separate from organ coloring.
- The recent-training layer uses only the last seven days of recorded region
  annotations; an unannotated workout does not imply untrained muscles.
- Historical Recovery dates apply to both self-report and cardio data.

酸痛保留四档，精力保留 0–5；未知与 0 分分开。恢复时间目前不可估计。
心肺读取已有长期趋势。模型按现有区域呈现记录，不能推断单块肌肉的状态。

## Illustration and runtime

`web/models/recovery/body-illustration.png` is an AI-generated four-view sprite
based on the user's preferred UI concept. It is a stylized gray athletic figure
wearing gray shorts. It is not a personal scan, anatomical measurement, or 3D mesh.
`models/recovery/ILLUSTRATION.md` records the image workflow and prompts.

The four fixed views run front → left → back → right. Buttons, horizontal swipes,
and left/right keyboard arrows switch views. Size is fixed; no zoom is offered.
The seven approximate regional hit areas match the existing check-in schema.
Anatomical left/right reverse on the back view; the far arm/calf is not selectable
through the visible side. Untracked thighs/forearms/hands/feet stay unclassified.
Transparent pixels do not select a region. A selected hidden region remains in the
accessible selector, while its image marker is hidden in that view.

Canvas 2D composites current soreness/training colors onto the neutral illustration,
clipped to its alpha and retaining muscle shading. No yellow or health values are
baked into the source image. Rendering happens only on view, data, appearance or
size changes, with pixel ratio capped at 2. Route changes release observers and
handlers. If the illustration cannot load, the region selector and data still work.
All assets are local; no WebGL or third-party requests are needed. Legacy BodyParts3D
and Three.js files retain their original credits but are no longer loaded here.

人体使用生成插画，四个视角切换，不声称可连续 3D 旋转。素材没有预设酸痛。
上色来自所选日期的记录；点击只选择，修改仍需明确保存。
