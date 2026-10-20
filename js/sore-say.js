// Where it hurts, said when it is felt (sore_say.py reads it, checkin.report saves it): one sentence, typed or
// spoken, read into places on this computer (or by the assistant when it is on); then a button for whatever the
// sentence left open (thigh or calf, which side, which part, how much). A place with everything known joins the
// card's soreness and is saved with the card. The following days the card asks how each sore place is now
// (followHtml), until you say it is fine.
import { isStatic, post } from "./api.js?v=65d4646a27";
import { esc } from "./charts.js?v=65d4646a27";
import { day, getLang, t } from "./i18n.js?v=65d4646a27";
import { stopLine } from "./care-ui.js?v=65d4646a27";

const spec = (areas, area) => areas.find((a) => a.area === area);

// the area a region id belongs to (left_thigh_back -> thigh)
export function areaOf(region, areas) {
  return areas.find((a) => region === a.area || region.startsWith(`${a.area}_`) || region.endsWith(`_${a.area}`) || region.includes(`_${a.area}_`))?.area;
}

// what an item still needs, in the order it is asked
function missing(item, areas) {
  if (item.area === "leg") return "leg";
  const s = spec(areas, item.area);
  if (item.area === "neck") return item.face ? (item.level == null ? "level" : null) : "face";
  if (s.sides.length && !item.side) return "side";
  if (s.faces.length && !item.face) return "face";
  return item.level == null ? "level" : null;
}

// the region ids an item names, once its place is known (the back of the neck with no side is both halves)
export function regionsOf(item, areas) {
  if (item.area === "neck") {
    if (item.face === "front") return ["neck_front"];
    if (item.face !== "back") return null;
    return (item.side === "left" || item.side === "right" ? [item.side] : ["left", "right"]).map((s) => `neck_back_${s}`);
  }
  const s = spec(areas, item.area);
  if (!s) return null;
  const sides = s.sides.length ? (item.side === "both" ? s.sides : item.side ? [item.side] : null) : [null];
  const faces = s.faces.length ? (item.face === "all" ? s.faces : item.face ? [item.face] : null) : [null];
  if (!sides || !faces) return null;
  return sides.flatMap((side) => faces.map((face) => [side, item.area, face].filter(Boolean).join("_")));
}

function label(item, areas) {
  const one = regionsOf(item, areas);
  if (one && one.length === 1) return t(`sore.region.${one[0]}`);
  const face = item.face ? t(`sore.face.${item.face}`) : "";
  if (getLang() === "zh") return [item.side ? t(`sore.side.${item.side}`) : "", t(`sore.area.${item.area}`), face].join("");
  // English: "Left shoulder", "Both thighs, front"; the neck has no left and right of its own, only its back's halves
  const area = t(`sore.area.${item.area}`), sided = spec(areas, item.area)?.sides.length;
  const place = !item.side ? area : !sided ? `${area}, ${t(`sore.side.${item.side}`)}`
    : item.side === "both" ? `${t("sore.side_btn.both")} ${area.toLowerCase()}` : `${t(`sore.side_btn.${item.side}`)} ${t(`sore.one.${item.area}`)}`;
  return [place, face].filter(Boolean).join(", ");
}

const btn = (cls, data, text, on = false) => `<button type="button" class="goal-btn ${cls}" ${data} aria-pressed="${on}">${esc(text)}</button>`;

export function sayHtml(p) {
  return `<div class="sore-say">
    <div class="now-row"><span class="small now-label"><b>${t("say.title")}</b></span><span class="xs muted">${t("say.sub")}</span></div>
    <div class="care-say"><button type="button" class="goal-btn say-mic" hidden>${t("say.mic")}</button>
      <input type="text" id="sore-said" maxlength="280" placeholder="${esc(t("say.placeholder"))}" aria-label="${esc(t("say.title"))}">
      <button type="button" class="goal-btn" id="sore-read"${isStatic ? " disabled" : ""}>${t("say.read")}</button></div>
    <p class="xs muted say-status" role="status">${p.sore_assistant?.on ? t("care.reader.assistant") : t("care.reader.rules")}</p>
    <div class="say-items"></div>
    <div class="say-signs" hidden></div>
  </div>`;
}

// the places said to be sore before today, each with a button per level and "fine now" (0)
export function followHtml(p) {
  const F = p.soreness.follow_up;
  if (!F.length) return "";
  return `<div class="sore-follow"><p class="small" style="margin:0 0 var(--s-2)"><b>${t("fu.title")}</b></p>
    ${F.map((f) => `<div class="lvl-row" role="group" aria-label="${esc(t(`sore.region.${f.region}`))}">
      <span class="small">${t(`sore.region.${f.region}`)} <span class="xs muted">${esc(t("fu.since", { day: day(f.date, { weekday: false }), level: t(`sore.level.${f.level}`) }))}</span></span>
      <span class="lvl-btns">${[0, 1, 2, 3].map((lv) => btn("lvl-btn", `data-region="${f.region}" data-level="${lv}"`, lv ? t(`sore.level.${lv}`) : t("sore.fine"))).join("")}</span></div>`).join("")}</div>`;
}

