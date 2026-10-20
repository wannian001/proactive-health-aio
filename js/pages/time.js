// Stimulation (#time; the page used to be "Where time went", and keeps its address): how stimulating these 7 days
// were against your normal, the long view, and how your body answered afterwards. Hormones (dopamine, cortisol,
// melatonin) cannot be measured by a phone or a watch, so no number on the page claims to be one; it shows what goes
// in (five Screen Time signals) and what the body does next (sleep, HRV, resting heart rate), and says plainly that
// the second is an association. The numbers and rules are in modules/time.py. One answer card, then the long view,
// then the detail in tabs (a typical day, devices at once, where it came from); how the body answered is on
// Follow-up, under "Tomorrow will be better".
import { bullet, draw, esc, lanes, timeChart } from "../charts.js?v=51ede4cbfe";
import { day, device, dur, getLang, num, t } from "../i18n.js?v=51ede4cbfe";
import { icon, STATE_ICON } from "../icons.js?v=51ede4cbfe";
import { mountTabs, tabs } from "./tabs.js?v=51ede4cbfe";

const SCREEN_PARTS = [["fun", "var(--c-fun)"], ["focus", "var(--c-focus)"], ["communication", "var(--c-comms)"], ["other", "var(--c-other)"]];
const KEYS = ["fun", "before_sleep", "switches", "ratio", "longest_focus"];
const ICON = { fun: "fun", before_sleep: "sleep", switches: "ratio", ratio: "screen", longest_focus: "focus" };
const COLOR = { fun: "var(--c-fun)", before_sleep: "var(--c-sleep)", switches: "var(--ink-2)", ratio: "var(--ink-2)", longest_focus: "var(--c-focus)" };
const toneCls = (tone) => (tone === "good" ? "good" : tone === "bad" ? "bad" : "");
const keep = (text) => text.replace(/ /g, " ");  // one value never breaks across lines ("4 小时 23 分")
// a value in its own unit: minutes, switches per screen hour, or the ratio kept in hundredths (142 = 1.42×)
function fmt(unit, v) {
  if (v == null) return "—";
  if (unit === "ratio") return t("time.ratio_v", { v: num(v / 100, 2) });
  if (unit === "per_hour") return t("stim.per_hour", { v: num(v, 1) });
  return dur(v);
}
// Chinese has no spaces between words: keep each phrase together (phrases end at punctuation or a "|" hint)
const phrases = (text) => (getLang() === "zh"
  ? text.split(/(?<=[，：；。])|\|/).filter(Boolean).map((x) => `<span class="ph">${esc(x)}</span>`).join("")
  : esc(text.replace(/\|/g, "")));

function bandText(m) {
  if (!m.band) return m.few ? t("time.few") : "";
  const low = keep(fmt(m.unit, m.band.q1)), high = keep(fmt(m.unit, m.band.q3));
  return low === high ? t("band_one", { low }) : t("band", { low, high });
}

// within normal; just past its edge (grey); or clearly outside (coloured)
function stateChip(m) {
  if (m.value == null) return "";
  if (!m.state) return `<span class="chip">${t(m.few ? "time.few" : "state.none")}</span>`;
  if (m.state !== "normal" && !m.clear) return `<span class="chip">${t(`time.slight_${m.state}`)}</span>`;
  const tone = m.state === "normal" ? "neutral" : m.tone;
  return `<span class="chip ${toneCls(tone)}">${STATE_ICON[tone] || ""}${t(`state.${m.state}`)}</span>`;
}

function tile(m, extra = []) {
  const pieces = [bandText(m), m.known < m.n ? t("time.known", { n: m.known, k: m.n }) : "", ...extra].filter(Boolean);
  const note = pieces.map((x, i) => `<span class="piece">${esc(x)}${i < pieces.length - 1 ? " ·" : ""}</span>`).join(" ");
  return `<div class="tile act-tile">
    <div class="label"><span class="act-name" style="color:${COLOR[m.key]}">${icon(ICON[m.key], 16)}<span>${t(`stim.m.${m.key}`)}</span></span>${stateChip(m)}</div>
    <div class="act-value"><div class="value">${fmt(m.unit, m.value)}</div><span class="xs muted">${t(`stim.what.${m.key}`)}</span></div>
    <div class="bul" data-key="${m.key}"></div>
    <div class="note">${note}</div></div>`;
}

function staleNote(S) {
  return (S.stale || []).map((s) => `<p class="chip watch stale">${esc(s.last
    ? t("time.stale", { what: t(`act.${s.activity}`), day: day(s.last) })
    : t("time.stale_none", { what: t(`act.${s.activity}`) }))}</p>`).join("");
}

