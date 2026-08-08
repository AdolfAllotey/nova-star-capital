import Anomalies from "./pages/Anomalies";
// src/App.jsx — routing NSC V2 (version FIX + stable)

import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";

import Layout from "./components/Layout";
import ComingSoon from "./pages/ComingSoon";
import { FEATURES } from "./config/features";

// Pages
import Dashboard from "./pages/Dashboard";
import Strategy from "./pages/Strategy";
import Offensive from "./pages/Offensive";
import Defensive from "./pages/Defensive";
import Bonds from "./pages/Bonds";
import PreciousMetals from "./pages/PreciousMetals";
import LongTerm from "./pages/LongTerm";
import SignalBoard from "./pages/SignalBoard";
import ControlRoom from "./pages/ControlRoom";
import Executive from "./pages/Executive";
import ExecutiveDecisionCenter from "./pages/ExecutiveDecisionCenter";
import OrderBoard from "./pages/OrderBoard";
import PositionsBoard from "./pages/PositionsBoard";
import FillsBoard from "./pages/FillsBoard";
import ExecutionTraceBoard from "./pages/ExecutionTraceBoard";
import PnLOverview from "./pages/PnLOverview";
import SystemStatus from "./pages/SystemStatus";
import Settings from "./pages/Settings";

import GoNoGo from "./pages/GoNoGo";

import AlphaBeta from "./pages/AlphaBeta";
import Portfolio from "./pages/Portfolio";
import FundingPools from "./pages/FundingPools";
import AllocationRebalance from "./pages/AllocationRebalance";
import RiskOverview from "./pages/RiskOverview";
import Protection from "./pages/Protection";
import Governance from "./pages/Governance";
import Attribution from "./pages/Attribution";

import TopMovers from "./pages/TopMovers";
import MarketRegime from "./pages/MarketRegime";
import MarketIntelligence from "./pages/MarketIntelligence";
import Explainability from "./pages/Explainability";

import Profitability from "./pages/Profitability";
import TradeJournal from "./pages/TradeJournal";
import WorstTrades from "./pages/WorstTrades";
import OpenPositions from "./pages/OpenPositions";

import Sentiment from "./pages/Sentiment";
import Whales from "./pages/Whales";
import Crypto from "./pages/Crypto";
import OptionsUS from "./pages/OptionsUS";
import FamilyOfficeDashboard from "./pages/FamilyOfficeDashboard";
import DocumentationCenter from "./pages/DocumentationCenter";


function BrickGate({ enabled, title }) {
  if (enabled) return null;
  return <ComingSoon title={title} />;
}

