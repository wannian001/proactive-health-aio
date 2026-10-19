import { esc } from "./charts.js";
import { day, num, rv, t, toDate, wtype } from "./i18n.js";
import { mountBody } from "./recovery-model.js";
import { forecastHtml, forecastText, forecastTarget } from "./recovery-forecast.js";

// All figures below come from existing records. No rescaling and no synthetic ETA. Nothing is written from here:
// choosing a region and a level fills in the "How you are right now" card below, which saves.
export function sorenessSummary(levels, known) {
  if (!known) return { value: null, regions: [], count: null };
  const entries = Object.entries(levels).filter(([, v]) => Number.isFinite(v) && v > 0);
  const value = Math.max(0, ...entries.map(([, v]) => v));
  return { value, count: entries.length, regions: entries.filter(([, v]) => v === value).map(([key]) => key) };
}

function ratingText(value, forecast) { return forecast?.value_range ? forecast.value_range.map(v => num(v)).join("–") : num(value); }

function ring(value, max, label, caption, kind, forecast) {
  const window = forecast?.status === "estimated" ? (forecast.range_hours || forecast.range_days?.map(d => d * 24)) : null;
  const horizon = window ? (window[1] <= 24 ? 24 : 168) : null;
  const midpoint = window ? (window[0] + window[1]) / 2 / horizon * 100 : 0;
  const valid = Number.isFinite(value), fraction = valid ? Math.max(0, Math.min(1, value / max)) : 0;
  const reading = ratingText(value, forecast);
  return `<div class="ov-gauge ${kind}" role="img" aria-label="${esc(`${label}: ${valid ? `${reading}/${max}` : rv("unknown")}`)}">
    <svg viewBox="0 0 180 180" aria-hidden="true">${window ? `<circle class="ov-time-track" cx="90" cy="90" r="82"/><circle class="ov-time-arc" cx="90" cy="90" r="82" pathLength="100" stroke-dasharray="${midpoint} 100" transform="rotate(-90 90 90)"/>` : ""}
      <circle class="ov-track" cx="90" cy="90" r="70"/>
      ${fraction > 0 ? `<circle class="ov-arc" cx="90" cy="90" r="70" pathLength="100" stroke-dasharray="${fraction * 100} 100" transform="rotate(-90 90 90)"/>` : ""}</svg>
    <div class="ov-gauge-label"><span>${esc(label)}</span><div><b>${valid ? reading : "—"}</b>${valid ? `<small>/${max}</small>` : ""}</div><span>${esc(caption)}</span>${window ? `<span class="ov-time-scale">${rv("fc_ring_time", { h: horizon })}</span>` : ""}</div></div>`;
}



function currentSore(p) { return p.current_ratings?.soreness || {}; }
function timedSore(p) { return Object.keys(currentSore(p)).length > 0; }
function colorLevels(p, levels) {
  if (!timedSore(p)) return levels;
  return Object.fromEntries(Object.entries(currentSore(p)).map(([r, f]) => [r, f.value ? Math.ceil(f.value * 3 / 10) : 0]));
}

function soreCard(p, levels = p.soreness.levels, draft = false) {
  const timed = timedSore(p) && !draft;
  if (timed) levels = Object.fromEntries(Object.entries(currentSore(p)).map(([r,f]) => [r,f.value]));
  const known = timed || p.soreness.today || draft, S = sorenessSummary(levels, known);
  const names = S.regions.map(r => t(`sore.region.${r}`)).join(t("ui.list_sep"));
  const f = S.regions.length ? p.forecast?.soreness[S.regions[0]] : null;
  return `${ring(S.value, timed ? 10 : 3, rv("worst"), timed ? rv("soreness") : S.value == null ? rv("unknown") : t(`sore.level.${S.value}`), "ov-sore", draft ? null : f)}
    <div class="ov-card-copy"><div class="ov-card-title"><h2>${t("sore.title")}</h2><span class="ov-tag">${rv("current")}</span></div>
      <p class="ov-description">${S.value == null ? rv("noToday") : S.value === 0 ? rv("noSoreness") : esc(rv("most", { regions: names }))}</p>
      <p class="ov-secondary">${draft ? rv("draft") : S.value == null ? (p.soreness.latest ? esc(rv("latestSore", { date: day(p.soreness.latest) })) : rv("selectPrompt")) : `${rv("count", { n: S.count })} · ${esc(day(p.day))}${timed ? ` · ${rv("newScale")}` : ` · ${t("now.sore_scale")}`}`}</p>
      ${forecastHtml(p, "soreness", { draft })}</div>`;
}

