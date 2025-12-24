// src/lib/api.js
const API_BASE =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_API_BASE) ||
  "https://api.preprod.novastarcapital.fr";

async function getJSON(path, { signal } = {}) {
  const url = `${API_BASE}${path}`;
  const r = await fetch(url, {
    method: "GET",
    credentials: "omit",
    headers: { Accept: "application/json" },
    signal,
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    throw new Error(`GET ${path} -> ${r.status} ${r.statusText} ${text || ""}`);
  }
  return r.json();
}

/** Essaie plusieurs endpoints et retourne le premier qui répond OK. */
async function getFirstJSON(paths, { signal } = {}) {
  let lastErr;
  for (const p of paths) {
    try {
      return await getJSON(p, { signal });
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("No endpoint responded");
}

/* ---------------- Public API helpers ---------------- */
export const getStatus = () => getJSON("/health");

export const getOpenPositions = () =>
  getFirstJSON(["/positions/open", "/positions", "/portfolio/open"]);

export const getTrades = () =>
  getFirstJSON(["/trades", "/trades/live", "/signals/trades"]);

export const getTradesHistory = () =>
  getFirstJSON(["/trades/history", "/history/trades", "/trades?scope=history"]);

export const getSignals = () =>
  getFirstJSON(["/signals", "/signals/latest"]);

export const getPnL = () =>
  getFirstJSON(["/pnl", "/metrics/pnl", "/reports/pnl"]);

export const getWorstTrades = () =>
  getFirstJSON(["/risk/worst-trades", "/worst_trades", "/risk/worst"]);

export const getCosts = () =>
  getFirstJSON(["/costs/monthly", "/reports/costs/monthly", "/metrics/costs"]);

export const getWhales = () =>
  getFirstJSON([
    "/whales",
    "/monitoring/whales",
    "/intelligence/whales",
    "/signals/whales",
  ]);

/* -------- Résumé LLM des pires trades -------- */
export const getWorstTradesSummary = () =>
  getFirstJSON([
    "/risk/worst-trades/summary",
    "/reports/worst_trades_summary",
    "/risk/worst/summary",
    "/reports/worst-trades-summary",
  ]);
