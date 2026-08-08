import { getUiLabel } from "../lib/uiVersion";
// src/components/Sidebar.jsx
// Sidebar officielle (source de vérité navigation) — NSC V2+ multi-briques

import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  TrendingUp,
  BarChart2,
  Activity,
  Briefcase,
  LineChart,
  ServerCog,
  Settings,
  ShieldAlert,
  Layers,
  Rocket,
  ClipboardCheck
} from "lucide-react";

import { FEATURES } from "../config/features";

function cls(...parts) {
  return parts.filter(Boolean).join(" ");
}

function SectionTitle({ children }) {
  return (
    <div className="mt-6 mb-2 px-3 text-[11px] font-semibold uppercase tracking-widest text-zinc-500">
      {children}
    </div>
  );
}

function NavItem({ to, label, icon: Icon, coming = false, disabled = false }) {
  const content = (
    <div
      className={cls(
        "flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors border",
        disabled ? "opacity-60 cursor-not-allowed" : "cursor-pointer",
        "border-transparent"
      )}
    >
      {Icon && <Icon className="h-4 w-4 shrink-0" />}
      <span className="truncate">{label}</span>
      {coming && (
        <span className="ml-auto inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-200">
          COMING
        </span>
      )}
    </div>
  );

  if (disabled) return <div className="px-0.5">{content}</div>;

  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        cls(
          "block px-0.5",
          isActive
            ? "[&>div]:bg-zinc-900 [&>div]:border-zinc-700 [&>div]:text-zinc-50 [&>div]:shadow-sm"
            : "[&>div]:text-zinc-300 hover:[&>div]:text-white hover:[&>div]:bg-zinc-900/60"
        )
      }
    >
      {content}
    </NavLink>
  );
}

export default function Sidebar() {
  return (
    <aside className="w-72 border-r border-zinc-800 bg-zinc-950/95 flex flex-col backdrop-blur">
      <div className="px-4 pt-4 pb-3 border-b border-zinc-800 flex items-center gap-3">
        <div className="h-9 w-9 rounded-xl bg-emerald-500/10 border border-emerald-500/60 flex items-center justify-center">
          <span className="text-emerald-400 text-xs font-bold">NSC</span>
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-zinc-100">
            Nova Star Capital
          </span>
          <span className="text-[11px] text-zinc-500">Preproduction · {getUiLabel()}</span>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 space-y-1">
        <SectionTitle>Global</SectionTitle>
        <div className="space-y-1">
          <NavItem to="/dashboard" label="Dashboard" icon={LayoutDashboard} />
          <NavItem to="/dashboard" label="Dashboard" icon={LayoutDashboard} />
          <NavItem to="/control-room" label="Control Room" icon={LayoutDashboard} />
          <NavItem to="/executive" label="Executive" icon={LayoutDashboard} />
          <NavItem to="/order-board" label="Order Board" icon={LayoutDashboard} />
          <NavItem to="/positions-board" label="Positions Board" icon={LayoutDashboard} />
          <NavItem to="/fills-board" label="Fills Board" icon={LayoutDashboard} />
          <NavItem to="/execution-trace" label="Execution Trace" icon={LayoutDashboard} />
          <NavItem to="/market/top-movers" label="Top Movers" icon={TrendingUp} />
          <NavItem to="/reporting/pnl" label="PnL" icon={LineChart} />
          <NavItem to="/reporting/alpha-beta" label="α / β" icon={LineChart} />
          <NavItem to="/reporting/profitability" label="Profitability" icon={BarChart2} />
          <NavItem to="/portfolio" label="Portfolio" icon={Layers} />
          <NavItem to="/risk" label="Risk" icon={ShieldAlert} />
          <NavItem to="/reporting/worst-trades" label="Worst Trades" icon={Activity} />
          <NavItem to="/reporting/open-positions" label="Open Positions" icon={Briefcase} />
        </div>

        <SectionTitle>Briques</SectionTitle>
        <div className="space-y-1">
          <NavItem to="/bricks/crypto" label="Crypto" icon={Rocket} />
          <NavItem
            to="/bricks/offensive"
            label="Actions Offensives"
            icon={Rocket}
            coming={!FEATURES.BRICK_OFFENSIVE}
          />
          <NavItem
            to="/bricks/defensive"
            label="Actions Défensives"
            icon={Rocket}
            coming={!FEATURES.BRICK_DEFENSIVE}
          />
          <NavItem to="/bricks/bonds" label="Bonds" icon={Rocket} />
          <NavItem to="/bricks/precious-metals" label="Precious Metals" icon={Rocket} />
          <NavItem to="/bricks/lt" label="Long Terme" icon={Rocket} />
          <NavItem
            to="/bricks/options"
            label="Options US"
            icon={Rocket}
          />
        </div>

        <SectionTitle>Système</SectionTitle>
        <div className="space-y-1">
          <NavItem to="/system/go-no-go" label="Go / No-Go" icon={ClipboardCheck} />
          <NavItem to="/system-status" label="System Status" icon={ServerCog} />
          <NavItem to="/settings" label="Settings" icon={Settings} />
        </div>
      </nav>

      <div className="px-4 py-3 border-t border-zinc-800 text-[11px] text-zinc-500 flex items-center justify-between">
        <span>© {new Date().getFullYear()} Nova Star Capital</span>
        <span className="inline-flex items-center gap-1">
          <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          <span>Préprod</span>
        </span>
      </div>
    </aside>
  );
}
