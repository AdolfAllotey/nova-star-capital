import React from "react";
import { NavLink, Outlet } from "react-router-dom";

function Tab({ to, label }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        [
          "px-3 py-2 rounded-xl text-sm border transition-colors",
          isActive
            ? "bg-zinc-900 border-zinc-700 text-zinc-50"
            : "border-zinc-800 text-zinc-300 hover:text-white hover:bg-zinc-900/60",
        ].join(" ")
      }
    >
      {label}
    </NavLink>
  );
}

export default function CryptoLayout() {
  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">Crypto</h1>
          <p className="text-sm text-zinc-400">
            Vue brique Crypto (overview + reporting + risk + ICO).
          </p>
        </div>
      </header>

      {/* Sous-menu (ce que tu appelles “sidebar sous crypto”) */}
      <div className="flex flex-wrap gap-2">
        <Tab to="/bricks/crypto" label="Overview" />
        <Tab to="/reporting/pnl" label="PnL" />
        <Tab to="/portfolio" label="Portfolio" />
        <Tab to="/risk" label="Risk" />
        <Tab to="/bricks/crypto/ico" label="ICO" />
        <Tab to="/bricks/crypto/whales" label="Whales" />
      </div>

      <Outlet />
    </div>
  );
}
