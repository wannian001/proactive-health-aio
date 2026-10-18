// Design kit gallery (#kit): every token, component, chart and icon of the kit, read from its manifest
// (/api/kit; api/kit.json on the static site) and drawn with made-up sample data. Not a menu item: the footer
// of every page and the Data page link here. Every manifest entry needs a sample below (tests/test_kit.py).
import { blockColumns, bullet, coverage, dayDots, dayRing, draw, esc, interval, keptDots, ladderChart, lanes, legendKey, mealTimeline,
  rangeStrip, RING_CATS, scoreDots, sleepWindows, spark, stackedColumns, timeChart, trendLine } from "../charts.js?v=93bad7f144";
import { dur, getLang, measure, num, shortDay, t } from "../i18n.js?v=93bad7f144";
import { COLOR, ICON_KEYS, icon, STATE_ICON } from "../icons.js?v=93bad7f144";

const DOCS = "https://github.com/wannian001/proactive-health-aio/blob/main/docs/DESIGN_KIT.md";
const SIZES = [13, 16, 28, 64];
// a doc comes from the code comment (English); in Chinese the gallery's own translation, kitdoc.<name>, when there is one
const docOf = (name, doc) => { if (getLang() !== "zh") return doc; const key = `kitdoc.${name}`; const zh = t(key); return zh === key ? doc : zh; };

// ---- made-up sample data (one person, the days up to 12 Oct 2026) ------------------------------------------
const pad = (n) => String(n).padStart(2, "0");
const iso = (k) => { const d = new Date(2026, 9, 12 - k); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };  // k days before
const DAY = iso(0);
const SLEEP14 = [412, 398, 430, null, 445, 401, 388, 420, 436, 410, 395, 452, 461, 474];
const SCREEN = [{ entertainment: 20 }, {}, {}, {}, {}, {}, {}, { communication: 8 }, { social: 12, communication: 6 }, { work: 35, communication: 10 },
  { learning: 20 }, { work: 50 }, { social: 25, communication: 15 }, { work: 40 }, { work: 30, other: 10 }, { learning: 45 },
  { work: 25, social: 10 }, { communication: 15 }, { entertainment: 30 }, {}, { entertainment: 45, social: 10 }, { entertainment: 50 },
  { social: 30, communication: 10 }, { entertainment: 25 }];
const SCREEN_PARTS = RING_CATS.map(([key, , color]) => [key, color]);
// stacked columns put entertainment on the baseline, so a day reads against the dashed limit (as a screen-time limit reads)
const FUN_FIRST = [SCREEN_PARTS[1], SCREEN_PARTS[0], ...SCREEN_PARTS.slice(2)];
const groupOf = (hour) => Object.fromEntries(RING_CATS.map(([key, keys]) => [key, keys.reduce((s, k) => s + (hour[k] || 0), 0)]));
const RING = {
  screen_hours: SCREEN,
  events: [{ start: `${DAY}T10:00`, end: `${DAY}T11:50`, title: "HCI 610", kind: "class" }, { start: `${DAY}T14:00`, end: `${DAY}T15:00`, title: "STAT 520", kind: "class" },
    { start: `${DAY}T19:00`, end: `${DAY}T20:00`, title: "—", kind: "personal" }],
  workouts: [{ start: `${DAY}T17:30`, end: `${DAY}T18:15`, type: "running" }],
  sleep: { start: `${iso(1)}T23:40`, end: `${DAY}T07:20` },
  now: `${DAY}T18:40`,
};
const weight = (k) => 78.6 - 0.045 * k + 0.35 * Math.sin(k * 1.7) + 0.25 * Math.sin(k * 0.6);  // k days after the first
const WEIGH = Array.from({ length: 70 }, (_, k) => k).filter((k) => k % 9 !== 4).map((k) => ({ date: iso(69 - k), value: Number(weight(k).toFixed(1)) }));
const AVG7 = WEIGH.map((p, i) => { const w = WEIGH.slice(Math.max(0, i - 6), i + 1); return { date: p.date, value: w.reduce((s, x) => s + x.value, 0) / w.length }; });
const CORRIDOR = Array.from({ length: 84 }, (_, k) => ({ date: iso(69 - k), low: 78.6 * (1 - 0.01 * k / 7), high: 78.6 * (1 - 0.005 * k / 7) }));
const FUN = [95, 120, 80, 150, 210, 60, 110, 100, 130, 90, 175, 140, 85, 120];
const days14 = () => FUN.map((fun, i) => ({ label: shortDay(iso(13 - i)), shade: i >= 7,
  values: i === 4 ? null : { fun, focus: 140 + ((i * 37) % 90), communication: 30 + ((i * 13) % 25), other: 15 + ((i * 7) % 20) } }));
const NIGHTS = [[6, "23:50", "07:35", "07:45"], [5, "00:20", "07:50", "07:45"], [4], [3, "23:30", "07:25", "07:30"], [2, "01:05", "08:40", "07:30"],
  [1, "23:45", "07:20", "07:30"], [0, "23:40", "07:20", "07:15"]].map(([k, a, b, alarm]) => {
  if (!a) return { date: iso(k) };
  const start = `${a >= "12:00" ? iso(k + 1) : iso(k)}T${a}`, end = `${iso(k)}T${b}`;
  return { date: iso(k), start, end, alarm, sleep_min: (new Date(end) - new Date(start)) / 60000 };
});
const mins = (hhmm) => Number(hhmm.slice(0, 2)) * 60 + Number(hhmm.slice(3));
const LADDER = [["08:30", "08:28"], ["08:15", "08:35"], ["08:15", "08:12"], ["08:00", "07:58"], ["07:45", "08:05"], ["07:45", "07:44"],
  ["07:30", null], ["07:30", "07:29"], ["07:15", "07:16"], ["07:00", "07:02"]].map(([alarm, woke], i) => ({
  date: iso(9 - i), alarm, woke: woke ? `${iso(9 - i)}T${woke}` : null, on_time: woke ? mins(woke) <= mins(alarm) + 2 : null }));
