// Exercise: this week against the weekly goal, the last 7 days against your normal, load against recovery,
// twelve weeks by kind, and how the body tends to answer each kind the next day; then the other half of moving,
// long stretches at the computer (modules/sitting.py) and the short moves for them (care-ui.js).
import { bullet, draw, esc, spark, stackedColumns } from "../charts.js?v=0f06915566";
import { clock, day, dur, measure, num, shortDay, signed, t, weekdayShort, wtype } from "../i18n.js?v=0f06915566";
import { STATE_ICON } from "../icons.js?v=0f06915566";
import { mountTabs, tabs } from "./tabs.js?v=0f06915566";
import { mountCare, routineHtml, stopLine } from "../care-ui.js?v=0f06915566";

// sitting: today's longest stretch at the computer against your usual, right now if the Mac app says so, 14 days of
// the longest stretch with the reminder line, today's long ones, and the moves (#exercise/sitting)
function sittingHtml(S) {
  if (!S) return "";
  const T = S.today, R = S.rule;
  const lede = !T ? t("sit.none_today") : S.usual != null ? t("sit.lede", { d: dur(T.longest), u: dur(S.usual) }) : t("sit.lede_no_usual", { d: dur(T.longest) });
  const longs = T ? T.stretches.filter((x) => x.minutes >= R.long_min) : [];
  return `<section class="card span-12" id="sitting"><h2>${t("sit.title")}<span class="aside">${t("sit.sub", { m: R.break_min })}</span></h2>
    <p class="lede" style="font-size:var(--t-lg);margin:0 0 4px">${esc(lede)}</p>
    ${S.live ? `<p class="small sit-live">${chip(S.live.minutes >= R.long_min ? "watch" : "", t("sit.live", { d: dur(S.live.minutes), at: clock(S.live.since) }))}</p>` : `<p class="xs muted" style="margin:0">${t("sit.no_live")}</p>`}
    <div id="sit-days" class="chart" style="margin-top:var(--s-3)"></div>
    ${longs.length ? `<p class="small" style="margin:var(--s-2) 0 0">${esc(t("sit.longs", { n: longs.length, m: R.long_min }))} ${longs.map((x) => `<span class="chip">${clock(x.start)}–${clock(x.end)} · ${dur(x.minutes)}</span>`).join(" ")}</p>` : ""}
    <h3 class="section-title" style="margin-top:var(--s-4)">${t("sit.moves")}</h3>
    <div class="routines">${S.routines.map((id) => routineHtml(id, S.info, { why: "sitting" })).join("")}</div>${stopLine(S.stop)}
    <details class="how"><summary>${t("ui.how")}</summary><p>${t("sit.rule", { b: R.break_min, l: R.long_min, r: R.repeat_min, n: R.base_days })}</p></details></section>`;
}

function mountSitting(root, S) {
  const box = root.querySelector("#sit-days");
  if (!S || !box) return;
  mountCare(root);
  const cols = S.days.map((d) => ({ label: shortDay(d.date), values: d.longest == null ? null : { longest: d.longest },
    tip: d.longest == null ? `${day(d.date)} · ${t("ui.no_data")}` : `${day(d.date)} · ${t("sit.tip", { d: dur(d.longest), n: d.long })}` }));
  draw(box, (w) => stackedColumns(cols, [["longest", "var(--c-focus)"]], { width: w, height: 170, limit: S.rule.long_min, limitLabel: t("sit.limit", { m: S.rule.long_min }), labelEvery: w < 560 ? 2 : 1 }));
}

const chip = (cls, text) => `<span class="chip ${cls}">${esc(text)}</span>`;

// kinds of training share the exercise hue and differ in lightness; minutes outside any logged workout are grey
export const KIND_PARTS = [["strength", "var(--c-exercise)"], ["cardio", "var(--c-exercise-2)"], ["walk", "var(--c-exercise-3)"], ["loose", "var(--c-other)"]];
const parts = (byKind, loose) => ({ strength: byKind.strength || 0, cardio: byKind.cardio || 0, walk: (byKind.walk || 0) + (byKind.other || 0), loose: loose || 0 });
const key = ([k, color]) => `<span class="key"><i style="background:${color}"></i>${t(`ex.kind.${k}`)}</span>`;

function value(r) {
  if (r.unit === "count") return r.value == null ? "—" : num(r.value, 0);
  if (r.unit === "kcal") return r.value == null ? "—" : `${num(r.value)} kcal`;
  return measure(r.value, r.unit);
}

