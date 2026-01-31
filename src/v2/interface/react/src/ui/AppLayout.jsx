// src/ui/AppLayout.jsx
// Layout principal : sidebar premium + contenu, avec barre de statut globale

import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  TrendingUp,
  BarChart2,
  Activity,
  Briefcase,
  RadioTower,
  LineChart,
  Target,
  Waves,
  PlayCircle,
  FolderGit2,
  Filter,
  Star,
  PieChart,
  ServerCog,
  Settings,
} from "lucide-react";
import _LiveStatusBar from "./_LiveStatusBar.jsx";

function cls(...parts) {
  return parts.filter(Boolean).join(" ");
}

function _NavItem({ to, label, icon: Icon }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        cls(
          "flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors",
          "border border-transparent",
          isActive
            ? "bg-zinc-900 border-zinc-700 text-zinc-50 shadow-sm"
            : "text-zinc-300 hover:text-white hover:bg-zinc-900/60"
        )
      }
    >
      {Icon && <Icon className="h-4 w-4 shrink-0" />}
      <span className="truncate">{label}</span>
    </NavLink>
  );
}

function _SectionTitle({ children }) {
  return (
    <div className="mt-6 mb-2 px-3 text-[11px] font-semibold uppercase tracking-widest text-zinc-500">
      {children}
    </div>
  );
}

export default function AppLayout({ children }) {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 flex">
      {/* SIDEBAR */}
      <aside className="w-72 border-r border-zinc-800 bg-zinc-950/95 flex flex-col backdrop-blur">
        {/* Logo / titre */}
        <div className="px-4 pt-4 pb-3 border-b border-zinc-800 flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-emerald-500/10 border border-emerald-500/60 flex items-center justify-center">
            <span className="text-emerald-400 text-xs font-bold">NSC</span>
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-zinc-100">
              Nova Star Capital
            </span>
            <span className="text-[11px] text-zinc-500">
              Trading Desk · V2 préprod
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4 space-y-1">
          {/* Vue globale */}
          <_SectionTitle>Vue globale</_SectionTitle>
          <div className="space-y-1">
            <_NavItem
              to="/dashboard"
              label="Dashboard"
              icon={LayoutDashboard}
            />
            <_NavItem
              to="/market/top-movers"
              label="Top Movers"
              icon={TrendingUp}
            />
            <_NavItem
              to="/reporting/profitability"
              label="Profitability"
              icon={BarChart2}
            />
            <_NavItem
              to="/reporting/pnl"
              label="PnL"
              icon={BarChart2}
            />
            <_NavItem
              to="/reporting/worst-trades"
              label="Worst Trades"
              icon={Activity}
            />
            <_NavItem
              to="/reporting/open-positions"
              label="Open Positions"
              icon={Briefcase}
            />
          </div>

          {/* Sentiment & Whales */}
          <_SectionTitle>Sentiment & Whales</_SectionTitle>
          <div className="space-y-1">
            <_NavItem
              to="/intelligence/sentiment"
              label="Sentiment"
              icon={RadioTower}
            />
            <_NavItem
              to="/intelligence/whales"
              label="Whales"
              icon={LineChart}
            />
          </div>

          {/* Stratégie */}
          <_SectionTitle>Stratégie</_SectionTitle>
          <div className="space-y-1">
            <_NavItem
              to="/strategy"
              label="Strategy"
              icon={Target}
            />
            <_NavItem
              to="/market/regime"
              label="Market Regime"
              icon={Waves}
            />
            <_NavItem
              to="/simulation/live"
              label="Live Simulation"
              icon={PlayCircle}
            />
          </div>

          {/* ICO */}
          <_SectionTitle>ICO</_SectionTitle>
          <div className="space-y-1">
                        <_NavItem
              to="/ico"
              label="ICO – Dashboard"
              icon={FolderGit2}
            />
<_NavItem
              to="/ico/candidates"
              label="ICO – Candidates"
              icon={FolderGit2}
            />
            <_NavItem
              to="/ico/screened"
              label="ICO – Screened"
              icon={Filter}
            />
            <_NavItem
              to="/ico/scored"
              label="ICO – Scored"
              icon={Star}
            />
            <_NavItem
              to="/ico/allocation"
              label="ICO – Allocation"
              icon={PieChart}
            />
          </div>

          {/* Système */}
          <_SectionTitle>Système</_SectionTitle>
          <div className="space-y-1">
            <_NavItem
              to="/system-status"
              label="System Status"
              icon={ServerCog}
            />
            <_NavItem
              to="/settings"
              label="Settings"
              icon={Settings}
            />
          </div>
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-zinc-800 text-[11px] text-zinc-500 flex items-center justify-between">
          <span>© {new Date().getFullYear()} Nova Star Capital</span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            <span>Préprod</span>
          </span>
        </div>
      </aside>

      {/* CONTENU */}
      <main className="flex-1 bg-gradient-to-b from-zinc-950 via-zinc-950 to-zinc-950/95 p-6">
        <div className="max-w-6xl mx-auto space-y-4">
          <_LiveStatusBar />
          <div>{children}</div>
        </div>
      </main>
    </div>
  );
}
