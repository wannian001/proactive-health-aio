// A card's detail as a row of tabs (the kit's .seg switch), one panel shown at a time, so a page keeps every chart
// without showing them all at once. A chart in a hidden panel is drawn when its panel opens (draw() redraws on resize).
import { esc } from "../charts.js?v=11473b41ff";

// items: [{ key, label, html }]; the first one is open
export function tabs(id, items) {
  const list = items.filter(Boolean);
  const seg = list.map((x, i) => `<button type="button" role="tab" data-tab="${id}" data-key="${x.key}" aria-selected="${i === 0}" aria-pressed="${i === 0}">${esc(x.label)}</button>`).join("");
  const panels = list.map((x, i) => `<div class="tab-panel" role="tabpanel" data-panel="${id}:${x.key}"${i ? " hidden" : ""}>${x.html}</div>`).join("");
  return `<div class="seg tabs-seg" role="tablist">${seg}</div>${panels}`;
}

export function mountTabs(root) {
  root.querySelectorAll("button[data-tab]").forEach((b) => {
    b.onclick = () => {
      const id = b.dataset.tab;
      root.querySelectorAll(`button[data-tab="${id}"]`).forEach((x) => { x.setAttribute("aria-pressed", String(x === b)); x.setAttribute("aria-selected", String(x === b)); });
      root.querySelectorAll(`[data-panel^="${id}:"]`).forEach((panel) => { panel.hidden = panel.dataset.panel !== `${id}:${b.dataset.key}`; });
    };
  });
}
