// src/ui/Sidebar.jsx
import React from "react";
import { NavLink } from "react-router-dom";

const linkBase =
  "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors";
const linkActive =
  "bg-zinc-800 text-zinc-50 font-medium";
const linkInactive =
  "text-zinc-300 hover:bg-zinc-800/60 hover:text-zinc-50";

function NavItem({ to, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `${linkBase} ${isActive ? linkActive : linkInactive}`
      }
    >
      <span>{label}</span>
    </NavLink>
  );
}

export default function Sidebar() {
  return (
    <aside className="w-64 bg-zinc-950/95 border-r border-zinc-800 flex flex-col">
      <div className="px-4 py-4 border-b border-zinc-800 flex items-center gap-2">
        <div className="h-7 w-7 rounded-lg bg-emerald-500 flex items-center justify-center">
          <span className="text-xs font-bold text-zinc-900">NSC</span>
        </div>
        <div>
          <div className="text-sm font-semibold text-zinc-50">
            Nova Star Capital
          </div>
          <div className="text-[11px] text-zinc-500 uppercase tracking-wide">
            v2 · préprod
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-4">
        <div>
          <div className="text-[11px] text-zinc-500 uppercase mb-2">
            Vue globale
          </div>
          <div className="flex flex-col gap-1">
            <NavItem to="/dashboard" label="Dashboard" />
            <NavItem to="/top-movers" label="Top Movers" />
            <NavItem to="/profitability" label="Profitability" />
            <NavItem to="/worst-trades" label="Worst Trades" />
            <NavItem to="/open-positions" label="Open Positions" />
          </div>
        </div>

        <div>
          <div className="text-[11px] text-zinc-500 uppercase mb-2">
            Sentiment & Whales
          </div>
          <div className="flex flex-col gap-1">
            <NavItem to="/sentiment" label="Sentiment" />
            <NavItem to="/whales" label="Whales" />
          </div>
        </div>

        <div>
          <div className="text-[11px] text-zinc-500 uppercase mb-2">
            Stratégie
          </div>
          <div className="flex flex-col gap-1">
            <NavItem to="/strategy" label="Strategy" />
            <NavItem to="/market-regime" label="Market Regime" />
            <NavItem to="/live" label="Live Simulation" />
          </div>
        </div>

        <div>
          <div className="text-[11px] text-zinc-500 uppercase mb-2">
            ICO
          </div>
          <div className="flex flex-col gap-1">
            <NavItem to="/ico/candidates" label="Candidates" />
            <NavItem to="/ico/screened" label="Screened" />
            <NavItem to="/ico/scored" label="Scored" />
            <NavItem to="/ico/allocation" label="Allocation" />
          </div>
        </div>

        <div>
          <div className="text-[11px] text-zinc-500 uppercase mb-2">
            Système
          </div>
          <div className="flex flex-col gap-1">
            <NavItem to="/metrics" label="Metrics" />
            <NavItem to="/system-status" label="System status" />
            <NavItem to="/settings" label="Settings" />
          </div>
        </div>
      </div>

      <div className="px-4 py-3 border-t border-zinc-800 text-[11px] text-zinc-500">
        © {new Date().getFullYear()} NSC · préprod
      </div>
    </aside>
  );
}
