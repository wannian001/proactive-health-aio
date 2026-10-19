# Recovery overview / 身体状态与恢复

The Recovery route (`#recovery`) opens with a selectable illustrated regional body map,
two stacked horizontal cards (soreness and energy), cardio fitness and related
sleep, HRV, resting-heart-rate and training-load records. The morning check-in,
14-day regional history and after-training analyses remain below it.

恢复页顶部为部位地图、上下排列的酸痛与精力横卡、心肺趋势和相关记录。
早上打卡、14 天记录与练后分析仍在下方。人体插画可左右切换正面、左右侧面和背面，大小固定；
点击只选择部位，明确选择酸痛等级后仍需在打卡区保存。

## Meaning and missing data

- New current-time check-ins keep the original **0–10** rating with timezone-aware server timestamps.
  A reported range remains a range; its drawing midpoint is not a training label. Legacy morning
  soreness **0–3** and energy **0–5** remain separate and are labeled with their original scale.
- The main soreness reading is the maximum of explicitly recorded regions. With timestamped input,
  untouched regions stay unknown. Selecting a region never changes whole-person energy.
- Both cards show a time window and target when personal history supports one. Daily observations
  produce day windows; dense timestamped observations can produce hour windows. Missing, old,
  incomplete or insufficient history explains why no time is shown.
- The purple outer ring is the window midpoint relative to its labeled 24/168-hour scale, not a
  progress percentage or confidence. No forecast means no outer ring. Algorithm and validation
  details are in [RECOVERY_FORECAST.md](RECOVERY_FORECAST.md).
- Related device readings carry their actual dates. Missing workout detail is not evidence of no training.
- Cardio uses `body.cardio()` unchanged, including the median, actual estimates,
  historical cutoff, comparison and freshness. It is separate from organ coloring.
- The recent-training layer uses only the last seven days of recorded region
  annotations; an unannotated workout does not imply untrained muscles.
- Historical Recovery dates apply to both self-report and cardio data.

新打卡采用原始 0–10 分并记录时间；旧四档酸痛、0–5 精力仍保留。时间和目标突出显示，
有足够历史才出范围。区间自评保持原区间；设备值不代替主观标签。心肺读取已有长期趋势，
人体只呈现现有区域，不能推断单块肌肉的状态。

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
