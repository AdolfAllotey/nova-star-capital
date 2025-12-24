import { NavLink } from "react-router-dom";
import { LayoutGrid, Flame } from "lucide-react"; // ajoute d’autres icônes si besoin

function Item({ to, icon: Icon, label }) {
  return (
    <li>
      <NavLink
        to={to}
        className={({ isActive }) =>
          `group flex items-center gap-2 px-3 py-2 rounded-xl transition
           ${isActive ? "bg-zinc-800 text-white" : "text-zinc-300 hover:bg-zinc-800/60"}`
        }
        end
      >
        <Icon size={18} className="shrink-0" />
        <span className="truncate">{label}</span>
      </NavLink>
    </li>
  );
}

export default function Sidebar() {
  return (
    <aside className="w-64 shrink-0 border-r border-zinc-800 bg-zinc-950/40">
      <div className="px-4 py-4">
        <div className="text-zinc-200 font-semibold tracking-wide">Nova Star Capital</div>
        <div className="text-xs text-zinc-500 mt-0.5">Interface V2</div>
      </div>

      <nav className="px-3">
        <ul className="space-y-1">
          {/* Lien Dashboard existant */}
          <Item to="/dashboard" icon={LayoutGrid} label="Dashboard" />

          {/* 👉 Nouveau lien Top Movers */}
          <Item to="/top-movers" icon={Flame} label="Top Movers" />

          {/* Exemple : ajoute tes autres liens ici
          <Item to="/worst-trades" icon={AlertTriangle} label="Worst Trades" />
          <Item to="/profitability" icon={LineChart} label="Profitability" />
          */}
        </ul>
      </nav>
    </aside>
  );
}
