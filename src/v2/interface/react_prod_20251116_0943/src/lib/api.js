// src/lib/api.js
// Petit client API centralisé pour l'UI Nova Star Capital

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/**
 * Appel JSON générique avec gestion des erreurs et fallback optionnel.
 */
export async function fetchJson(path, { fallback = null, signal } = {}) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

  try {
    const res = await fetch(url, { signal });
    if (!res.ok) {
      console.error(`[API] ${res.status} ${res.statusText} for ${url}`);
      return fallback;
    }
    return await res.json();
  } catch (err) {
    if (err.name !== "AbortError") {
      console.error("[API] fetch error:", err);
    }
    return fallback;
  }
}

// Compatibilité ancienne version : helper générique getJSON
// (utilisé par ex. dans TopMovers.jsx)
export function getJSON(path, options = {}) {
  return fetchJson(path, options);
}

// --- Endpoints "core" déjà utilisés par le dashboard ---

export function getTopMovers(options = {}) {
  return fetchJson("/market/top-movers", {
    fallback: { updated_at: null, items: [] },
    ...options,
  });
}

export function getMonthlyProfitability(options = {}) {
  return fetchJson("/profitability/monthly", {
    fallback: { updated_at: null, items: [] },
    ...options,
  });
}

export function getWorstTrades(options = {}) {
  return fetchJson("/risk/worst-trades", {
    fallback: { updated_at: null, items: [] },
    ...options,
  });
}

export function getOpenPositions(options = {}) {
  return fetchJson("/open-positions", {
    fallback: { updated_at: null, positions: [] },
    ...options,
  });
}

// --- Market regime (barre en haut) ---

export function getMarketRegime(options = {}) {
  return fetchJson("/market/regime", {
    fallback: {
      mode: "neutral",
      score: 0.0,
      updated_at: null,
      source: "default",
    },
    ...options,
  });
}

// --- Sentiment & Whales ---

export function getSentimentOverview(options = {}) {
  return fetchJson("/sentiment/overview", {
    fallback: {
      mode: "neutral",
      score: 0.0,
      updated_at: null,
      source: "default",
    },
    ...options,
  });
}

export function getWhaleLeaderboard(options = {}) {
  // On normalise en { items: [...] } même si l’API renvoie { wallets: [...] }
  return fetchJson("/whales/leaderboard", {
    fallback: { items: [] },
    ...options,
  }).then((data) => {
    if (!data) return { items: [] };
    if (Array.isArray(data)) return { items: data };
    if (Array.isArray(data.items)) return { items: data.items };
    if (Array.isArray(data.wallets)) return { items: data.wallets };
    return { items: [] };
  });
}

// --- ICO flows ---

export function getIcoCandidates(options = {}) {
  return fetchJson("/ico/candidates", {
    fallback: { updated_at: null, items: [] },
    ...options,
  });
}

export function getIcoScreened(options = {}) {
  return fetchJson("/ico/screened", {
    fallback: { updated_at: null, items: [] },
    ...options,
  });
}

export function getIcoScored(options = {}) {
  return fetchJson("/ico/scored", {
    fallback: { updated_at: null, items: [] },
    ...options,
  });
}

export function getIcoAllocation(options = {}) {
  return fetchJson("/ico/allocation", {
    fallback: { updated_at: null, items: [] },
    ...options,
  });
}

// Compatibilité ancienne version : helper générique fetchJSON
// (utilisé par ex. dans les pages ICO)
export function fetchJSON(path, options = {}) {
  return fetchJson(path, options);
}