// the answer: the level of entertainment & social against your normal, then the other signals clearly outside it
function heroHtml(p) {
  const S = p.span, M = S.metrics, fun = M.fun;
  const lede = S.level ? t(`stim.level.${S.level}`) : t("stim.level.none");
  const sub = fun.value == null ? t("stim.no_screens")
    : fun.band ? t("stim.fun_line", { v: keep(dur(fun.value)), band: bandText(fun) }) : t("stim.fun_line_none", { v: keep(dur(fun.value)), n: p.baseline_days, min: p.baseline_min });
  const plan = p.plan.fun_max_min != null && p.plan.known ? t("stim.plan_line", { h: dur(p.plan.fun_max_min, { short: true }), n: p.plan.over, k: p.plan.known }) : "";
  const also = S.also.length ? `<div class="chg-also"><span class="xs muted">${t("stim.also")}</span>${S.also.map((k) => {
    const m = M[k];
    return `<span class="chip ${toneCls(m.tone)}">${icon(m.state === "high" ? "up" : "down", 12)}${esc(t(`stim.dir.${k}.${m.state}`))}</span>`;
  }).join("")}</div>` : "";
  const mark = S.level === "high" || S.level === "low"
    ? `<span class="chg-icon" style="color:var(--c-fun)">${icon("fun", 56)}<span class="chg-badge ${toneCls(fun.tone)}">${icon(S.level === "high" ? "up" : "down", 24)}</span></span>`
    : `<span class="chg-icon" style="color:var(--ink-3)">${icon(S.level ? "check" : "not_recorded", 56)}</span>`;
  const tiles = KEYS.map((k) => tile({ ...M[k], n: S.n }, k === "fun" && p.plan.fun_max_min != null ? [t("time.fun_limit", { v: dur(p.plan.fun_max_min, { short: true }) })] : [])).join("");
  return `<section class="card span-12"><div class="time-hero stim-hero">
    <div class="time-top">${mark}</div>
    <div class="time-lede"><span class="eyebrow">${t("stim.eyebrow", { n: S.n })}</span><p class="lede" style="margin:4px 0">${phrases(lede)}</p>
      <p class="small muted" style="margin:0">${esc(sub)}${plan ? ` ${esc(plan)}` : ""}</p>${also}${staleNote(S)}</div></div>
    <div class="time-avg"><h2 class="section-title">${t("stim.signals")}<span class="aside">${t("time.vs_normal", { n: p.baseline_days })}</span></h2>
      <div class="tiles act-tiles">${tiles}</div>
      <p class="xs muted stim-note">${phrases(t("stim.hormone_note"))}</p></div></section>`;
}

// the long view: stimulation and focus as 7-day averages over 90 days (modules/time.py, trend)
const TREND = [["fun", "fun", "var(--c-fun)"], ["longest_focus", "focus", "var(--c-focus)"]];
const tenths = (v) => num(Math.round(v * 10) / 10, Math.round(v * 10) % 10 ? 1 : 0);
// stimulation is drawn in hours, so the axis steps on round hours (1, 2, 5) rather than 100 minutes (1.7h)
const TREND_SCALE = { fun: 1 / 60, longest_focus: 1 };
const TREND_FMT = { fun: (v) => t("trend.h", { h: tenths(v) }), longest_focus: (v) => t("trend.m", { m: Math.round(v) }) };

function trendHtml(p) {
  const T = p.trend;
  if (!T) return "";
  const box = ([key, ico, color]) => {
    const s = T.series[key], r = s.recent.avg, b = s.before.avg;
    const level = r == null ? t("trend.level_none", { n: T.level_days, min: T.level_min })
      : b == null ? t("trend.level_one", { n: T.level_days, v: dur(r) })
      : t("trend.level", { n: T.level_days, v: dur(r), w: dur(b) });
    return `<div style="--c-mark:${color};min-width:0">
      <div class="section-title"><span class="act-name" style="color:${color}">${icon(ico, 16)}<span>${t(`trend.${key}`)}</span></span><span class="aside">${phrases(t(`trend.${key}_what`))}</span></div>
      <p class="small" style="margin:2px 0 8px">${phrases(level)}</p>
      <div id="trend-${key}" class="chart"></div></div>`;
  };
  return `<section class="card span-12"><h2>${t("trend.title")}</h2><p class="xs muted tab-note">${phrases(t("trend.note"))}</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:20px 32px">${TREND.map(box).join("")}</div>
    <p class="xs muted" style="margin:10px 0 0">${esc(t("trend.key"))}</p></section>`;
}

