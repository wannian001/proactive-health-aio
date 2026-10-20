// Follow-up (#followup): did yesterday's advice happen, checked against the data (nothing to tick); the last 14 days
// of each piece of advice; and, for advice that keeps not happening, other ways to do it with the person's own
// numbers instead of the same reminder again; and "tomorrow will be better": what has gone with a better next day
// (the list that used to be on Weekly review). The rules are in modules/followup.py.
import { draw, esc } from "../charts.js?v=65d4646a27";
import { clock, day, dur, num, shortDay, t } from "../i18n.js?v=65d4646a27";
import { COLOR, icon, STATE_ICON } from "../icons.js?v=65d4646a27";
import { effectsHtml, mountEffects, mountResponses, screenResponseHtml, trainingResponseHtml } from "./effects.js?v=65d4646a27";
import { TODO_ICON, todoTitle } from "./today.js?v=65d4646a27";
import { activeHtml, mountRestore, triedHtml } from "../restore-ui.js?v=65d4646a27";

const hours = (h) => num(h, Number.isInteger(h) ? 0 : 1);

function resultChip(x) {
  if (!x.checked) return `<span class="chip">${t("fu.not_checked")}</span>`;
  if (x.met === true) return `<span class="chip good">${STATE_ICON.good}${t("fu.kept")}</span>`;
  if (x.met === false) return `<span class="chip bad">${STATE_ICON.bad}${t("fu.missed")}</span>`;
  return `<span class="chip">${t("fu.no_record")}</span>`;
}

// what the data shows for one piece of advice, in a few words
function fact(x) {
  if (!x.checked) return t("fu.fact.training");
  const f = x.fact;
  if (!f) return t("fu.fact.none");
  switch (x.key) {
    case "asleep_by": return x.met ? t("fu.fact.asleep_ok", { clock: clock(f.asleep) }) : t("fu.fact.asleep_late", { clock: clock(f.asleep), d: dur(f.late_min) });
    case "phone_away": return t("fu.fact.phone_away", { d: dur(f.minutes) });
    case "late_meal": return t("fu.fact.late_meal", { clock: clock(f.last), h: num(f.gap_h, 1) });
    case "protein": return t("fu.fact.protein", { g: num(f.grams) });
    case "kcal": return t("fu.fact.kcal", { kcal: num(f.kcal) });
    case "fun_cap": return t("fu.fact.fun_cap", { d: dur(f.minutes) });
    default: return "";
  }
}

const adviceIcon = (x, size) => `<span class="todo-icon" style="color:${COLOR[TODO_ICON[x.domain]] || "var(--ink-2)"}">${icon(TODO_ICON[x.domain], size)}</span>`;

function yesterdayHtml(p) {
  const y = p.yesterday;
  const score = p.yesterday_known ? t("fu.score", { k: p.yesterday_kept, m: p.yesterday_known }) : t("fu.score_none");
  const body = y.items.length
    ? `<ol class="todo">${y.items.map((x) => `<li><div class="todo-item">${adviceIcon(x, 20)}
        <span class="todo-body"><b>${esc(todoTitle(x))}</b><span class="row" style="gap:8px;flex-wrap:wrap">${resultChip(x)}<span class="small muted">${esc(fact(x))}</span></span></span></div></li>`).join("")}</ol>`
    : `<p class="lede" style="font-size:var(--t-lg);margin:0">${t("fu.yesterday_none")}</p>`;
  return `<section class="card span-12"><span class="eyebrow">${t("fu.yesterday")} · ${esc(day(y.date))}</span>
    ${y.items.length ? `<p class="lede" style="margin:6px 0 var(--s-4)">${esc(score)}</p>` : ""}${body}</section>`;
}

// 14 days in a row: done (filled), not done (ring), given without a record (dash), not given that day (a faint dot)
function adviceDots(days, { width, height = 20 }) {
  const n = Math.max(1, days.length), gap = 6, gaps = Math.floor((n - 1) / 7);
  const slot = (width - gaps * gap) / n;
  const r = Math.max(2.5, Math.min(5, slot / 2 - 1.5));
  const cy = height / 2;
  return `<svg viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" role="img">${days.map((d, i) => {
    const cx = (slot * i + slot / 2 + Math.floor(i / 7) * gap).toFixed(1);
    const word = !d.given ? t("fu.not_given") : d.met === true ? t("fu.kept") : d.met === false ? t("fu.missed") : t("fu.no_record");
    const mark = !d.given ? `<circle cx="${cx}" cy="${cy}" r="1.5" fill="var(--line-2)"/>`
      : d.met === true ? `<circle cx="${cx}" cy="${cy}" r="${r.toFixed(1)}" fill="var(--c-mark)"/>`
        : d.met === false ? `<circle cx="${cx}" cy="${cy}" r="${(r - 0.8).toFixed(1)}" fill="none" stroke="var(--c-mark)" stroke-width="1.5"/>`
          : `<line x1="${(cx - r + 1).toFixed(1)}" x2="${(+cx + r - 1).toFixed(1)}" y1="${cy}" y2="${cy}" stroke="var(--ink-3)" stroke-width="2" stroke-linecap="round"/>`;
    return `<g data-tip="${esc(`${shortDay(d.date)} · ${word}`)}"><rect x="${(cx - slot / 2).toFixed(1)}" y="0" width="${slot.toFixed(1)}" height="${height}" fill="transparent"/>${mark}</g>`;
  }).join("")}</svg>`;
}

