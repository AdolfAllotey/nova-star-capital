// src/App.jsx
// Router principal de l'interface Nova Star Capital

import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import AppLayout from "./ui/AppLayout.jsx";

// Pages principales
import TopMovers from "./pages/TopMovers.jsx";
import Profitability from "./pages/Profitability.jsx";
import WorstTrades from "./pages/WorstTrades.jsx";
import OpenPositions from "./pages/OpenPositions.jsx";

// Pages ICO
import Candidates from "./pages/ico/Candidates.jsx";
import Screened from "./pages/ico/Screened.jsx";
import Scored from "./pages/ico/Scored.jsx";
import Allocation from "./pages/ico/Allocation.jsx";

function Stub({ label }) {
  return (
    <div className="p-6 text-zinc-100">
      <h1 className="text-2xl font-semibold mb-2">{label}</h1>
      <p className="text-zinc-400">
        Vue &quot;{label}&quot; en mode placeholder pour le moment.
      </p>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          {/* Dashboard principal = Top Movers pour l'instant */}
          <Route path="/dashboard" element={<TopMovers />} />

          {/* Pages marché & trading */}
          <Route path="/top-movers" element={<TopMovers />} />
          <Route path="/profitability" element={<Profitability />} />
          <Route path="/worst-trades" element={<WorstTrades />} />
          <Route path="/open-positions" element={<OpenPositions />} />

          {/* Sentiment & Whales (placeholders pour l’instant) */}
          <Route path="/sentiment" element={<Stub label="Sentiment" />} />
          <Route path="/whales" element={<Stub label="Whales Tracker" />} />

          {/* ICO */}
          <Route path="/ico/candidates" element={<Candidates />} />
          <Route path="/ico/screened" element={<Screened />} />
          <Route path="/ico/scored" element={<Scored />} />
          <Route path="/ico/allocation" element={<Allocation />} />

          {/* Divers */}
          <Route path="/health" element={<Stub label="Health" />} />
          <Route path="/settings" element={<Stub label="Settings" />} />

          {/* Redirection par défaut */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}
