// src/pages/Profitability.jsx
// Suivi de la rentabilité mensuelle (P&L vs coûts) à partir de /profitability/monthly

import React, { useEffect, useMemo, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://api.preprod.novastarcapital.fr";

function buildUrl(path) {
  return `${API_BASE.replace(/\/+$/, "")}${path}`;
}

function Section({ title, description, children }) {
  return (
    <section className="mb-8">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-lg font-semibold text-zinc-100 border-b border-zinc-800 pb-1">
          {title}
        </h2>
        {description && (
          <p className="text-xs text-zinc-500 ml-4">{description}</p>
        )}
      </div>
      <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
        {children}
      </div>
    </section>
  );
}

function Stat({ label, value, hint }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-sm font-semibold text-zinc-100">{value}</span>
      {hint && <span className="text-[11px] text-zinc-500 mt-0.5">{hint}</span>}
    </div>
  );
}

function formatCurrency(v) {
  if (v === null || v === undefined || isNaN(v)) return "–";
  return `${v.toFixed(2)} €`;
}

function formatPct(v) {
  if (v === null || v === undefined || isNaN(v)) return "–";
  return `${v.toFixed(2)} %`;
}

function formatMonthLabel(item) {
  // tolerante: year/month ou label direct
  if (item.label) return item.label;
  const y = item.year;
  const m = item.month;
  if (!y || !m) return "N/A";
  const month = String(m).padStart(2, "0");
  return `${y}-${month}`;
}