// devices at once: device time, screens at once and the longest stretch on one thing, then device time by hour
function stackHtml(p) {
  const K = p.stack;
  if (!K) return "";
  const byDevice = Object.entries(K.devices).sort((a, b) => b[1] - a[1]).map(([d, m]) => `${device(d)} ${dur(m)}`).join(" · ");
  const best = K.best_single;
  const lines = [
    K.stacked != null ? t("time.ratio_note", { s: dur(K.stacked), c: dur(K.screen) }) : "",
    byDevice,
    best ? t("time.single_best", { d: dur(best.minutes), app: best.app, device: device(best.device), day: day(best.date), at: best.start }) : "",
  ].filter(Boolean);
  const agent = Object.values(K.agent_by_hour).reduce((a, b) => a + b, 0);
  return `<p class="xs muted tab-note">${phrases(t("time.stack_note"))}</p>
    <ul class="agenda">${lines.map((l) => `<li style="grid-template-columns:minmax(0,1fr)"><span class="small">${esc(l)}</span></li>`).join("")}</ul>
    <div class="section-title stack-hours-title"><span>${phrases(t("time.stack_hours"))}</span><span class="aside legend">${SCREEN_PARTS.map(([k, c]) => `<span class="key"><i style="background:${c}"></i>${t(`cat.${k}`)}</span>`).join("")}
      <span class="key"><i style="background:var(--c-axis)"></i>${t("time.key_clock")}</span><span class="key"><i class="hatch"></i>${t("time.key_extra")}</span></span></div>
    <div id="stack-hours" class="chart"></div>
    ${agent >= 1 ? `<p class="xs muted" style="margin:8px 0 0">${esc(t("time.agent_note", { v: dur(agent) }))}</p>` : ""}`;
}

function appsHtml(p) {
  if (!p.apps.length) return `<p class="muted small">${t("time.no_screens")}</p>`;
  const max = Math.max(1, ...p.apps.map((a) => a.minutes));
  const items = p.apps.map((a) => `<li><span class="app"><span class="app-name" title="${esc(a.app)}">${esc(a.app)}</span><span class="chip">${esc(device(a.device))}</span></span>
    <span class="hbar"><span style="width:${(a.minutes / max * 100).toFixed(1)}%;background:var(--c-fun)"></span></span>
    <span class="num small">${dur(a.minutes)}</span></li>`).join("");
  return `<p class="xs muted tab-note">${t("stim.apps_note")}</p><ul class="apps">${items}</ul>`;
}

