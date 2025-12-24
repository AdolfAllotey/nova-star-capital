// src/App.jsx — routing NSC V2 (version FIX + stable)

import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";

import Layout from "./components/Layout";

// Pages
import Dashboard from "./pages/Dashboard";
import Strategy from "./pages/Strategy";
import SystemStatus from "./pages/SystemStatus";
import Settings from "./pages/Settings";

import TopMovers from "./pages/TopMovers";
import MarketRegime from "./pages/MarketRegime";
import LiveSimulation from "./pages/LiveSimulation";

import Profitability from "./pages/Profitability";
import WorstTrades from "./pages/WorstTrades";
import OpenPositions from "./pages/OpenPositions";

import Sentiment from "./pages/Sentiment";
import Whales from "./pages/Whales";

import IcoDashboard from "./pages/IcoDashboard";
import ICOCandidates from "./pages/ICOCandidates";
import ICOScreened from "./pages/ICOScreened";
import ICOScored from "./pages/ICOScored";
import ICOAllocation from "./pages/ICOAllocation";

export default function App() {
  return (
    <Router>
      <Routes>
        {/* ROUTE PARENTE */}
        <Route path="/" element={<Layout />}>
          
          {/* Default redirect */}
          <Route index element={<Navigate to="/dashboard" replace />} />

          {/* Core */}
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="strategy" element={<Strategy />} />
          <Route path="system-status" element={<SystemStatus />} />
          <Route path="settings" element={<Settings />} />

          {/* Market */}
          <Route path="market/top-movers" element={<TopMovers />} />
          <Route path="market/regime" element={<MarketRegime />} />

          {/* Simulation */}
          <Route path="simulation/live" element={<LiveSimulation />} />

          {/* Reporting */}
          <Route path="reporting/profitability" element={<Profitability />} />
          <Route path="reporting/worst-trades" element={<WorstTrades />} />
          <Route path="reporting/open-positions" element={<OpenPositions />} />

          {/* Intelligence */}
          <Route path="intelligence/sentiment" element={<Sentiment />} />
          <Route path="intelligence/whales" element={<Whales />} />

          {/* ICO */}
          <Route path="ico" element={<IcoDashboard />} />
          <Route path="ico/candidates" element={<ICOCandidates />} />
          <Route path="ico/screened" element={<ICOScreened />} />
          <Route path="ico/scored" element={<ICOScored />} />
          <Route path="ico/allocation" element={<ICOAllocation />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />

        </Route>
      </Routes>
    </Router>
  );
}
