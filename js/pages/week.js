import { blockColumns, draw, esc } from "../charts.js?v=93bad7f144";
import { clock, day, dur, num, shortDay, t, weekdayShort, wtype } from "../i18n.js?v=93bad7f144";
import { icon } from "../icons.js?v=93bad7f144";

const shift = (iso, n) => { const d = new Date(`${iso}T12:00:00`); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const leftText = (n) => (n < 0 ? t("week.days_ago", { n: -n }) : n <= 1 ? t(`today.days_left.${n}`) : t("today.days_left.n", { n }));

// the plan's training for the day; once the day is over it says whether a workout happened
function planLine(d) {
  if (!d.training) return "";
  const done = (d.workouts || []).length > 0 || (d.actual && d.actual.workout_min > 0);
  if (d.past && !done && d.actual && d.actual.workout_min === 0) {
    return `<p class="xs day-train missed"><span class="workout-icon">${icon("exercise", 14)}</span>${esc(t("week.planned_missed", { what: d.training }))}</p>`;
  }
  if ((d.past || d.is_today) && done) return "";  // the workout itself is listed above
  return `<p class="xs day-train"><span class="workout-icon">${icon("exercise", 14)}</span>${esc(t("week.planned", { what: d.training }))}</p>`;
}

function dayCard(d) {
  const items = [];
  const timed = [...d.events.map((e) => ({ start: e.start, html: `<li><span class="num">${clock(e.start)}</span> ${esc(e.title)}${e.location ? `<span class="muted"> · ${esc(e.location)}</span>` : ""}</li>` })),
    ...(d.workouts || []).map((w) => ({ start: w.start, html: `<li class="workout"><span class="workout-icon">${icon("exercise", 14)}</span><span class="num">${clock(w.start)}</span> ${esc(wtype(w.type))}<span class="muted"> · ${dur(w.minutes)}</span></li>` }))];
  timed.sort((a, b) => (a.start < b.start ? -1 : 1)).forEach((x) => items.push(x.html));
  const due = d.deadlines.map((x) => `<li class="due ${x.status !== "todo" ? "done" : x.days_left <= 1 ? "soon" : ""}"><span class="num">${clock(x.due)}</span> ${esc(x.title)}
    <span class="muted">· ${esc(x.group || "")}${x.weight_pct ? ` · ${num(x.weight_pct)}%` : ""}${x.status !== "todo" ? ` · ${t(`status.${x.status}`)}` : ""}</span></li>`).join("");
  let actual = "";
  if (d.actual) {
    const bits = [];
    if (d.actual.sleep_min != null) bits.push(t("week.slept", { d: dur(d.actual.sleep_min) }));
    if (d.actual.workout_min && !(d.workouts || []).length) bits.push(t("week.trained", { what: d.actual.workout_type ? wtype(d.actual.workout_type) : "", d: dur(d.actual.workout_min) }));
    else if (d.actual.workout_min === 0 && !d.training) bits.push(t("week.rested"));
    actual = bits.length ? `<p class="xs muted day-actual">${esc(bits.join(" · "))}</p>` : "";
  }
  return `<article class="daycol ${d.is_today ? "is-today" : ""} ${d.past ? "past" : ""}">
    <header><b>${weekdayShort(d.date)}</b><span>${shortDay(d.date)}</span>${d.is_today ? `<span class="chip accent">${t("nav.today")}</span>` : ""}</header>
    ${due ? `<ul class="daylist">${due}</ul>` : ""}
    ${items.length ? `<ul class="daylist">${items.join("")}</ul>` : `<p class="xs muted">${t("week.free")}</p>`}
    ${planLine(d)}
    ${actual}</article>`;
}

// the coming weeks as the kit's blockColumns: one block per deadline, height = share of the grade (4 when ungraded,
// in grey), amber = due within 3 days, faded = done
function loadColumns(load) {
  return load.map((w, i) => ({
    label: i === 0 ? t("week.this") : t("week.in_weeks", { n: i }), sub: shortDay(w.week_start), total: w.total_pct ? `${num(w.total_pct)}%` : "",
    blocks: w.items.map((x) => {
      const soon = x.days_left >= 0 && x.days_left <= 3 && x.status === "todo";
      return { value: x.weight_pct || 4, tone: !x.weight_pct ? "none" : soon ? "watch" : "mark", faded: x.status !== "todo", text: x.group || x.title,
        tip: `${shortDay(x.due)} · ${x.group || ""} ${x.title}${x.weight_pct ? ` · ${num(x.weight_pct)}%` : ""}` };
    }),
  }));
}

function dueList(items, empty) {
  if (!items.length) return `<p class="muted small">${empty}</p>`;
  return `<ul class="agenda">${items.map((x) => `<li><span class="when">${day(x.due)}<br><span class="xs muted">${clock(x.due)}</span></span>
    <span class="what"><b>${esc(x.title)}</b><span class="muted">${esc([x.group, x.weight_pct ? t("today.graded", { pct: num(x.weight_pct) }) : t("today.ungraded"), x.note].filter(Boolean).join(" · "))}</span></span>
    <span class="chip ${x.days_left <= 3 && x.days_left >= 0 ? "watch" : x.days_left < 0 ? "bad" : ""}">${leftText(x.days_left)}</span></li>`).join("")}</ul>`;
}

export default {
  render(p) {
    const stepper = `<div class="stepper"><a href="#week/${shift(p.week_start, -7)}">‹ ${t("week.prev")}</a>
      ${p.is_current ? "" : `<a href="#week">${t("week.current")}</a>`}<a href="#week/${shift(p.week_start, 7)}">${t("week.next")} ›</a></div>`;
    return `<div class="head"><div><h1>${t("week.title_range", { from: day(p.week_start, { weekday: false }), to: day(p.week_end, { weekday: false }) })}</h1>
      <div class="sub">${t("week.sub")}</div></div>${stepper}</div>
      <div class="grid">
        <section class="span-12 days7">${p.days.map(dayCard).join("")}</section>
        <section class="card span-12"><h2>${t("week.load")}<span class="aside">${t("week.load_note")}</span></h2><div id="load" class="chart"></div></section>
        <section class="card span-7"><h2>${t("week.upcoming")}</h2>${p.overdue.length ? `<p class="small" style="margin:0 0 8px"><b>${t("week.overdue")}</b></p>${dueList(p.overdue, "")}` : ""}${dueList(p.upcoming, t("week.none_soon"))}</section>
        <section class="card span-5"><h2>${t("week.later")}</h2>${dueList(p.later, t("week.none_later"))}</section>
      </div>`;
  },
  mount(root, p) { const columns = loadColumns(p.load); draw(root.querySelector("#load"), (w) => blockColumns(columns, { width: w, label: t("week.load") })); },
};
