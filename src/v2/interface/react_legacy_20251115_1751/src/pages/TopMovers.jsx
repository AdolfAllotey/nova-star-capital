// src/pages/TopMovers.jsx
import React, { useEffect, useMemo, useState } from "react";
import { fetchJSON } from "../lib/api";

function formatPercent(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  const s = n.toFixed(2).replace(".", ",");
  return (n > 0 ? "+" : "") + s + " %";
}

function formatNumber(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString("fr-FR");
}

export default function TopMovers() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);
        const res = await fetchJSON("/market/top-movers");
        if (cancelled) return;
        setData(res || { items: [] });
      } catch (err) {
        if (cancelled) return;
        console.error("TopMovers error:", err);
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

  const items = Array.isArray(data?.items) ? data.items : [];

  const [gainers, losers] = useMemo(() => {
    if (!items.length) return [[], []];

    const withDelta = items.map((it) => ({
      ...it,
      change_24h:
        it.change_24h ??
        it.change24h ??
        it.change ??
        it.price_change_percentage_24h,
    }));

    const positives = withDelta.filter(
      (it) => Number(it.change_24h) > 0
    );
    const negatives = withDelta.filter(
      (it) => Number(it.change_24h) < 0
    );

    positives.sort((a, b) => Number(b.change_24h) - Number(a.change_24h));
    negatives.sort((a, b) => Number(a.change_24h) - Number(b.change_24h));

    return [positives.slice(0, 10), negatives.slice(0, 10)];
  }, [items]);

  return (
    <div className="p-6 space-y-6">
      {/* En-tête */}
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Top Movers</h1>
          <p className="text-sm text-zinc-400">
            Meilleurs hausses/baisses 24h — base de travail pour le scalp &
            momentum.
          </p>
        </div>
        {data?.updated_at && (
          <div className="text-xs text-zinc-500">
            Dernière mise à jour :{" "}
            {new Date(data.updated_at).toLocaleString("fr-FR")}
          </div>
        )}
      </header>

      {/* Erreur */}
      {error && (
        <div className="rounded-xl border border-red-500/40 bg-red-950/40 px-4 py-3 text-sm text-red-200">
          Impossible de charger les top movers :{" "}
          <span className="font-mono">{error}</span>
        </div>
      )}

      {/* Contenu */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Gainers */}
        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
            <h2 className="text-sm font-medium text-emerald-300">
              Top Gainers (24h)
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
                    #
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-zinc-400">
                    Token
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-zinc-400">
                    Prix
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-zinc-400">
                    Var. 24h
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-zinc-400">
                    Volume 24h
                  </th>
                </tr>
              </thead>
              <tbody>
                {!loading && !gainers.length && (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-6 text-center text-sm text-zinc-500"
                    >
                      Aucun top gainer disponible pour le moment.
                    </td>
                  </tr>
                )}
                {gainers.map((it, idx) => {
                  const symbol =
                    it.symbol || it.ticker || it.token || it.name || "—";
                  const price = it.price_usd ?? it.price ?? null;
                  const change = it.change_24h;
                  const vol =
                    it.volume_24h ??
                    it.total_volume ??
                    it.volume ??
                    null;

                  return (
                    <tr
                      key={`${symbol}-g-${idx}`}
                      className="border-t border-zinc-900/70 hover:bg-zinc-900/60"
                    >
                      <td className="px-4 py-2 text-xs text-zinc-500">
                        {idx + 1}
                      </td>
                      <td className="px-4 py-2 text-zinc-100 font-medium">
                        {symbol.toUpperCase()}
                      </td>
                      <td className="px-4 py-2 text-right text-zinc-100">
                        {price == null
                          ? "—"
                          : `$${Number(price).toLocaleString("en-US", {
                              maximumFractionDigits: 6,
                            })}`}
                      </td>
                      <td className="px-4 py-2 text-right font-medium text-emerald-300">
                        {formatPercent(change)}
                      </td>
                      <td className="px-4 py-2 text-right text-zinc-300">
                        {vol == null ? "—" : formatNumber(vol)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* Losers */}
        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
            <h2 className="text-sm font-medium text-rose-300">
              Top Losers (24h)
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
                    #
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-zinc-400">
                    Token
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-zinc-400">
                    Prix
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-zinc-400">
                    Var. 24h
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-zinc-400">
                    Volume 24h
                  </th>
                </tr>
              </thead>
              <tbody>
                {!loading && !losers.length && (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-6 text-center text-sm text-zinc-500"
                    >
                      Aucun top loser disponible pour le moment.
                    </td>
                  </tr>
                )}
                {losers.map((it, idx) => {
                  const symbol =
                    it.symbol || it.ticker || it.token || it.name || "—";
                  const price = it.price_usd ?? it.price ?? null;
                  const change = it.change_24h;
                  const vol =
                    it.volume_24h ??
                    it.total_volume ??
                    it.volume ??
                    null;

                  return (
                    <tr
                      key={`${symbol}-l-${idx}`}
                      className="border-t border-zinc-900/70 hover:bg-zinc-900/60"
                    >
                      <td className="px-4 py-2 text-xs text-zinc-500">
                        {idx + 1}
                      </td>
                      <td className="px-4 py-2 text-zinc-100 font-medium">
                        {symbol.toUpperCase()}
                      </td>
                      <td className="px-4 py-2 text-right text-zinc-100">
                        {price == null
                          ? "—"
                          : `$${Number(price).toLocaleString("en-US", {
                              maximumFractionDigits: 6,
                            })}`}
                      </td>
                      <td className="px-4 py-2 text-right font-medium text-rose-300">
                        {formatPercent(change)}
                      </td>
                      <td className="px-4 py-2 text-right text-zinc-300">
                        {vol == null ? "—" : formatNumber(vol)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