// set(region, level) / unset(region): the card's soreness to save. Returns what was said and who read it.
export function mountSay(root, p, { set, unset }) {
  const box = root.querySelector(".sore-say");
  if (!box) return { said: () => "", parsedBy: () => null };
  const input = box.querySelector("#sore-said"), status = box.querySelector(".say-status"), list = box.querySelector(".say-items");
  const signsBox = box.querySelector(".say-signs"), read = box.querySelector("#sore-read"), mic = box.querySelector(".say-mic");
  const items = [], said = [], signs = new Set();
  let parsedBy = null;

  const apply = (item) => {
    (item.applied || []).forEach(unset);
    const regions = item.level != null ? regionsOf(item, p.areas) : null;
    item.applied = regions || [];
    item.applied.forEach((r) => set(r, item.level));
  };
  const paint = () => {
    list.innerHTML = items.map((item, i) => {
      const need = missing(item, p.areas), s = spec(p.areas, item.area);
      let ask = "";
      if (need === "leg") ask = ["thigh", "calf"].map((a) => btn("say-leg", `data-i="${i}" data-area="${a}"`, t(`sore.leg.${a}`))).join("");
      else if (need === "side") ask = ["left", "right", "both"].map((x) => btn("say-side", `data-i="${i}" data-side="${x}"`, t(`sore.side_btn.${x}`))).join("");
      else if (need === "face") ask = (item.area === "neck" ? ["front", "back"] : [...s.faces, ...(s.faces.length > 2 ? ["all"] : [])])
        .map((x) => btn("say-face", `data-i="${i}" data-face="${x}"`, t(`sore.face.${x}`))).join("");
      const question = need && need !== "level" ? `<span class="xs muted">${t(`sore.q.${need}`)}</span> ${ask}` : "";
      const levels = need === "level" || need == null
        ? `${need === "level" ? `<span class="xs muted">${t("sore.q.level")}</span> ` : ""}${[1, 2, 3].map((lv) => btn("say-level", `data-i="${i}" data-level="${lv}"`, t(`sore.level.${lv}`), item.level === lv)).join("")}${btn("say-level", `data-i="${i}" data-level="0"`, t("sore.fine"), item.level === 0)}` : "";
      return `<div class="now-row say-item"><span class="small now-label"><b>${esc(label(item, p.areas))}</b></span>
        <span class="now-btns">${question}${levels}<button type="button" class="doc-link say-drop" data-i="${i}" aria-label="${esc(t("sore.remove"))}">×</button></span></div>`;
    }).join("");
    const on = (sel, fn) => list.querySelectorAll(sel).forEach((b) => { b.onclick = () => { fn(items[b.dataset.i], b); apply(items[b.dataset.i]); paint(); }; });
    on(".say-leg", (item, b) => { item.area = b.dataset.area; });
    on(".say-side", (item, b) => { item.side = b.dataset.side; });
    on(".say-face", (item, b) => { item.face = b.dataset.face; });
    on(".say-level", (item, b) => { item.level = Number(b.dataset.level); });
    list.querySelectorAll(".say-drop").forEach((b) => { b.onclick = () => { const [item] = items.splice(Number(b.dataset.i), 1); (item.applied || []).forEach(unset); paint(); }; });
    signsBox.hidden = !signs.size;
    if (signs.size) signsBox.innerHTML = `<p class="care-blocked">${esc(t("say.signs", { signs: [...signs].map((x) => t(`care.sign.${x}`)).join(t("ui.list_sep")) }))}</p>${stopLine(p.care.stop)}`;
  };

  const readIt = async () => {
    const text = input.value.trim();
    if (!text || isStatic) return;
    read.disabled = true; status.textContent = t("say.reading");
    try {
      const out = await post("sore-parse", { said: text });
      parsedBy = out.parsed_by;
      status.textContent = out.items.length
        ? (out.parsed_by === "assistant" ? t("care.read_by.assistant") : t(`care.read_by.rules${out.assistant ? `_${out.assistant}` : ""}`))
        : t("say.none");
      if (out.items.length) { said.push(text); input.value = ""; }
      out.items.forEach((x) => { const item = { ...x }; items.push(item); apply(item); });
      out.signs.forEach((x) => signs.add(x));
      paint();
    } catch (error) {
      status.textContent = t("care.err", { e: error.message });
    } finally { read.disabled = false; }
  };
  read.onclick = readIt;
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); readIt(); } });

  // speech: the browser's own recogniser where there is one (the keyboard's microphone works everywhere else)
  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (Speech && !isStatic) {
    mic.hidden = false;
    let rec = null;
    mic.onclick = () => {
      if (rec) { rec.stop(); return; }
      rec = new Speech();
      rec.lang = getLang() === "zh" ? "zh-CN" : "en-US";
      rec.interimResults = true;
      rec.onresult = (e) => { input.value = Array.from(e.results).map((r) => r[0].transcript).join(""); };
      rec.onerror = (e) => { status.textContent = t("say.mic_err", { e: e.error }); };
      rec.onend = () => { rec = null; mic.textContent = t("say.mic"); mic.setAttribute("aria-pressed", "false"); if (input.value.trim()) readIt(); };
      try {
        rec.start();
        mic.textContent = t("say.mic_stop"); mic.setAttribute("aria-pressed", "true");
        status.textContent = `${t("say.listening")} ${t("say.mic_note")}`;
      } catch (error) { rec = null; status.textContent = t("say.mic_err", { e: error.message }); }
    };
  }
  return { said: () => said.join(" / "), parsedBy: () => parsedBy };
}
