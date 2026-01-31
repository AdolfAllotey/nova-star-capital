// src/components/Sidebar.jsx
// Sidebar officielle (source de vérité navigation) — NSC V2+ multi-briques

import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  TrendingUp,
  BarChart2,
  Activity,
  Briefcase,
  LineChart,
  FolderGit2,
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
  const location = useLocation();
  const isCrypto = location.pathname.startsWith("/bricks/crypto");

  return (
    <aside className="w-72 border-r border-zinc-800 bg-zinc-950/95 flex flex-col backdrop-blur">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-zinc-800 flex items-center gap-3">
        <div className="h-9 w-9 rounded-xl bg-emerald-500/10 border border-emerald-500/60 flex items-center justify-center">
          <span className="text-emerald-400 text-xs font-bold">NSC</span>
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-zinc-100">
            Nova Star Capital
          </span>
          <span className="text-[11px] text-zinc-500">Trading Desk · V2 préprod</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 space-y-1">
        {/* 1) GLOBAL */}
        <SectionTitle>Global</SectionTitle>
        <div className="space-y-1">
          <NavItem to="/dashboard" label="Dashboard" icon={LayoutDashboard} />
          <NavItem to="/market/top-movers" label="Top Movers" icon={TrendingUp} />
          <NavItem to="/reporting/pnl" label="PnL" icon={LineChart} />
          <NavItem to="/reporting/alpha-beta" label="α / β" icon={LineChart} />
          <NavItem
            to="/reporting/profitability"
            label="Profitability"
            icon={BarChart2}
          />
          <NavItem to="/portfolio" label="Portfolio" icon={Layers} />
          <NavItem to="/risk" label="Risk" icon={ShieldAlert} />
          <NavItem
            to="/reporting/worst-trades"
            label="Worst Trades"
            icon={Activity}
          />
          <NavItem
            to="/reporting/open-positions"
            label="Open Positions"
            icon={Briefcase}
          />
        </div>

        {/* 2) BRIQUES */}
        <SectionTitle>Briques</SectionTitle>
        <div className="space-y-1">
          {/* Crypto */}
          <NavItem to="/bricks/crypto/ico" label="Crypto" icon={Rocket} />

          {/* Sous-menu ICO visible uniquement quand on est dans /bricks/crypto/* */}
          {isCrypto && (
            <div className="ml-6 mt-2 border-l border-zinc-800 pl-3 space-y-1">
              <div className="text-[11px] font-semibold uppercase tracking-widest text-zinc-600 mb-1">
                Crypto · ICO
              </div>

              <NavItem
                to="/bricks/crypto/ico"
                label="ICO – Dashboard"
                icon={FolderGit2}
                coming={!FEATURES.CRYPTO_ICO}
              />
              <NavItem
                to="/bricks/crypto/ico/candidates"
                label="ICO – Candidates"
                icon={FolderGit2}
                coming={!FEATURES.CRYPTO_ICO}
              />
              <NavItem
                to="/bricks/crypto/ico/screened"
                label="ICO – Screened"
                icon={FolderGit2}
                coming={!FEATURES.CRYPTO_ICO}
              />
              <NavItem
                to="/bricks/crypto/ico/scored"
                label="ICO – Scored"
                icon={FolderGit2}
                coming={!FEATURES.CRYPTO_ICO}
              />
              <NavItem
                to="/bricks/crypto/ico/allocation"
                label="ICO – Allocation"
                icon={FolderGit2}
                coming={!FEATURES.CRYPTO_ICO}
              />
              <div className="mt-3 text-[11px] font-semibold uppercase tracking-widest text-zinc-600">
                Crypto · Whales
              </div>
              <NavItem
                to="/bricks/crypto/whales"
                label="Whales"
                icon={FolderGit2}
              />

            </div>
          )}

          {/* Autres briques */}
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
          <NavItem
            to="/bricks/lt"
            label="Long Terme"
            icon={Rocket}
            coming={!FEATURES.BRICK_LT}
          />
          <NavItem
            to="/bricks/options"
            label="Options US"
            icon={Rocket}
            coming={!FEATURES.BRICK_OPTIONS}
          />
        </div>

        {/* 3) SYSTEME */}
        <SectionTitle>Système</SectionTitle>
        <div className="space-y-1">
          <NavItem to="/system/go-no-go" label="Go / No-Go" icon={ClipboardCheck} />
          <NavItem to="/system-status" label="System Status" icon={ServerCog} />
          <NavItem to="/settings" label="Settings" icon={Settings} />
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
  );
}