const LOAD = [
  { n: 0, total: 50, blocks: [["HCI 610", 15, "watch"], ["SWEN 530", 5, "done"], ["INFO 540", 30, "mark"]] },
  { n: 1, total: 10, blocks: [["HCI 610", 0, "none"], ["SWEN 530", 10, "mark"]] },
  { n: 2, total: 20, blocks: [["STAT 520", 20, "done"]] },
  { n: 3, total: 40, blocks: [["HCI 610", 40, "mark"]] },
  { n: 4, total: 100, blocks: [["STAT 520", 50, "mark"], ["SWEN 530", 50, "mark"]] },
  { n: 5, total: 40, blocks: [["INFO 540", 40, "mark"]] },
];
const TONES = [["good", 63, { q1: 48, median: 52, q3: 56 }], ["bad", 66, { q1: 55, median: 57, q3: 59 }], ["neutral", 57, { q1: 55, median: 57.5, q3: 60 }]];
const STRIPS = [{ value: 64, band: { q1: 58, median: 60, q3: 62 }, plan: null, tone: "bad", key: "kit.tone.bad" },
  { value: 145, band: { q1: 90, median: 110, q3: 130 }, plan: { limit: 120 }, tone: "bad", key: "kit.tone.plan" },
  { value: 41, band: { q1: 38, median: 44, q3: 50 }, plan: null, tone: "neutral", key: "kit.tone.neutral" },
  { value: 24, band: { q1: 30, median: 38, q3: 45 }, plan: { limit: 60 }, tone: "good", key: "kit.tone.good" }];
const INTERVALS = [{ status: "ok", diff: 1.8, low: 0.5, high: 3.1, detected: true, key: "kit.iv.good" },
  { status: "ok", diff: 0.6, low: -1.2, high: 2.4, detected: false, key: "kit.iv.none" },
  { status: "ok", diff: -2.2, low: -3.5, high: -0.9, detected: true, key: "kit.iv.bad" },
  { status: "few", key: "eff.too_few" }];
const WEEKS8 = [44, 46, null, 45, 48, 47, 50, 52].map((value, i) => ({ value, to: iso(7 * (7 - i)) }));
const COVER = [["data.s.sleep", "111111111p11111101111111p11111"], ["data.s.screen", "1111110000011111111111111p1111"]];
// five days of meals: a late snack inside the striped hours, a day not logged, a day logged in part, today so far
const meal = (k, hhmm, title, kcal) => ({ time: `${iso(k)}T${hhmm}`, title, kcal });
const MEALS = [
  { date: iso(4), status: "full", wake: `${iso(4)}T08:05`, asleep: `${iso(3)}T00:10`, meals: [meal(4, "08:40", "Oats", 360), meal(4, "12:50", "Rice bowl", 650), meal(4, "19:05", "Curry", 720)] },
  { date: iso(3), status: "full", wake: `${iso(3)}T08:30`, asleep: `${iso(2)}T00:50`, meals: [meal(3, "12:30", "Pho", 520), meal(3, "18:50", "Pasta", 830), meal(3, "23:25", "Noodles", 420)] },
  { date: iso(2), status: "none" },
  { date: iso(1), status: "partial", wake: `${iso(1)}T09:10`, asleep: `${iso(0)}T00:05`, meals: [meal(1, "13:15", "Sushi", 540)] },
  { date: iso(0), status: "today", wake: `${DAY}T07:20`, asleep: null, meals: [meal(0, "07:50", "Toast and eggs", 430), meal(0, "12:40", "Burrito", 760)] },
];
const KEPT = [[8, "1101111011110x1111011111011x"], [3, "0011010x01100101x01101000110"]].map(([h, marks], r) => ({
  label: r === 0 ? ["goals.slept", { h }] : ["goals.last_meal", { h }],
  days: [...marks].map((c, i) => ({ date: iso(27 - i), met: c === "x" ? null : c === "1" })) }));

