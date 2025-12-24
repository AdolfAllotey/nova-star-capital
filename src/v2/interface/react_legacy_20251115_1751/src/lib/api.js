// src/lib/api.js
// =============================================
// Client API centralisé pour l’interface NSC V2
// =============================================

// Base de l’API backend
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// Utility: fetch + JSON
export async function fetchJSON(path) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url);

  if (!res.ok) {
    throw new Error(`API error ${res.status} on ${url}`);
  }
  return await res.json();
}

// Alias rétro-compatibilité pour l’ancien nom utilisé dans certaines pages
export async function getJSON(path) {
  return fetchJSON(path);
}

// ===============================
//        MARKET
// ===============================
export function getTopMovers() {
  return fetchJSON("/market/top-movers");
}

export function getMarketRegime() {
  return fetchJSON("/market/regime");
}

// ===============================
//        PROFITABILITY
// ===============================
export function getMonthlyProfitability() {
  return fetchJSON("/profitability/monthly");
}

// ===============================
//        TRADING
// ===============================
export function getOpenPositions() {
  return fetchJSON("/open-positions");
}

export function getWorstTrades() {
  return fetchJSON("/worst-trades");
}

// ===============================
//        SENTIMENT
// ===============================
export function getSentimentOverview() {
  return fetchJSON("/sentiment/overview");
}

// ===============================
//        WHALES
// ===============================
export function getWhalesLeaderboard() {
  return fetchJSON("/whales/leaderboard");
}

// Compat pour anciens imports
export const getWhaleLeaderboard = getWhalesLeaderboard;

// ===============================
//        ICO PIPELINE
// ===============================
export function getIcoCandidates() {
  return fetchJSON("/ico/candidates");
}

export function getIcoScreened() {
  return fetchJSON("/ico/screened");
}

export function getIcoScored() {
  return fetchJSON("/ico/scored");
}

export function getIcoAllocation() {
  return fetchJSON("/ico/allocation");
}

// ===============================
//        GENERIC
// ===============================
export function getSystemMetrics() {
  return fetchJSON("/metrics");
}

// =============================================
//        OBJET COMPAT "api" (vieux imports)
// =============================================
export const api = {
  API_BASE,
  fetchJSON,
  getJSON,

  // Market
  getTopMovers,
  getMarketRegime,

  // Profit
  getMonthlyProfitability,

  // Trading
  getOpenPositions,
  getWorstTrades,

  // Sentiment
  getSentimentOverview,

  // Whales
  getWhalesLeaderboard,
  getWhaleLeaderboard,

  // ICO
  getIcoCandidates,
  getIcoScreened,
  getIcoScored,
  getIcoAllocation,

  // Metrics
  getSystemMetrics,
};