function stateChip(r) {
  if (r.value == null) return `<span class="chip">${t("drain.no_window")}</span>`;
  if (!r.state) return `<span class="chip">${t("state.none")}</span>`;
  const cls = r.tone === "good" ? "good" : r.tone === "bad" ? "bad" : "";
  return `<span class="chip ${cls}">${STATE_ICON[r.tone] || ""}${t(`state.${r.state}`)}</span>`;
}

function tile(r, i) {
  const band = r.band ? t("band", { low: value({ ...r, value: r.band.q1 }), high: value({ ...r, value: r.band.q3 }) }) : "";
  return `<div class="tile"><div class="label"><span>${t(`ex.m.${r.key}`)}</span>${stateChip(r)}</div>
    <div class="value">${esc(value(r))}</div><div class="bul" data-i="${i}"></div><div class="spk" data-i="${i}"></div>
    <div class="note">${esc([t(`ex.how.${r.how}`), band].filter(Boolean).join(" · "))}</div></div>`;
}

// the seven days of the week: active minutes as a bar split by kind (one scale for the week), the workouts done,
// and the training planned for the days still to come
function weekStrip(p) {
  const w = p.week;
  const top = Math.max(p.goal.weekly_min / 7 * 2, ...w.days.map((d) => d.minutes || 0));
  const cells = w.days.map((d) => {
    const done = d.workouts.map((x) => `${wtype(x.type)} ${dur(x.minutes)}`).join(" · ");
    const loose = Math.max(0, (d.minutes || 0) - Object.values(d.by_kind).reduce((a, b) => a + b, 0));
    const split = parts(d.by_kind, loose);
    const bar = d.future ? "" : `<div class="hbar ex-bar">${KIND_PARTS.map(([k, color]) => (split[k] ? `<span style="width:${(split[k] / top * 100).toFixed(1)}%;background:${color}"></span>` : "")).join("")}</div>`;
    const note = d.future ? (d.planned ? t("week.planned", { what: d.planned }) : t("week.free"))
      : done || (d.planned ? t(d.is_today ? "week.planned" : "week.planned_missed", { what: d.planned }) : "");
    return `<div class="ex-day${d.is_today ? " is-today" : ""}${d.future ? " future" : ""}">
      <span class="xs muted">${weekdayShort(d.date)} ${shortDay(d.date)}</span>
      <b class="num">${d.future ? "—" : esc(dur(d.minutes))}</b>${bar}
      <span class="xs ex-note">${esc(note)}</span></div>`;
  }).join("");
  return `<div class="ex-days">${cells}</div>`;
}

function recentHtml(p) {
  if (!p.recent.length) return `<p class="muted small">${t("ex.no_workouts")}</p>`;
  return `<ul class="agenda">${p.recent.map((x) => {
    const facts = [dur(x.minutes), x.kcal != null ? `${num(x.kcal)} kcal` : null, x.avg_hr != null ? t("ex.avg_hr", { v: num(x.avg_hr) }) : null].filter(Boolean).join(" · ");
    const next = x.hrv_pct == null ? `<span class="xs muted">${t("ex.next_unknown")}</span>` : `<span class="chip">${t("ex.next_hrv", { v: signed(x.hrv_pct, 0, "%") })}</span>`;
    return `<li><span class="when">${weekdayShort(x.start)} ${clock(x.start)}</span><span class="what"><b>${esc(wtype(x.type))}</b><span class="muted">${esc(`${shortDay(x.start)} · ${facts}`)}</span></span>${next}</li>`;
  }).join("")}</ul>`;
}

