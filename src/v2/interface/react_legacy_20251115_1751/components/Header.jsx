import { useEffect, useState } from "react";
import { Menu, Bell, Circle, CircleCheck, CircleAlert, Search } from "lucide-react";

export default function Header({
  onToggleSidebar,
  title = "Nova Star Capital",
  subtitle = "V2 Interface",
  apiStatusUrl = "/status", // endpoint exposé par ton app FastAPI
}) {
  const [apiOk, setApiOk] = useState(null);
  const [now, setNow] = useState(new Date());
  const [query, setQuery] = useState("");

  useEffect(() => {
    // horloge légère
    const id = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    // ping API léger
    let aborted = false;
    (async () => {
      try {
        const res = await fetch(apiStatusUrl, { cache: "no-store" });
        const data = await res.json().catch(() => ({}));
        if (!aborted) setApiOk(Boolean(data?.status === "ok"));
      } catch {
        if (!aborted) setApiOk(false);
      }
    })();
    return () => {
      aborted = true;
    };
  }, [apiStatusUrl]);

  const StatusIcon = () => {
    if (apiOk === null) return <Circle className="h-3.5 w-3.5 text-zinc-400" />;
    if (apiOk) return <CircleCheck className="h-3.5 w-3.5 text-emerald-400" />;
    return <CircleAlert className="h-3.5 w-3.5 text-amber-400" />;
  };

  const dateStr = now.toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "2-digit",
    month: "short",
  });

  return (
    <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/60 backdrop-blur-md px-4 py-2">
      {/* Gauche */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="md:hidden p-2 rounded-lg hover:bg-zinc-800 transition"
          aria-label="Basculer la barre latérale"
        >
          <Menu size={18} />
        </button>

        <div className="flex items-center gap-2">
          <h1 className="font-semibold text-lg tracking-tight text-zinc-100">
            {title}
          </h1>
          {subtitle && (
            <span className="text-xs text-zinc-500 ml-1">{subtitle}</span>
          )}
        </div>

        {/* Badge status API */}
        <div className="ml-3 inline-flex items-center gap-1 rounded-lg border border-zinc-800 bg-zinc-900 px-2 py-1">
          <StatusIcon />
          <span className="text-xs text-zinc-400">
            {apiOk === null ? "Vérification…" : apiOk ? "API OK" : "API degradée"}
          </span>
        </div>
      </div>

      {/* Centre : recherche (optionnel) */}
      <div className="hidden md:flex items-center relative w-[380px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Rechercher un token, un wallet, un rapport…"
          className="w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-zinc-700"
        />
      </div>

      {/* Droite */}
      <div className="flex items-center gap-3">
        <span className="hidden sm:inline text-sm text-zinc-400">{dateStr}</span>
        <button
          className="p-2 rounded-lg hover:bg-zinc-800 transition"
          aria-label="Notifications"
        >
          <Bell size={18} />
        </button>
        {/* Avatar placeholder */}
        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-zinc-700 to-zinc-600 border border-zinc-500/30" />
      </div>
    </header>
  );
}
