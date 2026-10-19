// Short moves (routines.py, both languages in the payload) and "I did it": shared by the sitting card on Exercise,
// the sitting reminder in the corner and the "where it's tight" part of Recovery's check-in card.
import { isStatic, post } from "./api.js";
import { esc } from "./charts.js";
import { getLang, t } from "./i18n.js";
import { icon } from "./icons.js";

export const words = (r) => r[getLang()] || r.en;

export function routineHtml(id, info, { why, compact = false } = {}) {
  const r = info[id];
  if (!r) return "";
  const w = words(r);
  return `<article class="routine${compact ? " routine-compact" : ""}" data-routine="${esc(id)}">
    <div class="routine-head"><b>${esc(w.name)}</b><span class="chip">${esc(w.dose)}</span></div>
    <p class="small">${esc(w.how)}</p>
    ${why ? `<button type="button" class="goal-btn" data-care-done="${esc(id)}" data-why="${esc(why)}"${isStatic ? " disabled" : ""}>${icon("check", 14)} ${t("care.done")}</button>` : ""}
  </article>`;
}

export const stopLine = (stop) => (stop ? `<p class="xs muted care-stop">${esc(stop[getLang()] || stop.en)}</p>` : "");
// the same line, folded (the reminder in the corner stays short)
export const stopFold = (stop) => (stop ? `<details class="care-stop-fold"><summary class="xs">${t("care.when_stop")}</summary><p class="xs muted">${esc(stop[getLang()] || stop.en)}</p></details>` : "");

// "I did it" appends a done event to body_care.jsonl; a retry after a failure reuses the request id
export function mountCare(root) {
  root.querySelectorAll("[data-care-done]").forEach((b) => {
    b.onclick = async () => {
      if (isStatic) return;
      b.dataset.request = b.dataset.request || crypto.randomUUID();
      b.disabled = true;
      try {
        await post("care", { op: "done", routine: b.dataset.careDone, why: b.dataset.why, request_id: b.dataset.request });
        b.innerHTML = `${icon("check", 14)} ${t("care.done_saved")}`;
        b.classList.add("done");
      } catch (error) {
        b.disabled = false;
        b.title = t("care.err", { e: error.message });
      }
    };
  });
}

// ---- where it feels tight: tomorrow's question ("how is it now?"), on Today and on Recovery -------------------------
export function askHtml(ask) {
  if (!ask?.length) return "";
  return `<div class="care-ask">${ask.map((a) => `<div class="care-ask-row" data-ask="${esc(a.ref)}" data-region="${esc(a.region)}">
    <span class="small">${esc(t("care.ask", { region: t(`care.region.${a.region}`), feel: t(`care.feel.${a.feel}`) }))}</span>
    <span class="now-btns">${["better", "same", "worse"].map((c) => `<button type="button" class="goal-btn" data-change="${c}"${isStatic ? " disabled" : ""}>${t(`care.change.${c}`)}</button>`).join("")}</span></div>`).join("")}</div>`;
}

export function mountAsk(root) {
  root.querySelectorAll(".care-ask-row").forEach((row) => {
    row.querySelectorAll("[data-change]").forEach((b) => {
      b.onclick = async () => {
        if (isStatic) return;
        row.dataset.request = row.dataset.request || crypto.randomUUID();
        row.querySelectorAll("button").forEach((x) => { x.disabled = true; });
        try {
          await post("care", { op: "answer", ref: row.dataset.ask, region: row.dataset.region, change: b.dataset.change, request_id: row.dataset.request });
          row.querySelector(".now-btns").innerHTML = `<span class="chip">${t("care.answered")} · ${t(`care.change.${b.dataset.change}`)}</span>`;
        } catch (error) {
          row.querySelectorAll("button").forEach((x) => { x.disabled = false; });
          b.title = t("care.err", { e: error.message });
        }
      };
    });
  });
}
