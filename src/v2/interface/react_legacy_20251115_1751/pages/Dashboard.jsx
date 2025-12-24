import React, { useEffect, useMemo, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";
import { RefreshCw, TrendingUp, TrendingDown, Activity } from "lucide-react";

// Endpoints servis par Vite (public/data/…)
const REPORT_URL = "/data/reports/daily_report.json";
const TRADES_URL = "/data/simulation/trade_simulation.json";

const fmtDate = (iso) => {
  try {
    const d = new Date(iso);
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d);
  } catch {
    return iso || "-";
  }
};

export default function Dashboard() {
  const [report, setReport] = useState(null);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [intervalSec, setIntervalSec] = useState(60);
  const [lastFetchAt, setLastFetchAt] = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const [r1, r2] = await Promise.all([
        fetch(REPORT_URL, { cache: "no-store" }),
        fetch(TRADES_URL, { cache: "no-store" }),
      ]);

      if (!r1.ok) throw new Error(`Report HTTP ${r1.status}`);
      if (!r2.ok) throw new Error(`Trades HTTP ${r2.status}`);

      const rep = await r1.json().catch(() => {
        throw new Error("Report JSON invalide");
      });
      const trs = await r2.json().catch(() => {
        throw new Error("Trades JSON invalide");
      });

      setReport(rep || {});
      setTrades(Array.isArray(trs) ? trs.slice().reverse() : []);
      setLastFetchAt(new Date());
    } catch (e) {
      setErr(e?.message || "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  useEffect(() => {
    if (!intervalSec || intervalSec < 5) return;
    const id = setInterval(fetchAll, intervalSec * 1000);
    return () => clearInterval(id);
  }, [intervalSec, fetchAll]);

  const dateStr = useMemo(() => {
    return report?.date ? report.date : "-";
  }, [report]);

  const topTokens = useMemo(() => report?.top_tokens ?? [], [report]);
  const worstTokens = useMemo(() => report?.worst_tokens ?? [], [report]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Résumé du jour</h1>
        <div className="ml-auto flex items-center gap-3">
          <label className="text-sm text-muted-foreground">Auto‑refresh</label>
          <input
            type="number"
            min={5}
            step={5}
            value={intervalSec}
            onChange={(e) => setIntervalSec(Number(e.target.value || 0))}
            className="w-20 rounded-md border px-2 py-1 text-sm bg-background"
          />
          <span className="text-sm text-muted-foreground">s</span>
          <Button size="sm" onClick={fetchAll}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Rafraîchir
          </Button>
        </div>
      </div>

      {/* Ligne 1 : Date + KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card className="md:col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Date</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-medium">{dateStr}</div>
            <div className="text-xs text-muted-foreground">
              {lastFetchAt ? `MAJ ${fmtDate(lastFetchAt)}` : ""}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">PnL total</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{report?.pnl_total ?? "N/A"}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Win rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{report?.win_rate ?? "N/A"}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Telegram</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{report?.telegram_messages ?? 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Twitter</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{report?.twitter_posts ?? 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Ligne 2 : Reddit + Top/Worst tokens */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Reddit
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{report?.reddit_posts ?? 0}</div>
            {loading && <div className="text-xs text-muted-foreground mt-1">Chargement…</div>}
            {err && <div className="text-xs text-red-500 mt-1">Erreur : {err}</div>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Top tokens
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topTokens.length === 0 ? (
              <div className="text-sm text-muted-foreground">Aucun token en tête.</div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {topTokens.map((t) => (
                  <span
                    key={t}
                    className="px-2 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200"
                  >
                    {t.toUpperCase()}
                  </span>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
              <TrendingDown className="h-4 w-4" />
              Worst tokens
            </CardTitle>
          </CardHeader>
          <CardContent>
            {worstTokens.length === 0 ? (
              <div className="text-sm text-muted-foreground">Aucun token en queue.</div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {worstTokens.map((t) => (
                  <span
                    key={t}
                    className="px-2 py-1 rounded-full text-xs font-medium bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-200"
                  >
                    {t.toUpperCase()}
                  </span>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Ligne 3 : Derniers trades */}
      <div className="grid grid-cols-1 gap-4">
        <Card>
          <CardHeader className="pb-2 flex items-center justify-between">
            <CardTitle className="text-sm text-muted-foreground">
              Derniers trades simulés
            </CardTitle>
            <div className="text-xs text-muted-foreground">source: {TRADES_URL}</div>
          </CardHeader>
          <CardContent>
            {trades.length === 0 ? (
              <div className="text-sm text-muted-foreground">Aucun trade simulé.</div>
            ) : (
              <ScrollArea className="h-60">
                <ul className="space-y-3 pr-2">
                  {trades.slice(0, 20).map((t, i) => (
                    <li
                      key={`${t.timestamp}-${t.token}-${i}`}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                            t.action?.toLowerCase() === "buy"
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200"
                              : "bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-200"
                          }`}
                        >
                          {t.action?.toUpperCase() || "-"}
                        </span>
                        <div className="text-sm">
                          <div className="font-medium">{(t.token || "-").toUpperCase()}</div>
                          <div className="text-xs text-muted-foreground">
                            @{t.exchange || "-"} • Montant :{" "}
                            {typeof t.amount === "number"
                              ? new Intl.NumberFormat("fr-FR").format(t.amount)
                              : t.amount || "-"}
                          </div>
                        </div>
                      </div>
                      <div className="text-xs text-muted-foreground">{fmtDate(t.timestamp)}</div>
                    </li>
                  ))}
                </ul>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Debug optionnel */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-muted-foreground">Debug : JSON rapport brut</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="text-xs whitespace-pre-wrap">
            {report ? JSON.stringify(report, null, 2) : "—"}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}