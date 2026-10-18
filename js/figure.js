// The body figure from the author's GEOM90007 project Ready to Train: seven regions, a male and a female figure
// ([healthaio] figure). Used by the morning check-in on Recovery (tap a region to set how sore it is) and by the
// after-workout prompt (tap the regions it trained).
//
// The drawing is line art with a see-through background (img/body-*-art.png, made from Ready to Train's reference
// images), painted in --plate-ink on --plate, so it follows light and dark mode. Each region is painted over it
// through its own mask, which leaves the muscle lines out, so they still show. An SVG mask does not change what a click hits, so the region under the pointer
// is read from the masks' own pixels (within a few pixels, so a muscle line still counts).
import { esc } from "./charts.js?v=11473b41ff";
import { t } from "./i18n.js?v=11473b41ff";

export const FIGURE = {
  male: { width: 581, height: 794, viewBox: "0 185 581 575", front: 166, back: 411, orientY: 206, sideY: 742, sideX: [138, 194, 383, 439] },
  female: { width: 1024, height: 1536, viewBox: "-163 60 1350 1350", front: 273, back: 750, orientY: 104, sideY: 1400, sideX: [210, 334, 690, 810] },
};

const sexOf = (p) => (p.figure === "female" ? "female" : "male");
let uid = 0;

// fills: {region: CSS colour}; label(region) gives each region's accessible name
export function figureSvg(p, fills, label) {
  const sex = sexOf(p), c = FIGURE[sex], id = `fig${(uid += 1)}`;
  const masks = p.regions.map((r) => `<mask id="${id}-${r}" x="0" y="0" width="${c.width}" height="${c.height}" maskUnits="userSpaceOnUse" style="mask-type:alpha">
    <image href="img/body-mask-${sex}-${r}.png" x="0" y="0" width="${c.width}" height="${c.height}" preserveAspectRatio="none"/></mask>`).join("");
  const art = `<mask id="${id}-art" x="0" y="0" width="${c.width}" height="${c.height}" maskUnits="userSpaceOnUse" style="mask-type:alpha">
    <image href="img/body-${sex}-art.png" x="0" y="0" width="${c.width}" height="${c.height}" preserveAspectRatio="none"/></mask>`;
  const regions = p.regions.map((r) => `<g class="fig-region" data-region="${r}" style="fill:${fills[r]}" role="button" tabindex="0"
      aria-label="${esc(label(r))}"><rect x="0" y="0" width="${c.width}" height="${c.height}" mask="url(#${id}-${r})"/></g>`).join("");
  const text = (x, y, s, cls) => `<text x="${x}" y="${y}" text-anchor="middle" class="${cls}">${esc(s)}</text>`;
  return `<svg class="fig" viewBox="${c.viewBox}" role="group" aria-label="${esc(t("sore.figure"))}">
    <defs>${masks}${art}</defs>
    <rect class="fig-art" x="0" y="0" width="${c.width}" height="${c.height}" mask="url(#${id}-art)" aria-hidden="true"/>
    ${regions}
    ${text(c.front, c.orientY, t("sore.front"), "fig-orient")}${text(c.back, c.orientY, t("sore.back"), "fig-orient")}
    ${text(c.sideX[0], c.sideY, t("sore.r"), "fig-side")}${text(c.sideX[1], c.sideY, t("sore.l"), "fig-side")}
    ${text(c.sideX[2], c.sideY, t("sore.l"), "fig-side")}${text(c.sideX[3], c.sideY, t("sore.r"), "fig-side")}</svg>`;
}

// tap(region) on a click or Enter / Space; tip(region) is the hover text
export function mountFigure(svg, p, { tap, tip }) {
  const sex = sexOf(p), c = FIGURE[sex];
  const alpha = {};
  p.regions.forEach((r) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = c.width; canvas.height = c.height;
      const g = canvas.getContext("2d", { willReadFrequently: true });
      g.drawImage(img, 0, 0, c.width, c.height);
      alpha[r] = g.getImageData(0, 0, c.width, c.height).data;
    };
    img.src = `img/body-mask-${sex}-${r}.png`;
  });
  const regionAt = (e) => {
    const pt = svg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const u = pt.matrixTransform(svg.getScreenCTM().inverse());
    const reach = Math.max(3, Math.round(c.width / 110));
    let best = null, most = 0;
    for (const r of p.regions) {
      const a = alpha[r];
      if (!a) continue;
      let n = 0;
      for (let dy = -reach; dy <= reach; dy += 2) {
        for (let dx = -reach; dx <= reach; dx += 2) {
          const x = Math.round(u.x) + dx, y = Math.round(u.y) + dy;
          if (x >= 0 && y >= 0 && x < c.width && y < c.height && a[(y * c.width + x) * 4 + 3] > 40) n += 1;
        }
      }
      if (n > most) { most = n; best = r; }
    }
    return best;
  };
  svg.querySelectorAll(".fig-region").forEach((g) => {
    g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); tap(g.dataset.region); } });
  });
  svg.addEventListener("click", (e) => { const r = regionAt(e); if (r) { tap(r); svg.dataset.tip = tip(r); } });
  svg.addEventListener("mousemove", (e) => {
    const r = regionAt(e);
    svg.style.cursor = r ? "pointer" : "";
    if (r) svg.dataset.tip = tip(r);
    else delete svg.dataset.tip;
  });
}

// the regions a note's words suggest (the words come from the server: checkin.REGION_WORDS, where the rule is)
const escRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
export function regionsIn(note, words) {
  let text = ` ${String(note || "").toLowerCase()} `;
  const found = new Set();
  const all = words.flatMap(([ws, rs]) => ws.map((w) => [w, rs])).sort((a, b) => b[0].length - a[0].length);
  for (const [w, rs] of all) {
    const src = /^[\x20-\x7e]+$/.test(w) ? `\\b${escRe(w)}(?:s|es)?\\b` : escRe(w);
    if (new RegExp(src).test(text)) {
      text = text.replace(new RegExp(src, "g"), " ");
      rs.forEach((r) => found.add(r));
    }
  }
  return found;
}
