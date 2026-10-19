<div align="center">

# The Health AIO design kit

The colours, components, charts and icons every Health AIO page is built from, in four files another app can copy.<br>
Health AIO 每一页用的颜色、组件、图表和图标，放在四个文件里，别的应用可以整套拷走。

**[Gallery · 展示页](https://wannian001.github.io/proactive-health-aio/#kit)** (every token, component and chart, drawn live · 每个变量、组件和图表现场画出来) &nbsp;·&nbsp; [English](#english) &nbsp;·&nbsp; [中文](#中文)

</div>

## English

### What it is, and what it is not

Health AIO has two jobs. It is a public showcase of a local-first dashboard, and it is the source of one look: the
design kit. Another app (the author's private system, say) copies the kit and keeps its own pages and features.
Design flows one way, from healthaio to the copies. Features flow the other way only when they are generic and can
be shown with demo data.

The kit **is**: the tokens of both modes, the base styles, the shell (header, menu, page column), the components,
the SVG charts with their helpers, and the stroke icons. It is plain CSS and ES modules with no build step.

The kit **is not**: Health AIO's page layouts (those stay in `healthaio/web/css/app.css`), anything that computes data,
the words on a page (the app hands its own to the charts with `setFormat()`), or a theme picker. There is one look
per mode.

The gallery page (`#kit`, not in the menu; every page links to it from its footer) shows every token with its light
and dark value whatever mode you are in, every component in its states and every chart drawn from made-up sample
data, each with its signature and one line on what it does. Locally it is <http://localhost:8790/#kit>.

### Files

| file | role | holds |
|---|---|---|
| `css/tokens.css` | tokens | every custom property, light values on `:root`, dark values twice (system setting and the moon button), kept equal by a test |
| `css/kit.css` | components | base styles, the shell and the components; every colour and every step of the space scale is a token (a few small sizes are plain numbers), and no rule names a Health AIO page |
| `js/charts.js` | charts | the SVG charts and their helpers; imports nothing |
| `js/icons.js` | icons | the stroke icons, their colours and the state-chip glyphs |
| `kit.json` | manifest | written by `export` into the app's folder only (there is none in `healthaio/web/`): version, every file's SHA-256 and size, the tokens, components and charts |

The four kit files' paths are relative to `healthaio/web/`. The manifest is built from the files as they are on disk
(`healthaio/kit.py`): `python3 -m healthaio kit json` prints it, the server answers it at `/api/kit`, and
`build-static` writes it to `api/kit.json` for the demo site. It reads three conventions in the files:

- tokens.css: a comment `/* [role] … */` starts each group of tokens (type, space, radius, motion, neutral, accent,
  effect, data, status);
- kit.css: a comment `/* @component <class> <one line> */` starts each group of rules;
- charts.js and icons.js: the `//` comment line right above each `export` is its one-line doc.

### Tokens

Type: `--font` (the system stack, with PingFang SC and Noto Sans SC for Chinese), `--mono`, and
`--t-xs` 12px, `--t-sm` 13px, `--t-md` 15px, `--t-lg` 18px, `--t-xl` 24px, `--t-2xl` 34px, `--t-3xl` 44px. Space: `--s-1` 4px, `--s-2` 8px, `--s-3` 12px, `--s-4` 16px, `--s-5` 20px, `--s-6` 28px, `--s-7` 40px, `--s-8` 56px. Radius: `--r-sm` 8px, `--r-md` 12px, `--r-lg` 18px, `--r-pill` 999px. Motion: `--ease` cubic-bezier(.2, .7, .2, 1). Shadows: `--shadow` (cards) and
`--seg-on-edge` (the chosen part of a switch).

Colours, light and dark ("same" = the same value in both modes):

| token | light | dark | used for |
|---|---|---|---|
| `--bg` | `#f4f4f3` | `#0b0d13` | page background |
| `--surface` | `#ffffff` | `#141822` | cards |
| `--surface-2` | `#f7f7f6` | `#1a1f2b` | tiles, chips, inset parts |
| `--ink` | `#161616` | `#eceef5` | text; the inverted menu pill |
| `--ink-2` | `#4a4a48` | `#b4bbcc` | secondary text, chart labels |
| `--ink-3` | `#6a6a67` | `#8c95a8` | muted text, axis text |
| `--line` | `#e4e4e1` | `#232937` | hairlines between rows, card edges |
| `--line-2` | `#cfcfcb` | `#313849` | control borders, dashed outlines, empty tracks |
| `--header` | `rgba(244, 244, 243, .84)` | `rgba(11, 13, 19, .8)` | the see-through sticky header |
| `--seg-on` | `#ffffff` | `#353d50` | the chosen part of a switch |
| `--halo` | `var(--surface)` | same | the ring round a chart mark |
| `--accent` | `#1f5fbf` | `#aea2f7` | links, focus ring, the now hand, progress |
| `--accent-soft` | `rgba(31, 95, 191, .1)` | `rgba(174, 162, 247, .14)` | accent chip, the weight corridor |
| `--on-accent` | `#ffffff` | `#14102e` | text on a solid accent fill (reserved) |
| `--c-focus` | `#2a78d6` | `#3987e5` | Focused work and learning (screen time) |
| `--c-fun` | `#eb6834` | `#d95926` | Entertainment & social |
| `--c-comms` | `#1baf7a` | `#199e70` | Communication |
| `--c-other` | `#a3a9b5` | `#5d6474` | Other screen time |
| `--c-sleep` | `#4a3aa7` | `#9085e9` | Sleep: its own ring track, lane and chart |
| `--c-exercise` | `#bf3fa6` | `#cb4db2` | Logged workouts |
| `--c-exercise-ink` | `#a8318f` | `#de78c8` | Workout minutes written as text |
| `--c-exercise-2` | `#da90cb` | `#86397b` | A kind of training, one step lighter: cardio (the Exercise page) |
| `--c-exercise-3` | `#e7b6dd` | `#5d2d5c` | A kind of training, lightest: walking and other workouts |
| `--c-event` | `#161616` | `#eceef5` | Calendar blocks (ink, not a hue) |
| `--c-band` | `rgba(22, 22, 22, .075)` | `rgba(236, 238, 245, .085)` | The “your normal” band and empty tracks |
| `--c-grid` | `rgba(22, 22, 22, .07)` | `rgba(236, 238, 245, .07)` | Gridlines |
| `--c-axis` | `rgba(22, 22, 22, .22)` | `rgba(236, 238, 245, .22)` | Axes and baselines |
| `--c-mark` | `#161616` | `#eceef5` | A neutral mark: this week, an average, a deadline |
| `--c-sore-0` | `#e5e5ea` | `#3a4152` | A body region with nothing sore, on the plate |
| `--c-sore-1` | `#f8dd8b` | same | Soreness: a little (the Recovery page's body figures, gauge and strips) |
| `--c-sore-2` | `#eeb947` | same | Soreness: clearly sore |
| `--c-sore-3` | `#d99519` | same | Soreness: very sore; also the soreness gauge's arc |
| `--c-estimate` | `#b4a0ed` | same | How far ahead an estimate reaches: the outer ring of Recovery's soreness and energy gauges |
| `--plate` | `#ffffff` | `#1c2130` | The body figure's plate |
| `--plate-ink` | `#3a3a3c` | `#c3c9d6` | The figure's line art and the labels on the plate |
| `--good` | `#0ca30c` | same | good mark in a chart |
| `--good-ink` | `#1d7a1d` | `#4cc94c` | good text |
| `--good-soft` | `rgba(12, 163, 12, .11)` | `rgba(12, 163, 12, .18)` | good chip background |
| `--watch` | `#fab219` | same | watch mark in a chart |
| `--watch-ink` | `#8a5a00` | `#f5bd4a` | watch text |
| `--watch-soft` | `rgba(250, 178, 25, .16)` | `rgba(250, 178, 25, .14)` | watch chip background |
| `--on-watch` | `#161616` | `#0b0d13` | text written on a watch fill |
| `--off` | `#d03b3b` | same | off (worse) mark in a chart |
| `--off-ink` | `#b42828` | `#f27c7c` | off text (.bad) |
| `--off-soft` | `rgba(208, 59, 59, .1)` | `rgba(208, 59, 59, .2)` | off chip background |

### Colour rules

- **A data colour is fixed to the thing measured.** Focus (work and learning) is always blue, entertainment and
  social orange, communication aqua, other screen time grey, sleep violet, logged workouts magenta; calendar blocks
  are ink. Each keeps its hue in both modes, with its own step per mode. A data colour never stands for a state, and
  a status colour never stands for a thing measured: use `--watch`, not `--c-fun`, for "worth a look".
- **Colour-vision checks.** Focus, entertainment and communication pass the checks for every pair in both modes
  (worst CVD ΔE 9.2). Sleep is too close to focus under protanopia, so it is never placed next to it: it has its own
  ring track, lane and chart. Exercise may sit next to sleep (worst ΔE 8.4).
- **Status colours are reserved and always come with a word or an icon.** Good, watch and off each have a fill (for
  marks in charts), an ink (for text) and a soft step (for a chip's background). The fills are the same in both
  modes on purpose; the ink and soft steps change. Text written on a watch fill uses `--on-watch`. The classes are
  `.good`, `.watch` and `.bad` (`.bad` uses the off colours).
- **One look per mode.** Light mode is graphite neutrals with a blue accent, dark mode dusk neutrals with a violet
  accent. The page follows the system setting; `data-mode="light"` or `"dark"` on `<html>` overrides it.
- **Charts are otherwise ink and grey.** The "your normal" band is a faint fill (`--c-band`), a dashed line is a
  plan or a limit, × is a day without a record, diagonal stripes are something added on top of the rest (a hatch
  part of `lanes`, such as the minutes a second device adds beyond the clock), and a mark drawn over others gets a
  `--halo` ring in the colour behind it (`--surface` on a card; `.tile` sets it to `--surface-2`).

### Components and charts

Each of these is shown in the gallery. Components (kit.css): `.sr`, `.top`, `.brand`, `.nav`, `.side`, `.tool`, `.demo-badge`, `.head`, `.stepper`, `.grid`, `.col`, `.card`, `.lede`, `.stack`, `.eyebrow`, `.hero-num`, `.chip`, `.dot`, `.legend`, `.ring`, `.agenda`, `.tonight`, `.tiles`, `.seg`, `.subnav`, `.how`, `.empty`, `.foot`, `.tip`, `.catbar`, `.hbar`, `.progress`, `.mark`, `.facts`, `table`, `.code`, `.chart`, `.ph`.

| function | what it draws |
|---|---|
| `spark(series, band, { width, height = 46, unit = "", tone = "neutral" })` | 14 days as a line over the "your normal" band; × marks a day without a record, the end dot takes the tone. |
| `bullet(value, band, { width, unit = "", tone = "neutral", height = 18 })` | One value against its band on a line: band = normal, tick = its median, dot = the value in its tone. |
| `rangeStrip(row, { width, height = 30, pad = 10 })` | One value on its own scale: band = normal (q1–q3), tick = median, dot = the value, dashed tick = a plan or limit. |
| `trendLine(points, { width, height = 34, tip = () => "" })` | A short line through a few averages (eight weeks, say) with an end dot; missing points are bridged; needs two. |
| `legendKey(kind)` | A legend key drawn the way its mark is drawn: "normal" (band), "median", "now" (dot), "plan" (dashed tick), "weeks" (trend). |
| `dayRing(ring, { size = 360, center = "", centerSub = "", cats = RING_CATS })` | A 24-hour clock, midnight at the top: sleep outside, workouts and (faint, as context) the calendar in the middle, screen minutes per hour inside. |
| `interval(row, domain, { width, height = 26, flip = false })` | A difference with its 95% interval against a zero line; right = a better next day (flip mirrors it). |
| `dayDots(series, { width, height = 30 })` | One circle per day: filled = done, hollow = 0, dashed = no record; the day of the month under each. |
| `timeChart(layers, { width, height = 240, first, last, unit = "", fmt = (v) => String(v), yPad = 0.15, maxGap = 7 })` | A date axis with a shaded corridor, faint daily points, a line that breaks after maxGap days and dashed reference lines. |
| `scoreDots(points, { width, height = 170, first, last, lo = 0, hi = 10, band = null, refs = [], fmt = (v) => String(v) })` | One dot per scored day on a fixed scale, a shaded band for the usual middle and dashed reference lines; each dot has its own tooltip. |
| `stackedColumns(columns, groups, { width, height = 200, limit = null, limitLabel = "", maxValue = null, labelEvery = 1, unitFmt = formatDuration, minutes = true })` | Columns of stacked categories on one scale (minutes tick on round hours), with an optional dashed limit named in a key under the axis; × = no record. |
| `blockColumns(columns, { width, height = 210, minTop = 60, label = "", maxChars = 12 })` | Columns of stacked blocks, one per item (block height = its value), a total above each column and two label lines under it. |
| `sleepWindows(nights, { width, target = null, rowH = 18 })` | One bar per night on a 20:00–14:00 axis, the alarm as an ink tick over it, an optional dashed target window. |
| `ladderChart(ladder, { width, height = 200, final })` | The alarm as a step line (earlier = higher) with wake dots, green on time and red late, and the goal dashed. |
| `coverage(marks, first, { width, height = 16 })` | One cell per day from first: "1" = has data, "p" = partial, anything else = nothing. |
| `lanes(rows, cols, { width, rowH = 46, gap = 10, labelW = 150, labelEvery = 1, unitFmt = formatDuration, showMax = true })` | One row per activity with columns over hours or days, each row on its own scale; × = no record, dashed = a limit, stripes = a hatch part, a flag = a word under a column. |
| `mealTimeline(days, { width, gapH = 3, rowH = 24 })` | One row per day on a 05:00–03:00 axis: awake from waking to falling asleep (sleep in violet at both ends), meals as dots sized by energy, the gapH hours before sleep striped; a meal inside them is ringed and its tooltip says how long before sleep it was. A day with status "none" is written as not logged; "partial" draws its meals faint. |
| `keptDots(days, { width, height = 20 })` | A run of days as dots, a small gap after every 7th: filled = the goal was kept, a ring = not kept, a short dash = no record that day. |

| helper | does |
|---|---|
| `esc(s)` (js/charts.js) | Escapes text for HTML and SVG attributes and content. |
| `CHART_WORDS` (js/charts.js) | The words the charts write, with their English defaults; an app's own t() gets the same keys. |
| `setFormat(fns)` (js/charts.js) | Hands the kit an app's words and formats: any of t, dur, clock, shortDay, measure, toDate, wtype; a word t() lacks falls back to CHART_WORDS. |
| `formatDuration(minutes)` (js/charts.js) | Minutes written as a duration by the dur() handed to setFormat() ("7h 54m" by default); stackedColumns and lanes write their values with it. |
| `toneColor(tone)` (js/charts.js) | The colour of a mark for a tone: "good" = --good, "bad" = --off, anything else = the neutral --c-mark. |
| `draw(el, fn)` (js/charts.js) | Draws fn(width) into el at its real pixel width and again whenever the box is resized. |
| `installTooltip()` (js/charts.js) | Adds the page's one tooltip (.tip): any element with data-tip shows it on hover and on keyboard focus. |
| `niceStep(span, count = 4)` (js/charts.js) | A round axis step (1, 2, 2.5 or 5 times a power of ten) that splits span into about count parts. |
| `RING_CATS` (js/charts.js) | The screen groups of the ring, inside out: [key, the categories it adds up, colour]. |
| `ICON_KEYS` (js/icons.js) | The names icon() knows, in drawing order. |
| `icon(key, size = 20)` (js/icons.js) | The icon for key at size px (an unknown key draws the dashed clock of "not recorded"). |
| `COLOR` (js/icons.js) | The colour each icon is drawn in: its data colour (ai, the AI assistant: focus blue), ink-3 for not recorded, ink-2 for the check, food (no data colour of its own) and the two devices-at-once measures; the menu glyphs take the text colour. |
| `STATE_ICON` (js/icons.js) | The 12px glyphs inside a state chip: good = a tick, bad = an exclamation mark. |

### Using the kit in another app

1. **Copy it.** `python3 -m healthaio kit export path/to/app/static/kit` writes `css/tokens.css`, `css/kit.css`,
   `js/charts.js`, `js/icons.js` and `kit.json` there. It stops, unless you pass `--force`, rather than overwrite a
   file of the same name that no export put there, or a `kit.json` it did not write.
2. **Load it first.** Link `kit/css/tokens.css`, then `kit/css/kit.css`, then your own stylesheets. Import the
   charts as ES modules (`import { draw, spark, setFormat } from "./kit/js/charts.js"`). A classic script (no
   `type="module"`) cannot use `await` at its top level: it loads the charts with
   `import("/kit/js/charts.js").then((kit) => { kit.setFormat({ … }); … })`, or with
   `const kit = await import("/kit/js/charts.js")` inside an async function. The URL is wherever your app serves
   the folder: an app that serves `static/` at `/` finds `static/kit` at `/kit/`.
3. **Give the charts your words.** Call `setFormat({ t, dur, clock, shortDay, measure, toDate, wtype })` once, with
   any of them. `CHART_WORDS` lists the keys the charts ask `t()` for, with their English defaults; a key your `t()`
   does not know (it answers with the key itself, or with nothing) is written with that English default.
4. **Keep your own things in your own files, and never edit a kit file in place.** If your app has its own token
   names, map them onto the kit's in a small bridge file with `var()` only (`--label: var(--ink)`), never with
   copied values, so a kit update reaches every page. kit.css styles `body`, links and generic classes (`.card`,
   `.chip`, `.tile`, `.grid`, `.row`, `.muted` …); if your app already uses those names for something else, load
   tokens.css and the scripts first and bring the components over one at a time.
5. **Check after each Health AIO update.** `python3 -m healthaio kit check path/to/app/static/kit` prints each file as
   *up to date*, *outdated* (the kit changed since the export), *modified locally* (the file differs from the hash
   recorded at export) or *missing*, and exits 0 only when every file is up to date.
6. **Port local improvements back.** A file that is *modified locally* holds a change worth keeping or losing. Make
   it in Health AIO (where the gallery shows it), bump `KIT_VERSION` and export again. `export` refuses to overwrite a
   modified copy unless you pass `--force`. A file an earlier export wrote that the kit no longer has is removed when
   it is untouched; when it was changed, `export --force` leaves it in place and `kit check` lists it until it is
   gone.

### Versioning

`KIT_VERSION` in `healthaio/kit.py` is a semantic version. Bump it on every change to any of the four kit files: the
patch number for a value or drawing fix, the minor number for a new token, class, function or option, the major
number for a rename or removal (an app that uses the old name breaks). The manifest carries the version and every
file's hash, so `kit check` can tell a stale copy from an edited one.

`healthaio/kit.lock.json` records the hashes of the current version's files, and `tests/test_kit.py` fails when a kit
file changes while `KIT_VERSION` stays the same. So a change goes: edit the file, bump `KIT_VERSION`, add a row to
the table below (in both halves of this file), then run `python3 -m healthaio kit lock`, which refuses to record
changed files under a version that is not newer.

| version | date | change |
|---|---|---|
| 1.9.0 | 2026-10-19 | Soreness `--c-sore-1..3` becomes one yellow getting stronger (the Recovery page's illustrated body used its own yellows; now every body figure, gauge and strip shares the kit's); new token `--c-estimate` for the outer ring that shows how far ahead an estimate reaches |
| 1.8.0 | 2026-10-14 | `scoreDots`: one dot per scored day on a fixed scale with the usual band and reference lines (Recovery's morning-after scores); `lanes` columns take `flag`, a word under the column in `--watch-ink` (the week to plan lighter, the heaviest week ahead) |
| 1.7.1 | 2026-10-14 | `--plate`, `--plate-ink` and `--c-sore-0` get dark-mode values: the body figure is now line art painted in `--plate-ink`, so it sits on a dark plate in dark mode instead of a white one |
| 1.7.0 | 2026-10-14 | Tokens `--c-sore-0` to `--c-sore-3` (soreness, one hue getting stronger, the same in both modes) and `--plate`, `--plate-ink` (the body figure's white plate), for the Recovery page |
| 1.6.0 | 2026-10-14 | Icons `watch`, `phone`, `laptop` and `tray`: the devices data comes from, on the Data sources page; `ai` now stands for an AI assistant (AI work left the app) |
| 1.5.0 | 2026-10-13 | `.side`: a menu item with pages opens and closes its list with a click: it ends in a `.side-caret` (turned down while open) and carries `aria-expanded`, and its `.side-sub` links are `[hidden]` while it is closed; the item stays highlighted while its list is closed. On the icon rail and the phone's tab bar the caret and the list stay hidden; icon `info` (the Overview page under the menu) |
| 1.4.1 | 2026-10-13 | `dayRing` draws calendar blocks faint (classes at 30%, other blocks at 18%): the calendar is context for the day, workouts on the same track stay in full |
| 1.4.0 | 2026-10-13 | For the health pages (Exercise, Food, Goals): tokens `--c-exercise-2` and `--c-exercise-3`, lighter steps of exercise that tell kinds of training apart by lightness (cardio, walking), never by a new hue; `mealTimeline` (meals by time of day, with the hours before sleep striped) and `keptDots` (days a goal was kept); icons `food` (ink-2: food has no data colour), `target` and `walk` (the Plan and Behaviour menu items); the comments name the kit Health AIO |
| 1.3.0 | 2026-10-13 | `lanes` rows take `fmt` (a row's values in its own unit, such as a count of instructions); `.legend .key i.hatch` takes its stripes from `color` (ink unless set), so a hatch part in another colour has a matching key; icon `ai` (focus blue: AI agents working for you, the AI work page). AI work is drawn as focus blue stripes rather than a new data colour: the five data hues leave no step that passes the colour-vision checks against all of them |
| 1.2.0 | 2026-10-13 | `.side`: the menu as a left sidebar from 900px that folds to a 64px icon rail (`html.side-folded`) and a bottom tab bar below that (`.top` and `.nav` stay for apps with a top bar); with a sidebar open, `.subnav` hides (its pages are listed in the sidebar); `lanes` parts take `{ hatch: true }` (diagonal stripes of the part's colour, keyed by `.legend .key i.hatch`) and a row's stacked parts never run past its top; icons `ratio` and `single` (the Time page's devices at once) and the menu glyphs `sun`, `heart`, `clock`, `battery`, `list`, `database`, `sidebar` |
| 1.1.0 | 2026-10-13 | `formatDuration` (the default `unitFmt` of `stackedColumns` and `lanes`) and `stackedColumns`' `minutes` option (minutes tick on round hours: 0 / 2h / 4h, not 3h 20m); `dayRing` defaults to the exported `RING_CATS`; `setFormat()` keeps the English default for a word the app's `t()` lacks; `stackedColumns` names its limit in a key under the axis instead of over the columns; the labels of `timeChart`'s reference lines and `ladderChart`'s goal go over the marks with a halo; `blockColumns`, `stackedColumns` and `ladderChart` leave out labels evenly when neighbours would run into each other, and keep the first and last inside the chart; `sleepWindows` puts its hour labels 2, 4 or 6 hours apart, whichever leaves room; `.stepper` pills never break inside (the row wraps); kit.css spacing written with the space tokens (no pixel changes) |
| 1.0.0 | 2026-10-13 | First kit: tokens.css (with `--halo` and `--on-watch` added), kit.css split out of app.css, charts.js without the i18n.js import (`setFormat()`), `rangeStrip`, `trendLine`, `legendKey` and `blockColumns` moved in from the Drain and Week pages, `toneColor`, `STATE_ICON` and `ICON_KEYS` |

---

## 中文

### 它是什么，不是什么

Health AIO 身兼两职：它是一个本地优先看板的公开展示，也是一套外观的源头，也就是这个设计套件。别的应用（比如作者的私人系统）拷走这套文件，页面和功能各管各的。设计只朝一个方向流：从 Health AIO 流到各个拷贝。功能反过来流，只限通用、能用演示数据展示的那些。

套件**包括**：两种模式的变量、基础样式、外框（页头、菜单、页面栏）、组件、SVG 图表和辅助函数、线条图标。都是普通 CSS 和 ES 模块，不用构建。

套件**不包括**：Health AIO 各页自己的布局（留在 `healthaio/web/css/app.css`）、任何算数据的代码、页面上的文字（应用用 `setFormat()` 把自己的文字交给图表），也没有主题切换：每种模式只有一套样子。

展示页（`#kit`，不在菜单里；每一页底部都有链接）摆出每个变量的浅色值和深色值（不管现在是哪种模式）、每个组件的各种状态，并用编造的示例数据把每张图现场画出来，旁边写函数签名和一句说明。本地打开 <http://localhost:8790/#kit>。

### 文件

| 文件 | 作用 | 里面是什么 |
|---|---|---|
| `css/tokens.css` | 变量 | 所有自定义属性：浅色值写在 `:root` 上，深色值写两遍（跟随系统、月亮按钮各一遍），由测试保证两遍一样 |
| `css/kit.css` | 组件 | 基础样式、外框和组件；所有颜色、所有间距档都用变量（少数小尺寸还是直接写的数），不提任何 Health AIO 页面 |
| `js/charts.js` | 图表 | SVG 图表和辅助函数；不导入任何文件 |
| `js/icons.js` | 图标 | 线条图标、它们的颜色、状态标签里的小图 |
| `kit.json` | 清单 | 只在 `export` 的目标目录里，`healthaio/web/` 下没有：版本、每个文件的 SHA-256 和大小、变量、组件、图表 |

四个套件文件的路径都相对 `healthaio/web/`。清单按磁盘上的文件现算（`healthaio/kit.py`）：`python3 -m healthaio kit json` 打出来，服务在 `/api/kit` 返回它，`build-static` 给演示站写成 `api/kit.json`。它读文件里的三条约定：

- tokens.css：每组变量前一行注释 `/* [作用] … */`（type、space、radius、motion、neutral、accent、effect、data、status）；
- kit.css：每组规则前一行注释 `/* @component <类名> <一句话> */`；
- charts.js 和 icons.js：每个 `export` 正上方那一行 `//` 注释就是它的说明。

### 变量

字体：`--font`（系统字体，中文用苹方和 Noto Sans SC）、`--mono`，字号 `--t-xs` 12px, `--t-sm` 13px, `--t-md` 15px, `--t-lg` 18px, `--t-xl` 24px, `--t-2xl` 34px, `--t-3xl` 44px。间距：`--s-1` 4px, `--s-2` 8px, `--s-3` 12px, `--s-4` 16px, `--s-5` 20px, `--s-6` 28px, `--s-7` 40px, `--s-8` 56px。圆角：`--r-sm` 8px, `--r-md` 12px, `--r-lg` 18px, `--r-pill` 999px。动效：`--ease` cubic-bezier(.2, .7, .2, 1)。阴影：`--shadow`（卡片）和 `--seg-on-edge`（开关里选中的那一格）。

颜色，浅色和深色（“同左” = 两种模式同一个值）：

| 变量 | 浅色 | 深色 | 用在 |
|---|---|---|---|
| `--bg` | `#f4f4f3` | `#0b0d13` | 页面底色 |
| `--surface` | `#ffffff` | `#141822` | 卡片 |
| `--surface-2` | `#f7f7f6` | `#1a1f2b` | 指标块、标签、嵌在里面的部分 |
| `--ink` | `#161616` | `#eceef5` | 文字；菜单里当前页那个反色胶囊 |
| `--ink-2` | `#4a4a48` | `#b4bbcc` | 次要文字、图上的标签 |
| `--ink-3` | `#6a6a67` | `#8c95a8` | 淡色文字、坐标轴文字 |
| `--line` | `#e4e4e1` | `#232937` | 行间细线、卡片边 |
| `--line-2` | `#cfcfcb` | `#313849` | 按钮边框、虚线框、空轨道 |
| `--header` | `rgba(244, 244, 243, .84)` | `rgba(11, 13, 19, .8)` | 半透明的顶栏 |
| `--seg-on` | `#ffffff` | `#353d50` | 开关里选中的那一格 |
| `--halo` | `var(--surface)` | 同左 | 图上标记外的一圈 |
| `--accent` | `#1f5fbf` | `#aea2f7` | 链接、聚焦框、“现在”指针、进度条 |
| `--accent-soft` | `rgba(31, 95, 191, .1)` | `rgba(174, 162, 247, .14)` | 强调标签、体重走廊 |
| `--on-accent` | `#ffffff` | `#14102e` | 实心强调色上的文字（备用） |
| `--c-focus` | `#2a78d6` | `#3987e5` | 专注：工作和学习（屏幕时间） |
| `--c-fun` | `#eb6834` | `#d95926` | 娱乐和社交 |
| `--c-comms` | `#1baf7a` | `#199e70` | 沟通 |
| `--c-other` | `#a3a9b5` | `#5d6474` | 其他屏幕时间 |
| `--c-sleep` | `#4a3aa7` | `#9085e9` | 睡眠：有自己的一圈、一条泳道和一张图 |
| `--c-exercise` | `#bf3fa6` | `#cb4db2` | 记录下来的训练 |
| `--c-exercise-ink` | `#a8318f` | `#de78c8` | 写成文字的训练分钟 |
| `--c-exercise-2` | `#da90cb` | `#86397b` | 一种训练，浅一档：有氧（运动页） |
| `--c-exercise-3` | `#e7b6dd` | `#5d2d5c` | 一种训练，最浅：步行和其他训练 |
| `--c-event` | `#161616` | `#eceef5` | 日程块（墨色，不用彩色） |
| `--c-band` | `rgba(22, 22, 22, .075)` | `rgba(236, 238, 245, .085)` | “你的平常”色带和空轨道 |
| `--c-grid` | `rgba(22, 22, 22, .07)` | `rgba(236, 238, 245, .07)` | 网格线 |
| `--c-axis` | `rgba(22, 22, 22, .22)` | `rgba(236, 238, 245, .22)` | 坐标轴和基线 |
| `--c-mark` | `#161616` | `#eceef5` | 中性标记：这一周、平均线、截止 |
| `--c-sore-0` | `#e5e5ea` | `#3a4152` | 人体图上不酸的部位 |
| `--c-sore-1` | `#f8dd8b` | 同左 | 酸痛：有点酸（恢复页的人体图、仪表和小格） |
| `--c-sore-2` | `#eeb947` | 同左 | 酸痛：明显酸 |
| `--c-sore-3` | `#d99519` | 同左 | 酸痛：很酸；也是酸痛仪表的弧 |
| `--c-estimate` | `#b4a0ed` | 同左 | 预估能看多远：恢复页酸痛、精力仪表的外圈 |
| `--plate` | `#ffffff` | `#1c2130` | 人体图的底板 |
| `--plate-ink` | `#3a3a3c` | `#c3c9d6` | 人体图的线条和底板上的文字 |
| `--good` | `#0ca30c` | 同左 | 图上“好”的标记 |
| `--good-ink` | `#1d7a1d` | `#4cc94c` | “好”的文字 |
| `--good-soft` | `rgba(12, 163, 12, .11)` | `rgba(12, 163, 12, .18)` | “好”的标签底色 |
| `--watch` | `#fab219` | 同左 | 图上“留意”的标记 |
| `--watch-ink` | `#8a5a00` | `#f5bd4a` | “留意”的文字 |
| `--watch-soft` | `rgba(250, 178, 25, .16)` | `rgba(250, 178, 25, .14)` | “留意”的标签底色 |
| `--on-watch` | `#161616` | `#0b0d13` | 写在“留意”色块上的字 |
| `--off` | `#d03b3b` | 同左 | 图上“偏了”的标记 |
| `--off-ink` | `#b42828` | `#f27c7c` | “偏了”的文字（.bad） |
| `--off-soft` | `rgba(208, 59, 59, .1)` | `rgba(208, 59, 59, .2)` | “偏了”的标签底色 |

### 颜色规则

- **数据颜色跟着被测的东西走。** 专注（工作和学习）永远是蓝，娱乐和社交是橙，沟通是青绿，其他屏幕时间是灰，睡眠是紫，记录下来的训练是品红；日程块用墨色。每种颜色两种模式色相不变，各有一档深浅。数据颜色不表示状态，状态色也不表示被测的东西：“值得看一眼”用 `--watch`，不用 `--c-fun`。
- **色弱检查。** 专注、娱乐、沟通两两之间在两种模式下都通过（最差 CVD ΔE 9.2）。睡眠在红色盲下和专注太像，所以从不挨着放：它有自己的一圈、一条泳道和一张图。运动可以挨着睡眠（最差 ΔE 8.4）。
- **状态色只表示状态，而且总配文字或图标。** 好、留意、偏了各有一个填充色（图上的标记）、一个字色（文字）和一个浅底（标签底色）。填充色两种模式故意一样，字色和浅底各有一档。写在“留意”色块上的字用 `--on-watch`。类名是 `.good`、`.watch`、`.bad`（`.bad` 用 off 那组颜色）。
- **每种模式一套样子。** 浅色是石墨中性色加蓝色强调，深色是暮蓝中性色加紫色强调。默认跟随系统；`<html>` 上的 `data-mode="light"` 或 `"dark"` 可以改。
- **其余的图只用墨色和灰色。** “你的平常”是一条淡色带（`--c-band`），虚线表示计划或上限，× 表示那天没有记录，斜纹表示叠在其余部分上面多出来的东西（`lanes` 的 hatch 部分，比如第二台设备比钟表多出来的分钟）；压在别的东西上的标记有一圈 `--halo`，颜色和它背后的底一样（卡片上是 `--surface`，`.tile` 里改成 `--surface-2`）。

### 组件和图表

下面每一项在展示页上都有。组件（kit.css）：`.sr`, `.top`, `.brand`, `.nav`, `.side`, `.tool`, `.demo-badge`, `.head`, `.stepper`, `.grid`, `.col`, `.card`, `.lede`, `.stack`, `.eyebrow`, `.hero-num`, `.chip`, `.dot`, `.legend`, `.ring`, `.agenda`, `.tonight`, `.tiles`, `.seg`, `.subnav`, `.how`, `.empty`, `.foot`, `.tip`, `.catbar`, `.hbar`, `.progress`, `.mark`, `.facts`, `table`, `.code`, `.chart`, `.ph`。

| 函数 | 画什么 |
|---|---|
| `spark(series, band, { width, height = 46, unit = "", tone = "neutral" })` | 14 天的折线画在“你的平常”色带上；× 表示那天没有记录，末端圆点带倾向颜色。 |
| `bullet(value, band, { width, unit = "", tone = "neutral", height = 18 })` | 一个值和它的平常范围画在一条线上：色带 = 平常，竖线 = 中间值，圆点 = 这个值（带倾向颜色）。 |
| `rangeStrip(row, { width, height = 30, pad = 10 })` | 一个值画在它自己的刻度上：色带 = 平常（q1–q3），竖线 = 中间值，圆点 = 这个值，虚线竖线 = 计划或上限。 |
| `trendLine(points, { width, height = 34, tip = () => "" })` | 穿过几个平均值（比如八周）的短线，末端一个圆点；缺的点直接连过去；至少要两个点。 |
| `legendKey(kind)` | 和标记画法一样的图例："normal"（色带）、"median"、"now"（圆点）、"plan"（虚线竖线）、"weeks"（走势）。 |
| `dayRing(ring, { size = 360, center = "", centerSub = "", cats = RING_CATS })` | 24 小时的钟，午夜在最上面：外圈睡眠，中圈训练和画得很淡的日程（日程只当背景），里圈每小时的屏幕分钟。 |
| `interval(row, domain, { width, height = 26, flip = false })` | 一个差值和它的 95% 区间，对着零线画；右边 = 第二天更好（flip 左右翻转）。 |
| `dayDots(series, { width, height = 30 })` | 一天一个圆：实心 = 做了，空心 = 0，虚线 = 没有记录；下面写几号。 |
| `timeChart(layers, { width, height = 240, first, last, unit = "", fmt = (v) => String(v), yPad = 0.15, maxGap = 7 })` | 日期轴：一条阴影走廊、淡淡的每日点、隔 maxGap 天以上就断开的线，加几条虚线参考线。 |
| `scoreDots(points, { width, height = 170, first, last, lo = 0, hi = 10, band = null, refs = [], fmt = (v) => String(v) })` | 固定刻度上，有分的日子各一个点，一条阴影带标出平常的中间段，加几条虚线参考线；每个点有自己的提示。 |
| `stackedColumns(columns, groups, { width, height = 200, limit = null, limitLabel = "", maxValue = null, labelEvery = 1, unitFmt = formatDuration, minutes = true })` | 同一刻度上的堆叠柱（分钟按整点的小时标刻度），可加一条虚线上限，名字写在坐标轴下面的图例里；× = 那一列没有记录。 |
| `blockColumns(columns, { width, height = 210, minTop = 60, label = "", maxChars = 12 })` | 一列一列叠起来的块，一项一块（块高 = 它的值），每列上面写合计、下面两行标签。 |
| `sleepWindows(nights, { width, target = null, rowH = 18 })` | 20:00–14:00 的轴上一晚一根条，闹钟是压在条上的一道墨色竖线，可加虚线目标框。 |
| `ladderChart(ladder, { width, height = 200, final })` | 闹钟画成台阶线（越早越高），醒来的点按时为绿、晚了为红，目标是虚线。 |
| `coverage(marks, first, { width, height = 16 })` | 从 first 起一天一格："1" = 有数据，"p" = 不全，其他 = 没有。 |
| `lanes(rows, cols, { width, rowH = 46, gap = 10, labelW = 150, labelEvery = 1, unitFmt = formatDuration, showMax = true })` | 一种活动一行，列是小时或日子，每行有自己的刻度；× = 没有记录，虚线 = 上限，斜纹 = hatch 部分，flag = 列下面的一个词。 |
| `mealTimeline(days, { width, gapH = 3, rowH = 24 })` | 一天一行，横轴 05:00 到次日 03:00：从醒来到睡着是醒着的底色（两头的睡眠画成紫色），每一餐是一个点、大小按热量，睡前 gapH 小时画斜纹；落在斜纹里的一餐加一圈，提示里写离睡着多久。状态 none 的一天写“没记”，partial 的一天把餐点画淡。 |
| `keptDots(days, { width, height = 20 })` | 一串日子画成一排点，每 7 天留一点空：实心 = 做到了，空心圈 = 没做到，短横 = 那天没有记录。 |

| 辅助 | 做什么 |
|---|---|
| `esc(s)` (js/charts.js) | 把文字转义后放进 HTML 和 SVG 的属性和内容。 |
| `CHART_WORDS` (js/charts.js) | 图表会写的字和它们的英文默认值；应用自己的 t() 收到的是同样的键。 |
| `setFormat(fns)` (js/charts.js) | 把应用自己的文字和格式交给套件：t、dur、clock、shortDay、measure、toDate、wtype 任选；t() 不认得的词退回 CHART_WORDS 里的英文。 |
| `formatDuration(minutes)` (js/charts.js) | 用交给 setFormat() 的 dur() 把分钟写成时长（默认写成“7h 54m”）；stackedColumns 和 lanes 用它写数值。 |
| `toneColor(tone)` (js/charts.js) | 某个倾向对应的标记颜色："good" = --good，"bad" = --off，其他 = 中性的 --c-mark。 |
| `draw(el, fn)` (js/charts.js) | 按 el 的实际像素宽度画 fn(width)，盒子大小一变就重画。 |
| `installTooltip()` (js/charts.js) | 给页面加唯一的提示框（.tip）：带 data-tip 的元素在悬停和键盘聚焦时显示它。 |
| `niceStep(span, count = 4)` (js/charts.js) | 把一段跨度分成大约 count 份的整齐刻度（10 的幂乘 1、2、2.5 或 5）。 |
| `RING_CATS` (js/charts.js) | 环上屏幕时间的分组，从里往外：[键、合并的类别、颜色]。 |
| `ICON_KEYS` (js/icons.js) | icon() 认得的名字，按画的顺序。 |
| `icon(key, size = 20)` (js/icons.js) | 画 size 像素大小的 key 图标（不认得的 key 画“没有记录”的虚线钟）。 |
| `COLOR` (js/icons.js) | 每个图标的颜色：它的数据颜色（ai 用专注蓝：替你做的事），“没有记录”用 ink-3，勾、饮食（没有自己的数据颜色）和“几台同时用”的两项用 ink-2；菜单图标跟文字颜色。 |
| `STATE_ICON` (js/icons.js) | 状态标签里的 12 像素小图：good = 勾，bad = 感叹号。 |

### 用到别的应用里

1. **拷过去。** `python3 -m healthaio kit export path/to/app/static/kit` 在那里写出 `css/tokens.css`、`css/kit.css`、`js/charts.js`、`js/icons.js` 和 `kit.json`。如果那里已经有同名、却不是导出写的文件，或者有一个不是导出写的 `kit.json`，它会停下来，不覆盖，除非加 `--force`。
2. **先加载套件。** 依次引用 `kit/css/tokens.css`、`kit/css/kit.css`，再引用你自己的样式。图表按 ES 模块导入（`import { draw, spark, setFormat } from "./kit/js/charts.js"`）。普通脚本（没有 `type="module"`）的最外层不能写 `await`：用 `import("/kit/js/charts.js").then((kit) => { kit.setFormat({ … }); … })`，或者在 async 函数里写 `const kit = await import("/kit/js/charts.js")`。网址取决于你的应用把这个目录放在哪：应用把 `static/` 放在 `/` 下，`static/kit` 就在 `/kit/`。
3. **把你的文字交给图表。** 调用一次 `setFormat({ t, dur, clock, shortDay, measure, toDate, wtype })`，给哪几个都行。`CHART_WORDS` 列出图表会向 `t()` 要的键和英文默认值；你的 `t()` 不认得的键（返回键本身，或者什么都不返回），图表照写英文默认值。
4. **自己的东西放在自己的文件里，套件文件一个字都不改。** 应用有自己的一套变量名，就在一个小的转接文件里用 `var()` 映射到套件的名字（`--label: var(--ink)`），不要抄数值，这样套件一更新每一页都跟着变。kit.css 会给 `body`、链接和一些通用类名（`.card`、`.chip`、`.tile`、`.grid`、`.row`、`.muted` 等）上样式；如果你的应用已经拿这些名字做别的事，先只加载 tokens.css 和两个脚本，组件一个一个搬。
5. **Health AIO 每次更新后检查一遍。** `python3 -m healthaio kit check path/to/app/static/kit` 给每个文件标上 *up to date*（最新）、*outdated*（导出后套件改过）、*modified locally*（和导出时记下的哈希不一样，本地改过）或 *missing*（缺失），全部最新时才返回 0。
6. **把本地的改进搬回 Health AIO。** 标着“本地改过”的文件里有一处改动，要么值得留下、要么该丢掉。要留就在 Health AIO 里改（展示页上能看到效果），升 `KIT_VERSION`，再导出。拷贝被本地改过时，`export` 拒绝覆盖，除非加 `--force`。以前导出过、现在套件里已经没有的文件，没动过就删掉；改过的话，`export --force` 把它留在原处，`kit check` 一直列着它，直到它被删掉。

### 版本

`healthaio/kit.py` 里的 `KIT_VERSION` 是语义化版本。四个套件文件里任何一个改了都要升：数值或画法的修正升第三位，新增变量、类、函数或选项升第二位，改名或删除升第一位（用旧名字的应用会坏）。清单里记着版本和每个文件的哈希，所以 `kit check` 分得清一份拷贝是过期了还是被改过。

`healthaio/kit.lock.json` 记着当前版本那四个文件的哈希；套件文件改了而 `KIT_VERSION` 没变，`tests/test_kit.py` 就不通过。所以改一处的顺序是：改文件，升 `KIT_VERSION`，在下面的表里加一行（本文件中英两半都加），再跑 `python3 -m healthaio kit lock`；版本没有变新时，它拒绝把改过的文件记下来。

| 版本 | 日期 | 改了什么 |
|---|---|---|
| 1.9.0 | 2026-10-19 | 酸痛 `--c-sore-1..3` 改成同一种黄色由浅到深（恢复页的人体插画原来用自己的一套黄色，现在所有人体图、仪表和小格都用套件里的这一套）；新增 `--c-estimate`，仪表外圈表示预估能看多远 |
| 1.8.0 | 2026-10-14 | 新增 `scoreDots`：固定刻度上，有分的日子各一个点，带平常的阴影带和参考线（恢复页的练后第二天分）；`lanes` 的列可以带 `flag`，用 `--watch-ink` 写在这一列下面的一个词（该减量的周、接下来最重的一周） |
| 1.7.1 | 2026-10-14 | `--plate`、`--plate-ink`、`--c-sore-0` 有了深色模式的值：人体图改成用 `--plate-ink` 画的线稿，深色模式下底板也是深色，不再是白的 |
| 1.7.0 | 2026-10-14 | 新变量 `--c-sore-0` 到 `--c-sore-3`（酸痛，同一色相由浅到深，深浅色下相同）和 `--plate`、`--plate-ink`（人体图的白色底板），给恢复页用 |
| 1.6.0 | 2026-10-14 | 新图标 `watch`、`phone`、`laptop`、`tray`：数据从哪台设备来（数据来源页用）；`ai` 现在指 AI 助手（AI 干活量已从应用里去掉） |
| 1.5.0 | 2026-10-13 | `.side`：有子页的菜单项点一下展开或收起子页：末尾一个 `.side-caret`（展开时转向下），带 `aria-expanded`，收起时它的 `.side-sub` 带 `[hidden]`；收起时高亮落在这一项本身。图标条和手机底部标签栏上不显示箭头和子页；新图标 `info`（菜单下面的项目说明页） |
| 1.4.1 | 2026-10-13 | `dayRing` 把日程画淡（课 30%、其他安排 18%）：日程只是一天的背景，同一圈上的训练照旧画满 |
| 1.4.0 | 2026-10-13 | 为健康页（运动、饮食、目标）新增：变量 `--c-exercise-2`、`--c-exercise-3`，运动洋红的两档浅色，按深浅区分训练种类（有氧、步行），不加新色相；`mealTimeline`（一天里什么时候吃，睡前几小时画斜纹）和 `keptDots`（目标哪几天做到了）；图标 `food`（用 ink-2：饮食没有自己的数据颜色）、`target` 和 `walk`（菜单的计划和行为）；注释里的名字改成 Health AIO |
| 1.3.0 | 2026-10-13 | `lanes` 的行可以带 `fmt`（这一行的值用自己的单位写，比如指令条数）；`.legend .key i.hatch` 的斜纹改用 `color`（默认墨色），别的颜色的 hatch 部分也有对得上的图例；新图标 `ai`（专注蓝：替你干活的 AI 代理，AI 干活量页）。AI 工时画成专注蓝斜纹，而不是新加一种数据颜色：现有五种数据色之外，已经找不到跟它们都能通过色盲校验的颜色 |
| 1.2.0 | 2026-10-13 | 新增 `.side`：900 像素以上是左侧栏，能收成 64 像素的图标条（`html.side-folded`），更窄时是底部标签栏（`.top` 和 `.nav` 留给用顶栏的应用）；有侧栏时 `.subnav` 隐藏（它的几页已经列在侧栏里）；`lanes` 的部分可以带 `{ hatch: true }`（用这部分的颜色画斜纹，图例是 `.legend .key i.hatch`），一行里叠起来的部分不再超出这一行的顶；新图标 `ratio`、`single`（时间页的“几台同时用”）和菜单图标 `sun`、`heart`、`clock`、`battery`、`list`、`database`、`sidebar` |
| 1.1.0 | 2026-10-13 | 新增 `formatDuration`（`stackedColumns` 和 `lanes` 的 `unitFmt` 默认用它）和 `stackedColumns` 的 `minutes` 选项（分钟按整点的小时标刻度：0 / 2h / 4h，不再是 3h 20m）；`dayRing` 默认用导出的 `RING_CATS`；应用的 `t()` 不认得的词，`setFormat()` 之后照写英文默认值；`stackedColumns` 的上限名字写在坐标轴下面的图例里，不再压在柱子上；`timeChart` 参考线和 `ladderChart` 目标的文字带一圈底色、压在标记上面；`blockColumns`、`stackedColumns` 和 `ladderChart` 相邻标签会撞在一起时均匀地省掉一些，头尾的标签不出图；`sleepWindows` 的整点标签按放得下的空间隔 2、4 或 6 小时；`.stepper` 的胶囊不在中间断行（整排换行）；kit.css 的间距改用间距变量（像素不变） |
| 1.0.0 | 2026-10-13 | 第一版：tokens.css（新增 `--halo` 和 `--on-watch`），从 app.css 拆出 kit.css，charts.js 不再导入 i18n.js（改用 `setFormat()`），把消耗页和本周页里的 `rangeStrip`、`trendLine`、`legendKey`、`blockColumns` 搬进来，新增 `toneColor`、`STATE_ICON`、`ICON_KEYS` |
