// "How it's worked out": a small i in the card's top-right corner that opens the explanation, instead of a fold under
// every card. Pages still write the explanation as details.how with the "How it's worked out" summary (so it reads in
// order without scripts, and the tests see it); once a page is drawn, mountInfo moves each one into its card's i. A
// card that held nothing but the explanation goes away, and its i sits by the page title. Folds with other summaries
// (the last 14 days, every time, importing) are content and stay as they are.
import { t } from "./i18n.js";
import { icon } from "./icons.js";

let pop = null;
const close = () => { if (!pop) return; pop.owner?.setAttribute("aria-expanded", "false"); pop.remove(); pop = null; };
document.addEventListener("click", (e) => { if (pop && !pop.contains(e.target) && !e.target.closest(".info-btn")) close(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
window.addEventListener("hashchange", close);
window.addEventListener("resize", close);

function open(button, nodes) {
  if (pop?.owner === button) { close(); return; }
  close();
  pop = document.createElement("div");
  pop.className = "info-pop";
  pop.setAttribute("role", "dialog");
  pop.setAttribute("aria-label", t("ui.how"));
  pop.innerHTML = `<b class="info-pop-title">${t("ui.how")}</b>`;
  nodes.forEach((n) => pop.appendChild(n.cloneNode(true)));
  pop.owner = button;
  document.body.appendChild(pop);
  button.setAttribute("aria-expanded", "true");
  // below the i, its right edge on the i's right edge, kept inside the window
  const r = button.getBoundingClientRect(), w = pop.offsetWidth, gutter = 12;
  const left = Math.max(gutter, Math.min(r.right - w, window.innerWidth - w - gutter));
  pop.style.left = `${left + window.scrollX}px`;
  pop.style.top = `${r.bottom + 8 + window.scrollY}px`;
}

function button(nodes) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "info-btn";
  b.setAttribute("aria-label", t("ui.how"));
  b.setAttribute("aria-expanded", "false");
  b.title = t("ui.how");
  b.innerHTML = icon("info", 16);
  b.onclick = (e) => { e.stopPropagation(); open(b, nodes); };
  return b;
}

export function mountInfo(main) {
  close();
  const words = new Set([t("ui.how"), t("rr.rules")]);
  const hosts = new Map();  // where an i goes -> the explanation's paragraphs
  for (const fold of main.querySelectorAll("details.how")) {
    if (!words.has(fold.querySelector(":scope > summary")?.textContent.trim())) continue;
    const card = fold.closest(".card") || fold.parentElement;
    const body = [...fold.children].filter((n) => n.tagName !== "SUMMARY");
    // the nearest title: the fold's own part of the card when that part has one (Today's "what to adjust"), else the card
    const part = fold.parentElement !== card ? fold.parentElement?.querySelector(":scope > h2, :scope > h3, :scope > .section-title") : null;
    fold.remove();
    const empty = card.matches(".card") && !card.textContent.trim() && !card.querySelector("svg, canvas, img, button, input");
    let host = part || card;
    if (empty) {
      host = main.querySelector(".head h1");
      if (host) card.remove(); else host = card;
    }
    if (!hosts.has(host)) hosts.set(host, []);
    hosts.get(host).push(...body);
  }
  for (const [host, nodes] of hosts) {
    const b = button(nodes);
    const title = host.matches("h1, h2, h3, .section-title") ? host : host.querySelector(":scope > h2");
    if (title?.matches("h1")) {
      b.classList.add("info-title");
      title.appendChild(b);
    } else if (title) {
      // beside what already sits on the title's right (its aside, a switch or a legend), so that stays where it was
      const last = title.lastElementChild;
      if (last) {
        const group = document.createElement("span");
        group.className = "info-group";
        title.insertBefore(group, last);
        group.append(last, b);
      } else {
        title.appendChild(b);
      }
    } else {
      host.classList.add("has-info");
      b.classList.add("info-corner");
      host.appendChild(b);
    }
  }
}
