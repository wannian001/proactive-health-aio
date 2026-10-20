import { esc } from "./charts.js?v=65d4646a27";
import { day, num, t, clock } from "./i18n.js?v=65d4646a27";
import { icon } from "./icons.js?v=65d4646a27";
import { rv } from "./i18n.js?v=65d4646a27";

export function forecastText(f, kind) {
  if (!f) return rv("fc_missing_current");
  if (f.status === "estimated") {
    if (f.resolution === "hour") return rv("fc_hours_range", { a: f.range_hours[0], b: f.range_hours[1] });
    const [a, b] = f.range_days;
    return rv(a === b ? "fc_days_one" : "fc_days_range", { a, b });
  }
  if (f.status === "at_target") return rv(kind === "energy" ? "fc_energy_at_target" : "fc_sore_at_target");
  if (f.status === "few_outcomes") return rv("fc_few_outcomes", { n: f.events });
  if (f.status === "insufficient") return rv("fc_insufficient", { n: f.n, min: 5 });
  return rv(`fc_${f.status}`);
}

export function forecastTarget(f, kind) {
  if (f?.target == null) return "";
  return rv(kind === "energy" ? "fc_target_energy_short" : "fc_target_sore_short", { n: num(f.target, Number.isInteger(f.target) ? 0 : 1), scale: f.scale || (kind === "energy" ? 5 : 3) });
}

function detail(f, kind) {
  if (!f || f.value == null) return "";
  if (f.method === "timestamped_intervals_v1") {
    const v = f.interval_validation;
    return `<details class="ov-basis"><summary>${rv("fc_basis")}</summary><p>${rv("fc_timed_method")}</p>
      <p>${rv("fc_timed_counts", { n: f.n, e: f.events, c: f.censored })}</p>
      <p>${f.matched_context?.length ? rv("fc_matched", { keys: f.matched_context.map(k => rv(`fc_context_${k}`)).join(t("ui.list_sep")) }) : rv("fc_broad")}</p>
      <p>${rv(v?.observed ? "fc_interval_validation" : "fc_validation_pending", { n: v?.observed || 0, e: num(v?.mean_interval_error_hours, 1) })}</p>
      <p>${rv("fc_timed_baseline")}</p><p>${rv("fc_boundary")}</p></details>`;
  }
  const stats = f.n ? `<p>${rv("fc_counts", { n: f.n, e: f.events, c: f.censored, z: f.no_followup })}</p>` : "";
  const target = f.target == null ? "" : `<p>${rv(kind === "energy" ? "fc_energy_target" : "fc_sore_target", { v: num(f.target, 1) })}</p>`;
  const context = f.matched_context?.length ? rv("fc_matched", { keys: f.matched_context.map(k => rv(`fc_context_${k}`)).join(t("ui.list_sep")) }) : rv("fc_broad");
  const validation = f.validation;
  const validationText = validation?.observed ? rv("fc_validation", {
    n: validation.observed, h: validation.inside_range, e: num(validation.mean_absolute_days, 1)
  }) : rv("fc_validation_pending");
  const records = f.evidence?.length ? `<ul class="ov-forecast-history">${f.evidence.slice(-8).reverse().map(e =>
    `<li>${esc(day(e.start, { weekday: false }))} · ${rv(e.event ? "fc_observed" : "fc_censored", { n: e.days })}</li>`).join("")}</ul>` : "";
  return `<details class="ov-basis"><summary>${rv("fc_basis")}</summary>${target}${stats}<p>${context}</p>
    <p>${validationText}</p>${f.phase_days ? `<p>${(f.phase_days >= 9 ? rv("fc_phase_long") : rv("fc_phase", { n: f.phase_days }))}</p>` : ""}${records}<p>${rv("fc_method")}</p><p>${rv("fc_boundary")}</p></details>`;
}

export function forecastHtml(p, kind, { draft = false, region = null } = {}) {
  if (draft) return `<p class="ov-forecast-note" role="status">${rv("fc_draft")}</p>`;
  const pack = p.forecast;
  if (!pack) return `<p class="ov-forecast-note">${rv("fc_missing_current")}</p>`;
  const label = rv(kind === "energy" ? "fc_energy_title" : "fc_sore_title");
  let entries;
  if (kind === "energy") entries = [[null, pack.energy]];
  else if (region) entries = [[region, Object.keys(p.current_ratings?.soreness || {}).length && !(region in p.current_ratings.soreness) ? {status:"missing_current", value:null} : pack.soreness[region]]];
  else entries = Object.entries(Object.keys(p.current_ratings?.soreness || {}).length ? p.current_ratings.soreness : pack.soreness).filter(([, f]) => f.value > 0);
  if (!region && kind === "soreness" && entries.length > 1) entries = entries.sort((a,b) => b[1].value - a[1].value).slice(0,1);
  if (!entries.length) {
    const f = Object.values(Object.keys(p.current_ratings?.soreness || {}).length ? p.current_ratings.soreness : pack.soreness)[0];
    return `<p class="ov-forecast-note">${label} · ${esc(forecastText(f, kind))}</p>`;
  }
  const hasEstimate = entries.some(([, f]) => f.status === "estimated");
  return `<section class="ov-forecast${hasEstimate ? " has-estimate" : ""}" aria-label="${label}">
    <h3>${label}<span>${rv("fc_reference")}${pack.demo ? ` · ${rv("fc_demo")}` : ""}</span></h3>
    ${entries.map(([key, f]) => `<div class="ov-forecast-item">
      ${f.status === "estimated" ? `<div class="ov-prediction-band">${icon("clock", 24)}<div>
        <p class="ov-forecast-result">${key ? `<span>${t(`sore.region.${key}`)}</span>` : ""}<span>${esc(forecastText(f, kind))}</span></p>
        <strong class="ov-prediction-target">${esc(forecastTarget(f, kind))}</strong></div></div>`
        : `<p class="ov-forecast-result"><strong>${esc(forecastText(f, kind))}</strong></p>`}
      ${f.range_dates ? `<p class="ov-secondary">${f.range_dates.map(d => esc(day(d, { weekday: false }))).join(" – ")}</p>` : ""}
      ${f.range_timestamps ? `<p class="ov-secondary">${f.range_timestamps.map(d => `${esc(day(d, { weekday: false }))} ${esc(clock(d))}`).join(" – ")}</p>` : ""}
      ${detail(f, kind)}</div>`).join("")}</section>`;
}
