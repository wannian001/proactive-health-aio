import { isStatic } from "../api.js";
import { esc } from "../charts.js";
import { day, t } from "../i18n.js";
import { ACTIVITY, activityIcon, activeHtml, checkinHtml, historyHtml, modeNote, mountRestore, nextStep, restoreButton } from "../restore-ui.js";

// Only UI preferences live in memory. All activity, check-in and reward state comes from the server.
let tab = "rest", filter = "all", selected = null;
const disabled = () => isStatic ? " disabled" : "";

function library(p) {
  const cards = p.activities.filter((key) => filter === "all" || ACTIVITY[key].category === filter).map((key) => `<button type="button" class="rr-activity" data-rr-pick="${key}" aria-pressed="${selected === key}"${p.active ? " disabled" : ""}>
    <span class="rr-glyph">${activityIcon(key, 26)}</span><span><b>${t(`rr.activity.${key}`)}</b><small>${t(`rr.${ACTIVITY[key].category}`)}</small></span><span class="rr-card-arrow" aria-hidden="true">${selected === key ? "✓" : "↗"}</span></button>`).join("");
  const choice = selected && !p.active ? `<div class="rr-selection"><h3>${t(`rr.activity.${selected}`)}</h3><p class="small muted">${t(`rr.desc.${selected}`)}</p><p class="xs muted">${t("rr.no_timer")}</p>${restoreButton("start", "rr.start", `data-rr-activity="${selected}"`, true)}<p class="rr-msg small" role="status"></p></div>` : "";
  return `${activeHtml(p)}<div class="rr-library-head"><h2>${t("rr.free")}</h2><div class="rr-filters" aria-label="${esc(t("rr.rest_tab"))}">${["all", "quiet", "outside", "social", "playful"].map((key) => `<button type="button" data-rr-filter="${key}" aria-pressed="${key === filter}">${t(`rr.${key}`)}</button>`).join("")}</div></div>
    <div class="rr-activities">${cards}</div>${choice}<div class="rr-section-gap">${historyHtml(p)}</div><a class="rr-more-link" href="#followup">${t("rr.followup")} →</a>`;
}

function rewardRow(r, pending) {
  return `<article class="rr-reward"><div class="rr-session-head"><span class="rr-glyph">${activityIcon("gift", 22)}</span><div><h3>${esc(r.title)}</h3><span class="xs muted">${day(r.at)} · ${t(pending ? "rr.reward_planned" : r.status === "done" ? "rr.finished" : "rr.cancelled")}</span></div></div>${r.note ? `<p class="small muted">${esc(r.note)}</p>` : ""}
    ${pending ? `<div class="rr-actions">${restoreButton("reward_done", "rr.reward_done", `data-rr-ref="${esc(r.id)}"`)}${restoreButton("reward_cancel", "rr.reward_remove", `data-rr-ref="${esc(r.id)}"`)}</div><p class="rr-msg small" role="status"></p>` : ""}</article>`;
}

function rewards(p) {
  const pending = p.rewards.filter((r) => r.status === "planned"), history = p.rewards.filter((r) => r.status !== "planned");
  return `<div class="rr-rewards-layout"><section><span class="rr-glyph">${activityIcon("gift", 28)}</span><h2>${t("rr.reward_intro")}</h2><p class="small muted">${t("rr.reward_hint")}</p>
    <form data-rr-form="reward_plan" class="rr-form"><label>${t("rr.reward_title")}<input name="title" maxlength="120" required placeholder="${esc(t("rr.reward_placeholder"))}"${disabled()}></label><label>${t("rr.reward_note")}<input name="note" maxlength="120" placeholder="${esc(t("rr.reward_note_placeholder"))}"${disabled()}></label><div class="rr-actions"><button type="submit" class="rr-button primary"${disabled()}>${t("rr.reward_plan")}</button><p class="rr-msg small" role="status"></p></div></form></section>
    <section>${pending.length ? pending.map((r) => rewardRow(r, true)).join("") : `<div class="rr-empty"><p>${t("rr.reward_empty")}</p></div>`}</section></div>
    <details class="rr-context"><summary>${t("rr.reward_history")}</summary>${history.length ? history.map((r) => rewardRow(r, false)).join("") : `<p class="small muted">${t("rr.reward_history_empty")}</p>`}</details>`;
}

function content(p) {
  return `<section class="card span-12 rr-library"><div class="rr-tabs" role="group" aria-label="${esc(t("nav.restore"))}">${["rest", "reward"].map((key) => `<button type="button" data-rr-tab="${key}" aria-pressed="${tab === key}">${activityIcon(key === "rest" ? "sleep" : "gift", 18)}${t(`rr.${key}_tab`)}</button>`).join("")}</div>${tab === "rest" ? library(p) : rewards(p)}</section>`;
}

export default {
  render(p) {
    return `<div class="head"><div><h1>${t("nav.restore")}</h1><div class="sub">${t("rr.sub")}</div></div></div>
      <div class="grid"><section class="card span-12 rr-intro">${nextStep(p, { details: true, link: false, controls: false })}${checkinHtml(p)}</section><div class="span-12" id="rr-content">${content(p)}</div>
      <section class="card span-12"><details class="how"><summary>${t("rr.rules")}</summary><p>${t("rr.rules_text")}</p></details>${modeNote(p)}</section></div>`;
  },
  mount(root, p) {
    const bind = () => {
      mountRestore(root);
      root.querySelectorAll("[data-rr-tab]").forEach((b) => { b.onclick = () => { tab = b.dataset.rrTab; paint(`[data-rr-tab="${tab}"]`); }; });
      root.querySelectorAll("[data-rr-filter]").forEach((b) => { b.onclick = () => { filter = b.dataset.rrFilter; paint(`[data-rr-filter="${filter}"]`); }; });
      root.querySelectorAll("[data-rr-pick]").forEach((b) => { b.onclick = () => { selected = b.dataset.rrPick; paint(`[data-rr-pick="${selected}"]`); }; });
    };
    const paint = (focus) => { root.querySelector("#rr-content").innerHTML = content(p); bind(); root.querySelector(focus)?.focus(); };
    bind();
  },
};