function responseHtml(p) {
  if (!p.response.length) return `<p class="muted small">${t("ex.response_few", { n: p.rule.min_response })}</p>`;
  const rows = p.response.map((r) => `<tr><th scope="row">${t(`ex.after.${r.kind}`)}</th><td class="num">${num(r.days)}</td>
    <td class="num">${signed(r.hrv_pct, 1, "%")}</td><td class="num">${r.rhr_bpm == null ? "—" : signed(r.rhr_bpm, 1, ` ${t("unit.bpm")}`)}</td></tr>`).join("");
  return `<div class="table-wrap"><table><thead><tr><th></th><th scope="col">${t("ex.col.days")}</th><th scope="col">${t("ex.col.hrv")}</th><th scope="col">${t("ex.col.rhr")}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

export default {
  render(p) {
    const g = p.goal, w = p.week;
    if (!p.has_data) {
      return `<div class="head"><div><h1>${t("nav.exercise")}</h1></div></div><div class="grid"><div class="card span-12"><div class="empty">${t("ex.empty")}</div></div>${sittingHtml(p.sitting)}</div>`;
    }
    const share = Math.min(100, (w.minutes / g.weekly_min) * 100);
    const load = p.load;
    const recovery = chip(p.recovery.verdict === "low" ? "bad" : p.recovery.verdict === "good" ? "good" : "", t(`recovery.${p.recovery.verdict}`));
    const loadLine = load.chronic_min == null ? t("ex.load.line_one", { a: dur(load.acute_min) })
      : t("ex.load.line", { a: dur(load.acute_min), c: dur(load.chronic_min), r: num(load.ratio, 2) });
    return `<div class="head"><div><h1>${t("nav.exercise")}</h1><div class="sub">${t(g.source === "plan" ? "ex.src.plan" : "ex.src.who")}</div></div></div>
      <div class="grid">
        <section class="card span-12"><span class="eyebrow">${t("ex.eyebrow", { from: day(w.start, { weekday: false }), to: day(w.end, { weekday: false }) })}</span>
          <p class="lede" style="margin:6px 0 10px">${esc(t("ex.week_short", { d: dur(w.minutes), goal: dur(g.weekly_min) }))}</p>
          <div class="progress" role="img" aria-label="${esc(`${dur(w.minutes)} / ${dur(g.weekly_min)}`)}"><span style="width:${share.toFixed(1)}%"></span></div>
          <p class="small" style="margin:8px 0 14px;color:var(--ink-2)">${esc(t("ex.strength_days", { n: w.strength_days, goal: g.strength_days }))}</p>
          ${weekStrip(p)}
          <div class="legend" style="margin-top:10px">${KIND_PARTS.map(key).join("")}</div></section>
        <section class="card span-12"><h2>${t("ex.last7")}<span class="aside">${day(p.window.from, { weekday: false })} – ${day(p.window.to, { weekday: false })}</span></h2>
          <p class="lede" style="font-size:var(--t-lg);margin:0 0 8px">${t(`ex.advice.${p.advice}`)}</p>
          <div class="row" style="gap:6px;margin-bottom:var(--s-4)">${recovery}${chip(load.state === "high" ? "watch" : "", t(`ex.load.${load.state}`))}<span class="xs muted">${esc(loadLine)}</span></div>
          <div class="tiles aligned ex-tiles">${p.rows.map(tile).join("")}</div>
          <details class="how"><summary>${t("ui.how")}</summary><p>${t("ex.rule_tiles", { b: p.rule.baseline, k: p.rule.min_total_days })}</p><p>${t("ex.load.rule", { hi: num(load.high, 1), lo: num(load.low, 1) })}</p></details></section>
        ${sittingHtml(p.sitting)}
        <section class="card span-12"><h2>${t("time.detail")}</h2>
          ${tabs("ex", [
            { key: "weeks", label: t("ex.weeks", { n: p.rule.weeks }), html: `<div id="exweeks" class="chart"></div><div class="legend" style="margin-top:8px">${KIND_PARTS.map(key).join("")}</div>` },
            { key: "response", label: t("ex.response"), html: `<p class="xs muted tab-note">${t("ex.response_note", { n: p.rule.response_days })}</p>${responseHtml(p)}<p class="xs muted" style="margin:10px 0 0">${t("ex.response_rule")}</p>` },
            { key: "recent", label: t("ex.recent"), html: recentHtml(p) },
          ])}</section>
      </div>`;
  },
  mount(root, p) {
    mountSitting(root, p.sitting);
    if (!p.has_data) return;
    mountTabs(root);
    const weeks = p.weeks.map((x) => ({
      label: shortDay(x.week_start),
      values: x.minutes == null ? null : parts(x.by_kind, x.loose),
      tip: `${t("ex.week_of", { day: shortDay(x.week_start) })}${x.partial ? ` (${t("goals.so_far")})` : ""} · ${x.minutes == null ? t("ui.no_data") : dur(x.minutes)} · ${t("ex.strength_days", { n: x.strength_days, goal: p.goal.strength_days })}`,
    }));
    draw(root.querySelector("#exweeks"), (width) => stackedColumns(weeks, KIND_PARTS, { width, height: 210, limit: p.goal.weekly_min,
      limitLabel: t("ex.goal_line", { d: dur(p.goal.weekly_min) }), labelEvery: width < 560 ? 3 : 2 }));
    root.querySelectorAll(".spk").forEach((el) => { const r = p.rows[el.dataset.i]; draw(el, (width) => spark(r.series, r.how === "mean" ? r.band : null, { width, unit: r.unit === "count" ? "" : r.unit, tone: r.tone })); });
    root.querySelectorAll(".bul").forEach((el) => { const r = p.rows[el.dataset.i]; draw(el, (width) => bullet(r.value, r.band, { width, unit: r.unit === "count" ? "" : r.unit, tone: r.tone })); });
  },
};
