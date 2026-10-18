import { draw, esc, ladderChart, sleepWindows } from "../charts.js?v=11473b41ff";
import { clock, dur, t } from "../i18n.js?v=11473b41ff";
import { mountTabs, tabs } from "./tabs.js?v=11473b41ff";

// the last 7 nights against the 7 before, as four small numbers over the chart
function compare(key, now, before, fmt) {
  return `<div class="sleep-fact"><span class="xs muted">${t(`sleep.${key}`)}</span><b class="num">${esc(fmt(now))}</b><span class="xs muted">${t("sleep.last_week", { v: fmt(before) })}</span></div>`;
}

export default {
  render(p) {
    const tw = p.this_week, lw = p.last_week;
    const s = p.shift;
    const tonight = p.tonight ? `<div class="tonight" style="margin-top:0"><div><span>${t("today.phone_away")}</span><b>${clock(p.tonight.phone_away)}</b></div>
      <div><span>${t("today.asleep_by")}</span><b>${clock(p.tonight.asleep_by)}</b></div><div><span>${t("today.alarm")}</span><b>${clock(p.tonight.alarm)}</b></div></div>` : `<p class="muted small">${t("sleep.no_plan")}</p>`;
    const progress = s ? (() => {
      const total = Math.max(1, (parseInt(s.first_alarm) * 60 + parseInt(s.first_alarm.split(":")[1])) - (parseInt(s.final_alarm) * 60 + parseInt(s.final_alarm.split(":")[1])));
      const share = Math.min(1, s.moved_min / total);
      return `<div style="margin-top:var(--s-4)"><div class="row" style="justify-content:space-between"><span class="small">${t("sleep.moved", { moved: dur(s.moved_min), total: dur(total) })}</span>
        <span class="xs muted">${s.first_alarm} → ${s.final_alarm}</span></div>
        <div class="progress"><span style="width:${(share * 100).toFixed(1)}%"></span></div></div>`;
    })() : "";
    const nights = `<div class="sleep-facts">
        ${compare("asleep", tw.onset, lw.onset, (v) => v || "—")}${compare("woke", tw.wake, lw.wake, (v) => v || "—")}
        ${compare("duration", tw.sleep_min, lw.sleep_min, (v) => dur(v))}${compare("spread", tw.onset_spread_min, lw.onset_spread_min, (v) => (v == null ? "—" : `± ${dur(v)}`))}</div>
      <div class="legend" style="margin-bottom:6px"><span class="key"><i style="background:var(--c-sleep)"></i>${t("ring.sleep")}</span>${s ? `<span class="key"><i style="background:var(--c-mark);width:3px;height:14px;border-radius:2px"></i>${t("today.alarm")}</span>` : ""}</div>
      <div id="nights" class="chart"></div>`;
    const ladder = s ? `<div class="legend" style="margin-bottom:6px"><span class="key"><i style="background:var(--accent);height:3px"></i>${t("today.alarm")}</span><span class="key"><i style="background:var(--good);border-radius:50%"></i>${t("sleep.on_time")}</span><span class="key"><i style="background:var(--off);border-radius:50%"></i>${t("sleep.late")}</span></div><div id="ladder" class="chart"></div>` : "";
    return `<div class="head"><div><h1>${t("nav.sleep")}</h1><div class="sub">${p.plan.target_hours ? t("sleep.sub", { h: p.plan.target_hours }) : ""}</div></div></div>
      <div class="grid">
        <section class="card span-12"><h2>${t("today.tonight")}</h2>${tonight}${progress}
          <p class="small" style="margin:var(--s-4) 0 0"><a href="#goals">${t("sleep.checks_moved")}</a></p></section>
        <section class="card span-12"><h2>${t("sleep.compare")}</h2>
          ${s ? tabs("sleep", [{ key: "nights", label: t("sleep.windows"), html: nights }, { key: "ladder", label: t("sleep.ladder"), html: ladder }]) : nights}
          <details class="how"><summary>${t("ui.how")}</summary>${s ? `<p>${t("sleep.shift_rule", { step: s.step_min, grace: s.grace_min })}</p>` : ""}<p>${t("sleep.checks_rule", { min: p.rules.fun_before_sleep_ok_min, slack: p.rules.slack_min })}</p></details></section>
      </div>`;
  },
  mount(root, p) {
    mountTabs(root);
    draw(root.querySelector("#nights"), (w) => sleepWindows([...p.nights].reverse(), { width: w }));
    if (p.shift) draw(root.querySelector("#ladder"), (w) => ladderChart(p.shift.ladder, { width: w, final: p.shift.final_alarm }));
  },
};
