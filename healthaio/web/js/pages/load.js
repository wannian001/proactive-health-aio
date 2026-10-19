// Body & mind load: what is being asked of you, week by week, from the body (training load) and from the mind (hours
// of classes and work, the share of grade due), the 8 weeks behind and the 4 ahead, each against your normal; then
// the training load day by day. Nothing is added into one number. The rules are in modules/load.py. It is drawn on
// the Schedule page (#week, schedule & load); #load still renders it alone, for old links and the tests.
import { draw, esc, lanes, stackedColumns } from "../charts.js";
import { day, dur, num, shortDay, t, wtype } from "../i18n.js";
import { icon, STATE_ICON } from "../icons.js";

const TONE = { high: "watch", low: "", normal: "" };
const hours = (v) => t("load.hours", { v: num(v, v < 10 && v % 1 ? 1 : 0) });
const pct = (v) => `${num(v)}%`;
const FMT = { training: (v) => num(v), calendar: hours, deadlines: pct };

function chip(state) {
  if (!state) return `<span class="chip">${t("state.none")}</span>`;
  return `<span class="chip ${TONE[state]}">${state === "high" ? STATE_ICON.bad : ""}${t(`load.state.${state}`)}</span>`;
}

function band(b, key) {
  if (!b) return t("load.no_band", { n: 4 });
  const low = FMT[key](b.q1), high = FMT[key](b.q3);
  return low === high ? t("band_one", { low }) : t("band", { low, high });
}

function tile(key, w, p) {
  const value = key === "training"
    ? (w.training == null && !w.planned ? "—" : `${num(w.training || 0)}${w.planned ? ` <span class="xs muted">${esc(t("load.plus_planned", { v: num(w.planned), n: w.planned_sessions }))}</span>` : ""}`)
    : w[key] == null ? "—" : FMT[key](w[key]);
  const sub = key === "deadlines" ? t("load.due_n", { n: w.deadline_count }) : t(`load.what.${key}`);
  return `<div class="tile act-tile">
    <div class="label"><span class="act-name">${icon(key === "training" ? "exercise" : key === "calendar" ? "calendar" : "target", 16)}<span>${t(`load.m.${key}`)}</span></span>${chip(w.state[key])}</div>
    <div class="act-value"><div class="value">${value}</div><span class="xs muted">${esc(sub)}</span></div>
    <div class="note"><span class="piece">${esc(band(p.bands[key], key))}</span></div></div>`;
}

export function heroHtml(p) {
  const w = p.this_week;
  const lede = w.stacked ? t("load.lede.stacked") : w.mind_heavy ? t("load.lede.mind") : w.state.training === "high" ? t("load.lede.body") : t("load.lede.usual");
  const lighter = p.weeks.filter((x) => x.plan_lighter);
  const heavy = p.heaviest ? t("load.heaviest", { day: day(p.heaviest.start, { weekday: false }), pct: num(p.heaviest.deadlines || 0), n: p.heaviest.count, h: hours(p.heaviest.calendar || 0) }) : "";
  return `<section class="card span-12"><span class="eyebrow">${t("load.eyebrow", { day: day(w.start, { weekday: false }) })}</span>
    <p class="lede" style="margin:6px 0 4px">${esc(lede)}</p>
    ${heavy ? `<p class="small" style="margin:0 0 var(--s-2)">${esc(heavy)}</p>` : ""}
    ${lighter.length ? `<p class="small load-lighter">${icon("exercise", 14)}<span>${esc(t("load.lighter", { weeks: lighter.map((x) => shortDay(x.start)).join(t("ui.list_sep")), n: p.usual_sessions }))}</span></p>` : ""}
    <div class="tiles act-tiles" style="margin-top:var(--s-3)">${["training", "calendar", "deadlines"].map((k) => tile(k, w, p)).join("")}</div></section>`;
}

export function weeksHtml(p) {
  const legend = `<span class="key"><i style="background:var(--c-exercise)"></i>${t("load.key.done")}</span>
    <span class="key"><i class="hatch" style="color:var(--c-exercise)"></i>${t("load.key.planned")}</span>
    <span class="key"><i style="background:var(--c-band)"></i>${t("load.key.now")}</span>`;
  return `<section class="card span-12"><h2>${t("load.weeks_title", { a: p.rule.past_weeks, b: p.rule.ahead_weeks })}<span class="aside legend">${legend}</span></h2>
    <div id="load-weeks" class="chart"></div>
    <p class="xs muted" style="margin:8px 0 0">${t("load.weeks_note")}</p></section>`;
}

