import { esc, draw, spark } from "./charts.js";
import { day, num, measure, t, toDate, wtype } from "./i18n.js";
import { icon } from "./icons.js";
import { rv } from "./recovery-copy.js";
import { mountBody } from "./recovery-model.js";

// All figures below come from existing records. No rescaling and no synthetic ETA.
export function sorenessSummary(levels, known) {
  if (!known) return { value: null, regions: [], count: null };
  const entries = Object.entries(levels).filter(([, v]) => Number.isFinite(v) && v > 0);
  const value = Math.max(0, ...entries.map(([, v]) => v));
  return { value, count: entries.length, regions: entries.filter(([, v]) => v === value).map(([key]) => key) };
}

function ring(value, max, label, caption, kind) {
  const valid = Number.isFinite(value), fraction = valid ? Math.max(0, Math.min(1, value / max)) : 0;
  return `<div class="ov-gauge ${kind}" role="img" aria-label="${esc(`${label}: ${valid ? `${value}/${max}` : rv("unknown")}`)}">
    <svg viewBox="0 0 180 180" aria-hidden="true"><circle class="ov-time-track" cx="90" cy="90" r="82"/>
      <circle class="ov-track" cx="90" cy="90" r="70"/>
      ${fraction > 0 ? `<circle class="ov-arc" cx="90" cy="90" r="70" pathLength="100" stroke-dasharray="${fraction * 100} 100" transform="rotate(-90 90 90)"/>` : ""}</svg>
    <div class="ov-gauge-label"><span>${esc(label)}</span><div><b>${valid ? num(value) : "—"}</b>${valid ? `<small>/${max}</small>` : ""}</div><span>${esc(caption)}</span></div></div>`;
}

function estimate(kind) {
  return `<div class="ov-estimate">${icon("clock", 21)}<div><span>${rv("forecast")}</span><b>${rv("unavailable")}</b></div></div>
    <details class="ov-basis"><summary>${rv("basis")}</summary><p>${rv("noForecast")}</p><p>${rv(kind === "sore" ? "soreBasis" : "energyBasis")}</p>
      <p>${rv(kind === "sore" ? "scale" : "energySource")}</p></details>`;
}

function soreCard(p, levels = p.soreness.levels, draft = false) {
  const known = p.soreness.today || draft, S = sorenessSummary(levels, known);
  const names = S.regions.map(r => t(`sore.region.${r}`)).join(t("ui.list_sep"));
  return `${ring(S.value, 3, rv("worst"), S.value == null ? rv("unknown") : t(`sore.level.${S.value}`), "ov-sore")}
    <div class="ov-card-copy"><div class="ov-card-title"><h2>${t("sore.title")}</h2><span class="ov-tag">${rv("whole")}</span></div>
      <p class="ov-description">${S.value == null ? rv("noToday") : S.value === 0 ? rv("noSoreness") : esc(rv("most", { regions: names }))}</p>
      <p class="ov-secondary">${draft ? rv("draft") : S.value == null ? (p.soreness.latest ? esc(rv("latestSore", { date: day(p.soreness.latest) })) : rv("selectPrompt")) : `${rv("count", { n: S.count })} · ${esc(day(p.day))}`}</p>
      ${estimate("sore")}</div>`;
}

function energyCard(p) {
  const self = p.self, value = self?.energy;
  return `${ring(value, 5, rv("self"), rv("energy"), "ov-energy")}
    <div class="ov-card-copy"><div class="ov-card-title"><h2>${rv("energy")}</h2><span class="ov-tag">${rv("current")}</span></div>
      <p class="ov-description">${value == null ? rv("noEnergy") : rv("global")}</p>
      <p class="ov-secondary">${self && value != null ? `${esc(rv("latest", { date: day(self.date) }))}${self.date !== p.day ? ` · ${rv("historicalEnergy")}` : ""}` : rv("energySource")}</p>
      ${estimate("energy")}</div>`;
}

function cardioCard(p) {
  const C = p.cardio, L = C?.latest;
  return `<section class="ov-metric ov-cardio"><div class="ov-mini-trend"><div class="ov-spark"></div><span>${t("cardio.chart")}</span></div>
    <div class="ov-card-copy"><div class="ov-card-title"><h2>${t("cardio.short")}</h2><span class="ov-tag">${rv("longTerm")}</span></div>
      ${L ? `<div class="ov-cardio-read"><strong>${num(L.level, 1)}</strong><span>mL/kg/min</span><span class="ov-cardio-change">${L.state ? t(`cardio.state.${L.state}`, { v: num(Math.abs(L.change), 1) }) : t("cardio.no_then")}</span></div>
      <p class="ov-secondary">${t("cardio.level_of", { n: L.n, d: C.rule.level_days })} · ${esc(rv("latest", { date: day(L.date, { weekday: false }) }))}</p>
      ${L.stale_days > 21 ? `<p class="ov-secondary">${t("cardio.stale", { n: L.stale_days })}</p>` : ""}` : `<p class="ov-secondary">${t("cardio.empty")}</p>`}
      <a class="ov-text-link" href="#body">${rv("trend")} ↗</a></div></section>`;
}

