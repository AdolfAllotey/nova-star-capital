/**
 * Charge les données de simulation pour une date donnée
 * @param {string} date - format YYYY-MM-DD
 * @returns {Promise<object>} - { trades: [], ... }
 */
export async function fetchSimulationData(date) {
  try {
    const response = await fetch(`/data/simulation/${date}.json`);
    if (!response.ok) throw new Error(`HTTP error! ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error(`Error loading data for ${date}:`, error);
    return { trades: [] };
  }
}

/**
 * Charge les données de simulation pour une liste de dates
 * @param {string[]} dates
 * @returns {Promise<Array<{ date: string, trades: [], totalPnl: number }>>}
 */
export async function fetchMultipleSimulationData(dates) {
  const results = [];

  for (const date of dates) {
    const data = await fetchSimulationData(date);
    const trades = data.trades || [];
    const totalPnl = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);
    results.push({ date, trades, totalPnl });
  }

  return results;
}

/**
 * Génère une liste des N derniers jours (au format YYYY-MM-DD)
 * @param {number} days
 * @returns {string[]}
 */
export function getLastNDates(days = 7) {
  const today = new Date();
  return [...Array(days)].map((_, i) => {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    return d.toISOString().slice(0, 10);
  }).reverse();
}