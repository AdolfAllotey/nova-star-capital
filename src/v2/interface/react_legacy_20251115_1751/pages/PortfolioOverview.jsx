import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";
import { Loader2, RefreshCw } from "lucide-react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip as RTooltip,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  BarChart,
  Bar,
  ReferenceLine,
} from "recharts";

const DATA_URL = "/data/portfolio_overview.json";

const fmtNum = (n, opt = {}) =>
  typeof n === "number" ? n.toLocaleString(undefined, { maximumFractionDigits: 2, ...opt }) : "—";
const clsPnL = (v) => (v > 0 ? "text-green-600" : v < 0 ? "text-red-600" : "text-muted-foreground");

export default function PortfolioOverview() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [raw, setRaw] = useState({
    as_of: "",
    equity: 0,
    cash: 0,
    positions: [],
    history: [],
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const res = await fetch(`${DATA_URL}?ts=${Date.now()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();

      const positions = Array.isArray(json?.positions) ? json.positions : [];
      const history = Array.isArray(json?.history) ? json.history : [];

      setRaw({
        as_of: String(json?.as_of ?? ""),
        equity: Number(json?.equity ?? 0),
        cash: Number(json?.cash ?? 0),
        positions: positions.map((p) => ({
          token: p?.token ?? p?.name ?? "",
          symbol: p?.symbol ?? (p?.token ? p.token.toUpperCase().slice(0, 5) : ""),
          quantity: Number(p?.quantity ?? 0),
          avg_price: Number(p?.avg_price ?? p?.avgPrice ?? 0),
          last_price: Number(p?.last_price ?? p?.lastPrice ?? 0),
          value: Number(p?.value ?? (Number(p?.quantity ?? 0) * Number(p?.last_price ?? p?.lastPrice ?? 0))),
          pnl: Number(p?.pnl ?? (Number(p?.last_price ?? 0) - Number(p?.avg_price ?? 0)) * Number(p?.quantity ?? 0)),
        })),
        history: history
          .map((h) => ({
            date: String(h?.date ?? ""),
            equity: Number(h?.equity ?? h?.value ?? 0),
          }))
          .filter((h) => h.date),
      });

      setLastUpdated(new Date());
    } catch (e) {
      console.error(e);
      setErr("Impossible de charger /data/portfolio_overview.json");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Dérivés
  const totals = useMemo(() => {
    const invested = raw.positions.reduce((a, p) => a + (p.avg_price * p.quantity || 0), 0);
    const value = raw.positions.reduce((a, p) => a + (p.value || 0), 0);
    const pnl = raw.positions.reduce((a, p) => a + (p.pnl || 0), 0);
    const count = raw.positions.length;
    return { invested, value, pnl, count };
  }, [raw.positions]);

  const alloc = useMemo(() => {
    const sum = raw.positions.reduce((a, p) => a + (p.value || 0), 0) || 1;
    return raw.positions
      .map((p) => ({
        name: p.symbol || p.token || "—",
        value: (p.value || 0),
        weight: ((p.value || 0) / sum) * 100,
      }))
      .sort((a, b) => b.value - a.value);
  }, [raw.positions]);

  const perfPerToken = useMemo(
    () =>
      raw.positions
        .map((p) => ({
          name: p.symbol || p.token || "—",
          pnl: Number(p.pnl || 0),
        }))
        .sort((a, b) => Math.abs(b.pnl) - Math.abs(a.pnl)),
    [raw.positions]
  );

  return (
    <div className="p-4 md:p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">Portfolio Overview</h1>
          <p className="text-sm text-muted-foreground">
            Vue d’ensemble des positions, répartition et équité dans le temps.
          </p>
        </div>
        <Button variant="outline" onClick={loadData} disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
          Refresh
        </Button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Équité</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold tabular-nums">
            ${fmtNum(raw.equity || totals.value + raw.cash)}
            <div className="text-xs text-muted-foreground mt-1">
              {raw.as_of ? `Au ${raw.as_of}` : ""} {lastUpdated ? `• MAJ ${lastUpdated.toLocaleTimeString()}` : ""}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Valeur investie</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold tabular-nums">${fmtNum(totals.invested)}</CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Valeur positions</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold tabular-nums">${fmtNum(totals.value)}</CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">PnL latent</CardTitle>
          </CardHeader>
          <CardContent className={`text-2xl font-semibold tabular-nums ${clsPnL(totals.pnl)}`}>
            ${fmtNum(totals.pnl)}
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground"># Positions</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold tabular-nums">{fmtNum(totals.count)}</CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Allocation */}
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Répartition par actif</CardTitle>
          </CardHeader>
          <CardContent>
            {err && (
              <div className="rounded-md border border-red-200 bg-red-50 text-red-700 p-3 text-sm mb-3">{err}</div>
            )}
            {loading ? (
              <div className="flex items-center justify-center py-16 text-muted-foreground">
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Chargement…
              </div>
            ) : alloc.length === 0 ? (
              <div className="flex items-center justify-center py-16 text-muted-foreground">Aucune position.</div>
            ) : (
              <div className="h-72 w-full">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={alloc} dataKey="value" nameKey="name" outerRadius="80%">
                      {alloc.map((_, i) => (
                        <Cell key={i} />
                      ))}
                    </Pie>
                    <RTooltip
                      formatter={(v, n, d) => [`$${fmtNum(v)} (${fmtNum(d.payload.weight, { maximumFractionDigits: 1 })}%)`, d.payload.name]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Equity curve */}
        <Card className="shadow-sm xl:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Équité dans le temps</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-16 text-muted-foreground">
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Chargement…
              </div>
            ) : raw.history.length === 0 ? (
              <div className="flex items-center justify-center py-16 text-muted-foreground">Aucune donnée.</div>
            ) : (
              <div className="h-72 w-full">
                <ResponsiveContainer>
                  <LineChart data={raw.history} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" fontSize={12} />
                    <YAxis fontSize={12} />
                    <RTooltip formatter={(v) => [`$${fmtNum(v)}`, "Equity"]} />
                    <Line type="monotone" dataKey="equity" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* PnL par token */}
      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">PnL par token</CardTitle>
        </CardHeader>
        <CardContent>
          {loading || perfPerToken.length === 0 ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              {loading ? "Chargement…" : "Aucune position."}
            </div>
          ) : (
            <div className="h-64 w-full">
              <ResponsiveContainer>
                <BarChart data={perfPerToken} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <RTooltip formatter={(v) => [`$${fmtNum(v)}`, "PnL"]} />
                  <ReferenceLine y={0} stroke="#999" strokeDasharray="4 4" />
                  <Bar dataKey="pnl" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Table positions */}
      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Positions</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Chargement…
            </div>
          ) : raw.positions.length === 0 ? (
            <div className="flex items-center justify-center py-12 text-muted-foreground">Aucune position.</div>
          ) : (
            <ScrollArea className="w-full">
              <div className="min-w-[860px]">
                <div className="grid grid-cols-8 px-3 py-2 text-xs font-medium text-muted-foreground border-b">
                  <div>Token</div>
                  <div>Symbol</div>
                  <div className="text-right">Qty</div>
                  <div className="text-right">Avg Price</div>
                  <div className="text-right">Last Price</div>
                  <div className="text-right">Value</div>
                  <div className="text-right">PnL</div>
                  <div className="text-right">PnL %</div>
                </div>
                {raw.positions.map((p, i) => {
                  const invested = (p.avg_price || 0) * (p.quantity || 0) || 0;
                  const pnlPct = invested ? ((p.pnl || 0) / invested) * 100 : 0;
                  return (
                    <div key={`${p.symbol}-${i}`} className="grid grid-cols-8 items-center px-3 py-3 border-b">
                      <div className="truncate">{p.token || "—"}</div>
                      <div className="text-muted-foreground">{p.symbol || "—"}</div>
                      <div className="text-right tabular-nums">{fmtNum(p.quantity)}</div>
                      <div className="text-right tabular-nums">${fmtNum(p.avg_price)}</div>
                      <div className="text-right tabular-nums">${fmtNum(p.last_price)}</div>
                      <div className="text-right tabular-nums">${fmtNum(p.value)}</div>
                      <div className={`text-right tabular-nums ${clsPnL(p.pnl)}`}>${fmtNum(p.pnl)}</div>
                      <div className={`text-right tabular-nums ${clsPnL(pnlPct)}`}>
                        {fmtNum(pnlPct, { maximumFractionDigits: 2 })}%
                      </div>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}