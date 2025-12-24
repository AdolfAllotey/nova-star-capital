"use client";

import React, { useEffect, useState } from "react";

export default function WorstTradeSummary() {
  const [summary, setSummary] = useState("");

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const response = await fetch("/data/risk/worst_trades_summary.json");
        if (response.ok) {
          const data = await response.json();
          setSummary(data.summary || "No summary available.");
        } else {
          console.error("Erreur lors du chargement du résumé LLM.");
        }
      } catch (error) {
        console.error("Erreur réseau:", error);
      }
    };

    fetchSummary();
  }, []);

  return (
    <div className="bg-yellow-100 dark:bg-yellow-900 border-l-4 border-yellow-500 dark:border-yellow-300 p-5 rounded-2xl shadow">
      <h2 className="text-lg font-semibold text-yellow-800 dark:text-yellow-200 mb-2">
        LLM Summary – Worst Trades
      </h2>
      <p className="text-sm text-yellow-800 dark:text-yellow-100 whitespace-pre-line">
        {summary}
      </p>
    </div>
  );
}