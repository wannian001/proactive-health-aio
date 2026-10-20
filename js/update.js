// The update notice: when GitHub has a newer release than this copy (the server asks once a day), one line above the
// page says so. On this computer's own page it can install it; the server then restarts itself and the page reloads.
// Elsewhere (a phone, another computer) it says where to update. "Later" hides it until the next version.
import { esc } from "./charts.js?v=0f06915566";
import { t } from "./i18n.js?v=0f06915566";

const LATER = "healthaio.update.later";
let info = null;

const isLocal = () => ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
const later = () => { try { return localStorage.getItem(LATER); } catch { return null; } };

async function json(url, options) {
  const res = await fetch(url, { headers: { Accept: "application/json", ...(options?.headers || {}) }, ...options });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export async function loadUpdate() {
  try { info = await json("api/version"); } catch { info = null; }
}

export function updateNote() {
  if (!info?.update_available || later() === info.latest) return "";
  const here = info.can_update && isLocal();
  const action = here ? `<button class="doc-link" type="button" data-update>${t("upd.install")}</button>` : "";
  const how = here ? "" : `<span class="upd-how">${esc(t(info.can_update ? "upd.elsewhere" : "upd.manual"))}</span>`;
  const notes = info.url ? `<a class="doc-link" href="${esc(info.url)}" target="_blank" rel="noopener">${t("upd.notes")}</a>` : "";
  return `<div class="doc-note upd" role="status"><p><span data-upd-text>${esc(t("upd.available", { latest: info.latest, current: info.current }))}</span>${how}</p>
    <span class="upd-actions">${action}${notes}<button class="doc-link" type="button" data-later>${t("upd.later")}</button></span></div>`;
}

const pause = (ms) => new Promise((done) => setTimeout(done, ms));

export function mountUpdate(root) {
  const note = root.querySelector(".upd");
  if (!note) return;
  note.querySelector("[data-later]").onclick = () => {
    try { localStorage.setItem(LATER, info.latest); } catch { /* private mode: hidden until reload */ }
    note.remove();
  };
  const button = note.querySelector("[data-update]");
  if (!button) return;
  button.onclick = async () => {
    const say = (key, vars) => { note.querySelector("[data-upd-text]").textContent = t(key, vars); };
    note.querySelector(".upd-actions").hidden = true;
    note.querySelector(".upd-how")?.remove();
    say("upd.running");
    try {
      await json("api/update", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    } catch (error) {
      return say("upd.failed", { message: error.message });
    }
    // wait for the install, then for the server to come back with the new version
    for (let i = 0; i < 150; i += 1) {
      await pause(2000);
      try {
        const job = await json("api/update");
        if (job.running) continue;
        if (job.last && !job.last.ok) return say("upd.failed", { message: job.last.message });
        say("upd.restarting");
      } catch { /* restarting: no answer for a moment */ }
      try {
        const now = await json("api/version");
        if (now.current === info.latest) return location.reload();
      } catch { /* not back yet */ }
    }
    say("upd.failed", { message: "timeout" });
  };
}
