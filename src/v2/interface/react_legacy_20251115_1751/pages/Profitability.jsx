import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";
import { Badge } from "../components/ui/badge";
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
} from "recharts";

/**
 * Format attendu (public/data/monthly_pnl.json)
 * {
 *   "cumulative_profit": number,
 *   "history": [{ "date": "YYYY-MM-DD", "daily_profit": number }, ...]
 * }
 */
const DATA_URL = "/data/monthly_pnl.json";

const fmtNumber = (x, opt = {}) =>
  typeof x === "number"
    ? x.toLocaleString(undefined, { maximumFractionDigits: 2, ...opt })
    : "—";

const profitColor = (p) => (p > 0 ? "text-green-600" : p < 0 ? "text-red-600" : "text-muted-foreground");

export default function Profitability() {
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

      const history = Array.isArray(json?.history) ? json.history : [];
      const normalized = history
        .map((d) => ({
          date: String(d?.date ?? ""),
          daily_profit: Number(d?.daily_profit ?? 0),
        }))
        // on garde l’ordre chrono
        .sort((a, b) => (a.date > b.date ? 1 : a.date < b.date ? -1 : 0));

      setData({
        cumulative_profit: Number(json?.cumulative_profit ?? 0),
        history: normalized,
      });
      setLastUpdated(new Date());
    } catch (e) {
      console.error(e);
      setErr("Impossible de charger /data/monthly_pnl.json");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const stats = useMemo(() => {
    const hist = data.history;
    const days = hist.length;

    const total = hist.reduce((acc, d) => acc + (d.daily_profit || 0), 0);
    const avg = days > 0 ? total / days : 0;
    const wins = hist.filter((d) => (d.daily_profit || 0) > 0).length;
    const winRate = days > 0 ? (wins / days) * 100 : 0;

    const best = hist.reduce(
      (m, d) => ((d.daily_profit ?? -Infinity) > (m?.daily_profit ?? -Infinity) ? d : m),
      days ? hist[0] : null
    );
    const worst = hist.reduce(
      (m, d) => ((d.daily_profit ?? Infinity) < (m?.daily_profit ?? Infinity) ? d : m),
      days ? hist[0] : null
    );

    return {
      days,
      total,
      avg,
      wins,
      winRate,
      best, // {date, daily_profit}
      worst, // {date, daily_profit}
    };
  }, [data]);

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">Profitability</h1>
          <p className="text-sm text-muted-foreground">
            Synthèse des performances quotidiennes et cumul mensuel.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={reload} disabled={loading}>
            {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
            Refresh
          </Button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Cumul (mois)</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className={`text-2xl font-semibold ${profitColor(data.cumulative_profit)}`}>
              ${fmtNumber(data.cumulative_profit)}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Total (jours listés)</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className={`text-2xl font-semibold ${profitColor(stats.total)}`}>${fmtNumber(stats.total)}</div>
            <div className="text-xs text-muted-foreground">{stats.days} jours</div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Moyenne quotidienne</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className={`text-2xl font-semibold ${profitColor(stats.avg)}`}>${fmtNumber(stats.avg)}</div>
            <div className="text-xs text-muted-foreground">{fmtNumber(stats.winRate, { maximumFractionDigits: 1 })}% win</div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Dernière MAJ</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-2xl font-semibold">
              {lastUpdated ? lastUpdated.toLocaleTimeString() : "—"}
            </div>
            <div className="text-xs text-muted-foreground">
              {lastUpdated ? lastUpdated.toLocaleDateString() : ""}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Graph */}
      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Daily PnL</CardTitle>
        </CardHeader>
        <CardContent>
          {err && (
            <div className="rounded-md border border-red-200 bg-red-50 text-red-700 p-3 text-sm mb-3">{err}</div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground">
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Chargement de la rentabilité…
            </div>
          ) : data.history.length === 0 ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground">
              Aucune donnée disponible.
            </div>
          ) : (
            <div className="h-72 w-full">
              <ResponsiveContainer>
                <LineChart data={data.history} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip formatter={(v) => [`$${fmtNumber(v)}`, "Daily PnL"]} />
                  <ReferenceLine y={0} stroke="#999" strokeDasharray="4 4" />
                  <Line type="monotone" dataKey="daily_profit" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Détails table-like */}
      {!loading && data.history.length > 0 && (
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Détail par jour</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="w-full">
              <div className="min-w-[600px]">
                <div className="grid grid-cols-3 px-3 py-2 text-xs font-medium text-muted-foreground border-b">
                  <div>Date</div>
                  <div>Daily PnL</div>
                  <div>Tag</div>
                </div>
                {data.history.map((d, idx) => {
                  const p = d.daily_profit ?? 0;
                  return (
                    <div key={`${d.date}-${idx}`} className="grid grid-cols-3 items-center px-3 py-3 border-b">
                      <div className="text-muted-foreground">{d.date}</div>
                      <div className={`font-medium tabular-nums ${profitColor(p)}`}>${fmtNumber(p)}</div>
                      <div>
                        {p > 0 ? (
                          <Badge className="bg-emerald-100 text-emerald-700 border border-emerald-200">Win</Badge>
                        ) : p < 0 ? (
                          <Badge className="bg-rose-100 text-rose-700 border border-rose-200">Loss</Badge>
                        ) : (
                          <Badge variant="outline">Flat</Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  );
}