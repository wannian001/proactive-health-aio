// Recovery (#recovery, under Body signals): how recovered you are (the Today page's verdict), the morning check-in
// (how you feel, 2 / 5 / 8, and where you are sore on the body figure from the author's GEOM90007 Ready to Train
// project; saved into self_report.csv and soreness.csv; the parts a recent workout trained are asked about first,
// a button per level), the score the morning after each training day (four parts side by side, averaged, with what
// it trained and how sore that was), and how your body has answered training. What training asked of you is on
// Body & mind load. The rules are in modules/recovery.py.
import { isStatic, post } from "../api.js";
import { checkinHtml, mountRestore } from "../restore-ui.js";
import { bullet, draw, esc, scoreDots } from "../charts.js";
import { figureSvg, mountFigure } from "../figure.js";
import { day, dur, measure, num, shortDay, t, toDate, wtype } from "../i18n.js";
import { icon, STATE_ICON } from "../icons.js";
import { openTrained } from "../trained.js";
import { compareHtml, mountCompare } from "./effects.js";
import { overviewHtml, mountOverview } from "../recovery-overview.js";
import { rv } from "../recovery-copy.js";

const toneCls = (tone) => (tone === "good" ? "good" : tone === "bad" ? "bad" : "");
const LOAD_TONE = { high: "watch", low: "", steady: "good" };

function stateChip(m) {
  if (m.partial) return `<span class="chip">${t("state.partial")}</span>`;
  if (!m.state) return `<span class="chip">${t("state.none")}</span>`;
  return `<span class="chip ${toneCls(m.tone)}">${STATE_ICON[m.tone] || ""}${t(`state.${m.state}`)}</span>`;
}

function tile(m) {
  const band = m.band ? t("band", { low: measure(m.band.q1, m.unit), high: measure(m.band.q3, m.unit) }) : "";
  return `<div class="tile act-tile">
    <div class="label"><span class="act-name">${icon(m.key === "sleep" ? "sleep" : "heart", 16)}<span>${t(`metric.${m.key}`)}</span></span>${stateChip(m)}</div>
    <div class="act-value"><div class="value">${measure(m.value, m.unit)}</div></div>
    <div class="bul" data-key="${m.key}"></div>
    <div class="note"><span class="piece">${esc(band)}</span></div></div>`;
}

const regionsText = (levels) => Object.entries(levels).sort((a, b) => b[1] - a[1])
  .map(([r, lv]) => t("sore.with_level", { region: t(`sore.region.${r}`), level: t(`sore.level_short.${lv}`) })).join(t("ui.list_sep"));
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

function heroHtml(p) {
  const r = p.recovery, L = p.load, S = p.soreness;
  const loadChip = L.state === "none" || L.state === "unknown" || L.state === "few_ratings"
    ? `<span class="chip">${t(`rec.load.${L.state}`)}</span>`
    : `<span class="chip ${LOAD_TONE[L.state]}">${t(`rec.load.${L.state}`)}</span>`;
  const sore = S.today ? (Object.keys(S.levels).length ? regionsText(S.levels) : t("sore.none_today")) : t("sore.not_today");
  return `<section class="card span-12"><span class="eyebrow">${t("recovery.eyebrow")}${r.as_of ? ` · ${esc(day(r.as_of))}` : ""}</span>
    <p class="lede" style="margin:6px 0 var(--s-3)">${t(`recovery.${r.verdict}`)}</p>
    <div class="rec-facts"><a class="rec-fact" href="#load">${icon("exercise", 16)}<span>${t("rec.load_title")}</span>${loadChip}</a>
      <span class="rec-fact">${icon("heart", 16)}<span>${t("sore.title")}</span><span class="chip">${esc(sore)}</span></span></div>
    <div class="tiles act-tiles" style="margin-top:var(--s-4)">${r.metrics.map(tile).join("")}</div>
    <p class="xs muted" style="margin:var(--s-3) 0 0">${t("rec.verdict_note")}</p></section>`;
}

