// Weight and fitness (#body): weight against the plan's corridor, and cardio fitness (VO2 max) against your own
// level three months ago. The rules are in modules/body.py.
import { draw, esc, timeChart } from "../charts.js?v=0f06915566";
import { day, num, signed, t } from "../i18n.js?v=0f06915566";
import { STATE_ICON } from "../icons.js?v=0f06915566";

const kg = (v) => (v == null ? "—" : `${num(v, 1)} kg`);
const STATUS = { on_track: "good", faster: "watch", slower: "watch", reached: "good" };
const CARDIO_TONE = { up: "good", down: "bad", steady: "" };

// cardio fitness: the level (a month's median), how it moved against three months ago, and twelve months of estimates
function cardioHtml(p) {
  const C = p.cardio, L = C.latest;
  if (!L) return `<section class="card span-12"><h2>${t("cardio.title")}</h2><p class="muted small" style="margin:0">${t("cardio.empty")}</p></section>`;
  const tone = CARDIO_TONE[L.state] ?? "";
  const chip = L.state ? `<span class="chip ${tone}">${tone ? STATE_ICON[tone] : ""}${t(`cardio.state.${L.state}`, { v: num(Math.abs(L.change), 1) })}</span>`
    : `<span class="chip">${t("cardio.no_then")}</span>`;
  return `<section class="card span-4"><h2>${t("cardio.title")}</h2>
      <p class="hero-num">${num(L.level, 1)} <span class="small muted">${t("cardio.unit")}</span></p>
      <p class="small muted" style="margin:0 0 10px">${t("cardio.level_of", { n: L.n, d: C.rule.level_days })}</p>${chip}
      <p class="xs muted" style="margin:var(--s-3) 0 0">${L.stale_days > 21 ? esc(t("cardio.stale", { n: L.stale_days })) : t("cardio.what")}</p></section>
    <section class="card span-8"><h2>${t("cardio.chart")}<span class="aside legend">
        <span class="key"><i style="background:var(--ink-3);border-radius:50%"></i>${t("cardio.key.points")}</span>
        <span class="key"><i style="background:var(--c-mark);height:3px"></i>${t("cardio.key.line", { d: C.rule.level_days })}</span></span></h2>
      <div id="cchart" class="chart"></div>
      <details class="how"><summary>${t("ui.how")}</summary><p>${t("cardio.rule", { d: C.rule.level_days, a: C.rule.then_to, b: C.rule.then_from, c: num(C.rule.change, 1) })}</p></details></section>`;
}

export default {
  render(p) {
    if (!p.points.length) {
      return `<div class="head"><div><h1>${t("nav.weight_tab")}</h1></div></div><div class="grid"><section class="card span-12"><div class="empty">${t("body.empty")}</div></section>${cardioHtml(p)}</div>`;
    }
    const L = p.latest;
    const plan = p.plan;
    const facts = [
      [t("body.rate"), L.rate_per_week == null ? "—" : `${signed(L.rate_per_week, 2, " kg")} · ${signed(L.rate_pct, 1, "%")}`],
      plan ? [t("body.since_start", { day: day(plan.start_date, { weekday: false }) }), signed(L.since_start, 1, " kg")] : null,
      plan ? [t("body.to_go", { target: kg(plan.target_kg) }), kg(L.to_go)] : null,
      plan && L.eta ? [t("body.eta"), day(L.eta, { weekday: false })] : null,
      [t("body.weighed"), t("body.weighed_n", { n: p.weighed_days_14 })],
    ].filter(Boolean);
    return `<div class="head"><div><h1>${t("nav.weight_tab")}</h1><div class="sub">${t("body.sub")}</div></div></div>
      <div class="grid">
        <section class="card span-4"><h2>${t("body.weight")}</h2>
          <p class="hero-num">${kg(L.avg7)}</p>
          <p class="small muted" style="margin:0 0 10px">${t("body.avg7_on", { day: day(L.date) })}</p>
          ${L.status ? `<span class="chip ${STATUS[L.status]}">${t(`body.status.${L.status}`)}</span>` : `<span class="chip">${t("body.no_plan")}</span>`}
          <dl class="facts">${facts.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd class="num">${esc(v)}</dd></div>`).join("")}</dl>
        </section>
        <section class="card span-8"><h2>${t("body.chart")}<span class="aside legend">
            <span class="key"><i style="background:var(--ink-3);border-radius:50%"></i>${t("body.daily")}</span>
            <span class="key"><i style="background:var(--c-mark);height:3px"></i>${t("chart.avg7")}</span>
            ${plan ? `<span class="key"><i style="background:var(--accent-soft);border:1px solid var(--accent)"></i>${t("body.corridor", { lo: num(Math.min(...plan.weekly_loss_pct), 1), hi: num(Math.max(...plan.weekly_loss_pct), 1) })}</span>` : ""}</span></h2>
          <div id="wchart" class="chart"></div>
          <details class="how"><summary>${t("ui.how")}</summary><p>${t("body.rule")}</p></details></section>
        <section class="card span-8"><h2>${t("body.long")}<span class="aside">${t("body.long_note")}</span></h2><div id="mchart" class="chart"></div></section>
        <section class="card span-4"><h2>${t("body.waist")}</h2>${p.waist.length ? `<ul class="agenda">${p.waist.slice(-6).reverse().map((w) => `<li style="grid-template-columns:1fr auto"><span>${day(w.date)}</span><b class="num">${num(w.value, 1)} cm</b></li>`).join("")}</ul>` : `<p class="muted small">${t("body.no_waist")}</p>`}</section>
        ${cardioHtml(p)}
      </div>`;
  },
  mount(root, p) {
    const C = p.cardio;
    if (C.points.length) {
      const back = (iso, n) => { const d = new Date(`${iso}T12:00`); d.setDate(d.getDate() - n); return d.toISOString().slice(0, 10); };
      draw(root.querySelector("#cchart"), (w) => timeChart({ points: C.points, line: C.line.filter((x) => x.value != null) },
        { width: w, height: 220, first: back(p.day, C.rule.days - 1), last: p.day, fmt: (v) => num(v, 1), maxGap: 45 }));
    }
    if (!p.points.length) return;
    const first = p.points[0].date, last = p.corridor.length ? p.corridor[p.corridor.length - 1].date : p.day;
    const band = p.corridor.filter((c) => c.date >= first);
    draw(root.querySelector("#wchart"), (w) => timeChart({
      band, points: p.points.map((x) => ({ date: x.date, value: x.kg })), line: p.avg7.map((x) => ({ date: x.date, value: x.kg })),
      refs: p.plan ? [{ value: p.plan.target_kg, label: t("body.target", { kg: num(p.plan.target_kg, 1) }) }] : [],
    }, { width: w, height: 280, first, last, fmt: (v) => num(v, 1) }));
    const months = p.monthly.map((m) => ({ date: `${m.month}-15`, value: m.kg }));
    if (months.length > 1) {
      draw(root.querySelector("#mchart"), (w) => timeChart({ line: months, points: months }, { width: w, height: 200, first: months[0].date, last: months[months.length - 1].date, fmt: (v) => num(v, 1), maxGap: 45 }));
    }
  },
};
