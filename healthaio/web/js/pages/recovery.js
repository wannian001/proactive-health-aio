// Recovery (#recovery, under Body signals): the illustrated body with today's soreness and energy and how long they
// usually take to come back (recovery-overview.js), one card to say how you are right now (energy, this morning's
// feeling, where you are sore, mind and task, each saved where it already lives), the score the morning after each
// training day (four parts side by side, averaged, with what it trained and how sore that was), the long view (Wear
// and tear, drain.js: seven quiet signals over 7 days), and at the bottom the personal HRV model (once one is trained). How the body answers hard days is on Follow-up. What training asked of you is on Body & mind load.
// The rules are in modules/recovery.py.
import { isStatic, post } from "../api.js";
import { draw, esc, scoreDots } from "../charts.js";
import { clock, day, dur, num, rv, shortDay, t, toDate, wtype } from "../i18n.js";
import { icon } from "../icons.js";
import { openTrained } from "../trained.js";
import { overviewHtml, mountOverview } from "../recovery-overview.js";
import { hrvModelHtml } from "../hrv-model.js";
import { drainCards, mountDrain } from "./drain.js";
import { askHtml, mountAsk, mountCare, routineHtml, stopLine } from "../care-ui.js";

// a list of regions, both upper arms (or calves) said once
const PAIRS = [["left_upper_arm", "right_upper_arm", "sore.pair.upper_arms"], ["left_calf", "right_calf", "sore.pair.calves"]];
function regionsShort(list) {
  const out = [], seen = new Set();
  for (const r of list) {
    if (seen.has(r)) continue;
    const pair = PAIRS.find(([a, b]) => (r === a || r === b) && list.includes(a) && list.includes(b));
    if (pair) { out.push(t(pair[2])); seen.add(pair[0]); seen.add(pair[1]); } else { out.push(t(`sore.region.${r}`)); seen.add(r); }
  }
  return out.join(t("ui.list_sep"));
}

