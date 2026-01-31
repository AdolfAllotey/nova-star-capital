// src/lib/apiClient.js
// Client API minimal (fetchJson + buildUrl), robuste côté PREPROD.

const API_BASE =
  (typeof window !== "undefined" && window.__NSC_API_BASE__) ||
  import.meta.env.VITE_API_BASE_URL ||     // legacy
  import.meta.env.VITE_API_BASE ||         // standard (celui que tu as mis dans .env.local)
  "https://api.preprod.novastarcapital.fr";

function buildUrl(path) {
  const base = String(API_BASE || "").replace(/\/+$/, "");
  const p = String(path || "");
  return `${base}${p.startsWith("/") ? p : `/${p}`}`;
}

// Compat: certains écrans importent apiUrl
export function apiUrl(path) { return buildUrl(path); }

async function _readJsonSafe(res) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchJson(path, opts = {}) {
  const { timeoutMs = 12000, ...rest } = opts || {};
  const url = buildUrl(path);

  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      ...rest,
      signal: ctrl.signal,
      headers: {
        Accept: "application/json",
        ...(rest.headers || {}),
      },
      cache: "no-store",
    });

    const data = await _readJsonSafe(res);

    if (!res.ok) {
      return { ok: false, status: res.status, error: data || { detail: res.statusText } };
    }
    return { ok: true, status: res.status, data };
  } catch (e) {
    return { ok: false, status: 0, error: { message: String(e?.message || e || "fetch error") } };
  } finally {
    clearTimeout(t);
  }
}

export { buildUrl, API_BASE };
