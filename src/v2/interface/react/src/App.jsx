// src/App.jsx — routing NSC V2 (version FIX + stable)

import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";

import Layout from "./components/Layout";
import ComingSoon from "./pages/ComingSoon";
import { FEATURES } from "./config/features";

// Pages
import Dashboard from "./pages/Dashboard";
import Strategy from "./pages/Strategy";
import ControlRoom from "./pages/ControlRoom";
import PnLOverview from "./pages/PnLOverview";
import SystemStatus from "./pages/SystemStatus";
import Settings from "./pages/Settings";

import GoNoGo from "./pages/GoNoGo";

import AlphaBeta from "./pages/AlphaBeta";
import Portfolio from "./pages/Portfolio";
import RiskOverview from "./pages/RiskOverview";
import Attribution from "./pages/Attribution";

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
import CryptoLayout from "./pages/bricks/CryptoLayout";

function BrickGate({ enabled, title }) {
  if (enabled) return null;
  return <ComingSoon title={title} />;
}

function IcoGate({ children }) {
  if (!FEATURES?.CRYPTO_ICO) return <ComingSoon title="ICO (Crypto)" />;
  return children;
}

export default function App()
 {
  return (
    <Router>
      <Routes>
        {/* ROUTE PARENTE */}
        <Route path="/" element={<Layout />}>
          
          {/* Default redirect */}
          <Route index element={<Navigate to="/dashboard" replace />} />

          {/* Core */}
<Route path="bricks/options/*" element={FEATURES.BRICK_OPTIONS ? <Navigate to="/dashboard" replace /> : <ComingSoon title="Options US" />} />
<Route path="bricks/lt/*" element={FEATURES.BRICK_LT ? <Navigate to="/portfolio" replace /> : <ComingSoon title="Long Terme" />} />
<Route path="bricks/defensive/*" element={FEATURES.BRICK_DEFENSIVE ? <Navigate to="/dashboard" replace /> : <ComingSoon title="Actions Défensives" />} />
<Route path="bricks/offensive/*" element={FEATURES.BRICK_OFFENSIVE ? <Navigate to="/dashboard" replace /> : <ComingSoon title="Actions Offensives" />} />
<Route path="bricks/crypto/reporting" element={<Navigate to="/reporting/pnl" replace />} />
<Route path="bricks/crypto/overview" element={<Navigate to="/dashboard" replace />} />
<Route path="global/risk" element={<Navigate to="/risk" replace />} />
<Route path="global/portfolio" element={<Navigate to="/portfolio" replace />} />
<Route path="global/pnl" element={<Navigate to="/reporting/pnl" replace />} />
<Route path="global/overview" element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="strategy" element={<Strategy />} />
          <Route path="control-room" element={<ControlRoom />} />
          <Route path="reporting/pnl" element={<PnLOverview />} />

          <Route path="reporting/alpha-beta" element={<AlphaBeta />} />
          <Route path="reporting/attribution" element={<Attribution />} />
          <Route path="portfolio" element={<Portfolio />} />
          <Route path="risk" element={<RiskOverview />} />          

          <Route path="system-status" element={<SystemStatus />} />
          <Route path="system/go-no-go" element={<GoNoGo />} />
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
          <Route path="ico" element={<IcoGate><IcoDashboard /></IcoGate>} />
          <Route path="ico/candidates" element={<IcoGate><ICOCandidates /></IcoGate>} />
          <Route path="ico/screened" element={<IcoGate><ICOScreened /></IcoGate>} />
          <Route path="ico/scored" element={<IcoGate><ICOScored /></IcoGate>} />
          <Route path="ico/allocation" element={<IcoGate><ICOAllocation /></IcoGate>} />

          {/* Crypto (layout brique) */}
          <Route path="bricks/crypto/*" element={<CryptoLayout />}>
  <Route index element={<Navigate to="ico" replace />} />
            <Route path="ico" element={<IcoGate><IcoDashboard /></IcoGate>} />
            <Route path="ico/candidates" element={<IcoGate><ICOCandidates /></IcoGate>} />
            <Route path="ico/screened" element={<IcoGate><ICOScreened /></IcoGate>} />
            <Route path="ico/scored" element={<IcoGate><ICOScored /></IcoGate>} />
            <Route path="ico/allocation" element={<IcoGate><ICOAllocation /></IcoGate>} />
            <Route path="whales" element={<Whales />} />
          </Route>

          {/* Aliases: /bricks/crypto/ico/* */}
          <Route path="bricks/crypto/ico" element={<IcoGate><IcoDashboard /></IcoGate>} />
          <Route path="bricks/crypto/ico/candidates" element={<IcoGate><ICOCandidates /></IcoGate>} />
          <Route path="bricks/crypto/ico/screened" element={<IcoGate><ICOScreened /></IcoGate>} />
          <Route path="bricks/crypto/ico/scored" element={<IcoGate><ICOScored /></IcoGate>} />
          <Route path="bricks/crypto/ico/allocation" element={<IcoGate><ICOAllocation /></IcoGate>} />


          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />

        </Route>
      </Routes>
    </Router>
  );
}
