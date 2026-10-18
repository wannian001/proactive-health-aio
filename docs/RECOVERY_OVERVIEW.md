# Recovery overview / 身体状态与恢复

The Recovery route (`#recovery`) opens with a selectable 3D regional body map,
two stacked horizontal cards (soreness and energy), cardio fitness and related
sleep, HRV, resting-heart-rate and training-load records. The morning check-in,
14-day regional history and after-training analyses remain below it.

恢复页顶部为部位地图、上下排列的酸痛与精力横卡、心肺趋势和相关记录。
早上打卡、14 天记录与练后分析仍在下方。人体仅水平旋转，视距固定；
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

## Model and runtime

`web/models/recovery/body.bin` contains only the FJ2810 surface from BodyParts3D
4.0, through Human Atlas revision `1c38bf35c254a891200d3cedecfd57abebe83d8d`.
It is an adult male reference, not a personal scan. Seven approximate interaction
regions match the existing schema; unsupported thighs/forearms/hands remain
unclassified. The visible attribution links to the supplied CC BY 4.0 credits.
The source skin surface is locally repacked without geometric changes.

Three.js r180 is vendored with its MIT license. All model and renderer assets are
served locally; there are no third-party network requests. Rendering is on demand,
pixel ratio is capped at 2, and route changes dispose GPU resources. A failed or
unavailable WebGL context leaves the accessible region selector and data intact.

模型与渲染库随应用提供；只在旋转、选取、改色和尺寸变化时绘制。
切页释放资源；无法使用 3D 时仍可通过部位列表查看与编辑记录。
