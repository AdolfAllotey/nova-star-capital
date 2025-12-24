"use client";

import React, { useEffect, useState } from "react";

export default function WorstTradeTable() {
  const [trades, setTrades] = useState([]);

  useEffect(() => {
    const fetchWorstTrades = async () => {
      try {
        const response = await fetch("/data/risk/worst_trades.json");
        if (response.ok) {
          const data = await response.json();
          setTrades(data);
        } else {
          console.error("Erreur lors du chargement des pires trades");
        }
      } catch (error) {
        console.error("Erreur réseau:", error);
      }
    };

    fetchWorstTrades();
  }, []);

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow">
      <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">Worst Trades (Simulated)</h2>

      {trades.length === 0 ? (
        <p className="text-gray-500 dark:text-gray-300">Aucune donnée disponible.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full table-auto text-sm">
            <thead className="bg-gray-100 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-2 text-left">Token</th>
                <th className="px-4 py-2 text-left">Perte (€)</th>
                <th className="px-4 py-2 text-left">% Perte</th>
                <th className="px-4 py-2 text-left">Score</th>
                <th className="px-4 py-2 text-left">Sentiment</th>
                <th className="px-4 py-2 text-left">Résumé LLM</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade, idx) => (
                <tr
                  key={idx}
                  className={idx % 2 === 0 ? "bg-white dark:bg-gray-800" : "bg-gray-50 dark:bg-gray-700"}
                >
                  <td className="px-4 py-2">{trade.token}</td>
                  <td className="px-4 py-2 text-red-600 dark:text-red-400">–€{trade.loss.toFixed(2)}</td>
                  <td className="px-4 py-2">{(trade.percent_loss * 100).toFixed(1)}%</td>
                  <td className="px-4 py-2">{trade.score}</td>
                  <td className="px-4 py-2">{trade.sentiment}</td>
                  <td className="px-4 py-2 italic text-gray-600 dark:text-gray-300">
                    {trade.llm_summary || "N/A"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}