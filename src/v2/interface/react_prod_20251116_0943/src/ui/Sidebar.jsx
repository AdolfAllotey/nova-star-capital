import React from "react";
import { NavLink } from "react-router-dom";

export default function Sidebar() {
  const links = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/top-movers", label: "Top Movers" },
    { to: "/profitability", label: "Profitability" },
    { to: "/worst-trades", label: "Worst Trades" },
    { to: "/open-positions", label: "Open Positions" },
    { to: "/sentiment", label: "Sentiment" },
    { to: "/whales", label: "Whales" },
    { to: "/ico/candidates", label: "ICO – Candidates" },
    { to: "/ico/screened", label: "ICO – Screened" },
    { to: "/ico/scored", label: "ICO – Scored" },
    { to: "/ico/allocation", label: "ICO – Allocation" }
  ];

  return (
    <aside className="w-64 border-r border-zinc-800 p-4 flex flex-col bg-zinc-950">
      <div className="flex items-center gap-2 mb-6">
        <div className="h-8 w-8 rounded-full bg-emerald-500 flex items-center justify-center text-xs font-bold">
          NSC
        </div>
        <div>
          <div className="text-sm font-semibold">Nova Star Capital</div>
          <div className="text-xs text-zinc-400">Trading desk</div>
        </div>
      </div>

      <nav className="space-y-1 text-sm">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) =>
              "block px-3 py-2 rounded-md " +
              (isActive
                ? "bg-emerald-600 text-white"
                : "text-zinc-400 hover:bg-zinc-800")
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto pt-4 text-[11px] text-zinc-500 border-t border-zinc-800">
        © 2025 Nova Star Capital — preprod
      </div>
    </aside>
  );
}
