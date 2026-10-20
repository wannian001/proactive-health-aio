// Goals: every plan in one place and on how many days it was kept, grouped by part of life. Counts, never streaks
// or scores. A goal can be set right here (Edit, or Set one for a plan not set yet): the change is a line in
// goals.jsonl laid over healthaio.toml, and every page is computed again. An assistant's proposals wait at the top
// until you accept or decline them. The online demo has no server, so there the form shows but does not save.
import { isStatic, post } from "../api.js?v=51ede4cbfe";
import { draw, esc, keptDots } from "../charts.js?v=51ede4cbfe";
import { day, dur, getLang, inSentence, num, shortDay, t } from "../i18n.js?v=51ede4cbfe";
import { icon } from "../icons.js?v=51ede4cbfe";

const DOMAIN_ICON = { sleep: "sleep", exercise: "exercise", food: "food", body: "heart", screens: "screen" };
const SOURCE = { plan: "goals.src.plan", guideline: "goals.src.who", rule: "goals.src.rule" };

// a number as typed: 2.5 stays 2.5 (goals set here can take half hours), 8 stays 8
const places = (v) => (Number.isInteger(v) ? 0 : Number.isInteger(v * 10) ? 1 : 2);
const n = (v) => num(v, places(v));

function goalName(r) {
  const g = r.target || {};
  switch (r.key) {
    case "asleep_in_time": return g.clock ? t("goals.asleep_clock", { clock: g.clock }) : t("goals.asleep_alarm", { h: n(g.before_alarm_h) });
    case "slept_enough": return t("goals.slept", { h: n(g.hours) });
    case "woke_on_time": return g.shift ? t("goals.woke_shift") : t("goals.woke_clock", { clock: g.clock });
    case "calm_last_hour": return t("goals.calm", { min: num(g.min) });
    case "weekly_min": return t("goals.weekly_min", { d: dur(g.value) });
    case "strength_days": return t("goals.strength", { n: n(g.value) });
    case "kcal_range": return g.low != null && g.high != null ? t("goals.kcal_range", { a: num(g.low), b: num(g.high) }) : g.high != null ? t("goals.kcal_max", { b: num(g.high) }) : t("goals.kcal_min", { a: num(g.low) });
    case "protein": return g.per_kg ? t("goals.protein_kg", { g: num(g.grams), per: num(g.per_kg, 1) }) : t("goals.protein", { g: num(g.grams) });
    case "last_meal": return t("goals.last_meal", { h: n(g.hours) });
    case "weight_pace": return t("goals.weight", { kg: num(g.target_kg, 1), lo: num(Math.min(...g.weekly_loss_pct), 1), hi: num(Math.max(...g.weekly_loss_pct), 1) });
    case "focus_min": return t("goals.focus", { h: n(g.hours) });
    case "fun_max": return t("goals.fun", { h: n(g.hours) });
    default: return r.key;
  }
}

// a value of a goal field in words: a clock as it is, a number with its unit
const value = (f, v) => (v == null ? "—" : f.type === "clock" ? v : `${n(v)} ${t(`goals.u.${f.unit}`)}`);

// the fields that set a goal, one input each, with Save; Back to the original when the goal was set here
function form(r, i) {
  const inputs = r.edit.map((f) => `<label class="goal-field"><span>${t(`goals.f.${f.field}`)}</span><span class="goal-input">
    <input name="${f.field}" ${f.type === "clock" ? 'type="time"' : `type="number" inputmode="decimal" min="${f.min}" max="${f.max}" step="${f.step}"`} value="${f.value ?? ""}">
    ${f.unit ? `<span class="xs muted">${t(`goals.u.${f.unit}`)}</span>` : ""}</span></label>`).join("");
  return `<form class="goal-form" data-i="${i}" hidden>${inputs}
    <div class="goal-act"><button type="submit" class="goal-btn primary"${isStatic ? " disabled" : ""}>${t("goals.save")}</button>
      <button type="button" class="goal-btn" data-cancel>${t("goals.cancel")}</button>
      ${r.set_here && !isStatic ? `<button type="button" class="goal-btn quiet" data-reset>${t("goals.reset")}</button>` : ""}</div>
    <p class="xs goal-msg" role="status">${isStatic ? t("goals.static") : ""}</p></form>`;
}

// the name of a goal with where it comes from, and the button that opens its form
function nameLine(r, i, label) {
  const src = r.set_here ? `<span class="chip">${t(r.set_here.accepted ? "goals.src.accepted" : "goals.src.you")}</span>`
    : SOURCE[r.source] ? `<span class="chip">${t(SOURCE[r.source])}</span>` : "";
  const edit = r.edit?.length ? `<button type="button" class="goal-edit" data-i="${i}" aria-expanded="false">${t(r.kind === "unset" ? "goals.set_one" : "goals.edit")}</button>` : "";
  return `<div class="goal-name"><b>${label}</b>${src}${edit}</div>`;
}

