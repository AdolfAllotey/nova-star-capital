import React, { useEffect, useState } from "react";
import WorstTradesTable from "./WorstTradesTable";

const WorstTrades = () => {
  const [trades, setTrades] = useState([]);
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchWorstTrades = async () => {
      try {
        const res = await fetch("/data/risk/worst_trades.json");
        const data = await res.json();
        setTrades(data || []);
      } catch (err) {
        console.error("Erreur lors du chargement des pires trades :", err);
      }
    };

    const fetchSummary = async () => {
      try {
        const res = await fetch("/data/risk/worst_trades_summary.json");
        const data = await res.json();
        setSummary(data?.summary || "Aucun résumé disponible.");
      } catch (err) {
        console.error("Erreur lors du chargement du résumé LLM :", err);
      }
    };

    Promise.all([fetchWorstTrades(), fetchSummary()]).then(() =>
      setLoading(false)
    );
  }, []);

  if (loading) {
    return (
      <div className="p-6 text-center text-gray-600 dark:text-gray-300">
        Chargement des données...
      </div>
    );
  }

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold text-gray-800 dark:text-white">
        Analyse des pires trades
      </h1>

      {/* Résumé LLM */}
      <div className="bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-100 p-4 rounded-2xl shadow-sm">
        <h2 className="text-lg font-semibold mb-2">Résumé LLM</h2>
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{summary}</p>
      </div>

      {/* Cartes individuelles */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {trades.map((trade, index) => (
          <div
            key={index}
            className="bg-white dark:bg-gray-900 rounded-2xl shadow-md p-4 border border-gray-200 dark:border-gray-700"
          >
            <h3 className="text-lg font-bold text-gray-800 dark:text-white mb-2">
              {trade.token}
            </h3>
            <p className="text-sm text-red-600 dark:text-red-400">
              Perte : -{trade.loss?.toFixed(2)} €
            </p>
            <p className="text-sm text-red-500">
              Rendement : {trade.return_pct?.toFixed(1)}%
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Score : {trade.score?.toFixed(2)} | Sentiment :{" "}
              {trade.sentiment?.toFixed(2)}
            </p>
          </div>
        ))}
      </div>

      {/* Tableau complet */}
      <div>
        <WorstTradesTable trades={trades} />
      </div>
    </div>
  );
};

export default WorstTrades;