// ---- charts: each one drawn into a .chart box --------------------------------------------------------------
const box = (id, extra = "") => `<div class="chart kit-draw" data-kit="${id}"${extra}></div>`;
const rowsOf = (items, id, head = "") => `<div class="kit-rows">${head}${items.map((x, i) => `<div class="kit-rowlabel xs muted">${esc(t(x.key))}</div>${box(`${id}-${i}`)}`).join("")}</div>`;
const CHARTS = {
  spark: {
    html: () => `<div class="tile"><div class="label"><span>${t("metric.sleep")}</span><span class="chip good">${STATE_ICON.good}${t("state.high")}</span></div>
      <div class="value">${dur(474)}</div><div class="spk">${box("spark")}</div><div class="note">${t("band", { low: dur(400), high: dur(438) })}</div></div>`,
    draw: { spark: (w) => spark(SLEEP14.map((value, i) => ({ date: iso(13 - i), value })), { q1: 400, median: 418, q3: 438 }, { width: w, unit: "min", tone: "good" }) },
  },
  bullet: {
    html: () => `<div class="tile kit-rows">${TONES.map(([tone], i) => `<div class="kit-rowlabel xs muted">${t(`kit.tone.${tone}`)}</div><div class="bul">${box(`bullet-${i}`)}</div>`).join("")}</div>`,
    draw: Object.fromEntries(TONES.map(([tone, value, band], i) => [`bullet-${i}`, (w) => bullet(value, band, { width: w, unit: "ms", tone })])),
  },
  rangeStrip: { html: () => rowsOf(STRIPS, "strip"), draw: Object.fromEntries(STRIPS.map((row, i) => [`strip-${i}`, (w) => rangeStrip(row, { width: w })])) },
  trendLine: { html: () => box("trend"), draw: { trend: (w) => trendLine(WEEKS8, { width: w, tip: (p) => `${t("drain.week_to", { day: shortDay(p.to) })} · ${p.value ?? "—"} ms` }) } },
  legendKey: { html: () => `<div class="legend">${["normal", "median", "now", "plan", "weeks"].map((k) => `<span class="key">${legendKey(k)}<code>${k}</code> ${t(`drain.key.${k}`)}</span>`).join("")}</div>` },
  dayRing: {
    html: () => `<div class="ring-wrap kit-ringrow">${box("ring", ' style="width:100%;max-width:360px"')}<div class="legend">
      <span class="key"><i style="background:var(--c-sleep)"></i>${t("ring.sleep")}</span><span class="key"><i style="background:var(--c-event)"></i>${t("act.calendar")}</span>
      <span class="key"><i style="background:var(--c-exercise)"></i>${t("act.exercise")}</span>
      ${RING_CATS.map(([key, , color]) => `<span class="key"><i style="background:${color}"></i>${t(`cat.${key}`)}</span>`).join("")}</div></div>`,
    draw: { ring: (w) => dayRing(RING, { size: Math.max(240, Math.min(360, w)), center: "18:40", centerSub: t("ring.now") }) },
  },
  interval: {
    html: () => rowsOf(INTERVALS, "ivl", `<span></span><div class="kit-axis xs muted"><span>${t("kit.axis.worse")}</span><span>${t("kit.axis.better")}</span></div>`),
    draw: Object.fromEntries(INTERVALS.map((row, i) => [`ivl-${i}`, (w) => interval(row, 4, { width: w })])),
  },
  dayDots: { html: () => `<div class="tile kit-narrow"><div class="label"><span>${t("metric.training")}</span><span class="chip">${t("training.days", { n: 3, k: 7 })}</span></div><div class="dots">${box("dots")}</div></div>`,
    draw: { dots: (w) => dayDots([45, 0, null, 30, 0, 60, 0].map((value, i) => ({ date: iso(6 - i), value })), { width: w }) } },
  timeChart: { html: () => box("weight"),
    draw: { weight: (w) => timeChart({ band: CORRIDOR, points: WEIGH, line: AVG7, refs: [{ value: 74, label: t("body.target", { kg: num(74, 1) }) }] },
      { width: w, height: 240, first: iso(69), last: iso(-14), fmt: (v) => num(v, 1) }) } },
  scoreDots: { html: () => box("scores"),
    draw: { scores: (w) => scoreDots([[58, 4.9], [53, 4.5], [51, 4.8], [44, 3.8], [40, 6.9], [37, 8.4], [36, 2.3], [34, 2.6], [32, 5.1], [30, 4.4], [26, 6.1], [23, 5.4], [19, 3.1], [16, 5.8], [12, 7.2], [9, 4.6], [5, 5.5], [2, 6.4]]
      .map(([k, value]) => ({ date: iso(k), value })), { width: w, first: iso(59), last: iso(0), band: { low: 3.5, high: 6.5 }, refs: [{ value: 5, label: t("after.usual") }], fmt: (v) => num(v, Number.isInteger(v) ? 0 : 1) }) } },
  stackedColumns: { html: () => box("columns"),
    draw: { columns: (w) => stackedColumns(days14(), FUN_FIRST, { width: w, limit: 180, limitLabel: t("time.fun_limit", { v: dur(180, { short: true }) }),
      labelEvery: w < 560 ? 3 : 2 }) } },
  blockColumns: { html: () => box("load"),
    draw: { load: (w) => blockColumns(LOAD.map((c) => ({ label: c.n ? t("week.in_weeks", { n: c.n }) : t("week.this"), sub: shortDay(iso(-7 * c.n)), total: `${c.total}%`,
      blocks: c.blocks.map(([text, value, kind]) => ({ value: value || 4, tone: kind === "watch" ? "watch" : kind === "none" ? "none" : "mark", faded: kind === "done", text, tip: `${text} · ${value}%` })) })),
    { width: w, label: t("week.load") }) } },
  sleepWindows: { html: () => box("nights"), draw: { nights: (w) => sleepWindows(NIGHTS, { width: w }) } },
  ladderChart: { html: () => box("ladder"), draw: { ladder: (w) => ladderChart(LADDER, { width: w, final: "07:00" }) } },
  coverage: { html: () => `<div class="kit-rows">${COVER.map(([key], i) => `<div class="kit-rowlabel xs muted">${t(key)}</div><div class="cov">${box(`cov-${i}`)}</div>`).join("")}</div>`,
    draw: Object.fromEntries(COVER.map(([, marks], i) => [`cov-${i}`, (w) => coverage(marks, iso(29), { width: w })])) },
  mealTimeline: { html: () => box("meals"), draw: { meals: (w) => mealTimeline(MEALS, { width: w, gapH: 3 }) } },
  keptDots: { html: () => `<div class="kit-rows">${KEPT.map((row, i) => `<div class="kit-rowlabel xs muted">${esc(t(...row.label))}</div>${box(`kept-${i}`)}`).join("")}</div>`,
    draw: Object.fromEntries(KEPT.map((row, i) => [`kept-${i}`, (w) => keptDots(row.days, { width: w })])) },
  lanes: { html: () => box("lanes"),
    draw: { lanes: (w) => {
      const labelW = w < 560 ? 92 : 150;
      const rows = [
        { label: t("act.sleep"), sub: dur(460), parts: [["sleep", "var(--c-sleep)"]], max: 60, values: SCREEN.map((_, h) => ({ sleep: h < 7 ? 60 : h === 7 ? 20 : h === 23 ? 20 : 0 })) },
        { label: t("act.exercise"), sub: dur(45), parts: [["exercise", "var(--c-exercise)"]], max: 60, values: SCREEN.map((_, h) => ({ exercise: h === 17 ? 30 : h === 18 ? 15 : 0 })) },
        { label: t("act.screen"), sub: dur(SCREEN.reduce((s, hr) => s + Object.values(hr).reduce((a, b) => a + b, 0), 0)), parts: SCREEN_PARTS, max: 60, values: SCREEN.map(groupOf) },
        // a hatch part: the minutes a second device adds on top of the clock (the Stimulation page's devices at once)
        { label: t("time.all_devices"), sub: t("time.key_extra"), max: 90, parts: [["clock", "var(--c-axis)"], ["extra", "var(--ink)", { hatch: true }]],
          values: SCREEN.map((hr, h) => ({ clock: Object.values(hr).reduce((a, b) => a + b, 0), extra: [0, 0, 0, 0, 0, 0, 0, 0, 4, 10, 0, 12, 20, 6, 0, 8, 10, 0, 15, 0, 25, 30, 20, 10][h] })) },
      ];
      return lanes(rows, SCREEN.map((_, h) => ({ label: pad(h), tip: `${pad(h)}:00` })), { width: w, labelW, labelEvery: w < 560 ? 6 : 3, showMax: false });
    } } },
};
// exports that draw nothing of their own: listed with their signature and doc
const HELPERS = ["esc", "CHART_WORDS", "setFormat", "formatDuration", "toneColor", "draw", "installTooltip", "niceStep", "RING_CATS", "ICON_KEYS", "icon", "COLOR", "STATE_ICON"];