export default function App()
 {
  return (
    <Router>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/executive" element={<Executive />} />
        <Route path="/executive-decision" element={<ExecutiveDecisionCenter />} />
        <Route path="/documentation-center" element={<DocumentationCenter />} />
        <Route path="/control-room" element={<ControlRoom />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/funding-pools" element={<FundingPools />} />
        <Route path="/allocation-rebalance" element={<AllocationRebalance />} />
        <Route path="/bricks/lt/*" element={<LongTerm />} />
        <Route path="/risk" element={<RiskOverview />} />
        <Route path="/anomalies" element={<Anomalies />} />
        <Route path="/reporting/pnl" element={<PnLOverview />} />
        <Route path="/reporting/alpha-beta" element={<AlphaBeta />} />
        <Route path="/reporting/profitability" element={<Profitability />} />
        <Route path="/reporting/trade-journal" element={<TradeJournal />} />
        <Route path="/reporting/worst-trades" element={<WorstTrades />} />
        <Route path="/market/top-movers" element={<TopMovers />} />
        <Route path="/market/intelligence" element={<MarketIntelligence />} />
        <Route path="/signals/board" element={<SignalBoard />} />
        <Route path="/market/regime" element={<MarketRegime />} />
        <Route path="/explainability" element={<Explainability />} />
        <Route path="/protection" element={<Protection />} />
        <Route path="/governance" element={<Governance />} />
        <Route path="/order-board" element={<OrderBoard />} />
        <Route path="/positions-board" element={<PositionsBoard />} />
        <Route path="/fills-board" element={<FillsBoard />} />
        <Route path="/execution-trace" element={<ExecutionTraceBoard />} />
        {/* ROUTE PARENTE */}
        <Route path="/" element={<Layout />}>
          
          {/* Default redirect */}
          <Route index element={<Navigate to="/dashboard" replace />} />

          {/* Core */}
<Route path="bricks/options/*" element={<OptionsUS />} />
<Route path="bricks/lt-legacy/*" element={<LongTerm />} />
<Route path="bricks/defensive/*" element={FEATURES.BRICK_DEFENSIVE ? <Defensive /> : <ComingSoon title="Actions Défensives" />} />
<Route path="bricks/bonds" element={<Bonds />} />
<Route path="bricks/precious-metals" element={<PreciousMetals />} />
<Route path="bricks/offensive/*" element={FEATURES.BRICK_OFFENSIVE ? <Offensive /> : <ComingSoon title="Actions Offensives" />} />
<Route path="bricks/crypto/reporting" element={<Navigate to="/reporting/pnl" replace />} />
<Route path="bricks/crypto/overview" element={<Navigate to="/dashboard" replace />} />
<Route path="global/risk" element={<Navigate to="/risk" replace />} />
<Route path="global/portfolio" element={<Navigate to="/portfolio" replace />} />
<Route path="global/pnl" element={<Navigate to="/reporting/pnl" replace />} />
<Route path="global/overview" element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Navigate to="/dashboard" replace />} />
          <Route path="strategy" element={<Strategy />} />
          <Route path="executive-legacy" element={<Executive />} />
          <Route path="reporting/pnl-legacy" element={<PnLOverview />} />

          <Route path="reporting/alpha-beta-legacy" element={<AlphaBeta />} />
          <Route path="reporting/attribution" element={<Attribution />} />
          <Route path="portfolio-legacy" element={<Portfolio />} />
          <Route path="risk-legacy" element={<RiskOverview />} />          

          <Route path="system-status" element={<SystemStatus />} />
          <Route path="system/go-no-go" element={<GoNoGo />} />
          <Route path="settings" element={<Settings />} />

          {/* Market */}

          <Route path="execution-trace-legacy" element={<ExecutionTraceBoard />} />
          <Route path="fills-board-legacy" element={<FillsBoard />} />
          <Route path="positions-board-legacy" element={<PositionsBoard />} />
          <Route path="order-board-legacy" element={<OrderBoard />} />
          <Route path="signals/board-legacy" element={<SignalBoard />} />
          <Route path="market/top-movers-legacy" element={<TopMovers />} />
          <Route path="market/regime-legacy" element={<MarketRegime />} />

          {/* Simulation */}

          {/* Reporting */}
          <Route path="reporting/profitability-legacy" element={<Profitability />} />
          <Route path="reporting/worst-trades-legacy" element={<WorstTrades />} />
          <Route path="reporting/open-positions" element={<OpenPositions />} />

          {/* Intelligence */}
          <Route path="intelligence/sentiment" element={<Sentiment />} />
          <Route path="intelligence/whales" element={<Whales />} />

          {/* ICO */}
          <Route path="ico" element={<Navigate to="/bricks/crypto" replace />} />
          <Route path="ico/candidates" element={<Navigate to="/bricks/crypto" replace />} />
          <Route path="ico/screened" element={<Navigate to="/bricks/crypto" replace />} />
          <Route path="ico/scored" element={<Navigate to="/bricks/crypto" replace />} />
          <Route path="ico/allocation" element={<Navigate to="/bricks/crypto" replace />} />

          {/* Crypto unified page */}
          <Route path="bricks/crypto" element={<Crypto />} />
          <Route path="bricks/crypto/whales" element={<Navigate to="/bricks/crypto" replace />} />
          <Route path="bricks/crypto/ico" element={<Navigate to="/bricks/crypto" replace />} />
          <Route path="bricks/crypto/ico/candidates" element={<Navigate to="/bricks/crypto" replace />} />
          <Route path="bricks/crypto/ico/screened" element={<Navigate to="/bricks/crypto" replace />} />
          <Route path="bricks/crypto/ico/scored" element={<Navigate to="/bricks/crypto" replace />} />
          <Route path="bricks/crypto/ico/allocation" element={<Navigate to="/bricks/crypto" replace />} />


          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />

        </Route>
              <Route path="/family-office" element={<FamilyOfficeDashboard />} />
      </Routes>
    </Router>
  );
}
