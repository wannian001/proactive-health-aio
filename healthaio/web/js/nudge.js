// The sitting reminder in the corner (modules/sitting.py nudge): asked for when a page opens and every two minutes,
// shown once per reminder (a stretch's since + its round), above the workout prompt. "Later" hides this round; the
// next round, REPEAT_MIN minutes on, comes back if you are still at the computer. The Mac app shows the same reminder
// as a notification when no page is open.
import { get, isStatic } from "./api.js";
import { esc } from "./charts.js";
import { dur, t } from "./i18n.js";
import { icon } from "./icons.js";
import { mountCare, routineHtml, stopFold, words } from "./care-ui.js";

const SEEN = "healthaio.nudge";
const EVERY_MS = 120000;
let timer = null;
const seen = () => { try { return sessionStorage.getItem(SEEN); } catch { return null; } };
const keep = (key) => { try { sessionStorage.setItem(SEEN, key); } catch { /* shown again next time */ } };

export function showNudge(n) {
  document.querySelector(".nudge-pop")?.remove();
  if (!n || n.kind !== "sitting") return;
  const key = `${n.since}#${n.round}`;
  if (seen() === key) return;
  document.querySelector(".pop:not(.nudge-pop)")?.remove();  // one thing in the corner at a time
  const pop = document.createElement("aside");
  pop.className = "pop nudge-pop";
  pop.setAttribute("role", "status");
  const [desk, ...rest] = n.routines;
  pop.innerHTML = `<span class="pop-icon">${icon("clock", 18)}</span>
    <div class="pop-text"><b>${esc(t("sit.pop_title", { d: dur(n.minutes) }))}</b>
      <span class="small">${esc(t("sit.pop_text"))}</span>
      ${routineHtml(desk, n.info, { why: "sitting", compact: true })}
      ${rest.filter((id) => n.info[id]).map((id) => `<span class="small">${t("sit.pop_or")} <b>${esc(words(n.info[id]).name)}</b></span>`).join("")}
      ${stopFold(n.stop)}</div>
    <button type="button" class="pop-close" data-later aria-label="${esc(t("sit.pop_later"))}" title="${esc(t("sit.pop_later"))}">×</button>`;
  document.body.appendChild(pop);
  pop.querySelector("[data-later]").onclick = () => { keep(key); pop.remove(); };
  mountCare(pop);
  pop.querySelector("[data-care-done]")?.addEventListener("click", () => keep(key));
}

export function startNudges() {
  const ask = () => get("nudge").then(showNudge, () => {});
  ask();
  if (!isStatic && !timer) timer = setInterval(ask, EVERY_MS);
  return ask;
}
