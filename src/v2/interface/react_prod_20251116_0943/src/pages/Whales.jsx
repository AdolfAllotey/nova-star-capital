// src/pages/Whales.jsx
import React, { useEffect, useState } from "react";
import { getWhaleLeaderboard } from "../lib/api.js";

export default function Whales() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let aborted = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await getWhaleLeaderboard();
        if (!aborted) {
          setRows(data?.items ?? []);
        }
      } catch (e) {
        if (!aborted) {
          console.error("[Whales] error:", e);
          setError(e);
        }
      } finally {
        if (!aborted) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      aborted = true;
    };
  }, []);

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">
            Whale tracker
          </h1>
          <p className="text-sm text-zinc-400">
            Classement des wallets les plus performants suivis par NSC.
          </p>
        </div>
      </header>

      {loading && (
        <div className="text-sm text-zinc-400">
          Chargement du leaderboard whales…
        </div>
      )}

      {error && (
        <div className="text-sm text-red-400">
          Erreur de chargement du leaderboard whales.
        </div>
      )}

      {!loading && !error && rows.length === 0 && (
        <div className="text-sm text-zinc-400">
          Aucun wallet en leaderboard pour l’instant.  
          Le module whale tracker se remplira dès que le bot tournera en
          conditions réelles.
        </div>
      )}

      {!loading && !error && rows.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900/60">
          <table className="min-w-full text-sm">
            <thead className="bg-zinc-900/80 text-zinc-400 text-xs uppercase tracking-wide">
              <tr>
                <th className="px-3 py-2 text-left">Rank</th>
                <th className="px-3 py-2 text-left">Wallet</th>
                <th className="px-3 py-2 text-right">Score</th>
                <th className="px-3 py-2 text-right">P&L (réalisé)</th>
                <th className="px-3 py-2 text-right">Winrate</th>
                <th className="px-3 py-2 text-right">Trades</th>
                <th className="px-3 py-2 text-left">Tags</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((w, idx) => {
                const address = w.address || w.wallet || "-";
                const score =
                  typeof w.score === "number"
                    ? w.score.toFixed(2)
                    : w.score ?? "-";
                const pnl =
                  typeof w.realized_pnl === "number"
                    ? w.realized_pnl.toFixed(2)
                    : w.realized_pnl ?? "-";
                const winrate =
                  typeof w.winrate === "number"
                    ? `${(w.winrate * 100).toFixed(1)}%`
                    : w.winrate ?? "-";
                const trades =
                  typeof w.trades === "number" ? w.trades : w.trades ?? "-";
                const tags = Array.isArray(w.tags) ? w.tags.join(", ") : "";

                return (
                  <tr
                    key={address + idx}
                    className="border-t border-zinc-800/80 hover:bg-zinc-800/60"
                  >
                    <td className="px-3 py-2 text-xs text-zinc-500">
                      #{idx + 1}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs truncate max-w-[200px]">
                      {address}
                    </td>
                    <td className="px-3 py-2 text-right">{score}</td>
                    <td className="px-3 py-2 text-right">{pnl}</td>
                    <td className="px-3 py-2 text-right">{winrate}</td>
                    <td className="px-3 py-2 text-right">{trades}</td>
                    <td className="px-3 py-2 text-left text-zinc-400">
                      {tags}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