function row(r, i) {
  const edit = r.edit?.length ? form(r, i) : "";
  if (r.kind === "unset") {
    return `<div class="goal-row goal-unset">${nameLine(r, i, t(`goals.unset.${r.key}`))}
      ${edit || `<span class="xs muted">${t("goals.unset_how")} <code>[${esc(r.section)}]</code></span>`}</div>`;
  }
  if (r.kind === "daily") {
    return `<div class="goal-row">${nameLine(r, i, esc(goalName(r)))}
      <div class="goal-dots" data-i="${i}"></div>
      <div class="goal-count"><b class="num">${t("goals.kept", { n: r.kept, k: r.known })}</b><span class="xs muted">${t("goals.kept28", { n: r.kept28, k: r.known28 })}</span></div>${edit}</div>`;
  }
  if (r.kind === "weekly") {
    const weeks = r.weeks.map((w) => {
      const share = w.value == null ? 0 : Math.min(100, (w.value / r.target.value) * 100);
      const text = w.value == null ? "—" : r.key === "weekly_min" ? dur(w.value) : `${num(w.value)}/${num(r.target.value)}`;
      const mark = w.met === true ? `<span class="mark good" aria-label="${esc(t("goal.kept"))}">✓</span>` : w.met === false ? `<span class="mark bad" aria-label="${esc(t("goal.missed"))}">✗</span>` : `<span class="mark" aria-label="${esc(t("ui.no_data"))}">–</span>`;
      return `<div class="goal-week" data-tip="${esc(`${t("ex.week_of", { day: shortDay(w.week_start) })} · ${text}${w.partial ? ` · ${t("goals.so_far")}` : ""}`)}">
        <span class="xs muted">${w.partial ? t("goals.this_week") : shortDay(w.week_start)}</span><div class="progress" style="margin:0"><span style="width:${share.toFixed(0)}%"></span></div>
        <span class="xs num">${esc(text)}</span>${mark}</div>`;
    }).join("");
    return `<div class="goal-row goal-weekly">${nameLine(r, i, esc(goalName(r)))}<div class="goal-weeks">${weeks}</div>
      <div class="goal-count"><b class="num">${t("goals.weeks_kept", { n: r.kept, k: r.known })}</b></div>${r.edit?.length ? form(r, i) : ""}</div>`;
  }
  // a status: the weight plan against its corridor
  const tone = r.status === "on_track" || r.status === "reached" ? "good" : r.status ? "watch" : "";
  return `<div class="goal-row">${nameLine(r, i, esc(goalName(r)))}
    <div class="goal-status">${r.status ? `<span class="chip ${tone}">${t(`body.status.${r.status}`)}</span>` : `<span class="chip">${t("ui.no_data")}</span>`}
      <span class="small muted">${esc([r.value != null ? `${num(r.value, 1)} kg` : "", r.rate_pct != null ? t("goals.rate", { v: num(r.rate_pct, 1) }) : "", r.eta ? t("goals.eta", { day: day(r.eta, { weekday: false }) }) : ""].filter(Boolean).join(" · "))}</span></div>${r.edit?.length ? form(r, i) : ""}</div>`;
}

// an assistant's proposals: what would change, from what to what, its reason, and Accept / Decline
function proposals(list) {
  if (!list?.length) return "";
  const items = list.map((p) => {
    const what = p.changes.map((c) => `${t(`goals.f.${c.field}`)}${t("today.colon")}<span class="num">${esc(value(c, c.value))} → <b>${esc(value(c, c.to))}</b></span>`).join("<br>");
    const note = p.note && typeof p.note === "object" ? p.note[getLang()] || p.note.en : p.note;
    const by = p.by === "assistant" ? t("goals.assistant") : p.by;
    return `<div class="goal-prop"><div class="goal-prop-what">${icon("ai", 18)}<p>${what}</p></div>
      ${note ? `<p class="small goal-prop-note">${esc(note)}</p>` : ""}
      <div class="goal-act"><button type="button" class="goal-btn primary" data-accept="${esc(p.id)}"${isStatic ? " disabled" : ""}>${t("goals.accept")}</button>
        <button type="button" class="goal-btn" data-decline="${esc(p.id)}"${isStatic ? " disabled" : ""}>${t("goals.decline")}</button>
        <span class="xs muted">${esc(t("goals.prop_from", { by, day: p.at ? shortDay(p.at.slice(0, 10)) : "" }))}</span></div></div>`;
  }).join("");
  return `<section class="card span-12 goal-props"><h2>${t("goals.props")}<span class="aside">${list.length}</span></h2>${items}
    <p class="xs muted goal-msg" role="status">${t(isStatic ? "goals.static" : "goals.props_note")}</p></section>`;
}

