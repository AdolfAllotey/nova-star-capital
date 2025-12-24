import React, { useEffect, useState } from "react";

const LLMSummaryCard = () => {
  const [summary, setSummary] = useState("");

  useEffect(() => {
    fetch("/data/risk/worst_trades_summary.json")
      .then((res) => res.json())
      .then((data) => {
        setSummary(data.summary || "No summary available.");
      })
      .catch((err) => {
        console.error("Erreur lors du chargement du résumé LLM :", err);
        setSummary("Erreur de chargement du résumé.");
      });
  }, []);

  return (
    <div className="bg-white dark:bg-neutral-800 p-4 rounded-2xl shadow">
      <h2 className="text-xl font-semibold mb-2">🧠 Résumé LLM des pires trades</h2>
      <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line">
        {summary}
      </p>
    </div>
  );
};

export default LLMSummaryCard;