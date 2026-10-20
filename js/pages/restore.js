import { isStatic, post } from "../api.js?v=65d4646a27";
import { draw, esc, keptDots, stackedColumns } from "../charts.js?v=65d4646a27";
import { day, dur, shortDay, t } from "../i18n.js?v=65d4646a27";
import { ACTIVITY, activityIcon, activeHtml, modeNote, mountRestore, nextStep, nowLine, restoreButton } from "../restore-ui.js?v=65d4646a27";

// Only UI preferences live in memory. All activity, check-in and reward state comes from the server.
let tab = "rest", filter = "all", selected = null;
const disabled = () => isStatic ? " disabled" : "";

function library(p) {
  // in the order your own answers put them; each says what it has done for you so far
  const stat = (key) => { const b = (p.tried || []).find((x) => x.activity === key); return b && b.answered ? t("rr.card_stat", { n: b.answered, b: b.better, g: b.glad }) : t(`rr.${ACTIVITY[key].category}`); };
  const cards = p.activities.filter((key) => filter === "all" || ACTIVITY[key].category === filter).map((key) => `<button type="button" class="rr-activity" data-rr-pick="${key}" aria-pressed="${selected === key}"${p.active ? " disabled" : ""}>
    <span class="rr-glyph">${activityIcon(key, 26)}</span><span><b>${t(`rr.activity.${key}`)}</b><small>${esc(stat(key))}</small></span><span class="rr-card-arrow" aria-hidden="true">${selected === key ? "✓" : "↗"}</span></button>`).join("");
  const choice = selected && !p.active ? `<div class="rr-selection"><h3>${t(`rr.activity.${selected}`)}</h3><p class="small muted">${t(`rr.desc.${selected}`)}</p><p class="xs muted">${t("rr.no_timer")}</p>${restoreButton("start", "rr.start", `data-rr-activity="${selected}"`, true)}<p class="rr-msg small" role="status"></p></div>` : "";
  return `${activeHtml(p)}<div class="rr-library-head"><h2>${t("rr.free")}</h2><div class="rr-filters" aria-label="${esc(t("rr.rest_tab"))}">${["all", "quiet", "outside", "social", "playful"].map((key) => `<button type="button" data-rr-filter="${key}" aria-pressed="${key === filter}">${t(`rr.${key}`)}</button>`).join("")}</div></div>
    <div class="rr-activities">${cards}</div>${choice}<a class="rr-more-link" href="#followup">${t("rr.followup")} →</a>`;
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

// the long view (modules/focus.py rhythm): this week so far, a run of days over budget and the half-day to keep light,
// 8 weeks as kept dots, a celebration once the rhythm held for weeks, and each day's deep focus against its budget
const halfDay = (L) => (L ? t("rhythm.when", { day: day(L.date), half: t(`rhythm.half.${L.half}`) }) : "");
function rhythmHtml(R) {
  if (!R) return "";
  const monday = R.weeks.length ? (() => { const d = new Date(`${R.weeks.at(-1).start}T12:00:00`); d.setDate(d.getDate() + 7); return d.toISOString().slice(0, 10); })() : null;
  const week = R.days.filter((x) => x.known && monday && x.date >= monday);
  const last = R.weeks.at(-1);
  const lede = R.over_run >= 3 ? t("rhythm.over_lede", { n: R.over_run, when: halfDay(R.light) })
    : week.length ? t("rhythm.week_lede", { known: week.length, good: week.filter((x) => x.sustainable).length })
      : last && last.known ? t("rhythm.last_week_lede", { known: last.known, good: last.sustainable_days }) : t("rhythm.week_none");
  const reward = R.reward_ready
    ? `<div class="rhythm-reward"><span class="rr-glyph">${activityIcon("gift", 22)}</span><div><b>${esc(t("rhythm.ready", { n: R.streak }))}</b><span class="xs muted">${t("rhythm.ready_hint")}</span></div>
        <button type="button" class="rr-button primary" id="rhythm-plan"${isStatic ? " disabled" : ""}>${t("rhythm.plan")}</button><p class="rr-msg xs" role="status"></p></div>`
    : `<p class="small">${esc(R.streak ? t("rhythm.streak", { n: R.streak, left: R.to_reward }) : t("rhythm.no_streak", { n: R.rule.sustained_weeks }))}</p>`;
  return `<section class="card span-12 rhythm" id="rhythm"><h2>${t("rhythm.title")}<span class="aside">${t("rhythm.sub")}</span></h2>
    <p class="lede" style="font-size:var(--t-lg);margin:0 0 6px">${esc(lede)}</p>${reward}
    <h3 class="section-title" style="margin-top:var(--s-4)">${t("rhythm.weeks")}</h3><div id="rhythm-weeks" class="chart"></div>
    <h3 class="section-title" style="margin-top:var(--s-4)">${t("rhythm.days")}</h3><div id="rhythm-days" class="chart"></div>
    <details class="how"><summary>${t("ui.how")}</summary><p>${esc(t("rhythm.rule", { d: R.rule.deep_min, o: R.rule.over_min, b: R.rule.breaks_min, k: R.rule.known_days, s: R.rule.sustained_days, w: R.rule.sustained_weeks }))}</p></details></section>`;
}

function mountRhythm(root, R) {
  if (!R) return;
  draw(root.querySelector("#rhythm-weeks"), (w) => keptDots(R.weeks.map((x) => ({ date: x.start, met: x.met })), { width: Math.min(w, 320) }));
  const cols = R.days.map((x) => {
    if (!x.known) return { label: shortDay(x.date), values: null, tip: `${day(x.date)} · ${t("ui.no_data")}` };
    const top = x.budget ? x.budget.high : x.used;
    const flags = [x.over ? t("rhythm.flag.over") : "", x.breaks ? "" : t("rhythm.flag.no_breaks", { m: R.rule.breaks_min })].filter(Boolean).join(t("ui.list_sep"));
    return { label: shortDay(x.date), values: { within: Math.min(x.used, top), over: Math.max(0, x.used - top) },
      tip: `${day(x.date)} · ${t("rhythm.tip_used", { d: dur(x.used) })}${x.budget ? ` · ${t("rhythm.tip_budget", { mid: dur(x.budget.middle), lo: dur(x.budget.low), hi: dur(x.budget.high) })}` : ""}${flags ? ` · ${flags}` : ""}` };
  });
  draw(root.querySelector("#rhythm-days"), (w) => stackedColumns(cols, [["within", "var(--c-focus)"], ["over", "var(--watch)"]], { width: w, height: 170, labelEvery: Math.max(1, Math.ceil(cols.length / Math.max(1, w / 46))) }));
  const plan = root.querySelector("#rhythm-plan");
  if (plan) plan.onclick = async () => {
    if (isStatic) return;
    plan.dataset.request = plan.dataset.request || crypto.randomUUID();
    plan.disabled = true;
    try {
      await post("restore", { op: "reward_plan", title: t("rhythm.reward_title", { n: R.streak }), note: t("rhythm.reward_note"), for: "rhythm", request_id: plan.dataset.request });
      window.dispatchEvent(new CustomEvent("healthaio:restore-saved", { detail: { op: "reward_plan" } }));
    } catch (error) { plan.disabled = false; plan.nextElementSibling.textContent = t("rr.error", { error: error.message }); }
  };
}

function content(p) {
  return `<section class="card span-12 rr-library"><div class="rr-tabs" role="group" aria-label="${esc(t("nav.restore"))}">${["rest", "reward"].map((key) => `<button type="button" data-rr-tab="${key}" aria-pressed="${tab === key}">${activityIcon(key === "rest" ? "sleep" : "gift", 18)}${t(`rr.${key}_tab`)}</button>`).join("")}</div>${tab === "rest" ? library(p) : rewards(p)}</section>`;
}

export default {
  render(p) {
    return `<div class="head"><div><h1>${t("nav.restore")}</h1><div class="sub">${t("rr.sub")}</div></div></div>
      <div class="grid"><section class="card span-12 rr-intro">${nextStep(p, { details: true, link: false, controls: true })}${nowLine(p)}</section>${rhythmHtml(p.rhythm)}<div class="span-12" id="rr-content">${content(p)}</div>
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
    mountRhythm(root, p.rhythm);
  },
};
