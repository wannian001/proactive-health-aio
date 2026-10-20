# Recovery overview / 身体状态与恢复

The Recovery route (`#recovery`) opens with a 3D regional body you can turn all the way round,
two stacked horizontal cards (soreness and energy), cardio fitness and related
sleep, HRV, resting-heart-rate and training-load records. Below it, one card, "How you are right now",
takes everything you say (energy 0–10, this morning's feeling, soreness chosen on the body, mind and task);
then the after-training analyses, and the personal HRV model at the bottom. The overview itself writes
nothing: choosing a region and a level fills in that card, which saves.

恢复页顶部为部位地图、上下排列的酸痛与精力横卡、心肺趋势和相关记录。下面是「此刻怎么样」一张卡，
要说的都在这里（精力 0–10、早上的恢复感受、在人体图上选的酸痛、精神状态和任务），再往下是练后分析，
个人 HRV 模型在最下面。3D 人体可拖动 360° 旋转（按钮和左右方向键一次转 90°），大小固定；点击只选择部位，
选了程度之后在「此刻怎么样」里保存。

## Meaning and missing data

- Energy is rated **0–10** with a timezone-aware server timestamp. Soreness keeps its three levels
  (**0–3**, a little / clearly / very) on the morning check-in. Older 0–10 soreness ratings and 0–5
  energy entered by hand are still read and labeled with their own scale; the page no longer asks for them.
  A reported range remains a range; its drawing midpoint is not a training label.
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

精力用 0–10 分并记录时间；酸痛在早上打卡里保留三档。以前记的 0–10 酸痛和手填的 0–5 精力照样读、标明各自的量表，页面不再问。时间和目标突出显示，
有足够历史才出范围。区间自评保持原区间；设备值不代替主观标签。心肺读取已有长期趋势，
人体只呈现现有区域，不能推断单块肌肉的状态。

## The body and its runtime

`web/models/recovery/body.bin` is a cartoon made from MakeHuman's CC0 base body by `tools/make_body_mesh.py`: a
lean young man rounded like a toy, a slightly big head without a face, mitten-like hands and slate shorts, with the
muscles' places drawn as lines the way a fitness chart draws them (sternum, under the pectorals, the abdomen's six
blocks, deltoids, biceps and triceps, thighs, kneecaps, shins; behind, the spine, trapezius, shoulder blades, lats,
hamstrings and calves). It shows where muscles are, roughly, and which region is sore; a realistic body read as
uncanny. `models/recovery/MODEL.md` records where it comes from, what was done to it and the file layout. It is
not a personal scan or an anatomical model.

It turns all the way round: dragging sideways turns it (with a little run-on after a flick, none with reduced
motion), the two buttons and the left/right arrow keys turn it a quarter, Front turns it back. Vertical swipes
still scroll the page. The corner names the side turned towards you. Size is fixed; no zoom is offered, and the
whole body fits at every angle. The seven regional hit areas match the existing check-in schema; a click picks the
nearest triangle along the ray and its strongest region. Untracked thighs/forearms/hands/feet stay unclassified,
and a click that misses the body selects nothing. The marker sits where you clicked while that point shows, else on
the side of the region facing you; when the whole region is out of sight it is hidden, and the region stays in the
accessible selector.

Plain WebGL draws it (no library) in three passes: a dark outline (the back faces pushed out by a pixel and a
half), the body in soft cartoon tones (shadow, light, a highlight, a little baked occlusion) with current
soreness/training colours as its surface colour by each region's share, and the muscle lines, thin strips lying
on the skin, over it. No yellow or health values are in the model file. Rendering happens only on turning, data,
appearance or size changes, with pixel ratio capped at 2. Route changes release observers, handlers and the WebGL
context. Without WebGL, or if the file cannot load, the region selector and data still work. All assets are local;
nothing is requested from a third party. Earlier versions, a Three.js model (BodyParts3D) and then a four-view AI
illustration, are gone from the repository.

人体是用 MakeHuman 开源（CC0）基础人体做的卡通 3D 人，可连续 360° 旋转：磨圆的精瘦身材、不带五官，用健身示意图那样的线条
标出主要肌肉的大概位置，不追求解剖细节（太写实会有恐怖谷感）。模型里没有预设酸痛。
上色来自所选日期的记录；点击只选择，修改仍需明确保存。
