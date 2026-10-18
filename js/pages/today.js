// Today: one card for the morning (the day ring, how recovered you are, what is on, tonight, and what to adjust), then
// every other part of your health in one line each. Numbers and a state only: the sentences that explain them live on
// each part's own page, one click away, so a first look takes seconds.
import { dayRing, draw, esc, RING_CATS, spark } from "../charts.js?v=93bad7f144";
import { clock, day, dur, measure, num, signed, t, wtype } from "../i18n.js?v=93bad7f144";
import { COLOR, icon, STATE_ICON } from "../icons.js?v=93bad7f144";
import { worseLine } from "./drain.js?v=93bad7f144";
import { helping } from "./effects.js?v=93bad7f144";

const shiftDay = (iso, n) => { const d = new Date(`${iso}T12:00:00`); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const chip = (cls, text, glyph = "") => `<span class="chip ${cls}">${glyph}${esc(text)}</span>`;
const SEP = () => t("today.sched_sep");

function stateChip(m) {
  if (m.partial) return chip("", t("state.partial"));
  if (!m.state) return chip("", t("state.none"));
  const cls = m.tone === "good" ? "good" : m.tone === "bad" ? "bad" : "";
  return chip(cls, t(`state.${m.state}`), STATE_ICON[m.tone] || "");
}

// ---- the morning card ------------------------------------------------------------------------------------------
// the calendar is context for the day, not its subject: training in full, the calendar as a count
function dayLines(p) {
  const a = p.agenda;
  const done = (p.ring.workouts || []).map((w) => t("today.trained_short", { what: wtype(w.type), d: dur((new Date(w.end) - new Date(w.start)) / 60000) }));
  const training = done.length ? `<b>${esc(done.join(SEP()))}</b>` : a.training ? `<b>${esc(a.training)}</b>` : `<span class="muted">${t("today.rest")}</span>`;
  const events = a.events.filter((e) => e.kind !== "training");
  const parts = [events.length ? t("today.sched_events", { n: events.length }) : t("today.sched_none")];
  if (a.deadlines.length) {
    const first = a.deadlines[0];
    parts.push(first.days_left <= 1 ? t("today.sched_due", { n: a.deadlines.length, when: t(`today.days_left.${first.days_left}`) })
      : t("today.sched_due_in", { n: a.deadlines.length, d: first.days_left }));
  }
  return `<ul class="agenda">
    <li class="training-row"><span class="when"><span class="workout-icon">${icon("exercise", 15)}</span>${t("today.training")}</span><span class="what">${training}</span><span></span></li>
    <li><span class="when">${t("today.sched")}</span><span class="what"><a href="#week">${esc(parts.join(SEP()))}</a></span><span></span></li></ul>`;
}

function tonightHtml(p) {
  const s = p.agenda.sleep;
  if (!s || p.looking_back) return "";
  return `<div class="tonight" style="margin-top:var(--s-4)"><div><span>${t("today.phone_away")}</span><b>${clock(s.phone_away)}</b></div>
    <div><span>${t("today.asleep_by")}</span><b>${clock(s.asleep_by)}</b></div>
    <div><span>${t("today.alarm")}</span><b>${clock(s.alarm)}</b></div></div>`;
}

// ---- what to adjust today: at most three things, at most one each for training, sleep, food and daytime screens;
// the reason in a few words. The Follow-up page (pages/followup.js) checks them the next day with the same titles.
export const TODO_ICON = { training: "exercise", sleep: "sleep", food: "food", screen: "fun" };

export function todoTitle(x) {
  const q = x.params || {};
  switch (x.key) {
    case "ease": return q.planned ? t("todo.ease", { what: q.planned }) : t("todo.ease_rest");
    case "deload": return t("todo.deload");
    case "move": return t("todo.move", { d: dur(q.min) });
    case "strength": return t("todo.strength", { n: q.left });
    case "spare": return t("todo.spare", { list: (q.regions || []).map((r) => t(`sore.region.${r}`)).join(t("ui.list_sep")) });
    case "asleep_by": return t("todo.asleep_by", { clock: clock(q.clock) });
    case "phone_away": return t("todo.phone_away", { clock: clock(q.clock) });
    case "late_meal": return q.clock ? t("todo.late_meal", { clock: clock(q.clock) }) : t("todo.late_meal_h", { h: num(q.hours) });
    case "protein": return t("todo.protein", { g: num(q.more_g) });
    case "kcal": return t("todo.kcal", { kcal: num(q.max) });
    case "fun_cap": return t("todo.fun_cap", { h: num(q.hours, Number.isInteger(q.hours) ? 0 : 1) });
    default: return x.key;
  }
}

function todoWhy(x) {
  const w = x.why || {};
  switch (x.key) {
    case "ease": return t("todo.short.ease");
    case "deload": return t("todo.short.deload");
    case "move": return t("todo.short.move", { left: dur(w.remaining) });
    case "strength": return t("todo.short.strength", { n: w.days_left });
    case "spare": return t("todo.short.spare");
    case "asleep_by": return w.low ? t("todo.short.ease") : t("todo.short.asleep", { d: dur(w.short_by) });
    case "phone_away": return w.drain ? t("todo.short.phone_drain") : t("todo.short.phone_last", { d: dur(w.last_night) });
    case "late_meal": return t("todo.short.late_meal", { n: w.late, k: w.known });
    case "protein": return t("todo.short.protein", { avg: num(w.avg_g), target: num(x.params.target_g) });
    case "kcal": return t("todo.short.kcal", { avg: num(w.avg), max: num(x.params.max) });
    case "fun_cap": return t(`todo.short.fun_cap_${x.params.source}`, { avg: dur(w.avg), h: num(x.params.hours, Number.isInteger(x.params.hours) ? 0 : 1) });
    default: return "";
  }
}

function todoHtml(p) {
  const a = p.actions;
  if (!a) return "";
  const body = a.steady ? `<p class="lede" style="font-size:var(--t-lg);margin:0">${t("todo.steady")}</p>`
    : `<ol class="todo">${a.items.map((x) => `<li><a class="todo-item" href="${x.link}">
        <span class="todo-icon" style="color:${COLOR[TODO_ICON[x.domain]] || "var(--ink-2)"}">${icon(TODO_ICON[x.domain], 20)}</span>
        <span class="todo-body"><b>${esc(todoTitle(x))}</b><span class="small muted">${esc(todoWhy(x))}</span></span></a></li>`).join("")}</ol>`;
  return `<div class="today-todo"><h2 class="section-title">${t("todo.title")}</h2>${body}
    <p class="small today-followup"><a href="#followup">${t("fu.today_link")} ›</a></p>
    <details class="how"><summary>${t("ui.how")}</summary><p>${t("todo.rule")}</p></details></div>`;
}

function morningHtml(p) {
  const r = p.recovery;
  const self = p.self && (p.self.energy != null || p.self.focus != null || p.self.feel != null)
    ? `<p class="small muted" style="margin:0">${esc(t("self.title"))}${t("today.colon")}${esc([p.self.feel != null ? t("self.feel", { v: t(`feel.${p.self.feel}`) }) : "", p.self.energy != null ? t("self.energy", { v: num(p.self.energy) }) : "", p.self.focus != null ? t("self.focus", { v: num(p.self.focus) }) : ""].filter(Boolean).join(SEP()))}</p>` : "";
  const behind = r.days_behind > 1 ? `<p class="chip watch" style="height:auto;padding:4px 10px;white-space:normal">${t("recovery.behind", { n: r.days_behind, day: day(r.as_of) })}</p>` : "";
  const legend = `<div class="legend">
    <span class="key"><i style="background:var(--c-sleep)"></i>${t("ring.sleep")}</span>
    <span class="key"><i style="background:var(--c-exercise)"></i>${t("act.exercise")}</span>
    <span class="key"><i style="background:var(--c-event);opacity:.3"></i>${t("act.calendar")}</span>
    ${RING_CATS.map(([key, , color]) => `<span class="key"><i style="background:${color}"></i>${t(`cat.${key}`)}</span>`).join("")}</div>`;
  return `<section class="card span-12"><div class="hero">
    <div class="ring-wrap"><div id="ring" style="width:100%;max-width:360px"></div>${legend}</div>
    <div class="stack" style="gap:var(--s-5)">
      <div class="verdict"><span class="eyebrow" ${r.as_of ? `title="${esc(t("recovery.as_of", { day: day(r.as_of) }))}"` : ""}>${t("recovery.eyebrow")}</span>
        <p class="lede" style="font-size:var(--t-3xl);margin:0">${t(`recovery.${r.verdict}`)}</p>${self}${behind}</div>
      <div><h2 class="section-title">${t("today.title")}</h2>${dayLines(p)}${tonightHtml(p)}</div>
    </div></div>${todoHtml(p)}</section>`;
}

// ---- every part in one line: name, number, a small picture, a state; the whole line opens the part's page --------
function line({ key, iconKey, name, text, viz = "", state = "", href }) {
  return `<a class="sum-row" href="${href}">
    <span class="sum-icon" style="color:${COLOR[iconKey] || "var(--ink-2)"}">${icon(iconKey, 18)}</span>
    <span class="sum-name">${esc(name)}</span>
    <span class="sum-text num">${esc(text)}</span>
    <span class="sum-viz" data-viz="${key}">${viz}</span>
    <span class="sum-state">${state}</span>
    <span class="sum-go" aria-hidden="true">›</span></a>`;
}

function recoveryLines(p) {
  const href = { sleep: "#sleep", hrv: "#recovery", resting_hr: "#recovery" };
  return p.recovery.metrics.map((m) => line({ key: m.key, iconKey: m.key === "sleep" ? "sleep" : "heart", name: t(`metric.${m.key}`),
    text: measure(m.value, m.unit), state: stateChip(m), href: href[m.key] })).join("");
}

function exerciseLine(p) {
  const x = p.summary.exercise;
  const name = t("sum.exercise_name");
  if (!x.tracked) return line({ key: "exercise", iconKey: "exercise", name, text: t("sum.none"), href: "#exercise" });
  const share = Math.min(100, (x.minutes / x.goal_min) * 100);
  const cls = { met: "good", behind: "watch", missed: "bad" }[x.status] || "";
  return line({ key: "exercise", iconKey: "exercise", name, text: `${dur(x.minutes)} / ${dur(x.goal_min)}`,
    viz: `<span class="progress" style="margin:0;display:block"><span style="width:${share.toFixed(1)}%"></span></span>`,
    state: chip(cls, t(`sum.ex.${x.status}`)), href: "#exercise" });
}

function foodLine(p) {
  const f = p.summary.food;
  const name = t("nav.food");
  if (!f.ever) return line({ key: "food", iconKey: "food", name, text: t("sum.none"), href: "#food" });
  if (f.logged < f.min_logged) return line({ key: "food", iconKey: "food", name, text: t("sum.food_few"), state: chip("", t("sum.food_few_chip")), href: "#food" });
  const off = [];
  if (f.protein_state === "below") off.push(t("sum.food_protein"));
  if (f.late >= 2) off.push(t("sum.food_late", { n: f.late }));
  if (f.kcal_state === "above" || f.kcal_state === "below") off.push(t(`sum.food_kcal_${f.kcal_state}`));
  return line({ key: "food", iconKey: "food", name, text: off.length ? off.join(SEP()) : t("sum.food_ok"),
    state: off.length ? chip("bad", t("sum.food_off"), STATE_ICON.bad) : chip("good", t("sum.food_within"), STATE_ICON.good), href: "#food" });
}

function screensLine(p) {
  const a = p.attention;
  const name = t("sum.screens_name");
  if (!a.day) return line({ key: "screens", iconKey: "screen", name, text: t("sum.none"), href: "#time" });
  const cats = a.by_category || {};
  const bar = RING_CATS.map(([key, keys, color]) => {
    const minutes = keys.reduce((s, k) => s + (cats[k] || 0), 0);
    return minutes ? `<span style="flex:${minutes};background:${color}" data-tip="${esc(`${t(`cat.${key}`)} ${dur(minutes)}`)}"></span>` : "";
  }).join("");
  const bad = a.metrics.some((m) => m.tone === "bad"), good = a.metrics.some((m) => m.tone === "good");
  const state = a.stale ? chip("watch", t("sum.stale", { n: a.days_behind })) : bad ? chip("bad", t("sum.screens_bad"), STATE_ICON.bad) : good ? chip("good", t("sum.screens_good"), STATE_ICON.good) : chip("", t("sum.screens_usual"));
  return line({ key: "screens", iconKey: "screen", name, text: dur(a.total),
    viz: `<span class="catbar" role="img" aria-label="${esc(dur(a.total))}" style="margin:0;display:flex">${bar}</span>`, state, href: "#time" });
}

function drainLine(p) {
  const d = p.drain;
  // the Wear and tear page (#drain) for the same 7 days as this line (the latest window when this is today)
  const more = p.looking_back ? `#drain/${d.window.to}` : "#drain";
  const state = d.strain ? chip("watch", t("sum.strain")) : d.worse.length ? chip("bad", t("sum.drain_n", { n: d.worse.length }), STATE_ICON.bad) : d.compared ? chip("good", t("sum.drain_ok"), STATE_ICON.good) : "";
  return line({ key: "drain", iconKey: "battery", name: t("sum.drain_name"), text: worseLine(d.worse, d.compared, d.signals), state, href: more });
}

function weightLine(p) {
  const w = p.summary.weight;
  const name = t("nav.weight");
  if (!w) return line({ key: "weight", iconKey: "heart", name, text: t("sum.none"), href: "#body" });
  const cls = w.status === "on_track" || w.status === "reached" ? "good" : w.status ? "watch" : "";
  return line({ key: "weight", iconKey: "heart", name,
    text: [`${num(w.avg7, 1)} kg`, w.rate_pct != null ? t("goals.rate", { v: signed(w.rate_pct, 1) }) : ""].filter(Boolean).join(SEP()),
    state: w.status ? chip(cls, t(`body.status.${w.status}`)) : "", href: "#body" });
}

function cardioLine(p) {
  const c = p.summary.cardio;
  const name = t("cardio.short");
  if (!c) return line({ key: "cardio", iconKey: "heart", name, text: t("sum.none"), href: "#body" });
  const cls = { up: "good", down: "bad", steady: "" }[c.state] ?? "";
  return line({ key: "cardio", iconKey: "heart", name, text: `${num(c.level, 1)} ${t("cardio.unit")}`,
    state: c.state ? chip(cls, t(`cardio.state.${c.state}`, { v: num(Math.abs(c.change), 1) }), c.state === "steady" ? "" : STATE_ICON[cls]) : "", href: "#body" });
}

function patternLine(p) {
  const found = helping(p.effects);
  const words = found.map((r) => t(`eff.short.${r.key}`, { min: num(r.params?.min), hours: num(r.params?.hours), clock: r.params?.clock }));
  return line({ key: "patterns", iconKey: "check", name: t("sum.patterns"), text: words.length ? words.join(SEP()) : t("sum.patterns_none"), href: "#followup" });
}

function linesHtml(p) {
  return `<section class="card span-12"><h2>${t("sum.title")}</h2>
    <div class="sum-rows">${recoveryLines(p)}${exerciseLine(p)}${foodLine(p)}${screensLine(p)}${drainLine(p)}${weightLine(p)}${cardioLine(p)}${patternLine(p)}</div>
    <details class="how"><summary>${t("ui.how")}</summary><p>${t("recovery.rule")}</p><p>${t("screens.rule")}</p><p>${t("sum.rule")}</p></details></section>`;
}

export default {
  render(p) {
    const prev = shiftDay(p.day, -1), next = shiftDay(p.day, 1);
    const stepper = `<div class="stepper"><a href="#today/${prev}">‹ ${t("ui.prev_day")}</a>
      ${p.looking_back ? `<a href="${next === p.today ? "#today" : `#today/${next}`}">${t("ui.next_day")} ›</a><a href="#today">${t("ui.back_today")}</a>` : `<span aria-disabled="true">${t("ui.next_day")} ›</span>`}</div>`;
    return `<div class="head"><div><h1>${p.looking_back ? t("today.looking_back", { day: day(p.day) }) : t("today.title")}</h1>
      <div class="sub">${day(p.day)}</div></div>${stepper}</div>
      <div class="grid">${morningHtml(p)}${linesHtml(p)}</div>`;
  },
  mount(root, p) {
    const ringBox = root.querySelector("#ring");
    const now = p.ring.now ? clock(p.ring.now) : clock(p.ring.sleep?.end);
    draw(ringBox, (w) => dayRing(p.ring, { size: Math.max(260, Math.min(360, w)), center: now, centerSub: p.ring.now ? t("ring.now") : day(p.day) }));
    p.recovery.metrics.forEach((m) => {
      const el = root.querySelector(`.sum-viz[data-viz="${m.key}"]`);
      if (el) draw(el, (w) => spark(m.series, m.band, { width: w, height: 30, unit: m.unit, tone: m.tone }));
    });
  },
};