// ---- the morning after each training day: four parts side by side, averaged ---------------------------------
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
function outcomeText(r, R) {
  const unit = R.units[r.outcome];
  const show = (v) => (unit === "%" ? `${num(Math.abs(v), 1)}%` : unit === "bpm" ? t("stim.bpm", { v: num(Math.abs(v), 1) }) : t("rec.levels", { v: num(Math.abs(v), 1) }));
  const range = (v) => `${v < 0 ? "−" : ""}${unit === "%" ? `${num(Math.abs(v), 1)}%` : num(Math.abs(v), 1)}`;
  return t("stim.out_line", { dir: t(`rec.out.${r.outcome}.${r.diff >= 0 ? "up" : "down"}`, { v: show(r.diff) }), low: range(r.low), high: range(r.high) });
}

function responseHtml(p) {
  const R = p.response;
  const head = R.median_load != null ? t("rec.exp", { v: num(R.median_load) }) : t("rec.exp_none", { n: R.method.min_group_days });
  const rows = compareHtml(R.rows, { name: (r) => t(`rec.out.${r.outcome}`), better: (r) => R.better[r.outcome],
    text: (r) => (r.status === "ok" ? outcomeText(r, R) : t("stim.too_few_line", { a: r.yes_days, b: r.no_days, n: R.method.min_group_days })) });
  return `<section class="card span-12"><h2>${t("rec.body_title")}<span class="aside">${t("rec.body_sub", { n: p.rule.response_days })}</span></h2>
    <h3 class="section-title">${esc(head)}</h3><div id="rec-compare">${rows}</div>
    <p class="xs muted" style="margin:10px 0 0">${t("rec.body_note")}</p></section>`;
}

// ---- soreness: the body figure (tap a region to set its level), the list, 14 days per region -------------------
// one hue getting stronger (--c-sore-1..3); "not sore" on the figure is --c-sore-0 and on the strips the band colour.
// The figure follows light and dark mode (figure.js)
const SORE = ["var(--c-sore-0)", "var(--c-sore-1)", "var(--c-sore-2)", "var(--c-sore-3)"];
const fill = (level) => SORE[level || 0];
const stripFill = (level) => (level ? SORE[level] : "var(--c-band)");
const soreLabel = (r, lv) => t("sore.region_aria", { region: t(`sore.region.${r}`), level: t(`sore.level.${lv || 0}`) });

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

