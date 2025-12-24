// src/pages/OpenPositions.jsx
import React, { useEffect, useState } from "react";
import { fetchJSON } from "../lib/api";

function formatMoney(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  return (n > 0 ? "+" : "") + n.toLocaleString("fr-FR", {
    maximumFractionDigits: 2,
  });
}

function formatPercent(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  const s = n.toFixed(2).replace(".", ",");
  return (n > 0 ? "+" : "") + s + " %";
}

function formatDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function OpenPositions() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);
        const res = await fetchJSON("/open-positions");
        if (cancelled) return;
        setData(res || { positions: [] });
      } catch (err) {
        if (cancelled) return;
        console.error("OpenPositions error:", err);
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const positions = Array.isArray(data?.positions)
    ? data.positions
    : Array.isArray(data?.items)
    ? data.items
    : [];

  const totalPnl = positions.reduce((acc, p) => {
    const v = Number(p.pnl_usd ?? p.pnl ?? 0);
    if (Number.isNaN(v)) return acc;
    return acc + v;
  }, 0);

  return (
    <div className="p-6 space-y-6">
      {/* En-tête */}
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Open Positions</h1>
          <p className="text-sm text-zinc-400">
            Vue temps quasi réel des positions ouvertes par le bot NSC.
          </p>
        </div>
        {data?.updated_at && (
          <div className="text-xs text-zinc-500">
            Dernière mise à jour : {formatDate(data.updated_at)}
          </div>
        )}
      </header>

      {/* Résumé rapide */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
          <div className="text-xs font-medium text-zinc-400 uppercase mb-1">
            Nombre de positions
          </div>
          <div className="text-2xl font-semibold text-zinc-100">
            {positions.length}
          </div>
        </div>
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
          <div className="text-xs font-medium text-zinc-400 uppercase mb-1">
            PnL latent (approx.)
          </div>
          <div
            className={`text-2xl font-semibold ${
              totalPnl > 0
                ? "text-emerald-300"
                : totalPnl < 0
                ? "text-rose-300"
                : "text-zinc-100"
            }`}
          >
            {formatMoney(totalPnl)} €
          </div>
        </div>
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
          <div className="text-xs font-medium text-zinc-400 uppercase mb-1">
            État
          </div>
          <div className="text-sm text-zinc-200">
            {loading
              ? "Chargement…"
              : positions.length
              ? "Positions actives détectées"
              : "Aucune position ouverte"}
          </div>
        </div>
      </div>

      {/* Erreur */}
      {error && (
        <div className="rounded-xl border border-red-500/40 bg-red-950/40 px-4 py-3 text-sm text-red-200">
          Impossible de charger les positions ouvertes :{" "}
          <span className="font-mono">{error}</span>
        </div>
      )}

      {/* Tableau principal */}
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
          <h2 className="text-sm font-medium text-zinc-200">
            Détail des positions
          </h2>
          {loading && (
            <span className="text-xs text-zinc-500">Chargement…</span>
          )}
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-zinc-900/80 border-b border-zinc-800">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-zinc-400">
                  Token
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-zinc-400">
                  Stratégie
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-zinc-400">
                  Taille
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-zinc-400">
                  Prix entrée
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-zinc-400">
                  PnL %
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium text-zinc-400">
                  PnL €
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-zinc-400">
                  Exchange
                </th>
                <th className="px-4 py-2 text-left text-xs font-medium text-zinc-400">
                  Ouvert
                </th>
              </tr>
            </thead>
            <tbody>
              {!loading && !positions.length && (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-6 text-center text-sm text-zinc-500"
                  >
                    Aucune position ouverte pour le moment.
                  </td>
                </tr>
              )}
              {positions.map((p, idx) => {
                const symbol =
                  p.symbol || p.token || p.ticker || p.name || "—";
                const size = p.size ?? p.quantity ?? p.amount;
                const entry = p.entry_price ?? p.entry ?? p.price;
                const pnlPct = p.pnl_pct ?? p.pnl_percent ?? null;
                const pnlUsd = p.pnl_usd ?? p.pnl ?? null;
                const exchange = p.exchange || p.venue || "—";
                const strategy = p.strategy || p.profile || "—";

                return (
                  <tr
                    key={`${symbol}-${idx}`}
                    className="border-t border-zinc-900/70 hover:bg-zinc-900/60"
                  >
                    <td className="px-4 py-2 text-zinc-100 font-medium">
                      {symbol.toUpperCase()}
                    </td>
                    <td className="px-4 py-2 text-xs text-zinc-400">
                      {strategy}
                    </td>
                    <td className="px-4 py-2 text-right text-zinc-100">
                      {size == null ? "—" : size.toLocaleString("fr-FR")}
                    </td>
                    <td className="px-4 py-2 text-right text-zinc-100">
                      {entry == null
                        ? "—"
                        : Number(entry).toLocaleString("en-US", {
                            maximumFractionDigits: 6,
                          })}
                    </td>
                    <td
                      className={`px-4 py-2 text-right font-medium ${
                        Number(pnlPct) > 0
                          ? "text-emerald-300"
                          : Number(pnlPct) < 0
                          ? "text-rose-300"
                          : "text-zinc-100"
                      }`}
                    >
                      {formatPercent(pnlPct)}
                    </td>
                    <td
                      className={`px-4 py-2 text-right font-medium ${
                        Number(pnlUsd) > 0
                          ? "text-emerald-300"
                          : Number(pnlUsd) < 0
                          ? "text-rose-300"
                          : "text-zinc-100"
                      }`}
                    >
                      {formatMoney(pnlUsd)}
                    </td>
                    <td className="px-4 py-2 text-xs text-zinc-400">
                      {exchange.toUpperCase()}
                    </td>
                    <td className="px-4 py-2 text-xs text-zinc-400">
                      {formatDate(p.opened_at || p.created_at)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
