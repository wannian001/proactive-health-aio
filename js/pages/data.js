// Data sources (#data), written for someone looking at how the app works: where the data comes from and how it
// travels (four sources, each to the files it lands in and the pages that read them), how much has built up, what
// stays private and what it costs, and the nine files. The daily check (90 days of arrivals under each device) and
// the import commands are folded away at the bottom, for the person whose data it is. Rules: modules/data.py.
import { coverage, draw, esc } from "../charts.js?v=51ede4cbfe";
import { clock, day, num, t } from "../i18n.js?v=51ede4cbfe";
import { icon } from "../icons.js?v=51ede4cbfe";

// the page each source feeds, by the name its menu entry has
const PAGE_NAME = { today: "nav.today", recovery: "nav.recovery", sleep: "nav.sleep_tab", drain: "nav.drain", body: "nav.weight_tab",
  exercise: "nav.exercise", food: "nav.food", time: "nav.time_tab", week: "nav.schedule_week", load: "nav.load_tab", goals: "nav.goals",
  followup: "nav.followup" };
const mb = (bytes) => (bytes >= 1e6 ? `${num(bytes / 1e6, 1)} MB` : `${num(Math.max(1, Math.round(bytes / 1e3)))} KB`);
// a month and its year ("2025 年 8 月", "Aug 2025"): the data runs across years, so a day without a year would mislead
const ym = (iso) => t("data.ym", { y: iso.slice(0, 4), m: Number(iso.slice(5, 7)), mon: new Date(`${iso.slice(0, 7)}-15T12:00`).toLocaleString("en", { month: "short" }) });
const months = (first, today) => Math.max(1, Math.round((new Date(today) - new Date(first)) / (30.44 * 864e5)));

// one row per source: what it records → how it gets to this computer → the files → the pages that read them
function flowHtml(p) {
  const arrow = `<span class="flow-arrow" aria-hidden="true"></span>`;
  const rows = p.sources.map((src) => `<div class="flow-row">
    <div class="flow-src" data-label="${esc(t("data.flow.src"))}"><span class="dev-icon">${icon(DEVICE_ICON[src.key], 22)}</span>
      <span><b>${t(`data.dev.${src.key}`)}</b><span class="flow-chips">${src.signals.map((k) => `<span class="chip">${t(`data.s.${k}`)}</span>`).join("")}</span></span></div>${arrow}
    <div class="flow-how small" data-label="${esc(t("data.flow.how"))}">${t(`data.flow_how.${src.key}`)}</div>${arrow}
    <div class="flow-chips" data-label="${esc(t("data.flow.files"))}">${src.files.map((f) => `<code>${esc(f)}.csv</code>`).join("")}</div>${arrow}
    <div class="flow-chips" data-label="${esc(t("data.flow.pages"))}">${src.pages.map((pg) => `<a class="chip flow-page" href="#${pg}">${t(PAGE_NAME[pg])}</a>`).join("")}</div></div>`).join("");
  return `<section class="card span-12"><h2>${t("data.flow.title")}</h2>
    <div class="flow"><div class="flow-head" aria-hidden="true"><span>${t("data.flow.src")}</span><span></span><span>${t("data.flow.how")}</span><span></span>
      <span>${t("data.flow.files")}</span><span></span><span>${t("data.flow.pages")}</span></div>${rows}</div></section>`;
}

function statsHtml(p) {
  const T = p.totals;
  const tile = (value, label) => `<div class="tile"><div class="value">${value}</div><div class="label">${label}</div></div>`;
  return `<section class="card span-12"><h2>${t("data.stats.title")}</h2><div class="tiles data-stats">
      ${tile(T.first ? t("data.stats.months", { n: months(T.first, p.today) }) : "—", T.first ? esc(t("data.stats.since", { day: ym(T.first) })) : "")}
      ${tile(num(T.rows), t("data.stats.rows"))}${tile(num(T.tables), t("data.stats.tables"))}${tile(mb(T.bytes), t("data.stats.size"))}</div>
    <ul class="data-facts">${["local", "pair", "cost", "gaps"].map((k) => `<li>${t(`data.fact.${k}`)}</li>`).join("")}</ul></section>`;
}

const STATUS = { ok: "good", stale: "watch", missing: "bad" };
const DEVICE_ICON = { watch: "watch", phone: "phone", mac: "laptop", manual: "check" };
const when = (iso) => `${day(iso, { weekday: false })} ${clock(iso)}`;

function stream(s, i, p) {
  return `<div class="stream">
    <div class="stream-head"><b>${t(`data.s.${s.key}`)}</b>${s.status === "ok" ? "" : `<span class="chip ${STATUS[s.status]}">${t(`data.status.${s.status}`)}</span>`}
      <span class="spacer"></span><span class="xs muted">${t("data.days", { n: s.days_with_data, k: p.days })}</span></div>
    <div class="cov" data-i="${i}"></div>
    <span class="xs muted">${s.last ? (s.days_behind === 0 ? t("data.last_today") : t("data.last", { day: day(s.last), n: s.days_behind })) : t("data.never")}</span></div>`;
}