function sorenessHtml(p) {
  const S = p.soreness;
  const head = S.today ? t("sore.head_today") : S.latest ? t("sore.head_latest", { day: day(S.latest) }) : t("sore.head_none");
  const legend = [0, 1, 2, 3].map((lv) => `<span class="key"><i style="background:${fill(lv)}"></i>${t(`sore.level.${lv}`)}</span>`).join("");
  const levels = S.today ? S.levels : {};
  const askedRegions = [...new Set(S.asked.flatMap((a) => a.regions))];
  const askedHead = S.asked.map((a) => t("asked.what", { day: day(a.date), what: wtype(a.type) })).join(t("ui.list_sep"));
  const asked = askedRegions.length ? `<div class="asked"><p class="small" style="margin:0 0 var(--s-2)">${icon("exercise", 14)} ${esc(t("asked.head", { what: askedHead }))}</p>
    ${askedRegions.map((r) => `<div class="lvl-row" role="group" aria-label="${esc(t(`sore.region.${r}`))}"><span class="small">${t(`sore.region.${r}`)}</span>
      <span class="lvl-btns">${[0, 1, 2, 3].map((lv) => `<button type="button" class="goal-btn lvl-btn" data-region="${r}" data-level="${lv}" aria-pressed="${(levels[r] || 0) === lv && S.today}">${t(`sore.level.${lv}`)}</button>`).join("")}</span></div>`).join("")}</div>` : "";
  const rows = S.regions.map((r, i) => `<div class="sore-row"><span>${t(`sore.region.${r.key}`)}</span>
    <span class="xs muted">${t("sore.days", { n: r.sore_days, k: S.checked })}</span><div class="sore-strip" data-i="${i}"></div></div>`).join("");
  return `<section class="card span-12"><h2>${t("sore.title")}<span class="aside">${t("sore.sub")}</span></h2>
    <div class="sore-layout">
      <div class="fig-plate">${figureSvg(p, Object.fromEntries(p.regions.map((r) => [r, fill(levels[r])])), (r) => soreLabel(r, levels[r]))}
        <div class="legend fig-legend">${legend}</div></div>
      <div class="sore-side">
        <p class="lede" style="font-size:var(--t-lg);margin:0 0 4px">${esc(head)}</p>
        <p class="small muted" style="margin:0 0 var(--s-3)">${S.latest && !S.today ? esc(t("sore.latest_was", { list: Object.keys(S.levels).length ? regionsText(S.levels) : t("sore.none_short") })) : ""}</p>
        <div class="feel-row" role="group" aria-label="${esc(t("feel.question"))}"><span class="small">${t("feel.question")}</span>
          ${[2, 5, 8].map((v) => `<button type="button" class="goal-btn feel-btn" data-feel="${v}" aria-pressed="${p.feel_today === v}">${t(`feel.${v}`)}</button>`).join("")}</div>
        <div class="feel-row" role="group" aria-label="${esc(rv("energyQuestion"))}"><span class="small">${rv("energyQuestion")}</span>
          ${[0, 1, 2, 3, 4, 5].map(v => `<button type="button" class="goal-btn energy-btn" data-energy="${v}" aria-pressed="${p.self?.date === p.day && p.self.energy === v}">${v}</button>`).join("")}</div>
        <p class="xs muted">${rv("energyHint")}</p>
        ${asked}
        <p class="small" style="margin:var(--s-3) 0 var(--s-2)">${askedRegions.length ? t("sore.how_to_rest") : rv("soreOptionalHint")}</p>
        <div class="goal-act"><button type="button" class="goal-btn primary" id="sore-save"${isStatic ? " disabled" : ""}>${t("sore.save")}</button>
          <button type="button" class="goal-btn" id="sore-clear">${rv("confirmNoSoreness")}</button></div>
        <p class="xs sore-msg" role="status">${isStatic ? t("sore.static") : ""}</p>
        <h3 class="section-title" style="margin-top:var(--s-4)">${t("sore.last_days", { n: S.days })}</h3>
        <div class="sore-rows">${rows}</div>
        <p class="xs muted sore-key"><i></i>${t("sore.trained_key")}</p>
      </div></div>
    <p class="xs muted" style="margin:var(--s-3) 0 0">${t("sore.credit")}</p></section>`;
}

