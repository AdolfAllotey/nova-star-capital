"use client";

import React, { useEffect, useState } from "react";
import fs from "fs";
import path from "path";

export default function LlmOpportunities() {
  const [opportunities, setOpportunities] = useState([]);

  useEffect(() => {
    async function fetchOpportunities() {
      try {
        const res = await fetch("/data/intelligence/llm_opportunities.json");
        if (!res.ok) throw new Error("Failed to load LLM opportunities");
        const data = await res.json();
        setOpportunities(data);
      } catch (error) {
        console.error("Erreur chargement opportunités LLM :", error);
      }
    }

    fetchOpportunities();
  }, []);

  if (opportunities.length === 0) {
    return (
      <div className="p-4 border rounded-lg shadow bg-white dark:bg-gray-900">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white mb-2">
          LLM Opportunities
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">No signals found.</p>
      </div>
    );
  }

  return (
    <div className="p-4 border rounded-lg shadow bg-white dark:bg-gray-900">
      <h2 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
        🔍 LLM Opportunities
      </h2>
      <ul className="space-y-2">
        {opportunities.map((item, idx) => (
          <li key={idx} className="bg-gray-50 dark:bg-gray-800 p-3 rounded-md border">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              🪙 {item.token} — <span className="text-green-600 dark:text-green-400">{item.reason}</span>
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{item.summary}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}