// save, then compute every page again (a goal changes what they compare with); a refusal is shown by the form
async function save(body, msg) {
  try {
    await post("goals", body);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  } catch (error) {
    if (msg) msg.textContent = t("goals.err", { e: error.message });
  }
}

export default {
  render(p) {
    const name = (x) => inSentence(goalName(p.rows.find((r) => r.key === x.key)));
    const lede = p.best && p.worst
      ? `<span class="ph">${esc(t("goals.lede_best", { best: name(p.best), bn: p.best.kept, bk: p.best.known }))}</span> <span class="ph">${esc(t("goals.lede_worst", { worst: name(p.worst), wn: p.worst.kept, wk: p.worst.known }))}</span>`
      : esc(p.same ? t("goals.lede_same") : t("goals.lede_none"));
    const cards = p.domains.map((d) => {
      const rows = p.rows.map((r, i) => [r, i]).filter(([r]) => r.domain === d);
      if (!rows.length) return "";
      const link = rows.find(([r]) => r.link)?.[0].link;
      return `<section class="card span-6"><h2><span class="row" style="gap:8px">${icon(DOMAIN_ICON[d], 16)}${t(`goals.domain.${d}`)}</span>${link ? `<span class="aside"><a href="${link}">${t("goals.open")} →</a></span>` : ""}</h2>
        <div class="goal-rows">${rows.map(([r, i]) => row(r, i)).join("")}</div></section>`;
    }).join("");
    return `<div class="head"><div><h1>${t("nav.goals")}</h1><div class="sub">${t("goals.sub", { n: p.set, u: p.unset })}</div></div></div>
      <div class="grid">
        <section class="card span-12"><span class="eyebrow">${t("goals.eyebrow", { n: p.rule.recent })}</span><p class="lede" style="margin:6px 0 4px">${lede}</p>
          <div class="legend" style="margin-top:6px"><span class="key"><i style="background:var(--c-mark);border-radius:50%"></i>${t("goal.kept")}</span>
            <span class="key"><i style="background:none;border:1.5px solid var(--c-mark);border-radius:50%"></i>${t("goal.missed")}</span>
            <span class="key"><i style="background:var(--line-2);height:2px"></i>${t("ui.no_data")}</span></div></section>
        ${proposals(p.proposals)}
        ${cards}
        <section class="card span-12"><details class="how" open><summary>${t("ui.how")}</summary><p>${t("goals.rule", { d: p.rule.days, n: p.rule.recent, k: p.rule.min_known, w: p.rule.weeks })}</p></details></section>
      </div>`;
  },
  mount(root, p) {
    root.querySelectorAll(".goal-dots").forEach((el) => { const r = p.rows[el.dataset.i]; draw(el, (w) => keptDots(r.days, { width: w })); });
    root.querySelectorAll(".goal-edit").forEach((button) => {
      button.onclick = () => {
        const f = root.querySelector(`.goal-form[data-i="${button.dataset.i}"]`);
        f.hidden = !f.hidden;
        button.setAttribute("aria-expanded", String(!f.hidden));
        if (!f.hidden) f.querySelector("input")?.focus();
      };
    });
    root.querySelectorAll(".goal-form").forEach((f) => {
      const r = p.rows[f.dataset.i];
      const msg = f.querySelector(".goal-msg");
      const close = () => { f.reset(); f.hidden = true; root.querySelector(`.goal-edit[data-i="${f.dataset.i}"]`)?.setAttribute("aria-expanded", "false"); };
      f.querySelector("[data-cancel]").onclick = close;
      f.onsubmit = (e) => {
        e.preventDefault();
        if (isStatic) return;
        const changes = {};
        for (const field of r.edit) {
          const v = f.elements.namedItem(field.field).value;
          if (v !== "") changes[field.field] = field.type === "clock" ? v : Number(v);  // empty = leave as it is
        }
        if (!Object.keys(changes).length) { msg.textContent = t("goals.nothing"); return; }
        save({ op: "set", changes }, msg);
      };
      const reset = f.querySelector("[data-reset]");
      if (reset) reset.onclick = () => save({ op: "set", changes: Object.fromEntries(r.edit.map((field) => [field.field, null])) }, msg);
    });
    const propMsg = root.querySelector(".goal-props .goal-msg");
    root.querySelectorAll("[data-accept]").forEach((b) => { b.onclick = () => save({ op: "accept", id: b.dataset.accept }, propMsg); });
    root.querySelectorAll("[data-decline]").forEach((b) => { b.onclick = () => save({ op: "decline", id: b.dataset.decline }, propMsg); });
  },
};
