import { esc } from "./charts.js";
import { getLang, num, day } from "./i18n.js";

const words = {
  title:["HRV · 个人训练模型","HRV · personal trained model"], ready:["下一日预测","Next-day forecast"],
  stale_data:["等待最新数据","Awaiting fresh data"], history_only:["历史检验","Historical evaluation"],
  insufficient_recent:["近期记录不足","Too few recent records"], not_trained:["尚未训练个人模型","Personal model not trained"],
  invalid_model:["模型文件无法读取，请重新训练","Model unavailable; retraining needed"],
  invalid_source:["来源有无效记录，请先核对","Invalid source records; review needed"],
  source_changed:["训练用的旧数据已修订，请重新训练","Training data revised; retraining needed"],
  empty:["接入 HRV 历史并完成训练后，这里显示预测与实际误差。","Train on your HRV history to see predictions and measured errors here."],
  actual:["实际 HRV","Recorded HRV"], prediction:["模型估计","Model estimate"], baseline:["28 天中位数","28-day median"],
  latest:["最新完整记录 · {date}","Latest complete record · {date}"], target:["{date} 的估计","Estimate for {date}"],
  interval:["参考范围 {low}–{high} ms","Reference range {low}–{high} ms"],
  stale:["历史估计 · 不是今天的预测","Historical estimate · not today"],
  metric:["留出检验误差 {error} ms · 中位数基线 {base} ms","Held-out MAE {error} ms · median baseline {base} ms"],
  counts:["本人 {n} 个次日样本 · 训练于 {date}","{n} personal next-day pairs · trained {date}"],
  detail:["模型详情","Model details"],
  holdout:["本轮按时间留出 {start} 至 {end}，共 {n} 天；这段未参与选参数。图为其中最近 60 个有效日。","Calendar holdout: {start}–{end}, {n} days, excluded from parameter selection. Chart: last 60 eligible holdout days."],
  inputs_hrv:["采用 HRV 历史：近期水平、变化、波动和记录覆盖。","Uses HRV history: recent level, change, variability and coverage."],
  inputs_context:["以 HRV 历史为主，加入此前睡眠、静息心率与活动记录。","HRV history plus previously observed sleep, resting heart rate and activity."],
  baseline_selected:["训练候选在验证期没有胜过简单基线，当前采用验证期更稳的基线。","Trained candidates did not beat the baseline in validation; the selected baseline is active."],
  coverage:["按更早的校准数据确定参考范围；留出期覆盖 {coverage}%。不是个人概率保证。","Range set using earlier calibration errors; holdout coverage {coverage}%. Not a personal probability guarantee."],
  uncertainty:["与基线的误差差值：7 天分块估计区间 {low} 至 {high} ms。跨过 0 时，尚不能确认有稳定优势。","Paired error difference: 7-day block interval {low} to {high} ms. An interval crossing zero does not establish a stable advantage."],
  boundary:["预测设备记录的日 HRV；不换算成酸痛、精力或临床恢复分，也不能说明某次行为导致了变化。","Predicts recorded daily HRV, not pain, energy or clinical recovery; it does not identify causes."],
  old_model:["模型超过 45 天未重训；当前结果谨慎参考。","Model is over 45 days old; interpret cautiously."],
  chart:["留出期：实际与预估（ms）","Held-out actual vs estimate (ms)"],
};
function w(key, data={}) { return (words[key]?.[getLang()==="zh"?0:1] || key).replace(/\{(\w+)\}/g,(_,k)=>data[k]??""); }
const dateText = d => day(d,{weekday:false});

function plot(cases) {
  if (!cases?.length) return "";
  const width=640,height=172,pad=28,span=width-2*pad;
  const all=cases.flatMap(r=>[r.actual,r.prediction,r.baseline]);
  const low=Math.floor(Math.min(...all)/5)*5, high=Math.max(low+5,Math.ceil(Math.max(...all)/5)*5);
  const dates=cases.map(r=>Date.parse(r.date)), start=dates[0], duration=dates.at(-1)-start||86400000;
  const x=i=>pad+(dates[i]-start)/duration*span, y=v=>height-pad-(v-low)/(high-low)*(height-2*pad);
  const path=key=>cases.map((r,i)=>`${i===0||dates[i]-dates[i-1]>3*86400000?"M":"L"}${x(i).toFixed(1)},${y(r[key]).toFixed(1)}`).join(" ");
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(w("chart"))}">
    ${[low,(low+high)/2,high].map(v=>`<line x1="${pad}" x2="${width-pad}" y1="${y(v)}" y2="${y(v)}" class="hm-grid"/><text x="${pad-6}" y="${y(v)+4}" text-anchor="end">${num(v,0)}</text>`).join("")}
    <path d="${path("baseline")}" class="hm-line hm-baseline"/><path d="${path("actual")}" class="hm-line hm-actual"/><path d="${path("prediction")}" class="hm-line hm-predicted"/>
    <text x="${pad}" y="${height-3}">${esc(dateText(cases[0].date))}</text><text x="${width-pad}" y="${height-3}" text-anchor="end">${esc(dateText(cases.at(-1).date))}</text></svg>`;
}

export function hrvModelHtml(p) {
  if (!p) return "";
  const head=`<div class="hm-heading"><h2>${w("title")}</h2><span class="ov-tag">${esc(w(p.status))}</span></div>`;
  if (!p.training) return `<section class="hrv-model-card hm-empty">${head}<p class="ov-secondary">${w("empty")}</p></section>`;
  const e=p.evaluation;
  return `<section class="hrv-model-card" aria-label="${w("title")}">${head}
    <div class="hm-summary">${p.prediction!=null ? `<div class="hm-readings"><div><span>${esc(w("latest",{date:dateText(p.anchor)}))}</span><b>${num(p.current,1)}<small> ms</small></b></div>
      <span class="hm-arrow" aria-hidden="true">→</span><div class="hm-next"><span>${esc(w("target",{date:dateText(p.target_date)}))}</span><b>${num(p.prediction,1)}<small> ms</small></b><p>${esc(w("interval",{low:num(p.interval[0],1),high:num(p.interval[1],1)}))}</p></div></div>`:""}
      ${p.status==="stale_data"?`<p class="hm-freshness">${esc(w("stale",{date:dateText(p.anchor)}))}</p>`:""}
      <p class="hm-error">${esc(w("metric",{error:num(e.mae_ms,2),base:num(e.baseline_mae_ms,2)}))}</p>
      ${p.model_age_days>45?`<p class="hm-freshness">${w("old_model")}</p>`:""}</div>
    <div class="hm-chart"><p>${w("chart")}</p>${plot(p.history)}<div class="hm-legend"><span class="hm-actual">${w("actual")}</span><span class="hm-predicted">${w("prediction")}</span><span class="hm-baseline">${w("baseline")}</span></div></div>
    <details class="hm-detail"><summary>${w("detail")}</summary><p>${esc(w("counts",{n:p.training.pairs,date:dateText(p.created_on)}))}</p><p>${esc(w("holdout",{start:e.start,end:e.end,n:e.n}))}</p>
      <p>${w(p.feature_groups.includes("sleep")?"inputs_context":"inputs_hrv")}</p>
      ${!p.model.startsWith("ridge_")?`<p>${w("baseline_selected")}</p>`:""}
      <p>${esc(w("coverage",{coverage:num(e.interval_coverage*100,0)}))}</p>
      ${e.difference_ci95_ms?`<p>${esc(w("uncertainty",{low:num(e.difference_ci95_ms[0],2),high:num(e.difference_ci95_ms[1],2)}))}</p>`:""}<p>${w("boundary")}</p></details></section>`;
}