const BAND_TONE = { good: "good", ok: "", low: "bad" };
function partText(k, x) {
  if (k === "feel") return t(`feel.${x.value}`);
  if (k === "hrv") return t("after.hrv", { a: num(x.before), b: num(x.after) });
  if (k === "resting_hr") return t("after.rhr", { v: num(x.value), m: num(x.median) });
  return x.efficiency != null ? t("after.sleep_eff", { d: dur(x.value), e: num(x.efficiency) }) : t("after.sleep", { d: dur(x.value) });
}
const isoBack = (iso, n) => { const d = toDate(iso); d.setDate(d.getDate() - n); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
const sessionsText = (d) => d.sessions.map((s) => `${wtype(s.type)} ${dur(s.minutes)}${s.effort ? ` · ${t("trained.effort", { v: num(s.effort) })}` : ""}`).join(t("ui.list_sep"));
const unnoted = (d) => d.sessions.find((s) => s.hard && s.note == null);

function afterHtml(p) {
  const A = p.after, L = A.latest;
  if (!A.days.length) return `<section class="card span-12"><h2>${t("after.title")}</h2><p class="muted small">${t("after.none")}</p></section>`;
  // the four parts, each a bar from 0 to 10 with a tick at 5 (a usual morning)
  const parts = L ? ["feel", "hrv", "resting_hr", "sleep"].map((k) => {
    const x = L.parts[k];
    return `<div class="after-part"><span class="small">${t(`after.part.${k}`)}</span>
      ${x ? `<b class="num">${num(x.score, 1)}</b><span class="after-bar"><span style="width:${(x.score * 10).toFixed(0)}%"></span></span><span class="xs muted">${esc(partText(k, x))}</span>`
        : `<b class="num muted">—</b><span class="after-bar"></span><span class="xs muted">${t(k === "feel" ? "after.no_feel" : "after.no_record")}</span>`}</div>`;
  }).join("") : "";
  // what that session trained, each part coloured by how sore it was the next morning
  const trained = L && L.trained.length ? `<div class="after-line">${icon("exercise", 14)}<span class="small">${t("after.trained")}</span>
    ${L.trained.map((r) => {
      const lv = L.sore_next ? L.sore_next[r] || 0 : null;
      return `<span class="sore-chip" data-tip="${esc(`${t(`sore.region.${r}`)} · ${lv == null ? t("after.sore_unchecked") : t(`sore.level.${lv}`)}`)}"><i style="background:${lv == null ? "var(--c-band)" : fill(lv)}"></i>${t(`sore.region.${r}`)}</span>`;
    }).join("")}<span class="xs muted">${t(L.sore_next ? "after.colour_next" : "after.sore_unchecked")}</span></div>` : "";
  // training days (today's too) whose strength or hard session has nothing written about what it trained
  const todo = A.days.slice(0, 10).filter(unnoted);
  const todoLine = todo.length ? `<p class="small after-todo">${t("after.todo")} ${todo.map((d) => `<button type="button" class="doc-link" data-note="${esc(d.date)}">${esc(`${shortDay(d.date)} ${wtype(unnoted(d).type)}`)}</button>`).join(" · ")}</p>` : "";
  return `<section class="card span-12"><h2>${t("after.title")}<span class="aside">${t("after.sub")}</span></h2>
    ${L ? `<div class="after-top"><div><span class="eyebrow">${t("after.eyebrow", { day: day(L.date), m: day(L.morning, { weekday: false }) })}</span>
      <p class="lede" style="margin:4px 0 0"><span class="after-score num">${num(L.score, 1)}</span> <span class="chip ${BAND_TONE[L.band]}">${t(`after.band.${L.band}`)}</span></p>
      <p class="xs muted" style="margin:4px 0 0">${t("after.formula", { n: Object.keys(L.parts).length })}</p></div>
      <div class="after-parts">${parts}</div></div>${trained}` : `<p class="muted small">${t("after.no_score")}</p>`}
    <h3 class="section-title" style="margin-top:var(--s-4)">${t("after.chart_title", { n: A.rule.after_days })}<span class="aside legend"><span class="key"><i style="background:var(--c-band)"></i>${t("after.key_band", { a: num(A.rule.low, 1), b: num(A.rule.good, 1) })}</span></span></h3>
    <div id="after-dots" class="chart"></div>${todoLine}</section>`;
}

// ---- how the body answered training, the next morning ------------------------------------------------------------
// ---- soreness: the body figure (tap a region to set its level), the list, 14 days per region -------------------
// one hue getting stronger (--c-sore-1..3); "not sore" on the figure is --c-sore-0 and on the strips the band colour.
// The figure follows light and dark mode (figure.js)
const SORE = ["var(--c-sore-0)", "var(--c-sore-1)", "var(--c-sore-2)", "var(--c-sore-3)"];
const fill = (level) => SORE[level || 0];
const stripFill = (level) => (level ? SORE[level] : "var(--c-band)");

// a cell per morning; under it, a short bar on the days that region was trained (as noted after the workout)
function stripSvg(days, width) {
  const n = days.length, gap = 3, w = (width - gap * (n - 1)) / n, h = 14, H = 19;
  return `<svg viewBox="0 0 ${width} ${H}" width="${width}" height="${H}" aria-hidden="true">${days.map((d, i) => {
    const x = (i * (w + gap)).toFixed(1);
    const tip = `${shortDay(d.date)} · ${d.level == null ? t("sore.unchecked") : t(`sore.level.${d.level}`)}${d.trained ? ` · ${t("sore.trained_that_day")}` : ""}`;
    return `<rect x="${x}" y="0" width="${w.toFixed(1)}" height="${h}" rx="3" fill="${d.level == null ? "none" : stripFill(d.level)}"
      stroke="${d.level == null ? "var(--line-2)" : "none"}" stroke-dasharray="${d.level == null ? "2 2" : ""}" data-tip="${esc(tip)}"/>${d.trained
      ? `<rect x="${x}" y="${h + 2}" width="${w.toFixed(1)}" height="3" rx="1.5" fill="var(--c-exercise)"/>` : ""}`;
  }).join("")}</svg>`;
}

// The one place to say how you are: energy right now (0–10, kept with its time), this morning's feeling (2 / 5 / 8) and
// where you are sore (chosen on the body above, a little / clearly / very), and mind and task for Rest & rewards. One
// save writes each answer where it already lives (recovery_observations.jsonl, self_report.csv and soreness.csv,
// restore.jsonl); anything left unanswered is not written.
const MIND = ["clear", "tired", "tense", "bored", "engaged"], TASK = ["easy", "fit", "hard"];
const sameDay = (iso, d) => Boolean(iso) && iso.slice(0, 10) === d;
const pressed = (on) => `aria-pressed="${Boolean(on)}"`;

function soreList(levels, known) {
  const set = Object.entries(levels).filter(([, lv]) => lv > 0);
  if (!set.length) return `<span class="small muted">${t(known ? "sore.none_short" : "now.sore_none_yet")}</span>`;
  return set.sort((a, b) => b[1] - a[1]).map(([r, lv]) => `<span class="chip now-sore-chip"><i style="background:${fill(lv)}"></i>${esc(t(`sore.region.${r}`))} · ${esc(t(`sore.level.${lv}`))}</span>`).join("");
}

function lastSaved(p) {
  const e = p.current_ratings?.energy, c = p.restore?.situation?.checkin;
  const parts = [], times = [];
  if (e && sameDay(e.recorded_at, p.today)) { parts.push(t("now.energy_value", { v: num(e.value) })); times.push(e.recorded_at); }
  if (c) { ["mind", "task"].forEach((k) => { if (c[k]) parts.push(t(`rr.${k}.${c[k]}`)); }); times.push(c.at); }
  if (p.feel_today != null) parts.push(t(`feel.${p.feel_today}`));
  if (!parts.length) return t("now.last_none");
  const latest = times.sort().at(-1);
  return latest ? t("now.last", { time: clock(latest), what: parts.join(t("ui.list_sep")) }) : t("now.last_morning", { what: parts.join(t("ui.list_sep")) });
}

// where it feels tight after sitting (care_log): pick places and how they feel, or say it in a sentence and let the
// reader (rules, or the assistant when it is on) pick them; then "anywhere else?", what it may be from, and the warning
// signs once something is painful. Saved with the rest of the card.
function tightHtml(p) {
  const C = p.care_choices, R = p.care?.report;
  const reader = C.assistant.on ? t("care.reader.assistant") : t("care.reader.rules");
  return `<details class="care-tight"${R && sameDay(R.at, p.today) ? " open" : ""}><summary>${t("care.title")}<span class="xs muted"> · ${t("care.sub")}</span></summary>
    <div class="care-say"><input type="text" id="care-said" maxlength="280" placeholder="${esc(t("care.say_placeholder"))}" aria-label="${esc(t("care.title"))}">
      <button type="button" class="goal-btn" id="care-read"${isStatic ? " disabled" : ""}>${t("care.read")}</button></div>
    <p class="xs muted care-reader" role="status">${esc(reader)}</p>
    <div class="now-btns care-regions">${C.regions.map((r) => `<button type="button" class="goal-btn care-region" data-region="${r}" aria-pressed="false">${t(`care.region.${r}`)}</button>`).join("")}</div>
    <div class="care-picked"></div>
    <p class="small care-also" hidden></p>
    <div class="now-row"><span class="small now-label">${t("care.cause")}</span><span class="now-btns">${["sitting", "training", "other"].map((c) => `<button type="button" class="goal-btn care-cause" data-cause="${c}" aria-pressed="false">${t(`care.cause.${c}`)}</button>`).join("")}</span></div>
    <div class="now-row care-signs" hidden><span class="small now-label">${t("care.signs")}</span><span class="now-btns">${C.signs.map((x) => `<button type="button" class="goal-btn care-sign" data-sign="${x}" aria-pressed="false">${t(`care.sign.${x}`)}</button>`).join("")}</span></div>
  </details>`;
}

// what was said (today or yesterday), what may be behind it, the moves, and the next day's question
function careHtml(p) {
  const C = p.care;
  if (!C || (!C.report && !C.ask.length)) return "";
  const R = C.report, M = C.moves;
  const list = R ? Object.entries(R.tight).map(([r, f]) => `${t(`care.region.${r}`)}${t(`care.feel.${f}`)}`).join(t("ui.list_sep")) : "";
  const S = C.maybe_sitting;
  return `<section class="card span-12 care-card" id="care"><h2>${t("care.card_title")}<span class="aside">${t("care.card_sub")}</span></h2>
    ${R ? `<p class="lede" style="font-size:var(--t-lg);margin:0 0 4px">${esc(t("care.reported", { when: `${sameDay(R.at, p.today) ? t("care.today") : t("care.yesterday")} ${clock(R.at)}`, list }))}</p>
      <p class="small muted" style="margin:0">${[R.cause ? t("care.cause_said", { cause: t(`care.cause.${R.cause}`) }) : "", R.said ? `“${esc(R.said)}”` : ""].filter(Boolean).join(" · ")}</p>
      ${S ? `<p class="small care-sitting">${icon("laptop", 14)} ${esc(t("care.maybe_sitting", { day: day(S.date, { weekday: false }), d: dur(S.longest) }))}</p>` : ""}` : ""}
    ${M?.blocked ? `<p class="care-blocked">${esc(t("care.blocked", { signs: R.signs.map((x) => t(`care.sign.${x}`)).join(t("ui.list_sep")) }))}</p>${stopLine(C.stop)}` : ""}
    ${M && !M.blocked ? `${M.stop_first ? stopLine(C.stop) : ""}<h3 class="section-title" style="margin-top:var(--s-3)">${t("care.moves")}</h3>
      <div class="routines">${M.routines.map((id) => routineHtml(id, C.info, { why: "care" })).join("")}</div>${M.stop_first ? "" : stopLine(C.stop)}` : ""}
    ${C.done_today.length ? `<p class="xs muted" style="margin:var(--s-2) 0 0">${esc(t("care.done_list", { n: C.done_today.length }))}</p>` : ""}
    ${askHtml(C.ask)}</section>`;
}

function nowHtml(p) {
  const S = p.soreness, levels = S.today ? S.levels : {};
  const askedRegions = [...new Set(S.asked.flatMap((a) => a.regions))];
  const askedHead = S.asked.map((a) => t("asked.what", { day: day(a.date), what: wtype(a.type) })).join(t("ui.list_sep"));
  const asked = askedRegions.length ? `<div class="asked"><p class="small" style="margin:0 0 var(--s-2)">${icon("exercise", 14)} ${esc(t("asked.head", { what: askedHead }))}</p>
    ${askedRegions.map((r) => `<div class="lvl-row" role="group" aria-label="${esc(t(`sore.region.${r}`))}"><span class="small">${t(`sore.region.${r}`)}</span>
      <span class="lvl-btns">${[0, 1, 2, 3].map((lv) => `<button type="button" class="goal-btn lvl-btn" data-region="${r}" data-level="${lv}" ${pressed((levels[r] || 0) === lv && S.today)}>${t(`sore.level.${lv}`)}</button>`).join("")}</span></div>`).join("")}</div>` : "";
  const rows = S.regions.map((r, i) => `<div class="sore-row"><span>${t(`sore.region.${r.key}`)}</span>
    <span class="xs muted">${t("sore.days", { n: r.sore_days, k: S.checked })}</span><div class="sore-strip" data-i="${i}"></div></div>`).join("");
  const c = p.restore?.situation?.checkin;
  const choices = (field, values) => `<div class="now-row" role="group" aria-label="${esc(t(`rr.${field}`))}"><span class="small now-label">${t(`rr.${field}`)}</span>
    <span class="now-btns">${values.map((v) => `<button type="button" class="goal-btn now-choice" data-field="${field}" data-value="${v}" ${pressed(c?.[field] === v)}>${t(`rr.${field}.${v}`)}</button>`).join("")}</span></div>`;
  return `<section class="card span-12 rec-now" id="now"><h2>${t("now.title")}<span class="aside">${t("now.sub")}</span></h2>
    <p class="small muted now-last">${esc(lastSaved(p))}</p>
    <div class="now-grid"><div>
      <div class="now-row" role="group" aria-label="${esc(t("now.energy"))}"><span class="small now-label">${t("now.energy")}</span>
        <span class="now-btns now-scale">${Array.from({ length: 11 }, (_, v) => `<button type="button" class="goal-btn now-energy" data-energy="${v}" ${pressed(false)}>${v}</button>`).join("")}</span>
        <span class="xs muted now-ends">${t("now.energy_ends")}</span></div>
      <div class="now-row" role="group" aria-label="${esc(t("feel.question"))}"><span class="small now-label">${t("feel.question")}</span>
        <span class="now-btns">${[2, 5, 8].map((v) => `<button type="button" class="goal-btn feel-btn" data-feel="${v}" ${pressed(p.feel_today === v)}>${t(`feel.${v}`)}</button>`).join("")}</span></div>
      ${p.restore ? choices("mind", MIND) + choices("task", TASK) : ""}
    </div><div>
      <div class="now-row"><span class="small now-label">${t("now.sore")}</span><span class="now-sore-list">${soreList(levels, S.today)}</span></div>
      <p class="xs muted" style="margin:0 0 var(--s-2)">${t(S.today ? "sore.head_today" : "now.sore_hint")}${S.today ? ` · ${t("now.sore_hint")}` : ""}</p>
      ${asked}
      <button type="button" class="goal-btn" id="sore-clear">${rv("confirmNoSoreness")}</button>
    </div></div>
    ${tightHtml(p)}
    <div class="goal-act"><button type="button" class="goal-btn primary" id="now-save"${isStatic ? " disabled" : ""}>${t("now.save")}</button></div>
    <p class="xs now-msg" role="status">${isStatic ? t("now.static") : ""}</p>
    <details class="how now-history"><summary>${t("sore.last_days", { n: S.days })}</summary>
      <div class="sore-rows">${rows}</div><p class="xs muted sore-key"><i></i>${t("sore.trained_key")}</p></details>
    <details class="how"><summary>${t("ui.how")}</summary><p>${t("now.rule")}</p></details></section>`;
}

export default {
  render(p) {
    return `<div class="head"><div><h1>${rv("title")}</h1><div class="sub">${rv("sub")}</div></div></div>
      ${overviewHtml(p)}
      <div class="grid">
        ${nowHtml(p)}
        ${careHtml(p)}
        ${afterHtml(p)}
        <h2 class="span-12 doc-section rec-long" id="drain">${t("drain.title")}<span class="aside">${t("drain.sub", { from: day(p.drain.window.from, { weekday: false }), to: day(p.drain.window.to, { weekday: false }) })}</span></h2>
        ${drainCards(p.drain)}
        ${p.hrv_prediction?.training ? `<div class="span-12">${hrvModelHtml(p.hrv_prediction)}</div>` : ""}
        <section class="card span-12"><details class="how"><summary>${t("ui.how")}</summary>
          <p>${t("rec.rule_after", { good: num(p.after.rule.good, 1), low: num(p.after.rule.low, 1), n: p.after.rule.after_days })}</p>
          <p>${t("sore.rule", { n: p.rule.sore_days })}</p></details></section>
      </div>`;
  },
  mount(root, p) {
    mountDrain(root, p.drain);
    const A = p.after, scored = A.days.filter((d) => d.score != null);
    const dotTip = (d) => [day(d.date), sessionsText(d), d.trained.length ? `${t("after.trained")} ${regionsShort(d.trained)}` : "", t("after.tip_score", { v: num(d.score, 1) })].filter(Boolean).join(" · ");
    const dots = root.querySelector("#after-dots");
    if (dots) draw(dots, (w) => scoreDots(scored.map((d) => ({ date: d.date, value: d.score, tip: dotTip(d) })),
      { width: w, first: isoBack(p.day, A.rule.after_days - 1), last: p.day, band: { low: A.rule.low, high: A.rule.good }, refs: [{ value: 5, label: t("after.usual") }], fmt: (v) => num(v, Number.isInteger(v) ? 0 : 1) }));
    const S = p.soreness;
    root.querySelectorAll(".sore-strip").forEach((el) => draw(el, (w) => stripSvg(S.regions[el.dataset.i].days, w)));
    // soreness is chosen on the illustrated body above (a region, then a level) or with the buttons of the parts a
    // recent workout trained; both stay in step, and nothing is saved until Save
    const levels = { ...(S.today ? S.levels : {}) };
    let overview, sorenessChanged = false;
    const list = root.querySelector(".now-sore-list");
    const set = (r, lv) => {
      sorenessChanged = true;
      if (lv) levels[r] = lv; else delete levels[r];
      root.querySelectorAll(`.lvl-btn[data-region="${r}"]`).forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.level) === (lv || 0))));
      list.innerHTML = soreList(levels, true);
      overview?.setLevels(levels);
    };
    overview = mountOverview(root, p, { onLevel: set, openEditor() {
      const card = root.querySelector("#now");
      card.scrollIntoView({ behavior: "smooth", block: "start" }); card.querySelector("#now-save").focus({ preventScroll: true });
    } });
    root.querySelectorAll(".lvl-btn").forEach((b) => { b.onclick = () => set(b.dataset.region, Number(b.dataset.level)); });
    root.querySelector("#sore-clear").onclick = () => { Object.keys(levels).forEach((r) => set(r, 0)); sorenessChanged = true; list.innerHTML = soreList(levels, true); overview?.setLevels(levels); };
    // a training day with nothing written about what it trained: the same dialog as the prompt after a workout
    root.querySelectorAll("[data-note]").forEach((b) => {
      b.onclick = () => {
        const d = p.after.days.find((x) => x.date === b.dataset.note);
        const s = d?.sessions.find((x) => x.hard && x.note == null);
        if (s) openTrained({ figure: p.figure, regions: p.regions, words: p.words }, { ...s, date: d.date });
      };
    });
    // one choice per row; pressing the chosen one again takes it back
    const choice = { energy: null, feel: p.feel_today ?? null, mind: p.restore?.situation?.checkin?.mind ?? null, task: p.restore?.situation?.checkin?.task ?? null };
    const start = { ...choice };
    const toggle = (sel, key, read) => root.querySelectorAll(sel).forEach((b) => {
      b.onclick = () => {
        choice[key] = choice[key] === read(b) ? null : read(b);
        root.querySelectorAll(sel).forEach((x) => x.setAttribute("aria-pressed", String(read(x) === choice[key])));
      };
    });
    toggle(".now-energy", "energy", (b) => Number(b.dataset.energy));
    toggle(".feel-btn", "feel", (b) => Number(b.dataset.feel));
    toggle('.now-choice[data-field="mind"]', "mind", (b) => b.dataset.value);
    toggle('.now-choice[data-field="task"]', "task", (b) => b.dataset.value);
    // where it feels tight: places, how each feels, what it may be from, warning signs, what was said and who read it
    const tight = {}, signs = new Set();
    let cause = null, said = "", parsedBy = null;
    const picked = root.querySelector(".care-picked"), signsRow = root.querySelector(".care-signs"), also = root.querySelector(".care-also");
    const paint = () => {
      root.querySelectorAll(".care-region").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.region in tight)));
      picked.innerHTML = Object.entries(tight).map(([r, f]) => `<div class="now-row"><span class="small now-label">${t(`care.region.${r}`)}</span>
        <span class="now-btns">${p.care_choices.feelings.map((x) => `<button type="button" class="goal-btn care-feel" data-region="${r}" data-feel="${x}" aria-pressed="${x === f}">${t(`care.feel.${x}`)}</button>`).join("")}</span></div>`).join("");
      picked.querySelectorAll(".care-feel").forEach((b) => { b.onclick = () => { tight[b.dataset.region] = b.dataset.feel; paint(); }; });
      root.querySelectorAll(".care-cause").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.cause === cause)));
      root.querySelectorAll(".care-sign").forEach((b) => b.setAttribute("aria-pressed", String(signs.has(b.dataset.sign))));
      signsRow.hidden = !(Object.values(tight).includes("pain") || signs.size);
    };
    root.querySelectorAll(".care-region").forEach((b) => { b.onclick = () => { if (b.dataset.region in tight) delete tight[b.dataset.region]; else tight[b.dataset.region] = "tight"; paint(); }; });
    root.querySelectorAll(".care-cause").forEach((b) => { b.onclick = () => { cause = cause === b.dataset.cause ? null : b.dataset.cause; paint(); }; });
    root.querySelectorAll(".care-sign").forEach((b) => { b.onclick = () => { if (signs.has(b.dataset.sign)) signs.delete(b.dataset.sign); else signs.add(b.dataset.sign); paint(); }; });
    const readBtn = root.querySelector("#care-read"), reader = root.querySelector(".care-reader");
    if (readBtn) readBtn.onclick = async () => {
      said = root.querySelector("#care-said").value.trim();
      if (!said || isStatic) return;
      readBtn.disabled = true; reader.textContent = t("care.reading");
      try {
        const out = await post("care-parse", { said });
        Object.assign(tight, out.tight); out.signs.forEach((x) => signs.add(x));
        if (out.cause) cause = out.cause;
        parsedBy = out.parsed_by;
        reader.textContent = out.parsed_by === "assistant" ? t("care.read_by.assistant") : t(`care.read_by.rules${out.assistant ? `_${out.assistant}` : ""}`);
        also.hidden = !out.also_ask.length;
        also.innerHTML = `${t("care.also")} ${out.also_ask.map((r) => `<button type="button" class="goal-btn care-also-btn" data-region="${r}">${t(`care.region.${r}`)}</button>`).join(" ")}`;
        also.querySelectorAll(".care-also-btn").forEach((b) => { b.onclick = () => { tight[b.dataset.region] = "tight"; b.remove(); paint(); }; });
        paint();
      } catch (error) {
        reader.textContent = t("care.err", { e: error.message });
      } finally { readBtn.disabled = false; }
    };
    mountCare(root);
    mountAsk(root);
    // a retry after a failed save reuses the request id of an unchanged answer, so nothing is written twice
    const ids = {};
    const once = (name, body) => { const sig = JSON.stringify(body); if (ids[name]?.sig !== sig) ids[name] = { sig, id: crypto.randomUUID() }; return { ...body, request_id: ids[name].id }; };
    const msg = root.querySelector(".now-msg");
    root.querySelector("#now-save").onclick = async () => {
      if (isStatic) return;
      const feelChanged = choice.feel !== start.feel, moodChanged = choice.mind !== start.mind || choice.task !== start.task;
      // Rest & rewards reads the body as tired, comfortable or sore: energy 3 or lower is tired, 6 or higher comfortable,
      // and a region clearly sore or worse today is sore (docs/REST_AND_REWARDS.md)
      const soreToday = (sorenessChanged || S.today) && Object.values(levels).some((lv) => lv >= 2);
      const body = soreToday ? "sore" : choice.energy == null ? null : choice.energy <= 3 ? "tired" : choice.energy >= 6 ? "comfortable" : null;
      const writes = [];
      if (choice.energy != null) writes.push(["recovery-checkin", once("energy", { kind: "energy", region: null, value: choice.energy })]);
      if (feelChanged || sorenessChanged) writes.push(["checkin", { date: p.today, levels: sorenessChanged ? levels : null, feel: choice.feel }]);
      if ((body || choice.mind || choice.task) && (moodChanged || choice.energy != null || sorenessChanged))
        writes.push(["restore", once("restore", { op: "checkin", body, mind: choice.mind, task: choice.task })]);
      if (Object.keys(tight).length) {
        said = root.querySelector("#care-said")?.value.trim() || said;
        writes.push(["care", once("care", { op: "report", tight: { ...tight }, said, signs: [...signs], cause, parsed_by: parsedBy })]);
      }
      if (!writes.length) { msg.textContent = t("now.nothing"); return; }
      const save = root.querySelector("#now-save");
      save.disabled = true; msg.textContent = t("rr.saving");
      try {
        for (const [name, body] of writes) await post(name, body);
        window.dispatchEvent(new HashChangeEvent("hashchange"));
      } catch (error) {
        msg.textContent = t("sore.err", { e: error.message });
        save.disabled = false;
      }
    };
  },
};
