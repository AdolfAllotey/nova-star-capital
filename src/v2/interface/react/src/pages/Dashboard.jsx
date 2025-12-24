// src/pages/Dashboard.jsx
// Dashboard global NSC – version robuste (ne casse pas si l’API renvoie null)

import React, { useEffect, useState } from "react";

// On fige la base URL de l'API préprod pour éviter localhost ou une mauvaise env
const API_BASE = "https://api.preprod.novastarcapital.fr";

function buildUrl(path) {
  return `${API_BASE.replace(/\/+$/, "")}${path}`;
}

function Section({ title, children }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold text-zinc-100 mb-3 border-b border-zinc-800 pb-1">
        {title}
      </h2>
      <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
        {children}
      </div>
    </section>
  );
}

function StatCard({ label, value, helper }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-zinc-400">
        {label}
      </span>
      <span className="text-xl font-semibold text-zinc-50">{value}</span>
      {helper && <span className="text-xs text-zinc-500">{helper}</span>}
    </div>
  );
}

export default function Dashboard() {
  const [sentiment, setSentiment] = useState(null);
  const [regime, setRegime] = useState(null);
  const [profitability, setProfitability] = useState(null);
  const [topWhales, setTopWhales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function safeFetch(path) {
      try {
        const res = await fetch(buildUrl(path));
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return await res.json();
      } catch (e) {
        console.error(`Erreur fetch ${path}:`, e);
        return null;
      }
    }

    async function loadDashboard() {
      setLoading(true);
      setError("");

      const [sent, reg, prof, whales] = await Promise.all([
        safeFetch("/sentiment/overview"),
        safeFetch("/market/regime"),
        safeFetch("/profitability/monthly"),
        safeFetch("/whales/leaderboard"),
      ]);

      if (cancelled) return;

      setSentiment(sent);
      setRegime(reg);
      setProfitability(prof);

      setTopWhales(
        Array.isArray(whales?.leaders)
          ? whales.leaders.slice(0, 5)
          : Array.isArray(whales)
          ? whales.slice(0, 5)
          : []
      );

      if (!sent && !reg && !prof && (!whales || whales.length === 0)) {
        setError("Impossible de charger les données du dashboard.");
      }

      setLoading(false);
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, []);

  // Sentiment : valeurs par défaut
  const sentimentScore =
    typeof sentiment?.score === "number" ? sentiment.score : 0;
  const sentimentLabel = sentiment?.label || "Neutre / indéterminé";

  // Régime : valeurs par défaut
  const regimeLabel = regime?.label || regime?.regime || "Inconnu";
  const regimeConfidence =
    typeof regime?.confidence === "number" ? regime.confidence : null;

  // Profitabilité : support plusieurs formats
  let monthlyPnl = null;
  let monthlyCosts = null;
  let netPnl = null;

  if (profitability) {
    // Cas 1 : format objet { monthly_pnl, monthly_costs, net_pnl }
    if (typeof profitability.monthly_pnl === "number") {
      monthlyPnl = profitability.monthly_pnl;
    }
    if (typeof profitability.monthly_costs === "number") {
      monthlyCosts = profitability.monthly_costs;
    }
    if (typeof profitability.net_pnl === "number") {
      netPnl = profitability.net_pnl;
    }

    // Cas 2 : format tableau (ton /profitability/monthly actuel)
    if (Array.isArray(profitability) && profitability.length > 0) {
      const last = profitability[profitability.length - 1];
      if (typeof last?.pnl === "number") {
        monthlyPnl = last.pnl;
        netPnl = last.pnl;
      }
    }

    if (netPnl === null && monthlyPnl !== null && monthlyCosts !== null) {
      netPnl = monthlyPnl - monthlyCosts;
    }
  }

  return (
    <div className="space-y-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">
            NSC Trading Desk – Dashboard
          </h1>
          <p className="text-sm text-zinc-400">
            Vue globale de l’état du bot (sentiment, régime de marché, PnL, whales).
          </p>
        </div>
      </header>

      {error && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-400">
          Chargement du dashboard…
        </div>
      ) : (
        <>
          {/* Ligne 1 : Sentiment + Régime + PnL */}
          <div className="grid gap-6 md:grid-cols-3">
            <Section title="Sentiment global">
              <div className="space-y-3">
                <StatCard
                  label="Sentiment agrégé"
                  value={`${sentimentLabel} (${sentimentScore.toFixed(2)})`}
                  helper="Score basé sur Telegram, Twitter, Reddit et signaux marché."
                />
                <div className="w-full h-2 rounded-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 overflow-hidden">
                  <div
                    className="h-full bg-zinc-900/70"
                    style={{
                      width: `${((sentimentScore + 1) / 2) * 100}%`,
                    }}
                  />
                </div>
                <div className="flex justify-between text-xs text-zinc-500">
                  <span>Bearish</span>
                  <span>Neutre</span>
                  <span>Bullish</span>
                </div>
              </div>
            </Section>

            <Section title="Régime de marché">
              <div className="space-y-3">
                <StatCard
                  label="Régime détecté"
                  value={regimeLabel}
                  helper={
                    regimeConfidence !== null
                      ? `Confiance : ${(regimeConfidence * 100).toFixed(0)} %`
                      : "Confiance : n/d"
                  }
                />
                <p className="text-xs text-zinc-500">
                  Le régime pilote les tailles de position, le risk mode et la
                  répartition Trading / Long Terme / Sécurité.
                </p>
              </div>
            </Section>

            <Section title="Performance mensuelle">
              <div className="grid grid-cols-2 gap-4">
                <StatCard
                  label="PnL brut (mois)"
                  value={
                    monthlyPnl !== null ? `${monthlyPnl.toFixed(2)} €` : "n/d"
                  }
                  helper="Dernier mois disponible sur /profitability/monthly."
                />
                <StatCard
                  label="Coûts (mois)"
                  value={
                    monthlyCosts !== null
                      ? `${monthlyCosts.toFixed(2)} €`
                      : "n/d"
                  }
                />
                <StatCard
                  label="PnL net (après coûts)"
                  value={netPnl !== null ? `${netPnl.toFixed(2)} €` : "n/d"}
                  helper={
                    netPnl !== null
                      ? netPnl >= 0
                        ? "Le bot couvre ses coûts ce mois-ci."
                        : "Le bot ne couvre pas encore ses coûts ce mois-ci."
                      : ""
                  }
                />
              </div>
            </Section>
          </div>

          {/* Ligne 2 : Top whales */}
          <Section title="Top wallets suivis (whales)">
            {topWhales.length === 0 ? (
              <p className="text-sm text-zinc-500">
                Aucun wallet whale disponible pour le moment. Ils apparaîtront
                ici dès que le module sera connecté en préproduction.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm text-zinc-200">
                  <thead>
                    <tr className="border-b border-zinc-800 text-xs uppercase text-zinc-500">
                      <th className="py-2 text-left">Wallet</th>
                      <th className="py-2 text-right">PnL 30j</th>
                      <th className="py-2 text-right">Trades suivis</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topWhales.map((w, idx) => (
                      <tr
                        key={w.address || idx}
                        className="border-b border-zinc-900/60"
                      >
                        <td className="py-2 pr-4">
                          <span className="font-mono text-xs">
                            {w.address || "N/A"}
                          </span>
                        </td>
                        <td className="py-2 text-right">
                          {typeof w.pnl_30d === "number"
                            ? `${w.pnl_30d.toFixed(2)} %`
                            : "n/d"}
                        </td>
                        <td className="py-2 text-right">
                          {typeof w.trades_followed === "number"
                            ? w.trades_followed
                            : "n/d"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>
        </>
      )}
    </div>
  );
}
