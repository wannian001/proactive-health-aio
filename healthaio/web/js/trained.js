// What a workout trained. After a strength session or a hard one (effort 7 or more), every page shows a prompt in the
// corner for 36 hours (modules/recovery.py prompt()): "Note it" opens a dialog with the body figure, a button per
// region and a note box (typed, or dictated with the phone keyboard's microphone); parts the note names light up by
// themselves. Saved into workout_notes.csv (POST /api/trained); the next mornings' check-in asks about those parts.
// "Not this time" saves an empty row, so the prompt does not come back on another device; the × only hides it until
// the app is opened again. The reading pages (Overview, Guide, the kit gallery) do not show it.
import { isStatic, post } from "./api.js";
import { esc } from "./charts.js";
import { figureSvg, mountFigure, regionsIn } from "./figure.js";
import { clock, day, dur, num, t, toDate, wtype } from "./i18n.js";
import { icon } from "./icons.js";

const SKIPPED = "healthaio.trained.skipped";  // the static demo cannot save: "Not this time" is remembered here
const LATER = "healthaio.trained.later";      // × : hidden until the app is opened again (this tab only)
const read = (store, key) => { try { return store.getItem(key); } catch { return null; } };
const keep = (store, key, value) => { try { store.setItem(key, value); } catch { /* private mode: back on reload */ } };

export const workoutText = (s) => `${wtype(s.type)} ${dur(s.minutes)}${s.effort ? ` · ${t("trained.effort", { v: num(s.effort) })}` : ""}`;
// "today 12:54", "yesterday 17:44", or the date: the prompt stays up to 36 hours, so "just now" would not be true
function when(iso, today) {
  const days = Math.round((toDate(today) - toDate(iso.slice(0, 10))) / 864e5);
  return days === 0 || days === 1 ? t(`trained.when.${days}`, { clock: clock(iso) }) : `${day(iso)} ${clock(iso)}`;
}

const refresh = () => window.dispatchEvent(new HashChangeEvent("hashchange"));

