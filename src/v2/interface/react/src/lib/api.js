// src/lib/api.js
// Client HTTP centralisé pour l'interface NSC V2

const API_BASE =
  import.meta.env.VITE_API_BASE?.replace(/\/+$/, "") || "http://localhost:8000";

/**
 * Helper générique : GET JSON
 */
export async function fetchJSON(path, options = {}) {
  const url =
    path.startsWith("http://") || path.startsWith("https://")
      ? path
      : `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;

  const res = await fetch(url, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    const err = new Error(
      `HTTP ${res.status} ${res.statusText} for ${url} — ${text.slice(
        0,
        200
      )}`
    );
    err.status = res.status;
    throw err;
  }

  return res.json();
}

/**
 * Alias historique (certains composants utilisaient getJSON)
 */
export { fetchJSON as getJSON };

/**
 * Wrappers dédiés par fonctionnalité
 */

export async function getTopMovers() {
  return fetchJSON("/market/top-movers");
}

export async function getMarketRegime() {
  return fetchJSON("/market/regime");
}

export async function getProfitabilityMonthly() {
  return fetchJSON("/profitability/monthly");
}

export async function getWorstTrades() {
  return fetchJSON("/worst-trades");
}

export async function getOpenPositions() {
  return fetchJSON("/open-positions");
}

export async function getSentimentOverview() {
  return fetchJSON("/sentiment/overview");
}

export async function getWhaleLeaderboard() {
  return fetchJSON("/whales/leaderboard");
}

// ICO
export async function getIcoCandidates() {
  return fetchJSON("/ico/candidates");
}
export async function getIcoScreened() {
  return fetchJSON("/ico/screened");
}
export async function getIcoScored() {
  return fetchJSON("/ico/scored");
}
export async function getIcoAllocation() {
  return fetchJSON("/ico/allocation");
}

// Export d’un objet "api" si on veut l’utiliser ailleurs
const api = {
  API_BASE,
  fetchJSON,
  getJSON: fetchJSON,
  getTopMovers,
  getMarketRegime,
  getProfitabilityMonthly,
  getWorstTrades,
  getOpenPositions,
  getSentimentOverview,
  getWhaleLeaderboard,
  getIcoCandidates,
  getIcoScreened,
  getIcoScored,
  getIcoAllocation,
};

export default api;
