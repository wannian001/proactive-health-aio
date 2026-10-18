// Data sources (#data): what arrived over 90 days, grouped by the device it comes from (watch, phone, Mac, files
// brought in by hand), each device with how its data reaches this computer; then the files and how to import more.
import { coverage, draw, esc } from "../charts.js?v=93bad7f144";
import { clock, day, num, t } from "../i18n.js?v=93bad7f144";
import { icon } from "../icons.js?v=93bad7f144";

const STATUS = { ok: "good", stale: "watch", missing: "bad" };
const DEVICE_ICON = { watch: "watch", phone: "phone", mac: "laptop", manual: "tray" };
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
    const tables = p.tables.map((tb) => `<tr><th scope="row"><code>${esc(tb.file)}</code><span class="xs muted" style="display:block;font-weight:400">${esc(t(`data.table.${tb.name}`))}</span></th>
      <td class="num">${tb.present ? num(tb.rows) : `<span class="muted">${t("data.absent")}</span>`}</td>
      <td class="xs muted">${tb.modified ? `${day(tb.modified, { weekday: false })} ${clock(tb.modified)}` : "—"}</td>
      <td>${tb.problem_count ? `<span class="chip bad">${t("data.problems", { n: tb.problem_count })}</span>` : tb.present ? `<span class="chip good">${t("data.clean")}</span>` : ""}</td></tr>
      ${tb.problems.map((pr) => `<tr class="problem"><td colspan="4" class="xs">${t("data.problem_line", { line: pr.line, column: pr.column })}: ${esc(pr.message)}</td></tr>`).join("")}`).join("");
    return `<div class="head"><div><h1>${t("nav.data")}</h1><div class="sub">${t("data.sub", { n: p.days })}</div></div>
      <span class="chip ${p.ok ? "good" : "watch"}">${t(p.ok ? "data.ok" : "data.attention")}</span></div>
      <div class="grid">
        <section class="card span-12"><h2>${t("data.arrivals")}<span class="aside legend">
          <span class="key"><i style="background:var(--c-mark);opacity:.8"></i>${t("data.mark.1")}</span>
          <span class="key"><i style="background:var(--ink-3);opacity:.5"></i>${t("data.mark.p")}</span>
          <span class="key"><i style="background:var(--c-band)"></i>${t("data.mark.0")}</span></span></h2>
          ${streams}
          <p class="xs muted" style="margin:12px 0 0">${t("data.honest")}</p></section>
        <section class="card span-7"><h2>${t("data.files")}</h2><div class="table-wrap"><table class="review data-table">
          <thead><tr><th scope="col">${t("data.file")}</th><th scope="col">${t("data.rows")}</th><th scope="col">${t("data.modified")}</th><th scope="col"></th></tr></thead>
          <tbody>${tables}</tbody></table></div></section>
        <section class="card span-5"><h2>${t("data.import")}</h2><p class="small" style="margin-top:0">${t("data.import_lede")}</p>
          <pre class="code">python -m healthaio import apple-health export.zip
python -m healthaio import ics timetable.ics --kind class
python -m healthaio import macos-screentime
python -m healthaio import csv deadlines my.csv \\
  --map "Due=due,Task=title,Course=group"
python -m healthaio import csv meals food-log.csv \\
  --map "Date=time,Meal=meal,Calories=kcal"
python -m healthaio check</pre>
          <p class="xs muted">${t("data.import_note")}</p>
          <p class="xs muted" style="margin:0"><a href="#kit">${t("kit.link")}</a> · ${t("kit.link_note")}</p></section>
      </div>`;
  },
  mount(root, p) {
    root.querySelectorAll(".cov").forEach((el) => draw(el, (w) => coverage(p.streams[el.dataset.i].marks, p.first, { width: w })));
  },
};
