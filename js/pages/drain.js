// Wear and tear: seven quiet signals over the last 7 days, in three groups (what the body already shows, sleep timing,
// screen habits), each against your normal and, where set, your plan. Drawn as the long-term section at the end of
// Recovery (#recovery/drain); #drain still renders it alone, for old links and the tests.
// No total score: the signals have different units and different strength of evidence.
import { draw, esc, legendKey, rangeStrip, trendLine } from "../charts.js?v=0f06915566";
import { day, dur, inSentence, num, shortDay, t } from "../i18n.js?v=0f06915566";

const STATUS = { bad: "bad", good: "good", neutral: "" };
const clockOf = (noon) => { const m = ((Math.round(noon + 720) % 1440) + 1440) % 1440; return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`; };

function fmt(unit, v) {
  if (v === null || v === undefined) return "—";
  if (unit === "bpm") return `${num(v)} ${t("unit.bpm")}`;
  if (unit === "ms") return `${num(v)} ms`;
  if (unit === "clock") return clockOf(v);
  if (unit === "per_hour") return t("drain.per_hour", { v: num(v, 1) });
  return dur(v);
}

// one row's own scale (the kit's rangeStrip): grey band = normal, tick = its median, dot = these 7 days,
// dashed tick = plan. Eight weekly averages (the kit's trendLine) show the direction; HRV in particular moves slowly.
const weekTip = (row) => (w) => `${t("drain.week_to", { day: shortDay(w.to) })} · ${fmt(row.unit, w.value)}`;

function stateChip(row) {
  if (row.value === null || row.value === undefined) return `<span class="chip">${t("drain.no_window")}</span>`;
  if (!row.band) return `<span class="chip">${t("drain.no_baseline")}</span>`;
  return `<span class="chip ${STATUS[row.tone]}">${t(`drain.state.${row.tone}`)}</span>`;
}

function planChip(row) {
  if (!row.plan || row.plan_over === undefined) return "";
  if (row.plan_tone === "good") return `<span class="chip good">${t("drain.plan.ok")}</span>`;
  return `<span class="chip bad">${t(`drain.plan.over.${row.key}`, { d: dur(row.plan_over) })}</span>`;
}

function usual(r) {
  if (!r.band) return "";
  if (r.unit === "per_hour") return t("drain.usual_per_hour", { a: num(r.band.q1, 1), b: num(r.band.q3, 1) });
  return t("drain.usual", { a: fmt(r.unit, r.band.q1), b: fmt(r.unit, r.band.q3) });
}

function planText(r) {
  if (!r.plan) return "";
  return r.plan.kind === "bedtime" ? t("drain.plan.bedtime", { clock: r.plan.clock }) : t("drain.plan.limit", { v: fmt(r.unit, r.plan.limit) });
}

const label = (k) => t(`drain.item.${k}`);
const listOf = (keys) => keys.map((k) => inSentence(label(k))).join(t("drain.sep"));
const hasValue = (r) => r.value !== null && r.value !== undefined;

// the top line: only signals that have both these 7 days and a normal can be set against your normal
export function worseLine(worse, compared, total) {
  if (worse.length) return t("drain.worse_some", { n: worse.length, list: listOf(worse) });
  if (compared === 0) return t("drain.worse_unknown");
  return compared < total ? t("drain.worse_none_some", { n: compared }) : t("drain.worse_none");
}

// the plan line names what is off the plan, and what could not be checked for want of records
export function planLine(rows) {
  const planned = rows.filter((r) => r.plan);
  if (!planned.length) return t("drain.plan_unset");
  const off = planned.filter((r) => r.plan_tone === "bad");
  const within = planned.filter((r) => r.plan_tone === "good");
  const unchecked = planned.filter((r) => r.plan_over === null || r.plan_over === undefined);
  const parts = [];
  if (off.length) parts.push(t("drain.plan_some", { list: off.map((r) => `${inSentence(label(r.key))}${t(`drain.plan.over.${r.key}`, { d: dur(r.plan_over) })}`).join(t("drain.plan_sep")) }));
  else if (within.length && !unchecked.length) parts.push(t("drain.plan_none"));
  else if (within.length) parts.push(t("drain.plan_within", { list: listOf(within.map((r) => r.key)) }));
  if (unchecked.length) parts.push(t("drain.plan_unchecked", { list: listOf(unchecked.map((r) => r.key)) }));
  return parts.join(t("drain.sentence_sep"));
}

export default {
  render(p) {
    const later = p.next === p.latest ? "#drain" : `#drain/${p.next}`;
    const stepper = `<div class="stepper"><a href="#drain/${p.prev}">‹ ${t("drain.prev")}</a>${p.next ? `<a href="${later}">${t("drain.next")} ›</a><a href="#drain">${t("drain.latest")}</a>` : ""}</div>`;
    return `<div class="head"><div><h1>${t("drain.title")}</h1><div class="sub">${t("drain.sub", { from: day(p.window.from, { weekday: false }), to: day(p.window.to, { weekday: false }) })}</div></div>${stepper}</div>
      <div class="grid">${drainCards(p)}</div>`;
  },
  mount(root, p) { mountDrain(root, p); },
};

