// src/pages/Profitability.jsx
import React, { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";

function formatCurrency(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  try {
    return Number(value).toLocaleString("fr-FR", {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    });
  } catch {
    return String(value);
  }
}

function formatMonth(label) {
  if (!label) return "—";
  // on accepte "2025-10" ou une date ISO
  try {
    if (/^\d{4}-\d{2}$/.test(label)) {
      const [y, m] = label.split("-");
      const d = new Date(Number(y), Number(m) - 1, 1);
      return d.toLocaleDateString("fr-FR", { month: "short", year: "numeric" });
    }
    const d = new Date(label);
    if (Number.isNaN(d.getTime())) return label;
    return d.toLocaleDateString("fr-FR", { month: "short", year: "numeric" });
  } catch {
    return label;
  }
}

function formatDateTime(value) {
  if (!value) return "—";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleString("fr-FR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return String(value);
  }
}

export default function Profitability() {
  const [data, setData] = useState(null); // réponse brute API
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        // On utilise le helper générique pour éviter les erreurs de binding
        const res = await api.getJSON("/profitability/monthly");
        if (!alive) return;
        setData(res);
      } catch (err) {
        if (!alive) return;
        console.error("[Profitability] Erreur API:", err);
        setError(err?.message || "Erreur lors du chargement de la rentabilité.");
      } finally {
        if (alive) setLoading(false);
      }
    }

    load();
    return () => {
      alive = false;
    };
  }, []);

  // On normalise la structure : data.items = tableau de mois
  const items = useMemo(() => {
    if (!data) return [];
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.months)) return data.months;
    return [];
  }, [data]);

  const updatedAt = data?.updated_at || data?.updatedAt || null;

  const metrics = useMemo(() => {
    if (!items.length) {
      return {
        totalPnl: null,
        totalCosts: null,
        net: null,
        best: null,
        worst: null,
      };
    }

    let totalPnl = 0;
    let totalCosts = 0;

    const enriched = items.map((m) => {
      const pnl = Number(m.pnl ?? m.gross_pnl ?? m.gain ?? 0);
      const costs = Number(m.costs ?? m.expenses ?? 0);
      const net = Number.isFinite(pnl - costs) ? pnl - costs : 0;
      return { ...m, _pnl: pnl, _costs: costs, _net: net };
    });

    for (const m of enriched) {
      if (Number.isFinite(m._pnl)) totalPnl += m._pnl;
      if (Number.isFinite(m._costs)) totalCosts += m._costs;
    }

    const net = totalPnl - totalCosts;

    const best = enriched.reduce(
      (acc, m) => (acc == null || m._net > acc._net ? m : acc),
      null,
    );
    const worst = enriched.reduce(
      (acc, m) => (acc == null || m._net < acc._net ? m : acc),
      null,
    );

    return { totalPnl, totalCosts, net, best, worst };
  }, [items]);

  return (
    <div className="p-6 space-y-6">
      {/* Titre + meta */}
      <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">
            Profitability & Rentabilité
          </h1>
          <p className="text-sm text-zinc-400">
            Synthèse mensuelle des performances du bot (PnL brut, coûts, net).
          </p>
        </div>
        <div className="text-xs text-right text-zinc-500 space-y-1">
          <div>
            Dernière mise à jour :{" "}
            <span className="text-zinc-300">{formatDateTime(updatedAt)}</span>
          </div>
          <div className="text-zinc-500">
            Endpoint :{" "}
            <code className="text-zinc-300 bg-zinc-900 px-1.5 py-0.5 rounded">
              /profitability/monthly
            </code>
          </div>
        </div>
      </header>

      {/* État erreur/chargement global */}
      {loading && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 text-sm text-amber-400">
          Chargement des données de rentabilité…
        </div>
      )}
      {!loading && error && (
        <div className="rounded-xl border border-red-900/60 bg-red-950/40 p-4 text-sm text-red-300">
          Erreur lors du chargement : {error}
        </div>
      )}

      {/* Cartes synthèse (si on a des données) */}
      {!loading && !error && (
        <>
          <section className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4">
              <div className="text-xs font-medium uppercase text-zinc-500 tracking-wide">
                PnL brut cumulé
              </div>
              <div className="mt-2 text-2xl font-semibold text-emerald-400">
                {formatCurrency(metrics.totalPnl)}
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                Somme de tous les mois, avant coûts (frais API, serveurs…)
              </p>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4">
              <div className="text-xs font-medium uppercase text-zinc-500 tracking-wide">
                Coûts cumulés
              </div>
              <div className="mt-2 text-2xl font-semibold text-amber-400">
                {formatCurrency(metrics.totalCosts)}
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                Coûts d&apos;exploitation estimés (API, infra, etc.).
              </p>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4">
              <div className="text-xs font-medium uppercase text-zinc-500 tracking-wide">
                Net cumulé
              </div>
              <div
                className={
                  "mt-2 text-2xl font-semibold " +
                  (metrics.net > 0
                    ? "text-emerald-400"
                    : metrics.net < 0
                    ? "text-red-400"
                    : "text-zinc-100")
                }
              >
                {formatCurrency(metrics.net)}
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                PnL brut moins coûts — base de travail pour la poche LT, BFR, etc.
              </p>
            </div>
          </section>

          {/* Best / Worst */}
          <section className="grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-emerald-900/60 bg-emerald-950/20 p-4">
              <div className="text-xs font-semibold uppercase text-emerald-400 tracking-wide">
                Meilleur mois (net)
              </div>
              {metrics.best ? (
                <div className="mt-2">
                  <div className="text-sm text-zinc-300">
                    {formatMonth(metrics.best.month || metrics.best.label)}
                  </div>
                  <div className="mt-1 text-xl font-semibold text-emerald-400">
                    {formatCurrency(metrics.best._net)}
                  </div>
                  <p className="mt-1 text-xs text-zinc-500">
                    Brut : {formatCurrency(metrics.best._pnl)} — Coûts :{" "}
                    {formatCurrency(metrics.best._costs)}
                  </p>
                </div>
              ) : (
                <p className="mt-2 text-xs text-zinc-500">Pas encore de données.</p>
              )}
            </div>

            <div className="rounded-2xl border border-red-900/60 bg-red-950/20 p-4">
              <div className="text-xs font-semibold uppercase text-red-400 tracking-wide">
                Pire mois (net)
              </div>
              {metrics.worst ? (
                <div className="mt-2">
                  <div className="text-sm text-zinc-300">
                    {formatMonth(metrics.worst.month || metrics.worst.label)}
                  </div>
                  <div className="mt-1 text-xl font-semibold text-red-400">
                    {formatCurrency(metrics.worst._net)}
                  </div>
                  <p className="mt-1 text-xs text-zinc-500">
                    Brut : {formatCurrency(metrics.worst._pnl)} — Coûts :{" "}
                    {formatCurrency(metrics.worst._costs)}
                  </p>
                </div>
              ) : (
                <p className="mt-2 text-xs text-zinc-500">Pas encore de données.</p>
              )}
            </div>
          </section>

          {/* Tableau mensuel si on a des items */}
          <section className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-zinc-200">
                Détail mensuel
              </h2>
              <span className="text-xs text-zinc-500">
                {items.length} mois
              </span>
            </div>

            {items.length === 0 ? (
              <p className="text-xs text-zinc-500">
                Aucune ligne pour le moment. Dès que le bot aura tourné sur plusieurs
                mois, elles apparaîtront ici.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-800 text-zinc-500">
                      <th className="py-2 pr-4">Mois</th>
                      <th className="py-2 pr-4">PnL brut</th>
                      <th className="py-2 pr-4">Coûts</th>
                      <th className="py-2 pr-4">Net</th>
                      <th className="py-2 pr-4">Commentaire</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((m, idx) => {
                      const pnl = Number(
                        m.pnl ?? m.gross_pnl ?? m.gain ?? 0,
                      );
                      const costs = Number(m.costs ?? m.expenses ?? 0);
                      const net = pnl - costs;
                      const note =
                        m.note ||
                        m.comment ||
                        m.remark ||
                        "";

                      return (
                        <tr
                          key={idx}
                          className="border-b border-zinc-900/80 last:border-0"
                        >
                          <td className="py-1.5 pr-4 text-zinc-200">
                            {formatMonth(m.month || m.label)}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-100">
                            {formatCurrency(pnl)}
                          </td>
                          <td className="py-1.5 pr-4 text-amber-300">
                            {formatCurrency(costs)}
                          </td>
                          <td
                            className={
                              "py-1.5 pr-4 " +
                              (net > 0
                                ? "text-emerald-400"
                                : net < 0
                                ? "text-red-400"
                                : "text-zinc-100")
                            }
                          >
                            {formatCurrency(net)}
                          </td>
                          <td className="py-1.5 pr-4 text-zinc-400">
                            {note || "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Bloc debug bas de page */}
          <section className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-4 text-xs text-zinc-400 font-mono overflow-auto max-h-[260px]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-zinc-300 font-semibold">
                Debug / Raw JSON
              </span>
              <span className="rounded-full bg-zinc-900 px-2 py-0.5 text-[10px] uppercase tracking-wide">
                profitability.monthly
              </span>
            </div>
            <pre className="whitespace-pre-wrap break-words">
              {loading && "Chargement…"}
              {!loading && error && `Erreur: ${error}`}
              {!loading && !error && data
                ? JSON.stringify(data, null, 2)
                : !loading && !error && !data
                ? "Aucune donnée."
                : null}
            </pre>
          </section>
        </>
      )}
    </div>
  );
}
