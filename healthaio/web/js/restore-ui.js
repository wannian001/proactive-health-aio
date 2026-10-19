// Shared components for Today, Rest & rewards and Follow-up. Current feelings are said in one place, the
// "How you are right now" card on Recovery; the pages here show what was said and link to it.
import { isStatic, post } from "./api.js";
import { esc } from "./charts.js";
import { clock, day, measure, num, t } from "./i18n.js";
import { icon } from "./icons.js";

export const ACTIVITY = {
  sit: { icon: "sleep", category: "quiet" }, music: { icon: "music", category: "quiet" },
  walk: { icon: "walk", category: "outside" }, friend: { icon: "communication", category: "social" },
  photo: { icon: "camera", category: "outside" }, play: { icon: "fun", category: "playful" },
};
export const quietSuggestion = (p) => p && ["quiet", "engaged", "active"].includes(p.situation.key);
const disabled = () => isStatic ? " disabled" : "";
const at = (value) => ({ date: day(value), time: clock(value) });
const button = (op, label, attrs = "", primary = false) => `<button type="button" class="rr-button${primary ? " primary" : ""}" data-rr-op="${op}" ${attrs}${disabled()}>${esc(t(label))}</button>`;
export function activityIcon(key, size = 24) {
  const name = ACTIVITY[key]?.icon || key;
  const paths = { music: '<path d="M9 17V5l11-2v12M9 8l11-2"/><ellipse cx="6" cy="17" rx="3" ry="2.5"/><ellipse cx="17" cy="15" rx="3" ry="2.5"/>',
    camera: '<path d="m8 5 1.5-2h5L16 5h3a2 2 0 0 1 2 2v12H3V7a2 2 0 0 1 2-2z"/><circle cx="12" cy="12" r="4"/>',
    gift: '<rect x="4" y="10" width="16" height="11" rx="1"/><path d="M3 6h18v4H3zM12 6v15"/><path d="M12 6C6 7 5 2 8 2c2 0 3 2 4 4 1-2 2-4 4-4 3 0 2 5-4 4z"/>' };
  return paths[name] ? `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]}</svg>` : icon(name, size);
}

export function modeNote(p) {
  return isStatic || p.demo ? `<p class="rr-mode xs muted">${t(isStatic ? "rr.static" : "rr.demo")}</p>` : "";
}

export function evidence(s) {
  const r = s.recovery, schedule = s.schedule, f = s.food;
  const metrics = r.metrics.map((m) => `<div class="rr-evidence-item"><span>${icon(m.key === "sleep" ? "sleep" : "heart", 17)} ${esc(t(`metric.${m.key}`))}</span><b class="num">${measure(m.value, m.unit)}</b><small>${m.band ? esc(t("rr.typical", { lo: num(m.band.q1), hi: num(m.band.q3) })) : t("rr.missing")}</small></div>`).join("");
  return `<details class="rr-evidence"><summary>${t("rr.more")}</summary>
    <p class="xs muted">${r.as_of ? t("rr.source", { date: day(r.as_of) }) : t("rr.no_source")}${r.as_of && !r.fresh ? ` · ${t("rr.stale")}` : ""}</p>
    <div class="rr-evidence-grid">${metrics}<div class="rr-evidence-item"><span>${icon("calendar", 17)} ${t("rr.schedule")}</span><b>${schedule.hours == null ? t("rr.missing") : t("rr.calendar", { h: num(schedule.hours, 1) })}</b><small>${schedule.deadlines == null ? t("rr.missing") : t("rr.deadlines", { n: schedule.deadlines })}</small></div></div>
    <p class="small"><b>${t("rr.food")}</b> · ${f.logged_carbs_g == null ? t("rr.missing") : t("rr.carbs", { g: num(f.logged_carbs_g), n: f.carb_entries })}</p>
    <p class="xs muted">${t("rr.food_note")}</p><p class="small muted">${t("rr.boundary")}</p></details>`;
}