export default {
  render(p) {
    if (p.empty) {
      const back = p.next ? `<p class="small"><a href="${p.next === p.newest ? "#time" : `#time/${p.next}`}">${t("time.next")} ›</a></p>` : "";
      return `<div class="head"><div><h1>${t("stim.title")}</h1></div></div><div class="card"><div class="empty">${t("stim.empty")}</div>${back}</div>`;
    }
    const S = p.span;
    // a server started before this page changed still sends the old numbers
    if (!S.metrics || !S.metrics.before_sleep) return `<div class="head"><div><h1>${t("stim.title")}</h1></div></div><div class="card"><div class="empty">${t("time.restart")}</div></div>`;
    // "Later" ends on the newest day when it gets there; that page is the latest one (#time, also on the static site)
    const nextHref = p.next === p.newest ? "#time" : `#time/${p.next}`;
    const stepper = `<div class="stepper">${p.prev ? `<a href="#time/${p.prev}">‹ ${t("time.prev")}</a>` : `<span aria-disabled="true">‹ ${t("time.prev")}</span>`}
      ${p.next ? `<a href="${nextHref}">${t("time.next")} ›</a>${p.next !== p.newest ? `<a href="#time">${t("time.latest")}</a>` : ""}` : ""}</div>`;
    return `<div class="head"><div><h1>${t("stim.title")}</h1><div class="sub">${t("time.span", { from: day(S.from, { weekday: false }), to: day(S.to, { weekday: false }), n: S.n })}</div></div>${stepper}</div>
      <div class="grid">
        ${heroHtml(p)}
        ${trendHtml(p)}
        <section class="card span-12"><h2>${t("time.detail")}</h2>
          ${tabs("time", [
            p.hours.now ? { key: "hours", label: t("stim.tab.hours"), html: `<p class="xs muted tab-note">${phrases(t("stim.hours_note"))}</p><div id="fun-hours" class="chart"></div>` } : null,
            p.stack ? { key: "stack", label: t("time.stack"), html: stackHtml(p) } : null,
            { key: "apps", label: t("stim.tab.apps"), html: appsHtml(p) },
          ])}
          <details class="how"><summary>${t("ui.how")}</summary><p>${esc(t("stim.rule", { n: p.baseline_days, min: p.baseline_min }))}</p>
            <p>${esc(t("time.rule_stack"))}</p>${p.trend ? `<p>${esc(t("trend.rule", { n: p.baseline_days, min: p.baseline_min, level: p.trend.level_days, lmin: p.trend.level_min, days: p.trend.days }))}</p>` : ""}</details></section>
      </div>`;
  },
  mount(root, p) {
    if (p.empty || !p.span.metrics || !p.span.metrics.before_sleep) return;
    mountTabs(root);
    const M = p.span.metrics;
    root.querySelectorAll(".bul").forEach((el) => {
      const m = M[el.dataset.key];
      draw(el, (w) => bullet(m.value, m.band, { width: w, unit: m.unit === "min" ? "min" : "", tone: m.clear ? m.tone : "neutral" }));
    });
    const cols = Array.from({ length: 24 }, (_, i) => ({ label: String(i).padStart(2, "0"), tip: `${String(i).padStart(2, "0")}:00` }));
    const every = (w, labelW, n, px) => Math.max(1, Math.ceil(px / Math.max(1, (w - labelW - 8) / n)));  // labels never touch
    const labelW = (w) => (w < 560 ? 92 : 150);
    const H = p.hours;
    if (H.now) {
      const max = Math.max(10, ...H.now, ...(H.normal || []));
      const rows = [{ key: "now", label: t("stim.hours_now"), sub: t("stim.hours_now_sub", { n: p.span.screen_days }), parts: [["fun", "var(--c-fun)"]], max, values: H.now.map((v) => ({ fun: v })) }];
      if (H.normal) rows.push({ key: "normal", label: t("stim.hours_normal"), sub: t("stim.hours_normal_sub", { n: H.normal_days }), parts: [["fun", "var(--ink-3)"]], max, values: H.normal.map((v) => ({ fun: v })) });
      draw(root.querySelector("#fun-hours"), (w) => lanes(rows, cols, { width: w, labelW: labelW(w), labelEvery: Math.max(every(w, labelW(w), 24, 26), w < 560 ? 6 : 3), showMax: false }));
    }
    const K = p.stack;
    if (K) {
      // one row per device in the priority order (others after), then all devices: the clock time and what devices at once add on top
      const order = [...(p.devices_order || []).filter((d) => d in K.devices), ...Object.keys(K.devices).filter((d) => !(p.devices_order || []).includes(d)).sort()];
      const devRows = order.map((d) => ({ key: d, label: device(d), sub: dur(K.devices[d]), parts: SCREEN_PARTS, max: 60,
        values: K.by_hour.map((h) => h[d] || {}) }));
      const totals = K.by_hour.map((h) => Object.values(h).reduce((s, parts) => s + Object.values(parts).reduce((a, b) => a + b, 0), 0));
      const allMax = Math.max(60, ...totals);
      const allRow = { key: "all", label: t("time.all_devices"), sub: t("chart.row_max", { v: dur(allMax) }), max: allMax,
        parts: [["clock", "var(--c-axis)"], ["extra", "var(--ink)", { hatch: true }]],
        values: totals.map((m, h) => ({ clock: K.clock_by_hour[h], extra: Math.max(0, m - K.clock_by_hour[h]) })) };
      draw(root.querySelector("#stack-hours"), (w) => lanes([...devRows, allRow], cols, { width: w, labelW: labelW(w), labelEvery: Math.max(every(w, labelW(w), 24, 26), w < 560 ? 6 : 3), showMax: false }));
    }
    const T = p.trend;
    if (T) {
      TREND.forEach(([key]) => {
        const D = T.series[key].days, k = TREND_SCALE[key];
        const layers = {
          points: D.filter((d) => d.value != null).map((d) => ({ date: d.date, value: d.value * k })),
          line: D.filter((d) => d.avg7 != null).map((d) => ({ date: d.date, value: d.avg7 * k })),
          band: D.filter((d) => d.band).map((d) => ({ date: d.date, low: d.band.q1 * k, high: d.band.q3 * k })),
        };
        draw(root.querySelector(`#trend-${key}`), (w) => timeChart(layers, { width: w, height: 190, first: T.from, last: T.to, fmt: TREND_FMT[key], maxGap: 1 }));
      });
    }
  },
};
