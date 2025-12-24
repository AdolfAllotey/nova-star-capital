// src/v2/interface/react/pages/LiveSimulation.jsx
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { ScrollArea } from "../components/ui/scroll-area";
import {
  ResponsiveContainer,
  AreaChart, Area, Tooltip, XAxis, YAxis, CartesianGrid,
} from "recharts";

const PATHS = {
  trades: "/data/simulation/trade_simulation.json",
  perf: "/data/simulation/global_performance.json",
};

async function fetchJSON(url, fallback = null) {
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return fallback;
    return await res.json();
  } catch {
    return fallback;
  }
}

const fmtInt = (n) => (Number.isFinite(n) ? n.toLocaleString() : "—");
const fmtMoney = (n) =>
  Number.isFinite(Number(n)) ? `${Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 })} €` : "—";
const ucfirst = (s) => (s ? String(s).charAt(0).toUpperCase() + String(s).slice(1) : "");

export default function LiveSimulation() {
  const [loading, setLoading] = useState(false);
  const [trades, setTrades] = useState([]);
  const [perf, setPerf] = useState(null);

  // contrôles
  const [intervalSec, setIntervalSec] = useState(30);
  const [tokenFilter, setTokenFilter] = useState("all");
  const [exchFilter, setExchFilter] = useState("all");
  const [actionFilter, setActionFilter] = useState("all");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const [t, p] = await Promise.all([
      fetchJSON(PATHS.trades, []),
      fetchJSON(PATHS.perf, null),
    ]);
    setTrades(Array.isArray(t) ? t : []);
    setPerf(p && typeof p === "object" ? p : null);
    setLoading(false);
  }, []);

  // première charge
  useEffect(() => {
    load();
  }, [load]);

  // auto refresh
  useEffect(() => {
    if (!intervalSec || intervalSec <= 0) return;
    const id = setInterval(load, intervalSec * 1000);
    return () => clearInterval(id);
  }, [intervalSec, load]);

  const tokens = useMemo(() => {
    const s = new Set();
    for (const r of trades) if (r.token) s.add(String(r.token));
    return Array.from(s).sort();
  }, [trades]);

  const exchanges = useMemo(() => {
    const s = new Set();
    for (const r of trades) if (r.exchange) s.add(String(r.exchange));
    return Array.from(s).sort();
  }, [trades]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return trades.filter((r) => {
      const okToken = tokenFilter === "all" || String(r.token) === tokenFilter;
      const okExch = exchFilter === "all" || String(r.exchange) === exchFilter;
      const okAction = actionFilter === "all" || String(r.action).toLowerCase() === actionFilter;
      const hay = `${r.token || ""} ${r.exchange || ""} ${r.action || ""}`.toLowerCase();
      const okSearch = !q || hay.includes(q);
      return okToken && okExch && okAction && okSearch;
    });
  }, [trades, tokenFilter, exchFilter, actionFilter, search]);

  const summary = useMemo(() => {
    const total = filtered.length;
    let buy = 0;
    let sell = 0;
    let amountSum = 0;
    for (const r of filtered) {
      amountSum += Number(r.amount || 0);
      const a = String(r.action || "").toLowerCase();
      if (a === "buy") buy++;
      else if (a === "sell") sell++;
    }
    return { total, buy, sell, amountSum };
  }, [filtered]);

  const perfSeries = useMemo(() => {
    if (!perf || !Array.isArray(perf.history)) return [];
    // On calcule une série “cumulative” pour le graphe si non fournie
    let cumulative = 0;
    return perf.history.map((d) => {
      cumulative += Number(d.daily_profit || 0);
      return { date: d.date, cumulative };
    });
  }, [perf]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Live Simulation</h1>
          <p className="text-sm text-muted-foreground">
            Suivi en temps réel des trades simulés et de la performance agrégée.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={load} disabled={loading}>
            {loading ? "Rafraîchissement…" : "Rafraîchir maintenant"}
          </Button>
          <Link to="/dashboard"><Button>Dashboard</Button></Link>
        </div>
      </div>

      {/* Contrôles */}
      <Card>
        <CardHeader>
          <CardTitle>Contrôles</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-5">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Recherche</label>
            <Input
              placeholder="bitcoin, binance, buy…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Token</label>
            <Select value={tokenFilter} onValueChange={setTokenFilter}>
              <SelectTrigger><SelectValue placeholder="Token" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous</SelectItem>
                {tokens.map((t) => (
                  <SelectItem key={t} value={t}>{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Exchange</label>
            <Select value={exchFilter} onValueChange={setExchFilter}>
              <SelectTrigger><SelectValue placeholder="Exchange" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous</SelectItem>
                {exchanges.map((e) => (
                  <SelectItem key={e} value={e}>{e}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

         <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Action</label>
            <Select value={actionFilter} onValueChange={setActionFilter}>
              <SelectTrigger><SelectValue placeholder="Action" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toutes</SelectItem>
                <SelectItem value="buy">Buy</SelectItem>
                <SelectItem value="sell">Sell</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Auto‑refresh (s)</label>
            <Input
              type="number"
              min={0}
              value={intervalSec}
              onChange={(e) => setIntervalSec(Math.max(0, Number(e.target.value || 0)))}
            />
          </div>
        </CardContent>
      </Card>

      {/* Résumé + graphe */}
      <div className="grid gap-3 md:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>Résumé</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-2 gap-2 text-sm">
            <div className="space-y-1">
              <div className="text-muted-foreground">Trades</div>
              <div className="text-lg font-semibold">{fmtInt(summary.total)}</div>
            </div>
            <div className="space-y-1">
              <div className="text-muted-foreground">Montant total</div>
              <div className="text-lg font-semibold">{fmtMoney(summary.amountSum)}</div>
            </div>
            <div className="space-y-1">
              <div className="text-muted-foreground">Buy</div>
              <div className="text-lg font-semibold">{fmtInt(summary.buy)}</div>
            </div>
            <div className="space-y-1">
              <div className="text-muted-foreground">Sell</div>
              <div className="text-lg font-semibold">{fmtInt(summary.sell)}</div>
            </div>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader><CardTitle>Performance cumulée</CardTitle></CardHeader>
          <CardContent className="h-48">
            {perfSeries.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={perfSeries}>
                  <defs>
                    <linearGradient id="pnlFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="currentColor" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="currentColor" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Area type="monotone" dataKey="cumulative" stroke="currentColor" fillOpacity={1} fill="url(#pnlFill)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-muted-foreground">Aucune série disponible. Vérifie {PATHS.perf}.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Table des trades */}
      <Card>
        <CardHeader>
          <CardTitle>Trades simulés</CardTitle>
        </CardHeader>
        <CardContent>
          {!filtered.length ? (
            <p className="text-sm text-muted-foreground">
              Aucun trade à afficher. Lance le pipeline et synchronise les données dans <code>public/data</code>.
            </p>
          ) : (
            <ScrollArea className="max-h-[60vh]">
              <div className="min-w-[900px]">
                <div className="grid grid-cols-8 px-3 py-2 text-xs text-muted-foreground">
                  <div>Timestamp</div>
                  <div>Token</div>
                  <div>Exchange</div>
                  <div>Action</div>
                  <div className="text-right">Montant</div>
                  <div>Statut</div>
                  <div className="col-span-2">ID / Meta</div>
                </div>
                <div className="divide-y">
                  {filtered.map((r, i) => (
                    <div key={(r.id || r.timestamp || i) + "_" + i} className="grid grid-cols-8 items-center px-3 py-3">
                      <div className="truncate">{r.timestamp || "—"}</div>
                      <div className="font-medium">{r.token || "—"}</div>
                      <div>{r.exchange || "—"}</div>
                      <div>
                        <Badge variant={String(r.action).toLowerCase() === "buy" ? "default" : "secondary"}>
                          {ucfirst(r.action) || "—"}
                        </Badge>
                      </div>
                      <div className="text-right">{fmtMoney(r.amount)}</div>
                      <div>
                        <Badge variant="outline">{r.status || "simulated"}</Badge>
                      </div>
                      <div className="col-span-2 text-xs text-muted-foreground truncate">
                        {r.id || r.txid || r.orderId || "—"}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}