// Shell: the menu (a left sidebar that folds to icons, a bottom tab bar on phones), language and light/dark,
// hash routing (#today, #today/2026-10-11).
import { get, isStatic } from "./api.js?v=11473b41ff";
import { installTooltip, esc, setFormat } from "./charts.js?v=11473b41ff";
import { getLang, setLang, t, clock, dur, measure, shortDay, toDate, wtype } from "./i18n.js?v=11473b41ff";
import { icon } from "./icons.js?v=11473b41ff";
import { mountPrompt } from "./trained.js?v=11473b41ff";
import { loadUpdate, mountUpdate, updateNote } from "./update.js?v=11473b41ff";
import body from "./pages/body.js?v=11473b41ff";
import data from "./pages/data.js?v=11473b41ff";
import drain from "./pages/drain.js?v=11473b41ff";
import exercise from "./pages/exercise.js?v=11473b41ff";
import followup from "./pages/followup.js?v=11473b41ff";
import load from "./pages/load.js?v=11473b41ff";
import recovery from "./pages/recovery.js?v=11473b41ff";
import food from "./pages/food.js?v=11473b41ff";
import goals from "./pages/goals.js?v=11473b41ff";
import guide from "./pages/guide.js?v=11473b41ff";
import kit from "./pages/kit.js?v=11473b41ff";
import project from "./pages/project.js?v=11473b41ff";
import sleep from "./pages/sleep.js?v=11473b41ff";
import time from "./pages/time.js?v=11473b41ff";
import today from "./pages/today.js?v=11473b41ff";
import week from "./pages/week.js?v=11473b41ff";

// the design kit gallery (#kit) is a page but not a menu item: the footer of every page and the Data page link to it
const PAGES = { today, week, body, recovery, load, sleep, exercise, food, time, drain, followup, goals, data, kit, project, guide };
// the menu is one axis, the loop of managing your health, one question per item: how am I today and what do I
// change (Today); what is my body showing, the outcomes (Body signals: recovery, sleep, drain, weight); what do I do every day,
// the causes I control (Daily life: exercise, food, stimulation); and what have I planned and did it happen (Plans &
// follow-up: the week on the calendar, how heavy the weeks are for body and mind, the goals, and whether yesterday's
// advice happened and helped, "tomorrow will be better"). Schedule and Actions & goals were one question asked
// twice (a plan, and whether it held), so they are one item. Weekly review was folded into Follow-up; where the
// numbers come from (Data sources) sits under the menu with the reading pages, since it is not a step of the loop.
const NAV = ["today", "body", "life", "plans"];
// a menu item that holds several pages shows a small switch above the page title and opens on its first page
const GROUPS = {
  body: [["recovery", "nav.recovery"], ["sleep", "nav.sleep_tab"], ["drain", "nav.drain"], ["body", "nav.weight_tab"]],
  life: [["exercise", "nav.exercise"], ["food", "nav.food"], ["time", "nav.time_tab"]],
  plans: [["week", "nav.schedule_week"], ["load", "nav.load_tab"], ["goals", "nav.goals"], ["followup", "nav.followup"]],
};
const groupOf = (page) => Object.keys(GROUPS).find((g) => GROUPS[g].some(([p]) => p === page)) || page;
// a page inside a group is titled by its own tab (Weight, Sleep), not by the group
const titleKey = (page) => (GROUPS[groupOf(page)] || []).find(([p]) => p === page)?.[1] || `nav.${page}`;
const ALIAS = { attention: "time", ai: "time", plan: "goals", life: "exercise", act: "followup", sched: "week", plans: "week", review: "followup" };  // old links keep working (AI work was removed)
// each menu item's glyph (icons.js)
const NAV_ICON = { today: "sun", body: "heart", life: "walk", plans: "calendar" };
// under the menu, apart from the health loop: where the numbers come from, what the project is and who it is for, how
// to use the app, and how the personal system it comes from changed over a year. History is on the author's own site
// (it quotes that personal system), so it is a link out, in a new tab. On a phone they are small links in the top
// row, so the tab bar keeps the four items of the loop.
const DOCS = ["data", "project", "guide", "history"];
const DOC_ICON = { data: "database", project: "info", guide: "communication", history: "clock" };
const OUTSIDE = { history: "doc.history_url" };  // the i18n key of its address (one page per language)
const docAttrs = (p) => (OUTSIDE[p] ? `href="${esc(t(OUTSIDE[p]))}" target="_blank" rel="noopener"` : `href="#${p}"`);
const docName = (p) => `${t(`nav.${p}`)}${OUTSIDE[p] ? " ↗" : ""}`;
const store = {
  get(key) { try { return localStorage.getItem(`healthaio.${key}`); } catch { return null; } },
  set(key, value) { try { localStorage.setItem(`healthaio.${key}`, value); } catch { /* private mode */ } },
};
let settings = { title: "Health AIO", locale: "en", demo: false };
// the kit's charts write their words and numbers with this app's i18n (charts.js imports nothing)
setFormat({ t, dur, clock, shortDay, measure, toDate, wtype });
const footer = () => `<footer class="foot">${DOCS.map((p) => `<a ${docAttrs(p)}>${docName(p)}</a>`).join("")}<a href="#kit">${t("kit.link")}</a></footer>`;