export function nextStep(p, { details = true, link = true, controls = true } = {}) {
  if (!p) return "";
  const s = p.situation, key = s.key, goal = ["challenge", "smaller"].includes(key);
  return `<section class="rr-next" aria-labelledby="rr-next-title"><div class="rr-next-mark">${activityIcon(key === "active" ? p.active.activity : goal ? "target" : "sleep", 28)}</div>
    <div class="rr-next-body"><span class="eyebrow">${t("rr.eyebrow")}</span><h2 id="rr-next-title">${esc(t(`rr.title.${key}`))}</h2>
      <p>${esc(t(`rr.why.${key}`, { time: clock(s.quiet_until) }))}</p>
      ${controls ? `<div class="rr-actions">${link ? `<a class="rr-button primary" href="${goal ? "#goals" : "#restore"}">${t(key === "active" ? "rr.current" : goal ? "rr.goals" : "rr.choose")}</a>` : ""}
        ${key === "quiet" ? button("resume", "rr.resume") : key !== "active" ? button("quiet", "rr.later") : ""}</div>` : ""}
      ${details ? evidence(s) : ""}<p class="rr-msg xs" role="status"></p></div></section>`;
}

const CHOICES = { body: ["comfortable", "tired", "sore"], mind: ["clear", "tired", "tense", "bored", "engaged"], task: ["easy", "fit", "hard"] };
function choices(field, values, selected, prefix = `rr.${field}`) {
  return `<fieldset><legend>${t(`rr.${field}`)}</legend><div class="rr-choices">${values.map((value) => `<button type="button" data-rr-field="${field}" data-rr-value="${value}" aria-pressed="${selected === value}"${disabled()}>${esc(t(`${prefix}.${value}`))}</button>`).join("")}</div></fieldset>`;
}

export function nowLine(p) {
  if (!p) return "";
  const c = p.situation.checkin, last = p.situation.last_checkin;
  const words = c ? Object.keys(CHOICES).filter((k) => c[k]).map((k) => t(`rr.${k}.${c[k]}`)).join(t("ui.list_sep")) : t("rr.check_none");
  return `<p class="rr-self small"><span>${icon("communication", 16)} <b>${esc(words)}</b></span>
    <span class="xs muted">${c ? t("rr.check_at", at(c.at)) : last ? t("rr.check_old", at(last.at)) : ""}</span>
    <a href="#recovery/now">${t("now.link")} ›</a></p>`;
}

// Today's "what to adjust" opens with this, when there is something to say right now
export function nowItem(p) {
  if (!p || ["steady", "unknown"].includes(p.situation.key)) return "";
  const s = p.situation, key = s.key, goal = ["challenge", "smaller"].includes(key);
  return `<a class="todo-item todo-now" href="${goal ? "#goals" : "#restore"}"><span class="todo-icon">${activityIcon(key === "active" ? p.active.activity : goal ? "target" : "sleep", 20)}</span>
    <span class="todo-body"><span class="eyebrow">${t("now.item")}</span><b>${esc(t(`rr.title.${key}`))}</b><span class="small muted">${esc(t(`rr.why.${key}`, { time: clock(s.quiet_until) }))}</span></span></a>`;
}

export function activeHtml(p) {
  const s = p?.active;
  if (!s) return "";
  return `<section class="rr-current"><div class="rr-current-title"><span class="rr-glyph">${activityIcon(s.activity)}</span><div><span class="eyebrow">${t("rr.active")}</span><h3>${t(`rr.activity.${s.activity}`)}</h3><p class="small muted">${t("rr.started", at(s.started_at))}</p></div></div>
    <p class="small muted">${t("rr.no_timer")}</p><div class="rr-actions">${button("finish", "rr.finish", `data-rr-ref="${esc(s.id)}"`, true)}${button("cancel", "rr.cancel", `data-rr-ref="${esc(s.id)}"`)}</div><p class="rr-msg small" role="status"></p></section>`;
}

function feedbackHtml(s, open) {
  const f = s.feedback;
  return `<details class="rr-feedback"${open && !f ? " open" : ""}><summary>${t(f ? "rr.feedback_edit" : "rr.feedback")}</summary>
    <form data-rr-form="feedback" data-rr-ref="${esc(s.id)}" class="rr-form">
      ${choices("change", ["better", "same", "worse"], f?.change, "rr")}${choices("enjoyment", ["yes", "neutral", "no"], f?.enjoyment, "rr")}
      <div class="rr-actions"><button class="rr-button primary" type="submit"${disabled()}>${t("rr.save")}</button><p class="rr-msg small" role="status"></p></div>
      <p class="xs muted">${t("rr.feedback_hint")}</p></form></details>`;
}