// ---- components: each kit.css group in its states ---------------------------------------------------------
const TILES = [["metric.sleep", "good", "state.high", "min", 474, { q1: 400, median: 418, q3: 438 }],
  ["metric.resting_hr", "bad", "state.high", "bpm", 66, { q1: 55, median: 57, q3: 59 }],
  ["metric.hrv", "", "state.normal", "ms", 52, { q1: 48, median: 51, q3: 56 }]];
const CARET = `<svg class="side-caret" viewBox="0 0 12 12" aria-hidden="true"><path d="m4.5 2.5 3.5 3.5-3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const chip = (cls, text, glyph = "") => `<span class="chip ${cls}">${glyph}${text}</span>`;
const SAMPLES = {
  ".sr": () => `<p class="small" style="margin:0">${t("kit.c.sr")}<span class="sr">${t("kit.c.sr_hidden")}</span></p>`,
  ".top": () => `<p class="small muted" style="margin:0">${t("kit.c.top")}</p>`,
  ".brand": () => `<p class="small muted" style="margin:0">${t("kit.c.brand")}</p>`,
  ".nav": () => `<nav class="nav" aria-label="${esc(t("kit.sample"))}"><a href="#kit" aria-current="page">${t("nav.today")}</a><a href="#kit">${t("nav.body")}</a><a href="#kit">${t("nav.life")}</a></nav>`,
  // drawn in place (not a child of <body>): the same menu as this page's, one menu item open on its second page and
  // two closed
  ".side": () => `<p class="small muted" style="margin:0 0 10px">${t("kit.c.side")}</p><div class="kit-side side"><div class="side-head"><span class="brand"><span>Health AIO</span></span></div>
    <nav class="side-nav" aria-label="${esc(t("kit.sample"))}"><a href="#kit">${icon("sun", 18)}<span>${t("nav.today")}</span></a>
      <a href="#kit" aria-current="page" aria-expanded="true">${icon("heart", 18)}<span>${t("nav.body")}</span>${CARET}</a><a class="side-sub" href="#kit"><span>${t("nav.sleep_tab")}</span></a><a class="side-sub" href="#kit" aria-current="page"><span>${t("nav.drain")}</span></a><a class="side-sub" href="#kit"><span>${t("nav.weight")}</span></a>
      <a href="#kit" aria-expanded="false">${icon("walk", 18)}<span>${t("nav.life")}</span>${CARET}</a><a href="#kit" aria-expanded="false">${icon("target", 18)}<span>${t("nav.act")}</span>${CARET}</a></nav>
    <div class="side-tools"><button class="tool" type="button">${t("ui.lang")}</button><button class="tool" type="button" aria-label="${esc(t("ui.mode"))}">${icon("sleep", 15)}</button></div></div>`,
  ".tool": () => `<div class="tools"><button class="tool" type="button">${t("ui.lang")}</button><button class="tool" type="button" aria-label="${esc(t("ui.mode"))}">${icon("sleep", 15)}</button></div>`,
  ".demo-badge": () => `<span class="demo-badge">${t("ui.demo")}</span>`,
  ".head": () => `<div class="head" style="margin:0"><div><h1>${t("kit.c.head")}</h1><div class="sub">${t("kit.c.head_sub")}</div></div>${SAMPLES[".stepper"]()}</div>`,
  ".stepper": () => `<div class="stepper"><a href="#kit">‹ ${t("time.prev")}</a><a href="#kit">${t("time.next")} ›</a><span aria-disabled="true">${t("time.latest")}</span></div>`,
  ".grid": () => `<div class="grid kit-grid"><div class="span-8">span-8</div><div class="span-4">span-4</div><div class="span-5">span-5</div><div class="span-7">span-7</div></div>`,
  ".col": () => `<div class="col kit-grid"><div>${t("kit.c.box")}</div><div>${t("kit.c.box")}</div></div>`,
  ".card": () => `<section class="card"><h2>${t("kit.c.card")}<span class="aside">${t("kit.c.aside")}</span></h2><p class="small" style="margin:0">${t("kit.c.card_body")}</p></section>`,
  ".lede": () => `<p class="lede">${t("recovery.normal")}</p><p class="small muted" style="margin:0">.muted .small · ${t("recovery.as_of", { day: shortDay(DAY) })}</p><p class="xs" style="margin:4px 0 0">.xs · .num <span class="num">1,234.5</span></p>`,
  ".stack": () => `<div class="stack" style="gap:var(--s-2)"><div class="row">${chip("", "A")}${chip("", "B")}<span class="spacer"></span>${chip("", "C")}</div><div class="row">${chip("", "D")}${chip("", "E")}</div></div>`,
  ".eyebrow": () => `<span class="eyebrow">${t("recovery.eyebrow")}</span>`,
  ".hero-num": () => `<p class="hero-num" style="margin:0">74.2 kg</p>`,
  ".chip": () => `<div class="row" style="gap:6px">${chip("", t("state.none"))}${chip("good", t("kit.status.good"), STATE_ICON.good)}${chip("bad", t("kit.status.off"), STATE_ICON.bad)}${chip("watch", t("kit.status.watch"))}${chip("accent", t("nav.today"))}</div>`,
  ".dot": () => `<div class="row" style="gap:6px">${RING_CATS.map(([key, , color]) => `<span class="dot" style="background:${color}"></span><span class="xs">${t(`cat.${key}`)}</span>`).join("")}</div>`,
  ".legend": () => `<div class="legend">${RING_CATS.map(([key, , color]) => `<span class="key"><i style="background:${color}"></i>${t(`cat.${key}`)}</span>`).join("")}<span class="key">${legendKey("normal")}${t("drain.key.normal")}</span></div>`,
  ".ring": () => `<p class="small muted" style="margin:0">${t("kit.c.ring")}</p>`,
  ".agenda": () => `<ul class="agenda">
    <li><span class="when">10:00–11:50</span><span class="what"><b>HCI 610</b><span class="muted">Old Quad 101</span></span><span></span></li>
    <li><span class="when">15:00</span><span class="what"><b>STAT 520</b><span class="muted">${t("today.graded", { pct: 15 })}</span></span>${chip("watch", t("today.due", { when: t("today.days_left.1") }))}</li>
    <li><span class="when">23:59</span><span class="what"><b>SWEN 530</b><span class="muted">${t("today.ungraded")}</span></span>${chip("", t("today.days_left.n", { n: 4 }))}</li></ul>`,
  ".tonight": () => `<div class="tonight" style="margin-top:0"><div><span>${t("today.phone_away")}</span><b>23:00</b></div><div><span>${t("today.asleep_by")}</span><b>23:30</b></div><div><span>${t("today.alarm")}</span><b>07:15</b></div></div>`,
  ".tiles": () => `<div class="tiles aligned">${TILES.map(([key, tone, state, unit, value, band], i) => `<div class="tile"><div class="label"><span>${t(key)}</span>${chip(tone, t(state), STATE_ICON[tone] || "")}</div>
    <div class="value">${esc(measure(value, unit))}</div><div class="bul">${box(`tile-${i}`)}</div><div class="note">${esc(t("band", { low: measure(band.q1, unit), high: measure(band.q3, unit) }))}</div><div></div></div>`).join("")}</div>`,
  ".seg": () => `<span class="seg kit-seg" role="group" aria-label="${esc(t("kit.sample"))}"><button type="button" aria-pressed="true">${t("out.hrv")}</button><button type="button" aria-pressed="false">${t("out.resting_hr")}</button><button type="button" aria-pressed="false">${t("out.energy")}</button></span>`,
  ".subnav": () => `<nav class="subnav seg" style="margin:0" aria-label="${esc(t("kit.sample"))}"><a href="#kit" aria-current="page">${t("nav.weight")}</a><a href="#kit">${t("nav.sleep_tab")}</a></nav>`,
  ".how": () => `<details class="how" style="margin:0"><summary>${t("ui.how")}</summary><p>${t("kit.c.how")}</p></details>`,
  ".empty": () => `<div class="empty">${t("ui.no_data")}</div>`,
  ".foot": () => `<p class="small muted" style="margin:0">${t("kit.c.foot")}</p>`,
  ".tip": () => `<span class="chip" tabindex="0" data-tip="${esc(t("kit.c.tip_text"))}">${t("kit.c.tip")}</span>`,
  ".catbar": () => `<div class="catbar" role="img" aria-label="${esc(t("kit.sample"))}">${RING_CATS.map(([key, , color], i) => `<span style="flex:${[180, 140, 45, 20][i]};background:${color}" data-tip="${esc(`${t(`cat.${key}`)} ${dur([180, 140, 45, 20][i])}`)}"></span>`).join("")}</div>`,
  ".hbar": () => `<div class="stack" style="gap:6px">${[[0.8, "var(--c-fun)"], [0.45, "var(--c-focus)"], [0.2, "var(--c-comms)"]].map(([share, color]) => `<div class="hbar"><span style="width:${share * 100}%;background:${color}"></span></div>`).join("")}</div>`,
  ".progress": () => `<div class="progress"><span style="width:60%"></span></div>`,
  ".mark": () => `<div class="row" style="gap:6px"><span class="mark good">✓</span><span class="mark bad">✗</span><span class="mark">–</span></div>`,
  ".facts": () => `<dl class="facts" style="margin:0"><div><dt>${t("body.rate")}</dt><dd class="num">−0.4 kg</dd></div><div><dt>${t("body.weighed")}</dt><dd class="num">${t("body.weighed_n", { n: 12 })}</dd></div></dl>`,
  table: () => `<div class="table-wrap"><table class="sectioned"><thead><tr><th></th><th scope="col">${t("review.this")}</th><th scope="col">${t("review.change")}</th></tr></thead>
    <tbody><tr class="sec"><th colspan="3" scope="rowgroup">${t("review.sec.sleep")}</th></tr><tr><th scope="row">${t("review.m.sleep_min")}</th><td class="num">${dur(452)}</td><td>${chip("good", `+${dur(22)}`)}</td></tr>
    <tr class="sec"><th colspan="3" scope="rowgroup">${t("review.sec.screens")}</th></tr><tr><th scope="row">${t("review.m.fun")}</th><td class="num">${dur(150)}</td><td>${chip("bad", `+${dur(35)}`)}</td></tr></tbody></table></div>`,
  ".code": () => `<p class="small" style="margin:0 0 8px"><code>var(--accent)</code></p><pre class="code" style="margin:0">python3 -m healthaio kit check DIR</pre>`,
  ".chart": () => `<p class="small muted" style="margin:0">${t("kit.c.chart")}</p>`,
  ".ph": () => `<p class="small" style="margin:0;max-width:16em">${t("kit.c.ph").split("|").map((x) => `<span class="ph">${esc(x)}</span>`).join("")}</p>`,
};
const WIDE = new Set([".tiles", ".head", ".grid", ".agenda", "table"]);
// samples that show figures carry the same "Sample data" chip as the charts: the numbers are made up
const FIGURES = new Set([".lede", ".hero-num", ".agenda", ".tonight", ".tiles", ".catbar", ".facts", "table"]);

// ---- tokens --------------------------------------------------------------------------------------------
// every role of tokens.css has a block below: the four colour roles in look(), type in typeScale(), space and radius in
// spaceScale(), effect, motion and the two font stacks in effects()
const PALETTE_ROLES = ["neutral", "accent", "data", "status"];
// a value of one mode with var() followed through, so a block can show a mode the page is not in
const resolver = (tokens, mode) => {
  const value = Object.fromEntries(tokens.map((tk) => [tk.name, tk[mode]]));
  const resolve = (v, depth = 0) => { const m = /^var\((--[\w-]+)\)$/.exec(v || ""); return m && depth < 5 ? resolve(value[m[1]], depth + 1) : v; };
  return { resolve, of: (name) => resolve(value[name]) };
};
function look(tokens, mode) {
  const { resolve, of } = resolver(tokens, mode);
  const bg = of("--bg"), ink = of("--ink"), ink3 = of("--ink-3"), line = of("--line"), edge = of("--line-2");
  const groups = PALETTE_ROLES.map((role) => `<h4 style="color:${esc(ink3)}">${t(`kit.role_name.${role}`)}</h4><div class="kit-swatches">${tokens.filter((tk) => tk.role === role).map((tk) =>
    `<div class="kit-sw"><i style="background:${esc(resolve(tk[mode]))};box-shadow:inset 0 0 0 1px ${esc(edge)}"></i><code>${esc(tk.name)}</code><span style="color:${esc(ink3)}">${esc(tk[mode])}</span></div>`).join("")}</div>`).join("");
  return `<section class="kit-pal" style="background:${esc(bg)};color:${esc(ink)};border-color:${esc(line)}"><h3>${t(`kit.${mode}`)}</h3>${groups}</section>`;
}

function dataTable(tokens) {
  const rows = tokens.filter((tk) => tk.role === "data").map((tk) => `<tr><td><span class="kit-chipsw" style="background:var(${tk.name})"></span></td><th scope="row"><code>${esc(tk.name)}</code></th>
    <td>${esc(t(`kit.enc.${tk.name.slice(2)}`))}</td><td class="xs muted"><code>${esc(tk.light)}</code></td><td class="xs muted"><code>${esc(tk.dark)}</code></td></tr>`).join("");
  return `<div class="table-wrap"><table class="kit-data"><thead><tr><th></th><th scope="col">${t("kit.col.token")}</th><th scope="col">${t("kit.col.encodes")}</th><th scope="col">${t("kit.col.light")}</th><th scope="col">${t("kit.col.dark")}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function statusTable(tokens) {
  const by = Object.fromEntries(tokens.map((tk) => [tk.name, tk]));
  const rows = [["good", "good", "good"], ["watch", "watch", "watch"], ["off", "bad", "off"]].map(([name, cls, word]) => {
    const sw = (n) => `<span class="kit-chipsw" style="background:var(${n})" title="${esc(`${n}: ${by[n]?.light} / ${by[n]?.dark}`)}"></span>`;
    return `<tr><td>${chip(cls, t(`kit.status.${word}`), STATE_ICON[cls] || "")}</td><td>${sw(`--${name}`)}</td><td>${sw(`--${name}-ink`)}</td><td>${sw(`--${name}-soft`)}</td></tr>`;
  }).join("");
  return `<div class="table-wrap"><table class="kit-status"><thead><tr><th></th><th scope="col">${t("kit.col.fill")}</th><th scope="col">${t("kit.col.ink")}</th><th scope="col">${t("kit.col.soft")}</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="xs muted" style="margin:8px 0 0"><code>--good</code> <code>--good-ink</code> <code>--good-soft</code> · <code>--watch</code> … · <code>--off</code> … · <code>--on-watch</code></p>`;
}

