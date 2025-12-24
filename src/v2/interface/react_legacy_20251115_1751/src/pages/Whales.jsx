import React, { useEffect, useState } from "react";
import { getWhaleLeaderboard } from "../lib/api";

export default function Whales() {
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getWhaleLeaderboard();

        // On logge brut pour debug éventuel
        console.log("[Whales] raw leaderboard:", data);

        let items = [];

        if (Array.isArray(data)) {
          // L'API renvoie directement un tableau
          items = data;
        } else if (data && Array.isArray(data.items)) {
          // L'API renvoie { items: [...] }
          items = data.items;
        } else {
          items = [];
        }

        setLeaderboard(items);
      } catch (err) {
        console.error("Erreur chargement whale leaderboard :", err);
        setError("Impossible de charger les données whales.");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  const formatPnL = (value) => {
    if (typeof value === "number") {
      return value.toFixed(2);
    }
    if (!value && value !== 0) {
      return "N/A";
    }
    // si c’est déjà une string, on la renvoie telle quelle
    return String(value);
  };

  if (loading) {
    return (
      <div className="text-white p-6">
        <h1 className="text-2xl mb-4">Whales</h1>
        <p>Chargement...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-white p-6">
        <h1 className="text-2xl mb-4">Whales</h1>
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  if (!leaderboard || leaderboard.length === 0) {
    return (
      <div className="text-white p-6">
        <h1 className="text-2xl mb-4">Whales</h1>
        <p>Aucune donnée whale disponible pour le moment.</p>
      </div>
    );
  }

  return (
    <div className="text-white p-6">
      <h1 className="text-3xl font-semibold mb-6">Whale Leaderboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {leaderboard.map((w, index) => (
          <div
            key={index}
            className="bg-zinc-900 border border-zinc-700 rounded-xl p-4 shadow-md"
          >
            <p className="text-zinc-300 mb-2">
              <span className="font-semibold text-green-400">Wallet :</span>{" "}
              {w.wallet || w.address || "N/A"}
            </p>

            <p className="text-zinc-300">
              <span className="font-semibold text-blue-400">P&L 30j :</span>{" "}
              {formatPnL(w.pnl_30d)} €
            </p>

            <p className="text-zinc-300">
              <span className="font-semibold text-yellow-400">P&L 90j :</span>{" "}
              {formatPnL(w.pnl_90d)} €
            </p>

            {w.strategy && (
              <p className="text-zinc-300 mt-1">
                <span className="font-semibold text-purple-400">
                  Stratégie dominante :
                </span>{" "}
                {w.strategy}
              </p>
            )}

            <p className="text-zinc-400 text-sm mt-2">
              Dernière mise à jour :{" "}
              {w.updated_at || "non renseignée"}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
