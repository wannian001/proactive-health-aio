// Food: the last 7 logged days against your normal and your plan, when the last meal came before sleep, the
// energy balance against the scale, and what an early dinner has gone with the next morning.
import { draw, esc, legendKey, mealTimeline, rangeStrip, trendLine } from "../charts.js?v=93bad7f144";
import { day, dur, inSentence, num, shortDay, signed, t } from "../i18n.js?v=93bad7f144";
import { STATE_ICON } from "../icons.js?v=93bad7f144";
import { mountTabs, tabs } from "./tabs.js?v=93bad7f144";

function fmt(unit, v) {
  if (v === null || v === undefined) return "—";
  if (unit === "kcal") return `${num(v)} kcal`;
  if (unit === "g") return `${num(v)} g`;
  if (unit === "h") return dur(v * 60);
  return num(v);
}

const label = (k) => t(`food.item.${k}`);

function stateChip(r) {
  if (r.value === null || r.value === undefined) return `<span class="chip">${t("food.too_few", { n: 3 })}</span>`;
  if (!r.band) return `<span class="chip">${t("drain.no_baseline")}</span>`;
  const cls = r.tone === "good" ? "good" : r.tone === "bad" ? "bad" : "";
  return `<span class="chip ${cls}">${STATE_ICON[r.tone] || ""}${t(`food.state.${r.state}`)}</span>`;
}

function planChip(r) {
  if (!r.plan_state) return "";
  const words = r.key === "gap_h" && r.late ? t(`food.plan.gap_h.${r.plan_state}_n`, { n: r.late.days, k: r.late.known }) : t(`food.plan.${r.key}.${r.plan_state}`);
  return `<span class="chip ${r.plan_tone === "good" ? "good" : "bad"}">${r.plan_tone === "good" ? STATE_ICON.good : STATE_ICON.bad}${words}</span>`;
}

// a range written once with its unit ("1,755–2,149 kcal"), so it does not break between two units
const range = (unit, a, b) => `${unit === "kcal" || unit === "g" ? num(a) : fmt(unit, a)}–${fmt(unit, b)}`;

function planText(r, p) {
  if (!r.plan) return "";
  if (r.key === "kcal") return t("food.plan_range", { a: num(r.plan.low), b: fmt("kcal", r.plan.high) });
  if (r.key === "protein_g") return p.plan.protein_g_per_kg ? t("food.plan_protein_kg", { g: fmt("g", r.plan.low), per: num(p.plan.protein_g_per_kg, 1) }) : t("food.plan_min", { v: fmt("g", r.plan.low) });
  if (r.key === "gap_h") return t("food.plan_gap", { h: num(r.plan.low, 0) });
  return "";
}

// the line at the top: what is off the plan (or, without a plan, off your normal), and how many days were logged
function offLine(p) {
  if (!p.logged.ever) return t("food.never");
  if (p.logged.full < p.rule.min_window) return t("food.few_logged", { n: p.logged.full, k: p.logged.days });
  const off = p.off.map((k) => (k === "gap_h" ? t("food.off.gap_h", { n: p.late.days, k: p.late.known, h: num(p.late.gap_h) })
    : t(`food.off.${k}.${p.rows.find((r) => r.key === k)?.plan_state || "below"}`)));
  if (off.length) return t("food.off_some", { list: off.map(inSentence).join(t("drain.sep")) });
  return p.plan.set ? t("food.off_none") : t("food.no_plan");
}


function balanceHtml(p) {
  const b = p.balance;
  if (!b) return `<p class="muted small">${t("food.balance_few", { n: p.rule.min_window })}</p>`;
  const kg = (v) => (v == null ? "—" : `${signed(v, 2)} kg`);
  return `<div class="food-balance"><div><span class="xs muted">${t("food.balance_log")}</span><b class="num">${esc(kg(b.implied_kg_week))}</b><span class="xs muted">${t("food.per_week")}</span></div>
      <div><span class="xs muted">${t("food.balance_scale")}</span><b class="num">${esc(kg(b.scale_kg_week))}</b><span class="xs muted">${t("food.per_week")}</span></div></div>
    <dl class="facts"><div><dt>${t("food.eaten")}</dt><dd class="num">${fmt("kcal", b.intake)}</dd></div>
      <div><dt>${t("food.burned")}</dt><dd class="num">${fmt("kcal", b.burned)}</dd></div>
      <div><dt>${t("food.diff")}</dt><dd class="num">${esc(signed(b.diff, 0, " kcal"))}</dd></div></dl>
    <p class="xs muted" style="margin:10px 0 0">${t("food.balance_rule", { n: b.days, kcal: num(p.rule.kcal_per_kg) })}</p>`;
}

function macrosHtml(p) {
  if (!p.macros) return `<p class="muted small">${t("food.macros_few")}</p>`;
  const fiber = p.rows.find((r) => r.key === "fiber_g");
  return `<dl class="facts">${p.macros.map((m) => `<div><dt>${t(`food.macro.${m.key}`)}</dt><dd class="num">${fmt("g", m.grams)} · ${num(m.share * 100)}%</dd></div>`).join("")}
    <div><dt>${t("food.macro.fiber_g")}</dt><dd class="num">${fmt("g", fiber?.value)}</dd></div></dl>
    <p class="xs muted" style="margin:10px 0 0">${t("food.macros_rule")}</p>`;
}

