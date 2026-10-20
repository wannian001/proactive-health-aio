// Four AI-rendered views, not a mesh. All overlays use recorded regional data.
import { rv } from "./i18n.js?v=51ede4cbfe";
import { t } from "./i18n.js?v=51ede4cbfe";

const VIEWS = ["angleFront", "angleLeft", "angleBack", "angleRight"];
// Polygons are in normalized sprite-cell coordinates. Forearms, thighs and feet
// remain unclassified because the check-in schema has no records for them.
const FRONT = {
  head: [[[.45,.02],[.58,.02],[.59,.15],[.55,.19],[.46,.19],[.44,.14]]],
  right_upper_arm: [[[.37,.205],[.43,.22],[.43,.30],[.40,.37],[.34,.395],[.32,.36],[.34,.26]]],
  left_upper_arm: [[[.60,.21],[.66,.20],[.69,.26],[.71,.36],[.68,.40],[.62,.37],[.60,.30]]],
  torso: [[[.46,.18],[.55,.18],[.60,.205],[.615,.28],[.60,.34],[.60,.45],[.57,.47],[.425,.47],[.415,.34],[.43,.29],[.425,.22]]],
  pelvis: [[[.425,.46],[.60,.46],[.63,.54],[.59,.575],[.52,.56],[.46,.57],[.40,.55]]],
  right_calf: [[[.40,.72],[.47,.72],[.48,.80],[.46,.91],[.45,.94],[.405,.94],[.40,.84],[.385,.79]]],
  left_calf: [[[.545,.72],[.62,.72],[.64,.79],[.62,.86],[.62,.94],[.575,.94],[.56,.88],[.54,.80]]],
};
const BACK = {
  head: [[[.45,.015],[.58,.015],[.59,.13],[.56,.175],[.46,.175],[.44,.13]]],
  left_upper_arm: [[[.37,.19],[.43,.20],[.43,.29],[.40,.36],[.34,.39],[.32,.35],[.34,.25]]],
  right_upper_arm: [[[.60,.19],[.66,.19],[.69,.26],[.71,.35],[.68,.39],[.62,.36],[.60,.29]]],
  torso: [[[.46,.16],[.56,.16],[.60,.20],[.615,.28],[.60,.34],[.60,.43],[.425,.43],[.42,.34],[.43,.28],[.425,.20]]],
  pelvis: [[[.425,.43],[.60,.43],[.64,.54],[.59,.57],[.51,.56],[.43,.57],[.40,.54]]],
  left_calf: [[[.40,.70],[.47,.70],[.48,.79],[.46,.90],[.45,.94],[.405,.94],[.395,.85],[.38,.79]]],
  right_calf: [[[.55,.70],[.62,.70],[.64,.79],[.625,.85],[.625,.94],[.58,.94],[.565,.88],[.55,.79]]],
};
const LEFT = {
  head: [[[.43,.02],[.57,.02],[.59,.12],[.55,.17],[.45,.18],[.41,.13]]],
  left_upper_arm: [[[.425,.195],[.49,.19],[.53,.23],[.54,.30],[.53,.37],[.50,.405],[.455,.365],[.425,.29]]],
  torso: [[[.435,.175],[.49,.17],[.55,.20],[.59,.25],[.58,.42],[.565,.455],[.545,.44],[.54,.37],[.55,.29],[.52,.21]],[[.415,.30],[.435,.32],[.45,.40],[.45,.44],[.405,.44]]],
  pelvis: [[[.405,.44],[.45,.44],[.48,.54],[.45,.575],[.40,.56]],[[.55,.44],[.57,.45],[.575,.57],[.55,.57]]],
  left_calf: [[[.43,.71],[.515,.71],[.51,.78],[.48,.86],[.48,.94],[.43,.94],[.405,.83],[.405,.78]]],
};
const RIGHT = {
  head: [[[.43,.02],[.57,.02],[.58,.13],[.54,.18],[.44,.18],[.40,.12]]],
  right_upper_arm: [[[.48,.19],[.55,.185],[.59,.23],[.575,.30],[.54,.38],[.50,.40],[.465,.36],[.485,.28]]],
  torso: [[[.45,.17],[.50,.17],[.49,.21],[.47,.26],[.47,.33],[.45,.41],[.44,.45],[.41,.44],[.41,.28],[.40,.235]],[[.575,.30],[.58,.34],[.575,.44],[.54,.45],[.55,.39]]],
  pelvis: [[[.54,.44],[.575,.44],[.58,.53],[.555,.575],[.52,.56]],[[.41,.445],[.44,.445],[.43,.54],[.41,.55]]],
  right_calf: [[[.435,.71],[.52,.71],[.545,.78],[.54,.84],[.515,.93],[.475,.94],[.465,.86],[.435,.79]]],
};
const REGIONS = [FRONT, LEFT, BACK, RIGHT];
const PINS = [
  { head:[.515,.10], torso:[.51,.32], pelvis:[.51,.51], right_upper_arm:[.37,.30], left_upper_arm:[.655,.30], right_calf:[.43,.81], left_calf:[.59,.81] },
  { head:[.50,.10], torso:[.57,.33], pelvis:[.425,.50], left_upper_arm:[.48,.29], left_calf:[.46,.81] },
  { head:[.515,.09], torso:[.51,.30], pelvis:[.51,.50], left_upper_arm:[.37,.29], right_upper_arm:[.655,.29], left_calf:[.43,.80], right_calf:[.59,.80] },
  { head:[.49,.10], torso:[.43,.32], pelvis:[.555,.50], right_upper_arm:[.53,.29], right_calf:[.50,.81] },
];