const ICON = {
  logo: `<svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="12.5" fill="none" stroke="var(--c-band)" stroke-width="5"/><path d="M16 3.5a12.5 12.5 0 0 1 11.8 8.3" fill="none" stroke="var(--c-sleep)" stroke-width="5" stroke-linecap="round"/><path d="M28.3 18.5a12.5 12.5 0 0 1-6.6 9.1" fill="none" stroke="var(--c-focus)" stroke-width="5" stroke-linecap="round"/><path d="M17.5 28.4a12.5 12.5 0 0 1-9.7-3.7" fill="none" stroke="var(--c-fun)" stroke-width="5" stroke-linecap="round"/></svg>`,
  moon: `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15.5 12.6A6.5 6.5 0 0 1 7.4 4.5a6.5 6.5 0 1 0 8.1 8.1z"/></svg>`,
};

const query = new URLSearchParams(location.search);  // ?mode=light&lang=zh for shared links
// ?app=1: the page is inside the iPhone app, which has its own tab bar at the bottom and its own update banner
const inApp = query.get("app") === "1";
if (inApp) document.documentElement.classList.add("in-app");
let picked = null;  // the moon button's choice in this tab: wins over a ?mode= link, works without storage
function applyLook() {
  const root = document.documentElement;
  const mode = picked || query.get("mode") || store.get("mode");
  if (mode === "light" || mode === "dark") root.dataset.mode = mode; else delete root.dataset.mode;
}

// the sidebar folds to an icon rail on desktop (remembered in this browser; index.html applies it before first paint)
const folded = () => document.documentElement.classList.contains("side-folded");
const wide = () => matchMedia("(min-width: 900px)").matches;

