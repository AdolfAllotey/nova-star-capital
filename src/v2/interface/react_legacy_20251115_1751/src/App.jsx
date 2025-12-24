// src/App.jsx
// Router principal de l'interface Nova Star Capital (trading desk v2)

import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

// Layout global (header + sidebar + barre de statut)
import AppLayout from "./ui/AppLayout.jsx";

// Pages principales
import Dashboard from "./pages/Dashboard.jsx";
import TopMovers from "./pages/TopMovers.jsx";
import Profitability from "./pages/Profitability.jsx";
import WorstTrades from "./pages/WorstTrades.jsx";
import OpenPositions from "./pages/OpenPositions.jsx";
import Sentiment from "./pages/Sentiment.jsx";
import Whales from "./pages/Whales.jsx";
import LiveSimulation from "./pages/LiveSimulation.jsx";
import Strategy from "./pages/Strategy.jsx";
import Metrics from "./pages/Metrics.jsx";
import MarketRegime from "./pages/MarketRegime.jsx";
import SystemStatus from "./pages/SystemStatus.jsx";
import Settings from "./pages/Settings.jsx";

// Pages ICO
import IcoCandidates from "./pages/ico/Candidates.jsx";
import IcoScreened from "./pages/ico/Screened.jsx";
import IcoScored from "./pages/ico/Scored.jsx";
import IcoAllocation from "./pages/ico/Allocation.jsx";

// Petite page 404 simple
function NotFound() {
  return (
    <div className="p-8 text-zinc-100">
      <h1 className="text-2xl font-semibold mb-2">404 – Page introuvable</h1>
      <p className="text-zinc-400 mb-4">
        Cette vue n’existe pas dans l’interface Nova Star Capital.
      </p>
      <a
        href="/"
        className="inline-flex items-center px-3 py-1.5 rounded-md border border-zinc-700 text-sm text-zinc-100 hover:bg-zinc-800"
      >
        ← Retour au dashboard
      </a>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          {/* Redirection racine -> dashboard */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          {/* Bloc "Vue globale" */}
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/top-movers" element={<TopMovers />} />
          <Route path="/profitability" element={<Profitability />} />
          <Route path="/worst-trades" element={<WorstTrades />} />
          <Route path="/open-positions" element={<OpenPositions />} />

          {/* Sentiment & Whales */}
          <Route path="/sentiment" element={<Sentiment />} />
          <Route path="/whales" element={<Whales />} />

          {/* Stratégie & régime de marché */}
          <Route path="/strategy" element={<Strategy />} />
          <Route path="/market-regime" element={<MarketRegime />} />

          {/* Live & monitoring système */}
          <Route path="/live" element={<LiveSimulation />} />
          <Route path="/metrics" element={<Metrics />} />
          <Route path="/system-status" element={<SystemStatus />} />

          {/* ICO */}
          <Route path="/ico/candidates" element={<IcoCandidates />} />
          <Route path="/ico/screened" element={<IcoScreened />} />
          <Route path="/ico/scored" element={<IcoScored />} />
          <Route path="/ico/allocation" element={<IcoAllocation />} />

          {/* Settings */}
          <Route path="/settings" element={<Settings />} />

          {/* 404 catch-all */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}