export function trainingHtml(p) {
  const L = p.training;
  let lede;
  if (L.state === "none") lede = t("rec.load_line.none");
  else if (L.chronic == null) lede = t("rec.load_line.no_base", { a: num(L.acute) });
  else lede = t("rec.load_line.ratio", { a: num(L.acute), c: num(L.chronic), r: num(L.ratio, 2) });
  const notes = [];
  if (L.rated_share != null && L.rated_share < 1) notes.push(t("rec.rated_share", { pct: num(L.rated_share * 100) }));
  if (L.unrated_min >= 1) notes.push(t("rec.unrated", { d: dur(L.unrated_min) }));
  const state = ["high", "low", "steady"].includes(L.state) ? `<span class="chip ${L.state === "high" ? "watch" : L.state === "steady" ? "good" : ""}">${t(`rec.load.${L.state}`)}</span>` : `<span class="chip">${t(`rec.load.${L.state}`)}</span>`;
  return `<section class="card span-12"><h2>${t("rec.load_title")}<span class="aside">${t("rec.load_sub")}</span></h2>
    <p class="lede" style="font-size:var(--t-lg);margin:0 0 4px">${esc(lede)} ${state}</p>
    ${notes.length ? `<p class="small muted" style="margin:0">${esc(notes.join(t("ui.list_sep")))}</p>` : ""}
    <div id="load-days" class="chart" style="margin-top:var(--s-3)"></div>
    <p class="xs muted rec-cns">${t("rec.cns_note")} <a href="#recovery">${t("rec.to_recovery")} ›</a></p></section>`;
}

function dueHtml(p) {
  const items = p.weeks.filter((w) => w.when !== "past").flatMap((w) => w.due.filter((d) => d.status === "todo"));
  if (!items.length) return "";
  const rows = items.map((d) => `<li><span class="num small">${esc(day(d.due, { weekday: false }))}</span><span><b>${esc(d.title)}</b>${d.group ? ` <span class="xs muted">${esc(d.group)}</span>` : ""}</span>
    <span class="num small">${d.weight_pct != null ? pct(d.weight_pct) : "—"}</span></li>`).join("");
  return `<section class="card span-12"><h2>${t("load.due_title")}<span class="aside"><a href="#week">${t("load.to_schedule")} ›</a></span></h2><ul class="load-due">${rows}</ul></section>`;
}

export const loadRules = (p) => `<p>${t("load.rule", { a: p.rule.past_weeks, n: p.rule.min_weeks })}</p>
  <p>${t("load.note")}</p>
  <p>${t("rec.rule_load", { a: p.rule.acute, c: p.rule.chronic, pct: num(p.rule.min_rated * 100) })}</p>`;

export default {
  render(p) {
    return `<div class="head"><div><h1>${t("load.title")}</h1><div class="sub">${t("load.sub")}</div></div></div>
      <div class="grid">
        ${heroHtml(p)}
        ${weeksHtml(p)}
        ${trainingHtml(p)}
        ${dueHtml(p)}
        <section class="card span-12"><details class="how"><summary>${t("ui.how")}</summary>${loadRules(p)}</details></section>
      </div>`;
  },
  mount(root, p) { mountLoad(root, p); },
};

export function mountLoad(root, p) {
  {
    const W = p.weeks;
    // the heaviest week ahead and the weeks to plan lighter are marked under their column
    const heaviest = p.heaviest?.start;
    const flag = (w) => (w.start === heaviest ? t("load.flag.heaviest") : w.plan_lighter ? t("load.flag.lighter") : "");
    const cols = W.map((w) => ({ label: shortDay(w.start), shade: w.when === "now", flag: flag(w), tip: t("load.week_of", { day: day(w.start, { weekday: false }) }) }));
    const max = (k, extra = () => 0) => Math.max(1, ...W.map((w) => (w[k] || 0) + extra(w)));
    const rows = [
      { key: "training", label: t("load.m.training"), sub: t("load.what.training_short"), max: max("training", (w) => w.planned || 0), fmt: (v) => num(v),
        parts: [["done", "var(--c-exercise)"], ["planned", "var(--c-exercise)", { hatch: true }]],
        values: W.map((w) => (w.training == null && !w.planned ? null : { done: w.training || 0, planned: w.planned || 0 })) },
      { key: "calendar", label: t("load.m.calendar"), sub: t("load.what.calendar"), max: max("calendar"), fmt: hours,
        parts: [["hours", "var(--c-event)"]], values: W.map((w) => (w.calendar == null ? null : { hours: w.calendar })) },
      { key: "deadlines", label: t("load.m.deadlines"), sub: t("load.what.deadlines"), max: max("deadlines"), fmt: pct,
        parts: [["pct", "var(--c-event)"]], values: W.map((w) => (w.deadlines == null ? null : { pct: w.deadlines })) },
    ];
    const labelW = (w) => (w < 560 ? 92 : 150);
    draw(root.querySelector("#load-weeks"), (w) => lanes(rows, cols, { width: w, rowH: 54, labelW: labelW(w), labelEvery: w < 560 ? 3 : 1 }));
    const days = p.training_days.map((d) => ({ label: shortDay(d.date), values: d.load == null ? null : { load: d.load },
      tip: d.load == null ? `${day(d.date)} · ${t("ui.no_data")}` : `${day(d.date)} · ${t("rec.tip_load", { v: num(d.load) })}${d.sessions?.length ? ` · ${d.sessions.map((s) => `${wtype(s.type)} ${dur(s.minutes)}${s.effort ? ` × ${num(s.effort)}` : ` (${t("rec.no_effort")})`}`).join(", ")}` : ""}` }));
    draw(root.querySelector("#load-days"), (w) => stackedColumns(days, [["load", "var(--c-exercise)"]], { width: w, height: 180, minutes: false, unitFmt: (v) => num(v), labelEvery: Math.max(1, Math.ceil(42 / Math.max(1, w / 44))) }));
  }
}