// a menu item that holds several pages opens and closes its list with a click (in the full sidebar; on the icon
// rail and the phone's tab bar it opens its first page). One list is open at a time: the item you arrive in opens by
// itself and closes the others, and opening one by hand closes the one that was open, so the menu stays short.
const openGroups = new Set();
let lastGroup = null;
const CARET = `<svg class="side-caret" viewBox="0 0 12 12" aria-hidden="true"><path d="m4.5 2.5 3.5 3.5-3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

// on a phone's tab bar the items share the width, so each takes its short name (Body, not Body signals)
const navName = (p) => t(wide() ? `nav.${p}` : `nav.short.${p}`);
let shown = "today";
matchMedia("(min-width: 900px)").addEventListener("change", () => header(shown));

function header(active) {
  shown = active;
  const top = document.querySelector(".side");
  const group = groupOf(active);
  if (group !== lastGroup) { openGroups.clear(); if (GROUPS[group]) openGroups.add(group); }
  lastGroup = group;
  const items = NAV.filter((p) => PAGES[p] || GROUPS[p]).map((p) => {
    const here = p === group;
    if (!GROUPS[p]) return `<a href="#${p}" title="${esc(t(`nav.${p}`))}" ${here ? 'aria-current="page"' : ""}>${icon(NAV_ICON[p], 18)}<span>${navName(p)}</span></a>`;
    const open = openGroups.has(p);
    const subs = GROUPS[p].map(([page, key]) => `<a class="side-sub" data-in="${p}" href="#${page}" ${page === active ? 'aria-current="page"' : ""}${open ? "" : " hidden"}><span>${t(key)}</span></a>`).join("");
    return `<a href="#${GROUPS[p][0][0]}" data-group="${p}" aria-expanded="${open}" title="${esc(t(`nav.${p}`))}" ${here ? 'aria-current="page"' : ""}>${icon(NAV_ICON[p], 18)}<span>${navName(p)}</span>${CARET}</a>${subs}`;
  }).join("");
  top.innerHTML = `
    <div class="side-head">
      <a class="brand" href="#today">${ICON.logo}<span>${esc(settings.title)}</span></a>
      <button class="side-fold" id="fold" type="button" aria-label="${esc(t("ui.fold"))}" title="${esc(t("ui.fold"))}">${icon("sidebar", 18)}</button>
    </div>
    <nav class="side-nav" aria-label="Pages">${items}</nav>
    <nav class="side-docs" aria-label="${esc(t("nav.about"))}"><span class="side-label">${t("nav.about")}</span>${DOCS.map((p) =>
      `<a ${docAttrs(p)} title="${esc(docName(p))}" ${p === active ? 'aria-current="page"' : ""}>${icon(DOC_ICON[p], 18)}<span>${docName(p)}</span></a>`).join("")}</nav>
    <div class="side-tools">
      ${settings.demo ? `<span class="demo-badge" title="${esc(t("ui.demo"))}">${t("ui.demo")}</span>` : ""}
      <button class="tool" id="lang" type="button" aria-label="Language">${t("ui.lang")}</button>
      <button class="tool" id="mode" type="button" aria-label="${esc(t("ui.mode"))}" title="${esc(t("ui.mode"))}">${ICON.moon}</button>
    </div>`;
  // folded, the logo unfolds the sidebar instead of opening Today
  const brand = top.querySelector(".brand");
  const label = () => {
    if (folded() && wide()) { brand.title = t("ui.unfold"); brand.setAttribute("aria-label", t("ui.unfold")); }
    else { brand.removeAttribute("title"); brand.removeAttribute("aria-label"); }
  };
  const setFold = (on) => { document.documentElement.classList.toggle("side-folded", on); store.set("side", on ? "folded" : "open"); label(); };
  label();
  top.querySelector("#fold").onclick = () => { setFold(true); brand.focus(); };
  top.querySelectorAll("a[data-group]").forEach((a) => {
    a.onclick = (e) => {
      if (folded() || !wide()) return;  // no room for the list: the item opens its first page
      e.preventDefault();
      const g = a.dataset.group, open = !openGroups.has(g);
      openGroups.clear();
      if (open) openGroups.add(g);
      top.querySelectorAll("a[data-group]").forEach((x) => x.setAttribute("aria-expanded", String(openGroups.has(x.dataset.group))));
      top.querySelectorAll("a.side-sub").forEach((sub) => { sub.hidden = !openGroups.has(sub.dataset.in); });
    };
  });
  brand.onclick = (e) => { if (folded() && wide()) { e.preventDefault(); setFold(false); top.querySelector("#fold").focus(); } };
  top.querySelector("#lang").onclick = () => { const next = getLang() === "zh" ? "en" : "zh"; store.set("lang", next); setLang(next); route(); };
  top.querySelector("#mode").onclick = () => {
    const dark = document.documentElement.dataset.mode ? document.documentElement.dataset.mode === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    picked = dark ? "light" : "dark";
    store.set("mode", picked);
    if (query.has("mode")) {  // so a reload keeps the choice instead of the link's
      query.delete("mode");
      const rest = query.toString();
      history.replaceState(null, "", `${location.pathname}${rest ? `?${rest}` : ""}${location.hash}`);
    }
    applyLook();
  };
}

async function route() {
  const [raw, param] = (location.hash.replace(/^#/, "") || "today").split("/");
  if (OUTSIDE[raw]) { location.replace(t(OUTSIDE[raw])); return; }  // an old #history link: the page moved to the author's site
  const name = ALIAS[raw] || raw;
  const page = PAGES[name] ? name : "today";
  header(page);
  const main = document.querySelector("main");
  main.setAttribute("aria-busy", "true");
  try {
    const data = await get(page, param);
    document.title = `${t(titleKey(page))} · ${settings.title}`;
    const group = GROUPS[groupOf(page)];
    const sub = group ? `<nav class="subnav seg" aria-label="${esc(t(`nav.${groupOf(page)}`))}">${group.map(([p, key]) => `<a href="#${p}" ${p === page ? 'aria-current="page"' : ""}>${t(key)}</a>`).join("")}</nav>` : "";
    main.innerHTML = updateNote() + sub + PAGES[page].render(data) + footer();
    mountUpdate(main);
    PAGES[page].mount?.(main, data);
    get("prompt").then((info) => mountPrompt(info, page), () => mountPrompt(null));  // after a strength or hard workout: what did it train?
  } catch (error) {
    const staticGap = isStatic && /^404/.test(error.message);  // the demo site only has a few pre-rendered dates
    main.innerHTML = `<div class="card"><p class="lede">${t(staticGap ? "ui.static_gap" : "ui.error")}</p><p class="muted small">${t(staticGap ? "ui.static_gap_hint" : "ui.error_hint")}</p>
      ${staticGap ? `<p><a href="#${page}">${t("ui.back_latest")}</a></p>` : `<p class="xs muted">${esc(error.message)}</p>`}</div>`;
  } finally {
    main.removeAttribute("aria-busy");
  }
}

async function start() {
  window.healthaioStarted = true;  // index.html shows a reload message if this never runs
  try { settings = { ...settings, ...(await get("settings")) }; } catch { /* defaults */ }
  if (!isStatic && !inApp && !settings.demo) await loadUpdate();  // the server's answer from its daily check
  setLang(query.get("lang") || store.get("lang") || settings.locale);
  applyLook();
  installTooltip();
  window.addEventListener("hashchange", route);
  route();
}

start();
export { clock };