export function viewIndex(index) { return ((index % 4) + 4) % 4; }
function inside(x, y, polygon) {
  let hit = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i], [xj, yj] = polygon[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) hit = !hit;
  }
  return hit;
}
export function regionAt(x, y, angle = 0) {
  return Object.entries(REGIONS[viewIndex(angle)]).find(([, polygons]) => polygons.some(p => inside(x, y, p)))?.[0] || null;
}
let asset;
function loadAsset() {
  if (!asset) asset = new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image); image.onerror = reject;
    image.src = new URL("../models/recovery/body-illustration.png", import.meta.url).href;
  }).catch(error => { asset = null; throw error; });
  return asset;
}

export async function mountBody(host, { regions, levels, known, trained, onSelect, onUnsupported }) {
  let disposed = false, resize, appearance, frame = 0;
  const cleanup = [];
  const detach = new MutationObserver(() => { if (!host.isConnected) dispose(); });
  detach.observe(host.closest("main") || document.body, { childList: true });
  function dispose() {
    if (disposed) return;
    disposed = true; cancelAnimationFrame(frame); detach.disconnect(); resize?.disconnect(); appearance?.disconnect();
    cleanup.forEach(fn => fn());
  }
  try {
    const image = await loadAsset();
    if (disposed || !host.isConnected) { dispose(); return null; }
    const canvas = document.createElement("canvas"), ctx = canvas.getContext("2d");
    if (!ctx) throw Error("Canvas unavailable");
    canvas.tabIndex = 0; canvas.setAttribute("role", "img");
    const badge = document.createElement("span"); badge.className = "ov-angle-label"; badge.setAttribute("aria-live", "polite");
    const label = document.createElement("span"); label.className = "ov-body-label"; label.hidden = true;
    host.replaceChildren(canvas, badge, label);
    const cellW = image.naturalWidth / 2, cellH = image.naturalHeight / 2;
    const base = document.createElement("canvas"), overlay = document.createElement("canvas");
    base.width = overlay.width = cellW; base.height = overlay.height = cellH;
    const body = base.getContext("2d", { willReadFrequently: true }), ink = overlay.getContext("2d");
    if (!body || !ink) throw Error("Canvas unavailable");
    let knownRegions = null, annotations = {};
    let angle = 0, view = "sore", selected = "", box = { x:0, y:0, size:1 }, alpha;
    const loadView = () => {
      body.clearRect(0, 0, cellW, cellH);
      body.drawImage(image, (angle % 2) * cellW, Math.floor(angle / 2) * cellH, cellW, cellH, 0, 0, cellW, cellH);
      alpha = body.getImageData(0, 0, cellW, cellH).data;
      badge.textContent = rv(VIEWS[angle]);
      canvas.setAttribute("aria-label", `${rv("bodyAria")} ${rv(VIEWS[angle])}`);
    };
    function draw() {
      frame = 0;
      if (disposed || !host.isConnected) return;
      const { width, height } = host.getBoundingClientRect();
      if (width < 1 || height < 1) return;
      const dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // Each source cell has broad transparent side margins. Its full height
      // remains fixed across views and fit never crops the figure on mobile.
      const size = Math.min(height - 16, width / .56);
      box = { x: (width - size) / 2, y: 8, size };
      ctx.clearRect(0, 0, width, height);
      ctx.drawImage(base, box.x, box.y, size, size);
      ink.clearRect(0, 0, cellW, cellH);
      const style = getComputedStyle(host);
      for (const [region, polygons] of Object.entries(REGIONS[angle])) {
        if (!regions.includes(region)) continue;
        const value = view === "trained" ? (trained.has(region) ? "trained" : null) : known && (!knownRegions || knownRegions.includes(region)) ? (levels[region] || 0) : null;
        // Preserve the neutral source shading for a recorded zero.
        if (value === 0) continue;
        ink.save(); ink.filter = "blur(5px)"; ink.globalAlpha = value == null ? .28 : value === "trained" ? .55 : [.0,.32,.57,.78][value];
        ink.fillStyle = style.getPropertyValue(value == null ? "--c-axis" : value === "trained" ? "--c-exercise" : `--c-sore-${value}`).trim();
        polygons.forEach(polygon => {
          ink.beginPath(); polygon.forEach(([x,y], i) => i ? ink.lineTo(x * cellW, y * cellH) : ink.moveTo(x * cellW, y * cellH));
          ink.closePath(); ink.fill();
        });
        ink.restore();
      }
      ink.save(); ink.globalCompositeOperation = "destination-in"; ink.drawImage(base, 0, 0); ink.restore();
      ctx.drawImage(overlay, box.x, box.y, size, size);
      const pin = PINS[angle][selected];
      label.hidden = !pin;
      if (pin) {
        const x = box.x + pin[0] * size, y = box.y + pin[1] * size;
        ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fillStyle = "#fff"; ctx.fill();
        ctx.strokeStyle = style.getPropertyValue("--accent").trim() || "#3174bb"; ctx.lineWidth = 2; ctx.stroke();
        const value = known ? t(`sore.level.${levels[selected] || 0}`) : rv("unknown");
        label.textContent = view === "sore" && annotations[selected] ? annotations[selected] : `${t(`sore.region.${selected}`)} · ${view === "trained" ? (trained.has(selected) ? rv("trainingLegend") : rv("unknown")) : value}`;
        label.style.left = `${Math.max(6, Math.min(width - 150, x + 14))}px`;
        label.style.top = `${Math.max(6, y - 38)}px`;
      }
    }
    const paint = () => { if (!disposed && !frame) frame = requestAnimationFrame(draw); };
    const rotate = step => { angle = viewIndex(angle + Math.sign(step)); loadView(); paint(); };
    resize = new ResizeObserver(paint); resize.observe(host);
    appearance = new MutationObserver(paint); appearance.observe(document.documentElement, { attributes:true, attributeFilter:["data-mode", "class"] });
    const media = matchMedia("(prefers-color-scheme: dark)"); media.addEventListener("change", paint);
    cleanup.push(() => media.removeEventListener("change", paint));
    let drag;
    canvas.onpointerdown = event => {
      if (!event.isPrimary || event.button !== 0) return;
      drag = { id:event.pointerId, x:event.clientX, y:event.clientY, moved:false };
      canvas.setPointerCapture(event.pointerId);
    };
    canvas.onpointermove = event => {
      if (drag?.id === event.pointerId && Math.hypot(event.clientX - drag.x, event.clientY - drag.y) > 8) drag.moved = true;
    };
    canvas.onpointercancel = () => { drag = null; };
    canvas.onpointerup = event => {
      if (!drag || event.pointerId !== drag.id) return;
      const { x, y, moved } = drag; drag = null;
      if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
      const dx = event.clientX - x, dy = event.clientY - y;
      if (moved) { if (Math.abs(dx) > 28 && Math.abs(dx) > Math.abs(dy)) rotate(Math.sign(dx)); return; }
      const rect = canvas.getBoundingClientRect(), px = (event.clientX - rect.left - box.x) / box.size, py = (event.clientY - rect.top - box.y) / box.size;
      if (px < 0 || px >= 1 || py < 0 || py >= 1 || alpha[(Math.floor(py * cellH) * cellW + Math.floor(px * cellW)) * 4 + 3] < 80) return;
      const region = regionAt(px, py, angle);
      if (region && regions.includes(region)) onSelect(region); else onUnsupported();
    };
    canvas.onkeydown = event => {
      if (["ArrowLeft", "ArrowRight"].includes(event.key)) { event.preventDefault(); rotate(event.key === "ArrowLeft" ? -1 : 1); }
    };
    cleanup.push(() => { canvas.onpointerdown = canvas.onpointermove = canvas.onpointerup = canvas.onpointercancel = canvas.onkeydown = null; });
    loadView(); paint();
    return {
      rotate,
      reset() { angle = 0; loadView(); paint(); },
      update(next) { levels = next.levels; known = next.known; knownRegions = next.knownRegions; annotations = next.annotations || {}; view = next.view; selected = next.selected; paint(); },
      dispose,
    };
  } catch {
    dispose();
    if (host.isConnected) host.innerHTML = `<p class="ov-model-message">${rv("fallback")}</p>`;
    return null;
  }
}