function typeScale(tokens) {
  return tokens.filter((tk) => /^--t-/.test(tk.name)).map((tk) => `<div class="kit-type"><span class="kit-type-sample" style="font-size:var(${tk.name})">${t("recovery.normal")}</span>
    <span class="xs muted"><code>${tk.name}</code> · ${esc(tk.light)} · ${t(`kit.type.${tk.name.slice(2)}`)}</span></div>`).join("");
}

// the shadows on each mode's own surfaces (a card on the page, the chosen part of a switch on its track), the easing,
// and each font stack written in its own face
const FX_ON = { "--shadow": ["--bg", "--surface"], "--seg-on-edge": ["--surface-2", "--seg-on"] };
function effects(tokens) {
  const looks = { light: resolver(tokens, "light").of, dark: resolver(tokens, "dark").of };
  const fx = tokens.filter((tk) => tk.role === "effect").map((tk) => {
    const [under, face] = FX_ON[tk.name] || ["--bg", "--surface"];
    const tiles = ["light", "dark"].map((mode) => `<figure class="kit-fx-tile" style="background:${esc(looks[mode](under))};color:${esc(looks[mode]("--ink-3"))}">
      <i style="background:${esc(looks[mode](face))};box-shadow:${esc(tk[mode])}"></i><figcaption>${t(`kit.mode.${mode}`)} · <code>${esc(tk[mode])}</code></figcaption></figure>`).join("");
    return `<div class="kit-fx"><p class="xs" style="margin:0"><code>${esc(tk.name)}</code> <span class="muted">${t(`kit.fx.${tk.name.slice(2)}`)}</span></p><div class="kit-fx-tiles">${tiles}</div></div>`;
  }).join("");
  const motion = tokens.filter((tk) => tk.role === "motion").map((tk) => `<div class="kit-fx"><p class="xs" style="margin:0"><code>${esc(tk.name)}</code> <span class="muted">${esc(tk.light)}</span></p>
    <div class="kit-ease" tabindex="0" role="img" aria-label="${esc(t("kit.fx.ease_try"))}"><i></i><span class="xs muted">${t("kit.fx.ease_try")}</span></div></div>`).join("");
  const fonts = tokens.filter((tk) => tk.name === "--font" || tk.name === "--mono").map((tk) => `<div class="kit-fx kit-font" style="font-family:var(${tk.name})">
    <p class="xs" style="margin:0;font-family:var(--font)"><code>${esc(tk.name)}</code> <span class="muted">${t(`kit.fx.${tk.name.slice(2)}`)}</span></p>
    <span class="kit-font-sample">Aa 一天 0123456789</span><span class="xs muted">${esc(tk.light)}</span></div>`).join("");
  return fx + motion + fonts;
}