export default {
  render(p) {
    const later = p.next === p.latest ? "#food" : `#food/${p.next}`;
    const stepper = `<div class="stepper"><a href="#food/${p.prev}">‹ ${t("drain.prev")}</a>${p.next ? `<a href="${later}">${t("drain.next")} ›</a><a href="#food">${t("drain.latest")}</a>` : ""}</div>`;
    const logged = t("food.logged", { n: p.logged.full, k: p.logged.days, p: p.logged.partial });
    const soFar = p.so_far ? t("food.so_far", { n: p.so_far.meals, kcal: fmt("kcal", p.so_far.kcal), g: fmt("g", p.so_far.protein_g) }) : t("food.so_far_none");
    const rows = p.rows.map((r, i) => `<div class="drain-row">
      <div class="what"><b data-tip="${esc(t(`food.why.${r.key}`))}">${esc(label(r.key))}</b></div>
      <div class="drain-strip" data-i="${i}"></div>
      <div class="drain-value"><b class="num">${esc(fmt(r.unit, r.value))}</b>
        <span class="xs muted">${esc([r.band ? t("food.usual", { v: range(r.unit, r.band.q1, r.band.q3) }) : "", planText(r, p)].filter(Boolean).join(" · "))}</span>
        <span class="drain-chips">${stateChip(r)}${planChip(r)}</span></div>
      <div class="drain-weeks-cell"><span class="drain-weeks-label xs muted" aria-hidden="true">${t("drain.weeks")}</span><div class="drain-weeks" data-i="${i}"></div></div></div>`).join("");
    const key = (k, text) => `<span class="key">${legendKey(k)}${text}</span>`;
    return `<div class="head"><div><h1>${t("nav.food")}</h1><div class="sub">${t("food.sub", { from: day(p.window.from, { weekday: false }), to: day(p.window.to, { weekday: false }) })}</div></div>${stepper}</div>
      <div class="grid">
        <section class="card span-12"><span class="eyebrow">${t("food.eyebrow")}</span>
          <p class="lede" style="margin:6px 0 4px">${esc(offLine(p))}</p>
          <p class="small" style="margin:0 0 var(--s-4);color:var(--ink-2)">${esc(logged)} · ${esc(soFar)}</p>
          <div class="legend" style="justify-content:flex-end">${key("normal", t("drain.key.normal"))}${key("now", t("food.key.now"))}${key("plan", t("drain.key.plan"))}<span class="drain-weeks-key">${key("weeks", t("drain.key.weeks"))}</span></div>
          <div class="drain-rows">${rows}</div>
          <details class="how"><summary>${t("ui.how")}</summary><p>${t("food.rule", { w: p.rule.window, b: p.rule.baseline, k: p.rule.min_window, m: p.rule.min_baseline, h: num(p.plan.last_meal_gap_h), d: p.rule.day_starts })}</p>
            ${["kcal", "protein_g", "gap_h", "fiber_g"].map((k) => `<p>${esc(label(k))}${t("today.colon")}${esc(t(`food.why.${k}`))}</p>`).join("")}</details></section>
        <section class="card span-12"><h2>${t("time.detail")}</h2>
          ${tabs("food", [
            { key: "meals", label: t("food.timeline"), html: `<p class="xs muted tab-note">${t("food.timeline_note", { h: num(p.plan.last_meal_gap_h) })}</p><div id="meals" class="chart"></div>
              <div class="legend" style="margin-top:8px"><span class="key"><i style="background:var(--c-mark);border-radius:50%"></i>${t("food.key.meal")}</span>
              <span class="key"><i style="background:var(--c-band)"></i>${t("food.key.awake")}</span><span class="key"><i style="background:var(--c-sleep)"></i>${t("ring.sleep")}</span>
              <span class="key"><i class="hatch" style="color:var(--c-axis)"></i>${t("food.key.zone", { h: num(p.plan.last_meal_gap_h) })}</span>
              <span class="key"><i style="background:none;border:2px solid var(--off);border-radius:50%"></i>${t("food.key.late")}</span></div>` },
            { key: "balance", label: t("food.balance"), html: `<div class="food-panel">${balanceHtml(p)}</div>` },
            { key: "macros", label: t("food.macros"), html: `<div class="food-panel">${macrosHtml(p)}</div>` },
          ])}
          <p class="small" style="margin:var(--s-4) 0 0"><a href="#followup">${t("food.effect_moved")}</a></p></section>
      </div>`;
  },
  mount(root, p) {
    mountTabs(root);
    // the strip's dot takes the plan's colour where there is a plan (the plan is the point of this page), else the normal's
    root.querySelectorAll(".drain-strip").forEach((el) => {
      const r = p.rows[el.dataset.i];
      const plan = r.plan ? { limit: r.key === "kcal" ? r.plan.high : r.plan.low } : null;
      draw(el, (w) => rangeStrip({ ...r, plan, tone: r.plan_tone || r.tone }, { width: w }));
    });
    root.querySelectorAll(".drain-weeks").forEach((el) => {
      const r = p.rows[el.dataset.i];
      draw(el, (w) => trendLine(r.weeks, { width: w, tip: (x) => `${t("drain.week_to", { day: shortDay(x.to) })} · ${fmt(r.unit, x.value)}` }));
    });
    draw(root.querySelector("#meals"), (w) => mealTimeline(p.timeline, { width: w, gapH: p.plan.last_meal_gap_h }));
  },
};