function related(p) {
  const rows = p.recovery.metrics.map(m => `<a class="ov-record" href="${m.key === "sleep" ? "#sleep" : "#"}" ${m.key !== "sleep" ? 'data-ov-evidence="true"' : ""}>
    <span class="ov-record-icon">${icon(m.key === "sleep" ? "sleep" : "heart", 22)}</span><div><span>${t(`metric.${m.key}`)}</span>
      <b>${measure(m.value, m.unit)}</b><small>${m.partial ? t("state.partial") : t(`state.${m.state || "none"}`)}</small>
      <small>${m.band ? t("band", { low: measure(m.band.q1, m.unit), high: measure(m.band.q3, m.unit) }) : ""}</small></div></a>`);
  rows.push(`<a class="ov-record" href="#load"><span class="ov-record-icon">${icon("exercise", 22)}</span><div><span>${t("rec.load_title")}</span>
    <b>${t(`rec.load.${p.load.state}`)}</b><small>${rv("record")} ↗</small></div></a>`);
  return `<section class="ov-records"><div class="ov-records-title"><h2>${rv("records")}</h2><span>${rv("compare")}</span></div><div class="ov-record-grid">${rows.join("")}</div>
    <details class="ov-evidence"><summary>${t(`recovery.${p.recovery.verdict}`)} · ${t("ui.how")}</summary><p>${t("rec.verdict_note")}</p>
    ${p.recovery.as_of ? `<p>${t("recovery.as_of", { day: day(p.recovery.as_of) })}</p>` : ""}</details></section>`;
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
      <p class="ov-model-note">${rv("scope")}</p><details class="ov-credit"><summary>${rv("modelCredit")}</summary><p>${rv("modelNote")}</p><a href="models/recovery/ILLUSTRATION.md" target="_blank" rel="noopener">${rv("modelCredit")} ↗</a></details>
    </section>
    <div class="ov-states"><section class="ov-metric ov-sore-card">${soreCard(p)}</section><section class="ov-metric ov-energy-card">${energyCard(p)}</section>${cardioCard(p)}<p class="ov-ring-key">${rv("ringKey")}</p></div>
    </div>${related(p)}</section>`;
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
    const known = p.soreness.today || draft, value = known ? (levels[selected] || 0) : null;
    const session = recent.flatMap(d => d.sessions.filter(s => s.note?.regions.includes(selected)).map(s => ({ ...s, date: d.date })))[0];
    el.innerHTML = `<div class="ov-selection-head"><b>${esc(rv("selected", { region: t(`sore.region.${selected}`) }))}</b><span>${value == null ? rv("unknown") : t(`sore.level.${value}`)}</span></div>
      <p>${session ? esc(rv("lastTrained", { date: day(session.date), type: wtype(session.type) })) : rv("notTrained")}</p>
      ${view === "trained" ? `<p>${rv("trainingHint")}</p>` : ""}
      <details class="ov-local-edit"><summary>${rv("edit")}</summary><div class="ov-levels" role="group" aria-label="${t(`sore.region.${selected}`)}">${[0, 1, 2, 3].map(v => `<button type="button" data-ov-level="${v}" aria-pressed="${known && v === value}">${t(`sore.level.${v}`)}</button>`).join("")}</div>
      <button type="button" class="ov-open-editor">${draft ? rv("draftHelp") : rv("editor")} →</button></details>`;
    el.querySelector(".ov-local-edit").open = !!editing;
    el.querySelectorAll("[data-ov-level]").forEach(b => { b.onclick = () => {
      const level = Number(b.dataset.ovLevel); onLevel(selected, level);
      el.querySelector(`[data-ov-level="${level}"]`)?.focus();
    }; });
    el.querySelector(".ov-open-editor").onclick = openEditor;
  }
  const repaint = () => { model?.update({ levels, known: p.soreness.today || draft, selected, view }); selection(); };
  const select = region => { selected = region; wrap.querySelector("#ov-region").value = region; repaint(); };
  wrap.querySelector("#ov-region").onchange = event => select(event.target.value);
  wrap.querySelectorAll("[data-ov-view]").forEach(b => { b.onclick = () => {
    view = b.dataset.ovView;
    wrap.querySelectorAll("[data-ov-view]").forEach(x => x.setAttribute("aria-pressed", String(x.dataset.ovView === view)));
    wrap.querySelectorAll(".ov-sore-legend").forEach(x => { x.hidden = view !== "sore"; }); wrap.querySelector(".ov-trained-legend").hidden = view !== "trained"; repaint();
  }; });
  wrap.querySelectorAll("[data-ov-turn]").forEach(b => { b.onclick = () => model?.rotate(Number(b.dataset.ovTurn)); });
  wrap.querySelector(".ov-front").onclick = () => model?.reset();
  wrap.querySelectorAll("[data-ov-evidence]").forEach(a => { a.onclick = event => { event.preventDefault(); const detail = wrap.querySelector(".ov-evidence"); detail.open = true; detail.scrollIntoView({ block: "nearest", behavior: "smooth" }); detail.querySelector("summary").focus(); }; });
  const C = p.cardio;
  if (C?.line.length) draw(wrap.querySelector(".ov-spark"), w => spark(C.line, null, { width: w, height: 78, unit: "mL/kg/min" })
    .replace(/aria-label="[^"]*"/, `aria-label="${esc(`${t("cardio.short")} · ${t("cardio.chart")}`)}"`));
  else wrap.querySelector(".ov-spark").textContent = rv("unknown");
  mountBody(wrap.querySelector(".ov-body-stage"), { regions: p.regions, levels, known: p.soreness.today, trained, onSelect: select,
    onUnsupported() { selected = ""; wrap.querySelector("#ov-region").value = ""; repaint(); wrap.querySelector(".ov-selection").innerHTML = `<p>${rv("untracked")}</p>`; }
  }).then(result => { model = result; repaint(); });
  return { setLevels(next, changed = true) { levels = { ...next }; draft = changed; wrap.querySelector(".ov-sore-card").innerHTML = soreCard(p, levels, draft); repaint(); } };
}
