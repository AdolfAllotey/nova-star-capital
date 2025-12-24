// src/components/Sidebar.jsx
// Sidebar "trading desk" premium pour Nova Star Capital

import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  TrendingUp,
  Briefcase,
  Activity,
  LineChart,
  BarChart2,
  Target,
  RadioTower,
  Waves,
  FolderGit2,
  Filter,
  Star,
  PieChart,
  Settings,
  ServerCog,
  Rocket,
} from "lucide-react";

const navSections = [
  {
    label: "Overview",
    items: [
      {
        label: "Dashboard",
        to: "/dashboard",
        icon: LayoutDashboard,
      },
      {
        label: "Profitability",
        to: "/reporting/profitability",
        icon: BarChart2,
      },
      {
        label: "Top Movers",
        to: "/market/top-movers",
        icon: TrendingUp,
      },
      {
        label: "Worst Trades",
        to: "/reporting/worst-trades",
        icon: Activity,
      },
    ],
  },
  {
    label: "Trading Live",
    items: [
      {
        label: "Open Positions",
        to: "/reporting/open-positions",
        icon: Briefcase,
      },
      {
        label: "Market Regime",
        to: "/market/regime",
        icon: Waves,
      },
      {
        label: "Live Simulation",
        to: "/simulation/live",
        icon: Rocket,
      },
      {
        label: "Strategy",
        to: "/strategy",
        icon: Target,
      },
      {
        label: "Sentiment",
        to: "/intelligence/sentiment",
        icon: RadioTower,
      },
      {
        label: "Whales",
        to: "/intelligence/whales",
        icon: LineChart,
      },
    ],
  },
  {
    label: "ICO / Pré-lancement",
    items: [
      {
        label: "ICO Dashboard",
        to: "/ico",
        icon: FolderGit2,
      },
      {
        label: "ICO Candidates",
        to: "/ico/candidates",
        icon: FolderGit2,
      },
      {
        label: "ICO Screened",
        to: "/ico/screened",
        icon: Filter,
      },
      {
        label: "ICO Scored",
        to: "/ico/scored",
        icon: Star,
      },
      {
        label: "ICO Allocation",
        to: "/ico/allocation",
        icon: PieChart,
      },
    ],
  },
  {
    label: "Système",
    items: [
      {
        label: "System Status",
        to: "/system-status",
        icon: ServerCog,
      },
      {
        label: "Settings",
        to: "/settings",
        icon: Settings,
      },
    ],
  },
];

function SidebarLink({ to, icon: Icon, label }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        [
          "flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors",
          "border border-transparent",
          isActive
            ? "bg-zinc-900 border-zinc-700 text-zinc-50 shadow-sm"
            : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900/60",
        ].join(" ")
      }
    >
      <Icon className="h-4 w-4" />
      <span className="truncate">{label}</span>
    </NavLink>
  );
}

export default function Sidebar() {
  return (
    <aside className="flex h-full flex-col border-r border-zinc-800 bg-zinc-950/90 backdrop-blur">
      {/* Logo */}
      <div className="flex h-16 items-center px-4 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-xl bg-emerald-500/10 border border-emerald-500/40 flex items-center justify-center">
            <span className="text-emerald-400 text-xs font-bold">NSC</span>
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-zinc-50">
              Nova Star Capital
            </span>
            <span className="text-xs text-zinc-500">
              Trading Desk · V2 Préprod
            </span>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {navSections.map((section) => (
          <div key={section.label} className="space-y-2">
            <div className="px-2 text-[0.7rem] font-semibold uppercase tracking-wide text-zinc-500">
              {section.label}
            </div>
            <div className="space-y-1">
              {section.items.map((item) => (
                <SidebarLink
                  key={item.to}
                  to={item.to}
                  icon={item.icon}
                  label={item.label}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-zinc-800 px-4 py-3 text-[0.7rem] text-zinc-500 flex items-center justify-between">
        <span>Préproduction</span>
        <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" />
      </div>
    </aside>
  );
}