// info: {figure, regions, words} (the prompt's or the Recovery page's payload); s: the session
export function openTrained(info, s, done = refresh) {
  document.querySelector(".trained-dlg")?.remove();
  const chosen = new Set(s.note?.regions || []);
  const on = new Set(), off = new Set();  // the user's own taps win over the note's words
  let fromWords = new Set();
  const selected = () => new Set([...info.regions].filter((r) => on.has(r) || ((chosen.has(r) || fromWords.has(r)) && !off.has(r))));
  const fills = (sel) => Object.fromEntries(info.regions.map((r) => [r, sel.has(r) ? "var(--c-exercise)" : "var(--c-sore-0)"]));
  const label = (r, sel = selected()) => t("trained.region_aria", { region: t(`sore.region.${r}`), state: t(sel.has(r) ? "trained.on" : "trained.off") });
  const dlg = document.createElement("dialog");
  dlg.className = "trained-dlg";
  dlg.setAttribute("aria-labelledby", "trained-title");
  dlg.innerHTML = `<form method="dialog" class="trained-form">
    <h2 id="trained-title">${esc(t("trained.title", { day: day(s.start, { weekday: true }), clock: clock(s.start), what: workoutText(s) }))}</h2>
    <div class="trained-layout">
      <div class="fig-plate">${figureSvg(info, fills(selected()), (r) => label(r))}</div>
      <div class="trained-side">
        <label class="small" for="trained-note">${t("trained.note_label")}</label>
        <textarea id="trained-note" rows="3" maxlength="500" placeholder="${esc(t("trained.placeholder"))}">${esc(s.note?.note || "")}</textarea>
        <p class="xs muted" style="margin:4px 0 var(--s-3)">${t("trained.words_note")}</p>
        <span class="section-title">${t("trained.regions")}</span>
        <div class="trained-chips">${info.regions.map((r) => `<button type="button" class="goal-btn trained-chip" data-region="${r}" aria-pressed="false">${t(`sore.region.${r}`)}</button>`).join("")}</div>
        <div class="goal-act" style="margin-top:var(--s-4)"><button type="button" class="goal-btn primary" data-save${isStatic ? " disabled" : ""}>${t("trained.save")}</button>
          <button type="button" class="goal-btn" data-cancel>${t("trained.cancel")}</button></div>
        <p class="xs trained-msg" role="status">${isStatic ? t("trained.static") : ""}</p>
      </div></div></form>`;
  document.body.appendChild(dlg);
  const svg = dlg.querySelector(".fig");
  const paint = () => {
    const sel = selected(), f = fills(sel);
    svg.querySelectorAll(".fig-region").forEach((g) => { g.style.fill = f[g.dataset.region]; g.setAttribute("aria-label", label(g.dataset.region, sel)); });
    dlg.querySelectorAll(".trained-chip").forEach((b) => b.setAttribute("aria-pressed", String(sel.has(b.dataset.region))));
  };
  const tap = (r) => {
    if (selected().has(r)) { off.add(r); on.delete(r); } else { on.add(r); off.delete(r); }
    paint();
  };
  mountFigure(svg, info, { tap, tip: (r) => `${t(`sore.region.${r}`)} · ${t(selected().has(r) ? "trained.on" : "trained.off")}` });
  dlg.querySelectorAll(".trained-chip").forEach((b) => { b.onclick = () => tap(b.dataset.region); });
  const note = dlg.querySelector("#trained-note");
  note.addEventListener("input", () => { fromWords = regionsIn(note.value, info.words); paint(); });
  if (!chosen.size) fromWords = regionsIn(note.value, info.words);
  paint();
  const close = () => { dlg.close(); dlg.remove(); };
  dlg.querySelector("[data-cancel]").onclick = close;
  dlg.addEventListener("cancel", () => dlg.remove());
  dlg.querySelector("[data-save]").onclick = async () => {
    if (isStatic) return;
    try {
      await post("trained", { start: s.start, regions: [...selected()], note: note.value });
      close();
      document.querySelector(".pop")?.remove();
      done();
    } catch (error) {
      dlg.querySelector(".trained-msg").textContent = t("trained.err", { e: error.message });
    }
  };
  dlg.showModal();
  if (matchMedia("(min-width: 900px)").matches) note.focus();  // on a phone the keyboard would cover the figure
}

// the prompt in the corner, on every page but the reading ones (info: the "prompt" payload)
const READING = ["project", "guide", "kit"];
export function mountPrompt(info, page) {
  document.querySelector(".pop:not(.nudge-pop)")?.remove();
  const s = info?.session;
  if (document.querySelector(".nudge-pop")) return;  // the sitting reminder has the corner; this one comes back on the next page
  if (!s || READING.includes(page) || read(sessionStorage, LATER) === s.start || (isStatic && read(localStorage, SKIPPED) === s.start)) return;
  const pop = document.createElement("aside");
  pop.className = "pop";
  pop.setAttribute("role", "status");
  pop.innerHTML = `<span class="pop-icon">${icon("exercise", 18)}</span>
    <div class="pop-text"><b>${esc(t("trained.pop_title", { what: workoutText(s) }))}</b>
      <span class="small">${esc(t("trained.pop_text", { when: when(s.end, info.today) }))}</span>
      <span class="goal-act"><button type="button" class="goal-btn primary" data-open>${t("trained.pop_open")}</button>
        <button type="button" class="goal-btn quiet" data-skip>${t("trained.pop_skip")}</button></span></div>
    <button type="button" class="pop-close" data-later aria-label="${esc(t("trained.pop_later"))}" title="${esc(t("trained.pop_later"))}">×</button>`;
  document.body.appendChild(pop);
  pop.querySelector("[data-later]").onclick = () => { keep(sessionStorage, LATER, s.start); pop.remove(); };
  pop.querySelector("[data-open]").onclick = () => openTrained(info, s);
  pop.querySelector("[data-skip]").onclick = async () => {
    pop.remove();
    if (isStatic) { keep(localStorage, SKIPPED, s.start); return; }
    try { await post("trained", { start: s.start, regions: [], note: "" }); } catch { /* it asks again next time */ }
  };
}
