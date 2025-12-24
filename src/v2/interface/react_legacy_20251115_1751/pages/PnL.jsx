import React, { useEffect, useMemo, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";
import { Loader2, RefreshCw } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  BarChart,
  Bar,
} from "recharts";

/**
 * Format attendu (public/data/global_performance.json)
 * {
 *   "cumulative_profit": number,
 *   "history": [{ "date": "YYYY-MM-DD", "daily_profit": number }, ...]
 * }
 */
const DATA_URL = "/data/global_performance.json";

const fmt = (n, opt = {}) =>
  typeof n === "number" ? n.toLocaleString(undefined, { maximumFractionDigits: 2, ...opt }) : "—";

const profitColor = (v) => (v > 0 ? "text-green-600" : v < 0 ? "text-red-600" : "text-muted-foreground");

export default function PnL() {
  const [data, setData] = useState({ cumulative_profit: 0, history: [] });
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const res = await fetch(`${DATA_URL}?ts=${Date.now()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();

      const history = (json?.history ?? [])
        .map((d) => ({ date: String(d?.date ?? ""), daily_profit: Number(d?.daily_profit ?? 0) }))
        .sort((a, b) => (a.date > b.date ? 1 : a.date < b.date ? -1 : 0));

      setData({
        cumulative_profit: Number(json?.cumulative_profit ?? 0),
        history,
      });
      setLastUpdated(new Date());
    } catch (e) {
      console.error(e);
      setErr("Impossible de charger /data/global_performance.json");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  // Equity curve (cumul du daily_profit)
  const equity = useMemo(() => {
    let acc = 0;
    return data.history.map((d) => {
      acc += d.daily_profit || 0;
      return { date: d.date, equity: acc, daily_profit: d.daily_profit || 0 };
    });
  }, [data.history]);

  const stats = useMemo(() => {
    const days = data.history.length;
    const total = data.history.reduce((a, d) => a + (d.daily_profit || 0), 0);
    const avg = days ? total / days : 0;
    const wins = data.history.filter((d) => (d.daily_profit || 0) > 0).length;
    const losses = data.history.filter((d) => (d.daily_profit || 0) < 0).length;
    const winRate = days ? (wins / days) * 100 : 0;
    const best = days ? data.history.reduce((m, d) => (d.daily_profit > (m?.daily_profit ?? -Infinity) ? d : m)) : null;
    const worst = days ? data.history.reduce((m, d) => (d.daily_profit < (m?.daily_profit ?? Infinity) ? d : m)) : null;
    return { days, total, avg, wins, losses, winRate, best, worst };
  }, [data.history]);

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">PnL</h1>
          <p className="text-sm text-muted-foreground">
            Cumul global, equity curve et distribution des PnL quotidiens.
          </p>
        </div>
        <Button variant="outline" onClick={reload} disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
          Refresh
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Cumul (global)</CardTitle>
          </CardHeader>
          <CardContent className={`text-2xl font-semibold ${profitColor(data.cumulative_profit)}`}>
            ${fmt(data.cumulative_profit)}
            <div className="text-xs text-muted-foreground mt-1">
              {lastUpdated ? `MAJ ${lastUpdated.toLocaleTimeString()}` : ""}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Total (période)</CardTitle>
          </CardHeader>
          <CardContent className={`text-2xl font-semibold ${profitColor(stats.total)}`}>
            ${fmt(stats.total)}
            <div className="text-xs text-muted-foreground mt-1">{stats.days} jours</div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Moyenne/jour</CardTitle>
          </CardHeader>
          <CardContent className={`text-2xl font-semibold ${profitColor(stats.avg)}`}>${fmt(stats.avg)}</CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Win rate</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {fmt(stats.winRate, { maximumFractionDigits: 1 })}%
            <div className="text-xs text-muted-foreground mt-1">
              {stats.wins} wins / {stats.losses} losses
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Best / Worst</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            <div>
              Best:{" "}
              <span className={profitColor(stats.best?.daily_profit ?? 0)}>
                ${fmt(stats.best?.daily_profit)} {stats.best?.date ? `(${stats.best.date})` : ""}
              </span>
            </div>
            <div>
              Worst:{" "}
              <span className={profitColor(stats.worst?.daily_profit ?? 0)}>
                ${fmt(stats.worst?.daily_profit)} {stats.worst?.date ? `(${stats.worst.date})` : ""}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Equity curve */}
      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Equity Curve</CardTitle>
        </CardHeader>
        <CardContent>
          {err && <div className="rounded-md border border-red-200 bg-red-50 text-red-700 p-3 text-sm mb-3">{err}</div>}
          {loading ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground">
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Chargement…
            </div>
          ) : equity.length === 0 ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground">Aucune donnée.</div>
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer>
                <LineChart data={equity} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip formatter={(v, n) => [`$${fmt(v)}`, n === "equity" ? "Equity" : "Daily PnL"]} />
                  <ReferenceLine y={0} stroke="#999" strokeDasharray="4 4" />
                  <Line type="monotone" dataKey="equity" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Histogramme des daily PnL */}
      {!loading && data.history.length > 0 && (
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Distribution des PnL quotidiens</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 w-full">
              <ResponsiveContainer>
                <BarChart data={data.history} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" hide />
                  <YAxis />
                  <Tooltip formatter={(v) => [`$${fmt(v)}`, "Daily PnL"]} />
                  <ReferenceLine y={0} stroke="#999" strokeDasharray="4 4" />
                  <Bar dataKey="daily_profit" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Table mini */}
            <div className="mt-4">
              <ScrollArea className="w-full">
                <div className="min-w-[620px]">
                  <div className="grid grid-cols-3 px-3 py-2 text-xs font-medium text-muted-foreground border-b">
                    <div>Date</div>
                    <div>Daily PnL</div>
                    <div>Tag</div>
                  </div>
                  {data.history.map((d, i) => (
                    <div key={`${d.date}-${i}`} className="grid grid-cols-3 items-center px-3 py-3 border-b">
                      <div className="text-muted-foreground">{d.date}</div>
                      <div className={`font-medium tabular-nums ${profitColor(d.daily_profit)}`}>
                        ${fmt(d.daily_profit)}
                      </div>
                      <div className="text-xs">
                        {d.daily_profit > 0 ? "Win" : d.daily_profit < 0 ? "Loss" : "Flat"}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}