function spaceScale(tokens) {
  const space = tokens.filter((tk) => /^--s-/.test(tk.name)).map((tk) => `<div class="kit-space"><code class="xs">${tk.name}</code><i style="width:var(${tk.name})"></i><span class="xs muted">${esc(tk.light)}</span></div>`).join("");
  const radii = tokens.filter((tk) => /^--r-/.test(tk.name)).map((tk) => `<div class="kit-radius"><i style="border-radius:var(${tk.name})"></i><code class="xs">${tk.name}</code><span class="xs muted">${esc(tk.light)}</span></div>`).join("");
  return `<div class="kit-spaces">${space}</div><div class="kit-radii">${radii}</div>`;
}

// ---- the page ------------------------------------------------------------------------------------------
function chartCell(c) {
  const sample = CHARTS[c.name];
  // the narrow charts fill two or three columns evenly; the ring, the day dots and the wide charts each take a row
  const span = ["dayRing", "dayDots", "timeChart", "scoreDots", "stackedColumns", "blockColumns", "sleepWindows", "ladderChart", "coverage", "lanes", "mealTimeline"].includes(c.name) ? " kit-full" : "";
  return `<article class="kit-cell${span}">
    <header><code class="kit-name">${esc(c.name)}</code><span class="chip">${t("kit.sample")}</span></header>
    <p class="kit-sig"><code>${esc(c.signature)}</code></p><p class="small kit-doc">${esc(docOf(c.name, c.doc))}</p>
    <div class="kit-sample">${sample.html()}</div></article>`;
}

