import { esc } from "./charts.js?v=65d4646a27";
import { day, num, t } from "./i18n.js?v=65d4646a27";

// the words are in i18n.js under hm.*
const w = (key, data = {}) => t(`hm.${key}`, data);
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
