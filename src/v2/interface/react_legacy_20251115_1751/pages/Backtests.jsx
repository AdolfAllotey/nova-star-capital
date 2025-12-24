// src/v2/interface/react/pages/Backtests.jsx
import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "../components/ui/select";
import { ScrollArea } from "../components/ui/scroll-area";

function cn(...cls) { return cls.filter(Boolean).join(" "); }
const percent = (v) => (v === null || v === undefined || isNaN(v) ? "—" : `${(Number(v) * 100).toFixed(1)}%`);
const money = (v) => (v === null || v === undefined || isNaN(v) ? "—" : `${Number(v).toFixed(2)}`);
const safeLower = (s) => (typeof s === "string" ? s.toLowerCase() : "");

export default function Backtests() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const [q, setQ] = useState("");
  const [strategy, setStrategy] = useState("all");
  const [token, setToken] = useState("all");
  const [sortKey, setSortKey] = useState("pnl");
  const [sortDir, setSortDir] = useState("desc");

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setErr("");
      try {
        const res = await fetch("/data/backtests.json", { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        // format attendu: [{ strategy, token, pair, period, trades, winRate (0-1), pnl, sharpe?, maxDD? }, ...]
        if (mounted) setRows(Array.isArray(data) ? data : []);
      } catch (e) {
        console.warn("Backtests: fichier manquant/illisible (ok pour dev):", e.message);
        if (mounted) setRows([]);
        if (mounted) setErr("Impossible de charger backtests.json");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  const strategies = useMemo(() => {
    const s = new Set(rows.map(r => r.strategy).filter(Boolean));
    return ["all", ...Array.from(s).sort()];
  }, [rows]);

  const tokens = useMemo(() => {
    const s = new Set(rows.map(r => r.token || r.pair?.split("/")[0]).filter(Boolean));
    return ["all", ...Array.from(s).sort()];
  }, [rows]);

  const filtered = useMemo(() => {
    const qq = safeLower(q);
    let out = rows.filter(r => {
      const inStrategy = strategy === "all" || r.strategy === strategy;
      const tok = r.token || r.pair?.split("/")[0];
      const inToken = token === "all" || tok === token;
      const text = [r.strategy, r.token, r.pair, r.period].map(s => safeLower(s)).join(" ");
      const inSearch = !qq || text.includes(qq);
      return inStrategy && inToken && inSearch;
    });
    out.sort((a, b) => {
      const av = a?.[sortKey] ?? (sortKey === "winRate" ? 0 : 0);
      const bv = b?.[sortKey] ?? (sortKey === "winRate" ? 0 : 0);
      return sortDir === "asc" ? (av > bv ? 1 : av < bv ? -1 : 0) : (av < bv ? 1 : av > bv ? -1 : 0);
    });
    return out;
  }, [rows, q, strategy, token, sortKey, sortDir]);

  const summary = useMemo(() => {
    const n = filtered.length || 1;
    const trades = filtered.reduce((s, r) => s + (Number(r.trades) || 0), 0);
    const pnl = filtered.reduce((s, r) => s + (Number(r.pnl) || 0), 0);
    const wr = filtered.reduce((s, r) => s + (Number(r.winRate) || 0), 0) / n;
    return { strategies: strategies.length - 1, entries: filtered.length, trades, pnl, wr };
  }, [filtered, strategies.length]);

  const exportCSV = () => {
    const headers = ["strategy", "token", "pair", "period", "trades", "winRate", "pnl", "sharpe", "maxDD"];
    const lines = [headers.join(",")].concat(
      filtered.map(r =>
        headers.map(h => (r[h] !== undefined ? String(r[h]).replaceAll(",", " ") : "")).join(",")
      )
    );
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "backtests_export.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Backtests</h1>
        <div className="text-xs text-muted-foreground">
          {loading ? "Chargement…" : `${summary.entries} résultats · ${summary.trades} trades · PnL ${money(summary.pnl)} · WR ${percent(summary.wr)}`}
        </div>
      </div>

      <Card>
        <CardContent className="pt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            placeholder="Rechercher (stratégie, token, paire, période)…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <Select value={strategy} onValueChange={setStrategy}>
            <SelectTrigger><SelectValue placeholder="Stratégie" /></SelectTrigger>
            <SelectContent>
              {strategies.map(s => <SelectItem key={s} value={s}>{s === "all" ? "Toutes les stratégies" : s}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={token} onValueChange={setToken}>
            <SelectTrigger><SelectValue placeholder="Token" /></SelectTrigger>
            <SelectContent>
              {tokens.map(t => <SelectItem key={t} value={t}>{t === "all" ? "Tous les tokens" : t}</SelectItem>)}
            </SelectContent>
          </Select>
          <div className="flex gap-2">
            <Button variant="secondary" className="w-full" onClick={() => { setQ(""); setStrategy("all"); setToken("all"); }}>
              Réinitialiser
            </Button>
            <Button className="w-full" onClick={exportCSV}>Exporter CSV</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Résultats</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="max-h-[65vh]">
            <div className="min-w-[900px]">
              <HeaderRow sortKey={sortKey} sortDir={sortDir} onSort={(k) => {
                if (k === sortKey) setSortDir(d => (d === "asc" ? "desc" : "asc"));
                else { setSortKey(k); setSortDir("desc"); }
              }} />
              {loading ? (
                <div className="p-6 text-sm text-muted-foreground">Chargement des backtests…</div>
              ) : err ? (
                <div className="p-6 text-sm text-destructive">Aucun fichier /data/backtests.json trouvé (ok en dev). {err}</div>
              ) : filtered.length === 0 ? (
                <div className="p-6 text-sm text-muted-foreground">Aucun résultat.</div>
              ) : (
                filtered.map((r, i) => <DataRow key={i} r={r} />)
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}

function HeaderRow({ sortKey, sortDir, onSort }) {
  const Th = ({ label, k }) => (
    <div
      role="button"
      onClick={() => onSort(k)}
      className="px-4 py-2 text-xs font-medium uppercase text-muted-foreground cursor-pointer select-none"
      title="Trier"
    >
      {label}{sortKey === k ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
    </div>
  );
  return (
    <div className="grid grid-cols-[1.2fr,1fr,1fr,1fr,0.8fr,0.8fr,0.8fr,0.8fr] border-b bg-muted/30">
      <Th label="Stratégie" k="strategy" />
      <Th label="Token" k="token" />
      <Th label="Paire" k="pair" />
      <Th label="Période" k="period" />
      <Th label="Trades" k="trades" />
      <Th label="WinRate" k="winRate" />
      <Th label="PnL" k="pnl" />
      <Th label="Sharpe" k="sharpe" />
    </div>
  );
}

function DataRow({ r }) {
  const tok = r.token || (r.pair ? String(r.pair).split("/")[0] : "—");
  const wr = r.winRate ?? r.winrate ?? r.win_rate;
  const dd = r.maxDD ?? r.maxDrawdown ?? r.max_drawdown;
  return (
    <div className="grid grid-cols-[1.2fr,1fr,1fr,1fr,0.8fr,0.8fr,0.8fr,0.8fr] border-b text-sm">
      <Cell>{r.strategy || "—"}</Cell>
      <Cell>{tok}</Cell>
      <Cell className="font-mono">{r.pair || `${tok}/USDT`}</Cell>
      <Cell>{r.period || "—"}</Cell>
      <Cell>{Number(r.trades ?? 0)}</Cell>
      <Cell className={cn((wr ?? 0) >= 0.5 ? "text-emerald-600" : "text-amber-600")}>{percent(wr)}</Cell>
      <Cell className={cn((r.pnl ?? 0) >= 0 ? "text-emerald-600" : "text-rose-600")}>{money(r.pnl)}</Cell>
      <Cell title={dd ? `MaxDD: ${money(dd)}` : undefined}>{r.sharpe !== undefined ? Number(r.sharpe).toFixed(2) : "—"}</Cell>
    </div>
  );
}
function Cell({ children, className }) {
  return <div className={cn("px-4 py-3 whitespace-nowrap", className)}>{children}</div>;
}