// "What has tended to help the next day": one row per condition, the next day's HRV, resting heart rate or self-rated
// energy on days after doing it against days after not, with its 95% interval. Shared by the Review page (the whole
// list) and the Today page (one summary line that links to it). compareHtml draws the same picture for the
// "how the body answered" cards on Recovery and Stimulation.
import { draw, esc, interval } from "../charts.js?v=93bad7f144";
import { num, signed, t } from "../i18n.js?v=93bad7f144";
import { STATE_ICON } from "../icons.js?v=93bad7f144";

export function effectLabel(r) {
  const p = r.params || {};
  return t(`eff.${r.key}`, { min: num(p.min), hours: num(p.hours), clock: p.clock });
}

// the conditions that came out as a significant effect for the better on any outcome, each named once
export function helping(e) {
  const seen = new Map();
  e.outcomes.forEach((o) => (e.rows[o] || []).forEach((r) => {
    const sign = e.better[o] === "lower" ? -1 : 1;
    if (r.status === "ok" && r.detected && sign * r.diff > 0 && !seen.has(r.key)) seen.set(r.key, r);
  }));
  return [...seen.values()];
}

export function effectsHtml(e) {
  const seg = e.outcomes.map((o, i) => `<button type="button" data-outcome="${o}" aria-pressed="${i === 0}">${t(`out.${o}`)}</button>`).join("");
  return `<h2>${t("effects.title")}<span class="seg" role="group" aria-label="${esc(t("effects.outcome"))}">${seg}</span></h2>
    <div class="effects" id="effects"></div>
    <details class="how"><summary>${t("ui.how")}</summary><p>${t("effects.rule")}</p></details>`;
}

function effectRows(e, outcome) {
  const rows = e.rows[outcome] || [];
  const unit = e.units[outcome];
  const sign = e.better[outcome] === "lower" ? -1 : 1;  // plotted so that right = a better next day
  const domain = Math.max(0.5, ...rows.filter((r) => r.status === "ok").map((r) => Math.max(Math.abs(r.low), Math.abs(r.high))));
  const fmt = (v) => (unit === "%" ? signed(v, 1, "%") : signed(v, 1, unit === "bpm" ? ` ${t("unit.bpm")}` : ` ${t("unit.points")}`));
  const head = `<div class="effect effect-head" aria-hidden="true"><span>${t("effects.col.what")}</span>
    <span class="axis"><span>${t("effects.col.worse")}</span><span>${t("effects.col.better")}</span></span><span>${t("effects.col.diff")}</span></div>`;
  return head + rows.map((r, i) => {
    const ok = r.status === "ok";
    const good = ok && sign * r.diff > 0;
    const verdict = !ok ? `<span class="xs muted">${t("eff.too_few")}</span>`
      : `<span class="chip ${r.detected ? (good ? "good" : "bad") : ""}">${t(r.detected ? "eff.detected" : "eff.not_detected")}</span>`;
    const read = ok ? t(`eff.read.${outcome}.${r.diff >= 0 ? "higher" : "lower"}`, { v: num(Math.abs(r.diff), 1) }) : "";
    const range = ok ? t("eff.range", { low: fmt(r.low), high: fmt(r.high) }) : "";
    return `<div class="effect" ${ok ? `data-tip="${esc(`${read} · ${range}`)}"` : ""}>
      <div class="what">${esc(effectLabel(r))}<span>${t("eff.days", { yes: r.yes_days, no: r.no_days })}</span></div>
      <div class="ivl" data-i="${i}" data-domain="${domain}" data-sign="${sign}"></div>
      <div class="verdict-cell">${verdict}${ok ? `<span class="xs muted read">${esc(read)}</span>` : ""}</div>
      ${ok ? `<span class="sr">${esc(`${read}, ${range}`)}</span>` : ""}</div>`;
  }).join("");
}

export function mountEffects(root, e) {
  const box = root.querySelector("#effects");
  if (!box) return;
  const show = (outcome) => {
    box.innerHTML = effectRows(e, outcome);
    const rows = e.rows[outcome] || [];
    box.querySelectorAll(".ivl").forEach((el) => draw(el, (w) => interval(rows[el.dataset.i], Number(el.dataset.domain), { width: w, flip: el.dataset.sign === "-1" })));
    root.querySelectorAll("[data-outcome]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.outcome === outcome)));
  };
  root.querySelectorAll("[data-outcome]").forEach((b) => { b.onclick = () => show(b.dataset.outcome); });
  if (e.outcomes.length) show(e.outcomes[0]);
}

// The night or next morning after one kind of day against the others, one row per outcome: the difference with its
// 95% interval against zero, right = better, as in "what has tended to help". The outcomes differ in unit, so each
// row has its own scale; what the picture shows is the direction and whether the interval crosses zero. The numbers
// are in each row's tooltip (and read out to screen readers). rows: the module's rows; name(r), text(r) (the
// numbers in words) and better(r) ("higher" or "lower").
export function compareHtml(rows, { name, text, better }) {
  const head = `<div class="effect effect-head" aria-hidden="true"><span></span>
    <span class="axis"><span>${t("cmp.worse")}</span><span>${t("cmp.better")}</span></span><span></span></div>`;
  return `<div class="effects compare">${head}${rows.map((r, i) => {
    const ok = r.status === "ok", good = ok && (better(r) === "lower" ? r.diff < 0 : r.diff > 0);
    const chip = !ok ? `<span class="chip">${t("stim.too_few")}</span>`
      : r.detected ? `<span class="chip ${good ? "good" : "bad"}">${STATE_ICON[good ? "good" : "bad"]}${t("stim.seen")}</span>`
        : `<span class="chip">${t("stim.not_seen")}</span>`;
    const words = text(r);
    return `<div class="effect" data-tip="${esc(words)}"><div class="what">${esc(name(r))}<span>${t("cmp.days", { yes: r.yes_days, no: r.no_days })}</span></div>
      <div class="ivl" data-cmp="${i}" data-sign="${better(r) === "lower" ? -1 : 1}"></div>
      <div class="verdict-cell">${chip}</div><span class="sr">${esc(words)}</span></div>`;
  }).join("")}</div>`;
}

export function mountCompare(box, rows) {
  box.querySelectorAll(".ivl[data-cmp]").forEach((el) => {
    const r = rows[el.dataset.cmp];
    const domain = r.status === "ok" ? Math.max(Math.abs(r.low), Math.abs(r.high), Math.abs(r.diff)) * 1.15 || 1 : 1;
    draw(el, (w) => interval(r, domain, { width: w, flip: el.dataset.sign === "-1" }));
  });
}