export function historyHtml(p, { limit = 5 } = {}) {
  if (!p) return "";
  const sessions = p.sessions.filter((s) => s.status !== "active").slice(0, limit);
  return `<section class="rr-history"><h2>${t("rr.history")}</h2><p class="small muted">${t("rr.history_hint")}</p>
    ${!sessions.length ? `<div class="rr-empty">${icon("clock", 26)}<p>${t("rr.history_empty")}</p></div>` : sessions.map((s, i) => {
      const f = s.feedback, status = t(s.status === "cancelled" ? "rr.cancelled" : "rr.finished");
      return `<article class="rr-session" data-rr-session="${esc(s.id)}"><div class="rr-session-head"><span class="rr-glyph">${activityIcon(s.activity, 20)}</span><div><h3>${t(`rr.activity.${s.activity}`)}</h3><span class="xs muted">${t("rr.started", at(s.started_at))}</span></div><span class="chip">${status}</span></div>
        <p class="small rr-reflection">${s.status === "cancelled" ? status : f ? [f.change ? `${t("rr.change")} · ${t(`rr.${f.change}`)}` : "", f.enjoyment ? `${t("rr.enjoyment")} ${t(`rr.${f.enjoyment}`)}` : ""].filter(Boolean).map(esc).join(" / ") : t("rr.unknown_feedback")}</p>
        ${s.status === "finished" ? feedbackHtml(s, i === 0) : ""}
        <details class="rr-context"><summary>${t("rr.context")}</summary><p class="xs muted">${t("rr.ends", at(s.ended_at))}</p><p class="small">${esc(t(`rr.title.${s.context.key}`))}</p>${evidence(s.context)}</details></article>`;
    }).join("")}</section>`;
}

// Reuse an ID after an uncertain network failure, but never after changing a form.
// No optimistic success: refresh every page's shared data only after the server confirms.
export function mountRestore(root) {
  if (isStatic) return;
  const send = async (element, payload) => {
    const area = element.closest("form, .rr-current, .rr-next-body, .rr-reward, .rr-selection");
    const msg = area?.querySelector(".rr-msg");
    const signature = JSON.stringify(payload);
    const retry = element._rrRetry;
    const request = retry?.signature === signature ? retry.request : { ...payload, request_id: crypto.randomUUID() };
    element._rrRetry = { signature, request };
    const controls = [...(area || element).querySelectorAll("button, input")];
    if (element.tagName === "BUTTON") controls.push(element);
    const wasDisabled = controls.map((b) => b.disabled);
    controls.forEach((b) => { b.disabled = true; });
    if (msg) msg.textContent = t("rr.saving");
    try {
      await post("restore", request);
      element._rrRetry = null;
      window.dispatchEvent(new CustomEvent("healthaio:restore-saved", { detail: { op: payload.op, ref: payload.ref } }));
    } catch (error) {
      if (msg) msg.textContent = t("rr.error", { error: error.message });
      controls.forEach((b, i) => { b.disabled = wasDisabled[i]; });
    }
  };
  root.querySelectorAll("[data-rr-op]").forEach((b) => {
    b.onclick = () => send(b, { op: b.dataset.rrOp, ...(b.dataset.rrRef ? { ref: b.dataset.rrRef } : {}), ...(b.dataset.rrActivity ? { activity: b.dataset.rrActivity } : {}) });
  });
  root.querySelectorAll("form[data-rr-form]").forEach((form) => {
    form.querySelectorAll("[data-rr-field]").forEach((b) => {
      b.onclick = () => {
        const turnOn = b.getAttribute("aria-pressed") !== "true";
        form.querySelectorAll(`[data-rr-field="${b.dataset.rrField}"]`).forEach((x) => x.setAttribute("aria-pressed", String(turnOn && x === b)));
      };
    });
    form.onsubmit = (e) => {
      e.preventDefault();
      const op = form.dataset.rrForm, payload = { op };
      if (form.dataset.rrRef) payload.ref = form.dataset.rrRef;
      if (op === "reward_plan") {
        payload.title = form.elements.title.value.trim(); payload.note = form.elements.note.value.trim();
      } else {
        const fields = ["change", "enjoyment"];
        fields.forEach((field) => { payload[field] = form.querySelector(`[data-rr-field="${field}"][aria-pressed="true"]`)?.dataset.rrValue || null; });
        if (fields.every((k) => payload[k] === null)) { form.querySelector(".rr-msg").textContent = t("rr.feedback_required"); return; }
      }
      send(form, payload);
    };
  });
}

export { button as restoreButton };
