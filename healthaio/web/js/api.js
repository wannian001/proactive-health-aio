// Live mode asks the local server (/api/today?day=...). Static mode (GitHub Pages demo) reads
// pre-built files (api/today.json, api/today@2026-10-11.json) written by `healthaio build-static`.
const STATIC = document.documentElement.dataset.static === "true";
const BUILD = document.documentElement.dataset.build || "";  // static builds stamp their data too, so caches never mix versions
const cache = new Map();

export function apiUrl(name, param) {
  if (STATIC) return `api/${name}${param ? `@${param}` : ""}.json${BUILD ? `?v=${BUILD}` : ""}`;
  return `api/${name}${param ? `?day=${encodeURIComponent(param)}` : ""}`;
}

export async function get(name, param) {
  const url = apiUrl(name, param);
  const hit = cache.get(url);
  if (hit && (STATIC || Date.now() - hit.at < 60000)) return hit.body;  // live data is re-read after a minute
  const abort = typeof AbortController === "function" ? new AbortController() : null;
  const timer = abort ? setTimeout(() => abort.abort(), 15000) : null;  // never hang on "Loading…"
  let res;
  try {
    res = await fetch(url, { headers: { Accept: "application/json" }, signal: abort?.signal });
  } finally {
    if (timer) clearTimeout(timer);
  }
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  const body = await res.json();
  cache.set(url, { body, at: Date.now() });
  return body;
}

export const isStatic = STATIC;

// Local app writes: goals, check-ins, workout notes, rest sessions and reflections.
// Every page is read again afterwards so that shared state cannot disagree across pages.
export async function post(name, body) {
  if (STATIC) throw new Error("This static demo is read-only.");
  const res = await fetch(`api/${name}`, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body) });
  const out = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(out.error || `${res.status}`);
  cache.clear();
  return out;
}