export default {
  render(p) {
    const tokens = p.tokens || [];
    const comps = (p.components || []).map((c) => `<article class="kit-cell${WIDE.has(c.class) ? " kit-wide" : ""}"><header><code class="kit-name">${esc(c.class)}</code>${FIGURES.has(c.class) ? `<span class="chip">${t("kit.sample")}</span>` : ""}</header>
      <p class="small kit-doc">${esc(docOf(c.class, c.doc))}</p><div class="kit-sample">${SAMPLES[c.class] ? SAMPLES[c.class]() : ""}</div></article>`).join("");
    const drawn = (p.charts || []).filter((c) => CHARTS[c.name]);
    const helpers = (p.charts || []).filter((c) => !CHARTS[c.name]).map((c) => `<tr><th scope="row"><code>${esc(c.signature)}</code><span class="xs muted" style="display:block;font-weight:400">${esc(c.file)}</span></th><td class="small">${esc(docOf(c.name, c.doc))}</td></tr>`).join("");
    const icons = ICON_KEYS.map((key) => `<figure class="kit-icon" style="color:${COLOR[key] || "var(--ink-2)"}">${SIZES.map((s) => icon(key, s)).join("")}<figcaption class="xs"><code>${key}</code></figcaption></figure>`).join("");
    const files = (p.files || []).map((f) => `<tr><th scope="row"><code>${esc(f.path)}</code></th><td class="small">${t(`kit.role.${f.role}`)}</td><td class="num small" style="white-space:nowrap">${num(f.bytes / 1024, 1)} KB</td><td class="xs muted"><code title="${esc(f.sha256)}">${esc(f.sha256.slice(0, 12))}</code></td></tr>`).join("");
    return `<div class="head"><div><h1>${t("kit.title")}</h1><div class="sub">${t("kit.sub", { v: esc(p.version) })}</div></div><span class="chip accent">${esc(p.name)} ${esc(p.version)}</span></div>
      <div class="grid">
        <div class="col span-7"><section class="card"><span class="eyebrow">${t("kit.eyebrow")}</span><p class="lede" style="margin:6px 0 8px">${t("kit.lede")}</p>
          <p class="small" style="margin:0;color:var(--ink-2)">${t("kit.what")}</p></section></div>
        <section class="card span-5"><h2>${t("kit.files")}<span class="aside">kit.json</span></h2><div class="table-wrap"><table class="kit-files">
          <thead><tr><th scope="col">${t("kit.col.file")}</th><th scope="col">${t("kit.col.role")}</th><th scope="col">${t("kit.col.size")}</th><th scope="col">SHA-256</th></tr></thead><tbody>${files}</tbody></table></div></section>
        <section class="card span-12"><h2>${t("kit.looks")}<span class="aside">${t("kit.looks_note")}</span></h2><div class="kit-pals">${look(tokens, "light")}${look(tokens, "dark")}</div></section>
        <div class="col span-7">
          <section class="card"><h2>${t("kit.data")}<span class="aside">${t("kit.data_note")}</span></h2>${dataTable(tokens)}<p class="small" style="margin:12px 0 0;color:var(--ink-2)">${t("kit.cvd")}</p></section>
          <section class="card"><h2>${t("kit.type")}<span class="aside">--t-xs … --t-3xl</span></h2><div class="kit-types">${typeScale(tokens)}</div></section>
        </div>
        <div class="col span-5">
          <section class="card"><h2>${t("kit.status")}<span class="aside">${t("kit.status_note")}</span></h2>${statusTable(tokens)}<p class="small" style="margin:12px 0 0;color:var(--ink-2)">${t("kit.status_rule")}</p></section>
          <section class="card"><h2>${t("kit.space")}</h2>${spaceScale(tokens)}</section>
          <section class="card"><h2>${t("kit.fx")}<span class="aside">${t("kit.fx_note")}</span></h2><div class="kit-fxs">${effects(tokens)}</div></section>
        </div>
        <section class="card span-12"><h2>${t("kit.components")}<span class="aside">${t("kit.components_note", { n: (p.components || []).length })}</span></h2><div class="kit-cells">${comps}</div></section>
        <section class="card span-12"><h2>${t("kit.charts")}<span class="aside">${t("kit.charts_note")}</span></h2><div class="kit-cells">${drawn.map(chartCell).join("")}</div>
          <h3 class="section-title" style="margin-top:var(--s-5)">${t("kit.helpers")}</h3><div class="table-wrap"><table class="kit-helpers"><tbody>${helpers}</tbody></table></div></section>
        <section class="card span-12"><h2>${t("kit.icons")}<span class="aside">${t("kit.icons_note")}</span></h2><div class="kit-icons">${icons}</div>
          <div class="row" style="margin-top:var(--s-3);gap:6px"><span class="xs muted"><code>STATE_ICON</code></span>${chip("good", "good", STATE_ICON.good)}${chip("bad", "bad", STATE_ICON.bad)}</div></section>
        <section class="card span-12"><h2>${t("kit.use")}<span class="aside"><a href="${DOCS}">${t("kit.use.docs")}</a></span></h2>
          <pre class="code kit-cmd">python3 -m healthaio kit export ../my-app/static/kit
python3 -m healthaio kit check ../my-app/static/kit</pre>
          <ol class="small kit-steps">${["export", "load", "own", "check", "back"].map((k) => `<li>${t(`kit.use.${k}`)}</li>`).join("")}</ol></section>
      </div>`;
  },
  mount(root) {
    const fns = Object.assign({}, ...Object.values(CHARTS).map((c) => c.draw || {}),
      Object.fromEntries(TILES.map(([, tone, , , value, band], i) => [`tile-${i}`, (w) => bullet(value, band, { width: w, tone: tone || "neutral" })])));
    root.querySelectorAll("[data-kit]").forEach((el) => { const fn = fns[el.dataset.kit]; if (fn) draw(el, fn); });
    root.querySelectorAll(".kit-seg").forEach((seg) => seg.querySelectorAll("button").forEach((b) => {
      b.onclick = () => seg.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    }));
  },
};
export { CHARTS, HELPERS, SAMPLES };