export default {
  render(p) {
    return `<div class="head"><div><h1>${rv("title")}</h1><div class="sub">${rv("sub")}</div></div></div>
      ${overviewHtml(p)}
      <div class="grid">
        ${p.restore ? `<section class="card span-12"><h2>${t("rr.mind")}</h2>${checkinHtml(p.restore, true)}<p class="small"><a href="#restore">${t("rr.choose")} →</a></p></section>` : ""}
        <details class="card span-12 rec-checkin"><summary>${rv("editor")}</summary>${sorenessHtml(p)}</details>
        ${afterHtml(p)}
        ${responseHtml(p)}
        <section class="card span-12"><details class="how"><summary>${t("ui.how")}</summary>
          <p>${t("rec.rule_after", { good: num(p.after.rule.good, 1), low: num(p.after.rule.low, 1), n: p.after.rule.after_days })}</p>
          <p>${t("rec.rule_body", { n: p.rule.response_days, k: p.response.method.min_group_days })}</p>
          <p>${t("sore.rule", { n: p.rule.sore_days })}</p></details></section>
      </div>`;
  },
  mount(root, p) {
    mountRestore(root);
    root.querySelectorAll(".bul").forEach((el) => {
      const m = p.recovery.metrics.find((x) => x.key === el.dataset.key);
      draw(el, (w) => bullet(m.value, m.band, { width: w, unit: m.unit, tone: m.tone }));
    });
    mountCompare(root.querySelector("#rec-compare"), p.response.rows);
    const A = p.after, scored = A.days.filter((d) => d.score != null);
    const dotTip = (d) => [day(d.date), sessionsText(d), d.trained.length ? `${t("after.trained")} ${regionsShort(d.trained)}` : "", t("after.tip_score", { v: num(d.score, 1) })].filter(Boolean).join(" · ");
    const dots = root.querySelector("#after-dots");
    if (dots) draw(dots, (w) => scoreDots(scored.map((d) => ({ date: d.date, value: d.score, tip: dotTip(d) })),
      { width: w, first: isoBack(p.day, A.rule.after_days - 1), last: p.day, band: { low: A.rule.low, high: A.rule.good }, refs: [{ value: 5, label: t("after.usual") }], fmt: (v) => num(v, Number.isInteger(v) ? 0 : 1) }));
    const S = p.soreness;
    root.querySelectorAll(".sore-strip").forEach((el) => draw(el, (w) => stripSvg(S.regions[el.dataset.i].days, w)));
    // tap a region: none → a little → clearly → very → none; the buttons of the parts a recent workout trained set
    // a level directly, and both stay in step
    const levels = { ...(S.today ? S.levels : {}) };
    const svg = root.querySelector(".sore-layout .fig");
    let overview;
    let sorenessChanged = S.today;
    const set = (r, lv) => {
      sorenessChanged = true;
      if (lv) levels[r] = lv; else delete levels[r];
      const g = svg.querySelector(`.fig-region[data-region="${r}"]`);
      g.style.fill = fill(lv);
      g.setAttribute("aria-label", soreLabel(r, lv));
      root.querySelectorAll(`.lvl-btn[data-region="${r}"]`).forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.level) === (lv || 0))));
      overview?.setLevels(levels);
    };
    overview = mountOverview(root, p, { onLevel: set, openEditor() {
      const details = root.querySelector(".rec-checkin"); details.open = true;
      details.scrollIntoView({ behavior: "smooth", block: "start" }); details.querySelector("summary").focus();
    } });
    mountFigure(svg, p, { tap: (r) => set(r, ((levels[r] || 0) + 1) % 4), tip: (r) => `${t(`sore.region.${r}`)} · ${t(`sore.level.${levels[r] || 0}`)}` });
    root.querySelectorAll(".lvl-btn").forEach((b) => { b.onclick = () => set(b.dataset.region, Number(b.dataset.level)); });
    // a training day with nothing written about what it trained: the same dialog as the prompt after a workout
    root.querySelectorAll("[data-note]").forEach((b) => {
      b.onclick = () => {
        const d = p.after.days.find((x) => x.date === b.dataset.note);
        const s = d?.sessions.find((x) => x.hard && x.note == null);
        if (s) openTrained({ figure: p.figure, regions: p.regions, words: p.words }, { ...s, date: d.date });
      };
    });
    let feel = p.feel_today ?? null;
    let energy = p.self?.date === p.day ? p.self.energy : null;
    root.querySelectorAll(".energy-btn").forEach(b => { b.onclick = () => {
      energy = Number(b.dataset.energy);
      root.querySelectorAll(".energy-btn").forEach(x => x.setAttribute("aria-pressed", String(Number(x.dataset.energy) === energy)));
    }; });
    root.querySelectorAll(".feel-btn").forEach((b) => {
      b.onclick = () => {
        feel = feel === Number(b.dataset.feel) ? null : Number(b.dataset.feel);
        root.querySelectorAll(".feel-btn").forEach((x) => x.setAttribute("aria-pressed", String(Number(x.dataset.feel) === feel)));
      };
    });
    root.querySelector("#sore-clear").onclick = () => { sorenessChanged = true; Object.keys(levels).forEach((r) => set(r, 0)); overview?.setLevels(levels); };
    const msg = root.querySelector(".sore-msg");
    root.querySelector("#sore-save").onclick = async () => {
      if (isStatic) return;
      try {
        await post("checkin", { date: p.today, levels: sorenessChanged ? levels : null, feel, energy });
        window.dispatchEvent(new HashChangeEvent("hashchange"));
      } catch (error) {
        msg.textContent = t("sore.err", { e: error.message });
      }
    };
  },
};
