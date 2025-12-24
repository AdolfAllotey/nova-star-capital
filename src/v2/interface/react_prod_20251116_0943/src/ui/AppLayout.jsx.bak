// src/ui/AppLayout.jsx
import React from "react";
import { Link, NavLink } from "react-router-dom";

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `px-3 py-2 rounded-xl text-sm transition
         ${isActive ? "bg-zinc-800 text-white" : "text-zinc-300 hover:text-white hover:bg-zinc-800/60"}`
      }
      end
    >
      {children}
    </NavLink>
  );
}

export default function AppLayout({ children }) {
  return (
    <div className="min-h-dvh bg-zinc-950 text-zinc-100">
      <header className="sticky top-0 z-30 border-b border-zinc-800/60 bg-zinc-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-[1400px] items-center gap-4 px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            {/* Petit logo discrêt (pas en plein écran) */}
            <div className="size-6 rounded-full bg-emerald-500/90 shadow-inner" />
            <span className="font-semibold tracking-wide">Nova Star Capital</span>
          </Link>
          <nav className="ml-auto flex flex-wrap items-center gap-2">
            <NavItem to="/">Dashboard</NavItem>
            <NavItem to="/top-movers">Top Movers</NavItem>
            <NavItem to="/profitability">Profitability</NavItem>
            <NavItem to="/worst-trades">Worst Trades</NavItem>
            <NavItem to="/open-positions">Open Positions</NavItem>
            <NavItem to="/ico/candidates">ICO Candidates</NavItem>
            <NavItem to="/ico/screened">ICO Screened</NavItem>
            <NavItem to="/ico/scored">ICO Scored</NavItem>
            <NavItem to="/ico/allocation">ICO Allocation</NavItem>
            <NavItem to="/settings">Settings</NavItem>
            <NavItem to="/health">Health</NavItem>
          </nav>
        </div>
      </header>

      {/* Barre de contenu */}
      <main className="mx-auto max-w-[1400px] px-4 py-6">
        {children}
      </main>

      <footer className="mt-10 border-t border-zinc-800/60 px-4 py-6 text-center text-xs text-zinc-400">
        © 2025 Nova Star Capital — preprod UI
      </footer>
    </div>
  );
}