export default function ProfitabilityPage() {
  const [data, setData] = useState(null);
  const [monthly, setMonthly] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(buildUrl("/profitability/monthly"));
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const json = await res.json();
        if (!cancelled) {
          setData(json);
          const items = Array.isArray(json.monthly) ? json.monthly : [];
          setMonthly(items);
        }
      } catch (err) {
        console.error("Error fetching profitability:", err);
        if (!cancelled) {
          setError(
            "Impossible de charger la rentabilité mensuelle. Vérifie l’API /profitability/monthly."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  const aggregates = useMemo(() => {
    if (!monthly.length) {
      return {
        pnlNetTotal: null,
        pnlGrossTotal: null,
        costsTotal: null,
        monthsCount: 0,
      };
    }

    let pnlNetTotal = 0;
    let pnlGrossTotal = 0;
    let costsTotal = 0;

    for (const m of monthly) {
      const gross =
        typeof m.pnl_gross_eur === "number"
          ? m.pnl_gross_eur
          : Number(m.pnl_gross_eur ?? 0);
      const net =
        typeof m.pnl_net_eur === "number"
          ? m.pnl_net_eur
          : Number(m.pnl_net_eur ?? 0);
      const cost =
        typeof m.costs_eur === "number"
          ? m.costs_eur
          : Number(m.costs_eur ?? 0);

      pnlGrossTotal += isNaN(gross) ? 0 : gross;
      pnlNetTotal += isNaN(net) ? 0 : net;
      costsTotal += isNaN(cost) ? 0 : cost;
    }

    return {
      pnlNetTotal,
      pnlGrossTotal,
      costsTotal,
      monthsCount: monthly.length,
    };
  }, [monthly]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="mb-4">
        <h1 className="text-2xl font-semibold text-zinc-100 mb-1">
          Rentabilité mensuelle
        </h1>
        <p className="text-sm text-zinc-400">
          Suivi des performances du bot Nova Star Capital (P&amp;L) comparées
          aux coûts d’exploitation (API, infra, envoi d’alertes…) pour vérifier
          la viabilité économique du système.
        </p>
      </header>

      {/* Bloc résumé global */}
      <Section
        title="Synthèse globale"
        description="Vue agrégée des mois disponibles dans monthly_pnl.json."
      >
        {loading && !data ? (
          <div className="text-sm text-zinc-400">Chargement…</div>
        ) : error ? (
          <div className="text-sm text-red-400">{error}</div>
        ) : !monthly.length ? (
          <div className="text-sm text-zinc-400">
            Aucun historique mensuel pour le moment.  
            Dès que le bot tournera en **simulation / réel**, les{" "}
            <span className="font-medium text-emerald-400">
              mois apparaîtront automatiquement
            </span>{" "}
            ici à partir de <code>monthly_pnl.json</code>.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Stat
              label="P&L brut cumulé"
              value={formatCurrency(aggregates.pnlGrossTotal)}
              hint="Somme des P&L bruts mensuels"
            />
            <Stat
              label="Coûts cumulés"
              value={formatCurrency(aggregates.costsTotal)}
              hint="APIs, serveurs, stockage, envoi…"
            />
            <Stat
              label="P&L net cumulé"
              value={formatCurrency(aggregates.pnlNetTotal)}
              hint="P&L brut - coûts (sur la période)"
            />
          </div>
        )}
      </Section>

      {/* Tableau mensuel */}
      <Section
        title="Détail par mois"
        description="Détail des gains, coûts et P&L nets mois par mois."
      >
        {loading && !data ? (
          <div className="text-sm text-zinc-400">Chargement…</div>
        ) : error ? (
          <div className="text-sm text-red-400">{error}</div>
        ) : !monthly.length ? (
          <div className="text-sm text-zinc-400">
            Les lignes mensuelles apparaîtront dès qu’un premier{" "}
            <code>monthly_pnl.json</code> sera généré par la pipeline
            (préprod).
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-xs text-zinc-500">
                  <th className="text-left py-2 pr-2">Mois</th>
                  <th className="text-right py-2 pr-2">P&amp;L brut (€)</th>
                  <th className="text-right py-2 pr-2">Coûts (€)</th>
                  <th className="text-right py-2 pr-2">P&amp;L net (€)</th>
                  <th className="text-right py-2 pr-2">P&amp;L brut (%)</th>
                  <th className="text-right py-2 pr-2">P&amp;L net (%)</th>
                  <th className="text-right py-2 pl-2">Equity fin de mois (€)</th>
                </tr>
              </thead>
              <tbody>
                {monthly.map((m, idx) => {
                  const monthLabel = formatMonthLabel(m);
                  const gross =
                    typeof m.pnl_gross_eur === "number"
                      ? m.pnl_gross_eur
                      : Number(m.pnl_gross_eur ?? NaN);
                  const costs =
                    typeof m.costs_eur === "number"
                      ? m.costs_eur
                      : Number(m.costs_eur ?? NaN);
                  const net =
                    typeof m.pnl_net_eur === "number"
                      ? m.pnl_net_eur
                      : Number(m.pnl_net_eur ?? NaN);
                  const grossPct =
                    typeof m.pnl_gross_pct === "number"
                      ? m.pnl_gross_pct
                      : Number(m.pnl_gross_pct ?? NaN);
                  const netPct =
                    typeof m.pnl_net_pct === "number"
                      ? m.pnl_net_pct
                      : Number(m.pnl_net_pct ?? NaN);
                  const equity =
                    typeof m.equity_eur === "number"
                      ? m.equity_eur
                      : Number(m.equity_eur ?? NaN);

                  return (
                    <tr
                      key={monthLabel || idx}
                      className="border-b border-zinc-800/60 hover:bg-zinc-900/60"
                    >
                      <td className="py-2 pr-2 text-zinc-100">{monthLabel}</td>
                      <td className="py-2 pr-2 text-right text-zinc-100">
                        {formatCurrency(isNaN(gross) ? null : gross)}
                      </td>
                      <td className="py-2 pr-2 text-right text-zinc-100">
                        {formatCurrency(isNaN(costs) ? null : costs)}
                      </td>
                      <td
                        className={`py-2 pr-2 text-right ${
                          !isNaN(net) && net < 0
                            ? "text-red-400"
                            : "text-emerald-400"
                        }`}
                      >
                        {formatCurrency(isNaN(net) ? null : net)}
                      </td>
                      <td className="py-2 pr-2 text-right text-zinc-100">
                        {formatPct(isNaN(grossPct) ? null : grossPct)}
                      </td>
                      <td className="py-2 pr-2 text-right text-zinc-100">
                        {formatPct(isNaN(netPct) ? null : netPct)}
                      </td>
                      <td className="py-2 pl-2 text-right text-zinc-100">
                        {formatCurrency(isNaN(equity) ? null : equity)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {/* Explications */}
      <Section
        title="Comment interpréter cette vue ?"
        description="Rappel du rôle de la page Profitability dans la préprod NSC."
      >
        <div className="space-y-2 text-sm text-zinc-300">
          <p>
            Cette page te permet de vérifier que le{" "}
            <span className="font-medium text-emerald-400">
              bot est rentable
            </span>{" "}
            une fois tous les coûts pris en compte : APIs (OpenAI, Etherscan,
            CEX…), serveurs (Hetzner), stockage, envoi d’alertes, etc.
          </p>
          <p>
            En préproduction, l’objectif est de valider la mécanique :{" "}
            <span className="font-medium">
              génération de <code>monthly_pnl.json</code>
            </span>{" "}
            par la pipeline, agrégation côté API, et affichage dans l’interface.
          </p>
          <p className="text-xs text-zinc-500">
            Une fois le mode réel activé, cette vue deviendra l’un des{" "}
            <span className="font-medium">
              KPI centraux de Nova Star Capital
            </span>{" "}
            pour piloter les réallocations de capital et les décisions
            stratégiques.
          </p>
        </div>
      </Section>
    </div>
  );
}