function fortnight(p, row) {
  const given = Object.fromEntries(row.dots.map((d) => [d.date, d.met]));
  return p.dates.map((date) => (date in given ? { date, given: true, met: given[date] } : { date, given: false }));
}

function daysHtml(p) {
  if (!p.rows.length) return "";
  const rows = p.rows.map((r, i) => `<div class="goal-row fu-row">
      <div class="goal-name">${adviceIcon(r, 16)}<b>${t(`fu.name.${r.key}`)}</b></div>
      <div class="goal-dots" data-i="${i}"></div>
      <div class="goal-count"><b class="num">${!r.checked ? t("fu.not_checked") : r.known ? t("fu.count", { k: r.kept, m: r.known }) : t("fu.count_none")}</b>
        <span class="xs muted">${t("fu.given", { n: r.given })}</span></div></div>`).join("");
  return `<section class="card span-12"><h2>${t("fu.days_title")}<span class="aside">${t("fu.days_sub")}</span></h2>
    <div class="legend" style="margin:0 0 var(--s-3)"><span class="key"><i style="background:var(--c-mark);border-radius:50%"></i>${t("fu.kept")}</span>
      <span class="key"><i style="background:none;border:1.5px solid var(--c-mark);border-radius:50%"></i>${t("fu.missed")}</span>
      <span class="key"><i style="background:var(--ink-3);height:2px"></i>${t("fu.no_record")}</span>
      <span class="key"><i style="background:var(--line-2);width:4px;height:4px;border-radius:50%"></i>${t("fu.not_given")}</span></div>
    <div class="goal-rows">${rows}</div></section>`;
}

function wayText(key, w) {
  const q = w.params || {};
  if (key === "late_meal" && w.kind === "if_then" && !q.clock) return t("fu.way.if_then.late_meal_h", { h: hours(q.hours) });
  return t(`fu.way.${w.kind}.${key}`, { clock: q.clock || "—", h: q.hours != null ? hours(q.hours) : "—", g: num(q.g), kcal: num(q.kcal) });
}

function waysHtml(p) {
  const stuck = p.rows.filter((r) => r.stuck);
  const sub = t("fu.ways_sub", { missed: p.rule.stuck_missed, of: p.rule.stuck_of });
  const body = stuck.length ? stuck.map((r) => `<div class="fu-ways">
      <div class="goal-name">${adviceIcon(r, 16)}<b>${t(`fu.name.${r.key}`)}</b>
        <span class="chip bad">${STATE_ICON.bad}${t("fu.count", { k: r.kept, m: r.known })}</span></div>
      <ol>${r.ways.map((w) => `<li><span class="eyebrow">${t(`fu.kind.${w.kind}`)}</span><span>${esc(wayText(r.key, w))}</span></li>`).join("")}</ol>
      ${r.ways.some((w) => w.kind === "smaller") ? `<p class="small" style="margin:0"><a href="#goals">${t("fu.goals_link")}</a></p>` : ""}</div>`).join("")
    : `<p class="lede" style="font-size:var(--t-lg);margin:0">${t("fu.ways_none", { missed: p.rule.stuck_missed, of: p.rule.stuck_of })}</p>`;
  return `<section class="card span-12"><h2>${t("fu.ways_title")}</h2>${stuck.length ? `<p class="small muted" style="margin:0 0 var(--s-3)">${esc(sub)}</p>` : ""}${body}
    <details class="how"><summary>${t("ui.how")}</summary><p>${t("fu.why_ways")}</p></details></section>`;
}

export default {
  render(p) {
    return `<div class="head"><div><h1>${t("nav.followup")}</h1><div class="sub">${t("fu.sub")}</div></div></div>
      <div class="grid">
        ${p.restore ? `<section class="card span-12">${activeHtml(p.restore)}${triedHtml(p.restore)}<p class="small"><a href="#restore">${t("nav.restore")} →</a></p></section>` : ""}
        ${yesterdayHtml(p)}
        ${waysHtml(p)}
        ${daysHtml(p)}
        <section class="card span-12" id="better">${effectsHtml(p.effects)}${trainingResponseHtml(p.training_response, p.training_days)}${screenResponseHtml(p.screen_response)}</section>
        <section class="card span-12"><details class="how"><summary>${t("ui.how")}</summary><p>${t("fu.rule")}</p></details></section>
      </div>`;
  },
  mount(root, p) {
    mountRestore(root);
    mountEffects(root, p.effects);
    mountResponses(root, p.training_response, p.screen_response);
    root.querySelectorAll(".fu-row .goal-dots").forEach((el) => { const r = p.rows[el.dataset.i]; draw(el, (w) => adviceDots(fortnight(p, r), { width: w })); });
  },
};