function energyCard(p) {
  const current = p.current_ratings?.energy, self = p.self, value = current ? current.value : self?.energy;
  const f = p.forecast?.energy;
  return `${ring(value, current ? 10 : 5, rv("self"), rv("energy"), "ov-energy", f)}
    <div class="ov-card-copy"><div class="ov-card-title"><h2>${rv("energy")}</h2><span class="ov-tag">${rv("current")}</span></div>
      ${value == null ? `<p class="ov-description">${rv("noEnergy")}</p>` : ""}
      <p class="ov-secondary">${current ? `${rv("latest", { date: day(current.recorded_at) })} · ${rv("newScale")}` : self && value != null ? `${esc(rv("latest", { date: day(self.date) }))}${self.date !== p.day ? ` · ${rv("historicalEnergy")}` : ""} · ${rv("legacyScale")}` : rv("energySource")}</p>
      ${forecastHtml(p, "energy")}<a class="ov-text-link" href="#recovery/now">${t("now.link")} ↓</a></div>`;
}

export function overviewHtml(p) {
  return `<section class="rec-overview" aria-label="${rv("title")}"><div class="ov-layout">
    <section class="ov-body-panel"><div class="ov-body-head"><h2>${rv("muscles")}</h2><div class="ov-view-switch" role="group" aria-label="${rv("muscles")}">
      <button type="button" data-ov-view="sore" aria-pressed="true">${rv("soreness")}</button><button type="button" data-ov-view="trained" aria-pressed="false">${rv("trained")}</button></div></div>
      <div class="ov-body-stage"><p class="ov-model-message">${rv("loading")}</p></div>
      <div class="ov-rotation"><button type="button" data-ov-turn="-1" aria-label="${rv("rotateLeft")}">↶</button><span>${rv("rotate")}</span><button type="button" data-ov-turn="1" aria-label="${rv("rotateRight")}">↷</button><button type="button" class="ov-front">${rv("front")}</button></div>
      <div class="ov-legend"><span class="ov-sore-legend"><i class="ov-yellow-key"></i>${rv("light")} → ${rv("heavy")}</span><span class="ov-sore-legend"><i class="ov-none-key"></i>${rv("none")}</span><span class="ov-trained-legend" hidden><i class="ov-trained-key"></i>${rv("trainingLegend")}</span><span><i class="ov-unknown-key"></i>${rv("unknown")}</span></div>
      <div class="ov-region-picker"><label for="ov-region">${rv("select")}</label><select id="ov-region"><option value="">${rv("choose")}</option>${p.regions.map(r => `<option value="${esc(r)}">${t(`sore.region.${r}`)}</option>`).join("")}</select></div>
      <div class="ov-selection" aria-live="polite"><p>${rv("selectPrompt")}</p></div>
      <details class="ov-credit"><summary>${rv("modelCredit")}</summary><p>${rv("modelNote")}</p><a href="models/recovery/ILLUSTRATION.md" target="_blank" rel="noopener">${rv("modelCredit")} ↗</a></details>
    </section>
    <div class="ov-states"><section class="ov-metric ov-sore-card">${soreCard(p)}</section><section class="ov-metric ov-energy-card">${energyCard(p)}</section></div>
    </div></section>`;
}