// the cards themselves, for this page and for the end of Recovery
export function drainCards(p) {
    const compared = p.rows.filter((r) => hasValue(r) && r.band).length;
    const worse = worseLine(p.worse, compared, p.rows.length);
    const plan = planLine(p.rows);
    const GROUP = { resting_hr: "body", asleep: "sleep", before_sleep: "screen" };
    const rows = p.rows.map((r, i) => `${GROUP[r.key] ? `<div class="drain-group section-title">${t(`drain.group.${GROUP[r.key]}`)}</div>` : ""}<div class="drain-row">
      <div class="what"><b>${esc(label(r.key))}</b><span>${esc(t(`drain.why.${r.key}`))}</span></div>
      <div class="drain-strip" data-i="${i}"></div>
      <div class="drain-value"><b class="num">${esc(fmt(r.unit, r.value))}</b>
        <span class="xs muted">${esc([usual(r), planText(r)].filter(Boolean).join(" · "))}</span>
        <span class="drain-chips">${stateChip(r)}${planChip(r)}</span></div>
      <div class="drain-weeks-cell"><span class="drain-weeks-label xs muted" aria-hidden="true">${t("drain.weeks")}</span><div class="drain-weeks" data-i="${i}"></div></div></div>`).join("");
    const s = p.strain;
    const strainFacts = s.nights ? [t("week.nights", { short: s.short_nights, n: s.nights, h: s.rule.short_hours }), t("week.train", { n: s.train_days })] : [];
    if (s.hrv_change !== null && s.hrv_change !== undefined) strainFacts.push(t("week.hrv", { dir: t(s.hrv_change >= 0 ? "week.up" : "week.down"), pct: `${num(Math.abs(s.hrv_change) * 100)}%` }));
    const load = s.strain ? "drain.load_strain" : s.nights < p.rule.min_window ? "drain.load_unknown" : "drain.load_ok";
    const key = (k, text) => `<span class="key">${legendKey(k)}${text}</span>`;
    // the seven in three groups, each headed where its first signal starts
    return `
        <section class="card span-12"><span class="eyebrow">${t("drain.eyebrow")}</span>
          <p class="lede" style="margin:6px 0 4px">${esc(worse)}</p><p class="small" style="margin:0;color:var(--ink-2)">${esc(plan)}</p></section>
        <section class="card span-12"><h2>${t("drain.items")}<span class="aside legend">
            ${key("normal", t("drain.key.normal"))}${key("median", t("drain.key.median"))}${key("now", t("drain.key.now"))}${key("plan", t("drain.key.plan"))}<span class="drain-weeks-key">${key("weeks", t("drain.key.weeks"))}</span></span></h2>
          <div class="drain-rows"><div class="drain-head" aria-hidden="true"><span></span><span></span><span></span><span>${t("drain.weeks")}</span></div>${rows}</div></section>
        <section class="card span-12"><h2>${t("drain.load_title")}</h2>
          <p class="lede" style="font-size:var(--t-lg)">${t(load)}</p>
          ${strainFacts.length ? `<ul class="agenda">${strainFacts.map((f) => `<li style="grid-template-columns:minmax(0,1fr)"><span>${esc(f)}</span></li>`).join("")}</ul>` : ""}
          <details class="how"><summary>${t("ui.how")}</summary><p>${t("week.rule")}</p></details></section>
        <section class="card span-12"><details class="how"><summary>${t("ui.how")}</summary><p>${t("drain.rule", { w: p.rule.window, b: p.rule.baseline })}</p></details></section>`;
}

export function mountDrain(root, p) {
    root.querySelectorAll(".drain-strip").forEach((el) => draw(el, (w) => rangeStrip(p.rows[el.dataset.i], { width: w })));
    root.querySelectorAll(".drain-weeks").forEach((el) => { const row = p.rows[el.dataset.i]; draw(el, (w) => trendLine(row.weeks, { width: w, tip: weekTip(row) })); });
  }
