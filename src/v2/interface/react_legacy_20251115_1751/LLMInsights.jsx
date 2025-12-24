import { useState } from "react";
import Dashboard from "./dashboard";
import BacktestComparison from "./components/BacktestComparison";
import LLMInsights from "./components/LLMInsights";

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="flex gap-4 p-4 bg-white shadow">
        <button
          onClick={() => setActiveTab("dashboard")}
          className={`px-4 py-2 rounded text-sm font-medium ${
            activeTab === "dashboard" ? "bg-blue-600 text-white" : "bg-gray-200"
          }`}
        >
          🧠 Dashboard
        </button>
        <button
          onClick={() => setActiveTab("backtest")}
          className={`px-4 py-2 rounded text-sm font-medium ${
            activeTab === "backtest" ? "bg-blue-600 text-white" : "bg-gray-200"
          }`}
        >
          📊 Backtests
        </button>
        <button
          onClick={() => setActiveTab("llm")}
          className={`px-4 py-2 rounded text-sm font-medium ${
            activeTab === "llm" ? "bg-blue-600 text-white" : "bg-gray-200"
          }`}
        >
          💬 LLM Insights
        </button>
      </nav>

      <main className="p-4">
        {activeTab === "dashboard" && <Dashboard />}
        {activeTab === "backtest" && <BacktestComparison />}
        {activeTab === "llm" && <LLMInsights />}
      </main>
    </div>
  );
}