export function mountOverview(root, p, { onLevel, openEditor }) {
  const wrap = root.querySelector(".rec-overview");
  let levels = { ...(p.soreness.today ? p.soreness.levels : {}) }, draft = false, selected = "", view = "sore", model;
  const recent = p.after.days.filter(d => (toDate(p.day) - toDate(d.date)) / 86400000 < 7);
  const trained = new Set(recent.flatMap(d => d.trained));
  function selection() {
    const el = wrap.querySelector(".ov-selection");
    const editing = el.querySelector(".ov-local-edit")?.open;
    if (!selected) { el.innerHTML = `<p>${rv("selectPrompt")}</p>`; return; }
    const timed = timedSore(p) && !draft;
    const known = timed ? selected in currentSore(p) : p.soreness.today || draft, value = timed ? currentSore(p)[selected]?.value : known ? (levels[selected] || 0) : null;
    const session = recent.flatMap(d => d.sessions.filter(s => s.note?.regions.includes(selected)).map(s => ({ ...s, date: d.date })))[0];
    el.innerHTML = `<div class="ov-selection-head"><b>${esc(rv("selected", { region: t(`sore.region.${selected}`) }))}</b><span>${value == null ? rv("unknown") : timed ? `${ratingText(value, currentSore(p)[selected])}/10` : t(`sore.level.${value}`)}</span></div>
      <p>${session ? esc(rv("lastTrained", { date: day(session.date), type: wtype(session.type) })) : rv("notTrained")}</p>
      ${view === "trained" ? `<p>${rv("trainingHint")}</p>` : ""}
      ${forecastHtml(p, "soreness", { draft, region: selected })}
      <details class="ov-local-edit"><summary>${rv("edit")}</summary><div class="ov-levels" role="group" aria-label="${t(`sore.region.${selected}`)}">${[0, 1, 2, 3].map(v => `<button type="button" data-ov-level="${v}" aria-pressed="${known && v === value}">${t(`sore.level.${v}`)}</button>`).join("")}</div>
      <button type="button" class="ov-open-editor">${draft ? rv("draftHelp") : rv("editor")} →</button></details>`;
    el.querySelector(".ov-local-edit").open = !!editing;
    el.querySelectorAll("[data-ov-level]").forEach(b => { b.onclick = () => {
      const level = Number(b.dataset.ovLevel); onLevel(selected, level);
      el.querySelector(`[data-ov-level="${level}"]`)?.focus();
    }; });
    el.querySelector(".ov-open-editor").onclick = openEditor;
  }
  const repaint = () => {
    const timed = timedSore(p) && !draft;
    const annotations = Object.fromEntries(p.regions.map(r => {
      const f = p.forecast?.soreness[r];
      const known = timed ? r in currentSore(p) : p.soreness.today || draft;
      return [r, `${t(`sore.region.${r}`)} · ${known ? draft ? `${levels[r] || 0}/3 · ${rv("draft")}` : `${ratingText(f?.value, f)}/${f?.scale || 3}` : rv("unknown")}${known && f?.status === "estimated" && !draft ? `\n${forecastText(f, "soreness")}\n${forecastTarget(f, "soreness")}` : ""}`];
    }));
    model?.update({ levels: timed ? colorLevels(p, levels) : levels, known: timed || p.soreness.today || draft,
      knownRegions: timed ? Object.keys(currentSore(p)) : null, selected, view, annotations }); selection();
  };
  const select = region => { selected = region; wrap.querySelector("#ov-region").value = region; repaint(); };
  wrap.querySelector("#ov-region").onchange = event => select(event.target.value);
  wrap.querySelectorAll("[data-ov-view]").forEach(b => { b.onclick = () => {
    view = b.dataset.ovView;
    wrap.querySelectorAll("[data-ov-view]").forEach(x => x.setAttribute("aria-pressed", String(x.dataset.ovView === view)));
    wrap.querySelectorAll(".ov-sore-legend").forEach(x => { x.hidden = view !== "sore"; }); wrap.querySelector(".ov-trained-legend").hidden = view !== "trained"; repaint();
  }; });
  wrap.querySelectorAll("[data-ov-turn]").forEach(b => { b.onclick = () => model?.rotate(Number(b.dataset.ovTurn)); });
  wrap.querySelector(".ov-front").onclick = () => model?.reset();
  mountBody(wrap.querySelector(".ov-body-stage"), { regions: p.regions, levels, known: p.soreness.today, trained, onSelect: select,
    onUnsupported() { selected = ""; wrap.querySelector("#ov-region").value = ""; repaint(); wrap.querySelector(".ov-selection").innerHTML = `<p>${rv("untracked")}</p>`; }
  }).then(result => { model = result; repaint(); });
  return { setLevels(next, changed = true) { levels = { ...next }; draft = changed; wrap.querySelector(".ov-sore-card").innerHTML = soreCard(p, levels, draft); repaint(); } };
}