// one card per device: its icon and name, how its data gets here (and, outside the demo, when it last did), its streams
// (a stream's own chip only when it stopped or never arrived; the device's chip says when all is well)
function device(d, p) {
  const mine = p.streams.map((s, i) => [s, i]).filter(([s]) => s.device === d);
  const status = mine.some(([s]) => s.status === "stale") ? "stale" : mine.every(([s]) => s.status === "missing") ? "missing" : "ok";
  const carried = p.carriers?.[d];
  const carrier = p.demo || !(d in (p.carriers || {})) ? ""
    : `<p class="xs dev-carrier">${carried ? t(`data.carrier.${d}`, { when: when(carried) }) : t(`data.carrier.${d}_none`)}</p>`;
  return `<section class="dev">
    <div class="dev-head"><span class="dev-icon">${icon(DEVICE_ICON[d], 24)}</span>
      <span class="dev-name"><b>${t(`data.dev.${d}`)}</b><span class="xs muted">${t(`data.dev_how.${d}`)}</span></span>
      <span class="chip ${STATUS[status]}">${t(`data.status.${status}`)}</span></div>
    ${carrier}<div class="streams">${mine.map(([s, i]) => stream(s, i, p)).join("")}</div></section>`;
}

export default {
  render(p) {
    const streams = `<div class="dev-grid">${(p.devices || []).map((d) => device(d, p)).join("")}</div>`;
    const span = (tb) => (tb.first ? (ym(tb.first) === ym(tb.last) ? ym(tb.first) : `${ym(tb.first)} – ${ym(tb.last)}`) : "—");
    const tables = p.tables.map((tb) => `<tr><th scope="row"><code>${esc(tb.file)}</code><span class="xs muted" style="display:block;font-weight:400">${esc(t(`data.table.${tb.name}`))}</span></th>
      <td class="num">${tb.present ? num(tb.rows) : `<span class="muted">${t("data.absent")}</span>`}</td>
      <td class="xs muted">${span(tb)}</td>
      <td>${tb.problem_count ? `<span class="chip bad">${t("data.problems", { n: tb.problem_count })}</span>` : ""}</td></tr>
      ${tb.problems.map((pr) => `<tr class="problem"><td colspan="4" class="xs">${t("data.problem_line", { line: pr.line, column: pr.column })}: ${esc(pr.message)}</td></tr>`).join("")}`).join("");
    const check = p.ok ? "" : ` <span class="chip watch">${t("data.attention")}</span>`;
    return `<div class="head"><div><h1>${t("data.title")}</h1><div class="sub">${t("data.sub")}</div></div></div>
      <div class="grid">
        ${flowHtml(p)}
        ${statsHtml(p)}
        <section class="card span-12"><h2>${t("data.files")}<span class="aside"><a href="https://github.com/wannian001/proactive-health-aio/blob/main/docs/DATA_FORMAT.md" target="_blank" rel="noopener">${t("data.format")} ↗</a></span></h2>
          <div class="table-wrap"><table class="review data-table">
          <thead><tr><th scope="col">${t("data.file")}</th><th scope="col">${t("data.rows")}</th><th scope="col">${t("data.span")}</th><th scope="col"></th></tr></thead>
          <tbody>${tables}</tbody></table></div></section>
        <section class="card span-12">
          <details class="how"><summary>${t("data.check_title", { n: p.days })}${check}</summary>
            <div class="legend" style="margin:var(--s-3) 0">
              <span class="key"><i style="background:var(--c-mark);opacity:.8"></i>${t("data.mark.1")}</span>
              <span class="key"><i style="background:var(--ink-3);opacity:.5"></i>${t("data.mark.p")}</span>
              <span class="key"><i style="background:var(--c-band)"></i>${t("data.mark.0")}</span></div>
            ${streams}</details>
          <details class="how"><summary>${t("data.import")}</summary><p class="small">${t("data.import_lede")}</p>
          <pre class="code">python -m healthaio import apple-health export.zip
python -m healthaio import ics timetable.ics --kind class
python -m healthaio import macos-screentime
python -m healthaio import csv deadlines my.csv \\
  --map "Due=due,Task=title,Course=group"
python -m healthaio import csv meals food-log.csv \\
  --map "Date=time,Meal=meal,Calories=kcal"
python -m healthaio check</pre>
          <p class="xs muted" style="margin:0"><a href="#kit">${t("kit.link")}</a> · ${t("kit.link_note")}</p></details></section>
      </div>`;
  },
  mount(root, p) {
    root.querySelectorAll(".cov").forEach((el) => draw(el, (w) => coverage(p.streams[el.dataset.i].marks, p.first, { width: w })));
  },
};
