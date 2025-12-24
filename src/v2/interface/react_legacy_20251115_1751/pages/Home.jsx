// src/v2/interface/react/pages/Home.jsx
import React, { useEffect, useMemo, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from "recharts";

const PATHS = {
  daily: "/data/reports/daily_report.json",
  monthly: "/data/reports/monthly_pnl.json",
  trades: "/data/simulation/trade_simulation.json",
  worst: "/data/risk/worst_trades.json",
};

const fmtMoney = (n, c = "€") =>
  typeof n === "number" && !isNaN(n)
    ? `${c} ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : "—";

const fmtInt = (n) => (Number.isFinite(n) ? n.toLocaleString() : "—");
const fmtDate = (s) => {
  if (!s) return "—";
  const d = new Date(s);
  return isNaN(d.getTime()) ? s : d.toLocaleDateString();
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

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [daily, setDaily] = useState(null);
  const [monthly, setMonthly] = useState(null);
  const [trades, setTrades] = useState([]);
  const [worst, setWorst] = useState([]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    const [d, m, t, w] = await Promise.all([
      fetchJSON(PATHS.daily, {}),
      fetchJSON(PATHS.monthly, {}),
      fetchJSON(PATHS.trades, []),
      fetchJSON(PATHS.worst, []),
    ]);
    setDaily(d || {});
    setMonthly(m || {});
    setTrades(Array.isArray(t) ? t : []);
    setWorst(Array.isArray(w) ? w : []);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const kpis = useMemo(() => {
    const telegram = daily?.telegram_messages ?? daily?.telegram_count ?? 0;
    const twitter = daily?.twitter_posts ?? daily?.twitter_count ?? 0;
    const reddit = daily?.reddit_posts ?? daily?.reddit_count ?? 0;
    const tradeCount = daily?.trade_count ?? trades.length ?? 0;

    const monthTotal =
      monthly?.month_total ??
      monthly?.total ??
      (Array.isArray(monthly?.history)
        ? monthly.history.reduce((acc, x) => acc + (Number(x.daily_profit) || 0), 0)
        : 0);

    return { telegram, twitter, reddit, tradeCount, monthTotal };
  }, [daily, monthly, trades]);

  const chartData = useMemo(() => {
    const history = Array.isArray(monthly?.history) ? monthly.history : [];
    return history.map((d) => ({
      date: d.date,
      pnl: Number(d.daily_profit ?? d.pnl ?? 0),
    }));
  }, [monthly]);

  const recentActivity = useMemo(() => {
    const lastTrades =
      trades
        ?.slice(-5)
        .reverse()
        .map((t) => ({
          type: "trade",
          when: t.timestamp || t.time || t.created_at,
          title: `${(t.action || "—").toUpperCase()} ${t.token || t.symbol || "—"}`,
          meta: `${t.exchange || "—"} • ${fmtMoney(Number(t.amount ?? 0))}`,
        })) || [];

    const worstItems =
      worst?.slice(-3).map((w) => ({
        type: "risk",
        when: w.timestamp || w.time,
        title: `Worst: ${w.token || "—"}`,
        meta: `${w.exchange || "—"} • ${w.action || "—"}`,
      })) || [];

    return [...lastTrades, ...worstItems].slice(0, 8);
  }, [trades, worst]);

  const llmSummary =
    (typeof daily?.llm_summary === "string" && daily.llm_summary) ||
    (typeof daily?.summary === "string" && daily.summary) ||
    "Aucun résumé LLM disponible.";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Bienvenue 👋</h1>
          <p className="text-sm text-muted-foreground">
            Vue d’ensemble rapide des signaux et performances du jour.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={loadAll} disabled={loading}>
            {loading ? "Rafraîchissement…" : "Rafraîchir"}
          </Button>
          <Link to="/dashboard">
            <Button>Aller au Dashboard</Button>
          </Link>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Messages Telegram (jour)</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{fmtInt(kpis.telegram)}</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Tweets (jour)</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{fmtInt(kpis.twitter)}</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Posts Reddit (jour)</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{fmtInt(kpis.reddit)}</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Trades simulés (jour)</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{fmtInt(kpis.tradeCount)}</CardContent>
        </Card>
      </div>

      {/* Quick panels */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Sparkline PnL */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>PnL quotidien — période récente</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            {!chartData.length ? (
              <p className="text-sm text-muted-foreground">
                Aucun fichier <code>{PATHS.monthly}</code> ou pas d’historique disponible.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip
                    formatter={(v) => fmtMoney(v)}
                    labelFormatter={(l) => `Date: ${fmtDate(l)}`}
                  />
                  <Area type="monotone" dataKey="pnl" strokeWidth={2} fillOpacity={0.15} />
                </AreaChart>
              </ResponsiveContainer>
            )}
            <div className="mt-3 text-sm text-muted-foreground">
              Total période: <span className="font-medium">{fmtMoney(kpis.monthTotal)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Shortcuts */}
        <Card>
          <CardHeader>
            <CardTitle>Raccourcis</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            <Link to="/pnl"><Button variant="outline" className="w-full">PnL & Historique</Button></Link>
            <Link to="/profitability"><Button variant="outline" className="w-full">Rentabilité mensuelle</Button></Link>
            <Link to="/best-trades"><Button variant="outline" className="w-full">Best Trades</Button></Link>
            <Link to="/worst-trades"><Button variant="outline" className="w-full">Worst Trades</Button></Link>
            <Link to="/insights"><Button variant="outline" className="w-full">Insights</Button></Link>
            <Link to="/settings"><Button variant="outline" className="w-full">Paramètres</Button></Link>
          </CardContent>
        </Card>
      </div>

      {/* LLM + Activity */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Résumé LLM (jour)</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="max-h-56">
              <p className="whitespace-pre-wrap text-sm leading-6">{llmSummary}</p>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Activité récente</CardTitle>
          </CardHeader>
          <CardContent>
            {!recentActivity.length ? (
              <p className="text-sm text-muted-foreground">Aucune activité récente.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {recentActivity.map((a, i) => (
                  <li key={i} className="flex items-start justify-between gap-4 border-b pb-2 last:border-b-0">
                    <div>
                      <div className="font-medium">{a.title}</div>
                      <div className="text-muted-foreground">{a.meta}</div>
                    </div>
                    <div className="text-xs text-muted-foreground">{fmtDate(a.when)}</div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}