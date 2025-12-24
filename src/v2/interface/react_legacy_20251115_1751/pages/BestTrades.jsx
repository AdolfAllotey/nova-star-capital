// src/v2/interface/react/pages/BestTrades.jsx
import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "../components/ui/card";
import { ScrollArea } from "../components/ui/scroll-area";

export default function BestTrades() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);

  // Charge optionnellement la liste des meilleurs trades
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        // 1) chemin principal
        let res = await fetch("/data/best_trades.json", { cache: "no-store" });
        if (!res.ok) {
          // 2) fallback compat
          res = await fetch("/data/trades/best_trades.json", {
            cache: "no-store",
          });
        }
        if (!res.ok) throw new Error("No best_trades.json available");
        const data = await res.json();
        if (!cancelled) setTrades(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setTrades([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // Tri décroissant par PnL
  const sorted = useMemo(() => {
    return [...trades].sort((a, b) => (Number(b.pnl) || 0) - (Number(a.pnl) || 0));
  }, [trades]);

  const topSummary = useMemo(() => {
    if (!sorted.length) return { count: 0, total: 0, avg: 0 };
    const total = sorted.reduce((s, t) => s + (Number(t.pnl) || 0), 0);
    return { count: sorted.length, total, avg: total / sorted.length };
  }, [sorted]);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Meilleurs trades</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="rounded-2xl shadow-sm">
          <CardContent className="p-6">
            <div className="text-xs text-muted-foreground">Nombre</div>
            <div className="text-2xl font-semibold">{topSummary.count}</div>
          </CardContent>
        </Card>
        <Card className="rounded-2xl shadow-sm">
          <CardContent className="p-6">
            <div className="text-xs text-muted-foreground">PNL total</div>
            <div className="text-2xl font-semibold">
              {formatCurrency(topSummary.total)}
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-2xl shadow-sm">
          <CardContent className="p-6">
            <div className="text-xs text-muted-foreground">PNL moyen</div>
            <div className="text-2xl font-semibold">
              {formatCurrency(topSummary.avg)}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border rounded-2xl shadow-sm">
        <CardContent className="p-0">
          {loading ? (
            <div className="p-6 text-sm text-muted-foreground">Chargement…</div>
          ) : sorted.length === 0 ? (
            <div className="p-6 text-sm text-muted-foreground">
              Aucun meilleur trade trouvé. Ajoute{" "}
              <code className="mx-1 px-1 py-0.5 rounded bg-muted text-xs">
                public/data/best_trades.json
              </code>{" "}
              via ton script de sync.
            </div>
          ) : (
            <ScrollArea className="max-h-[70vh]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-background/80 backdrop-blur">
                  <tr className="[&>th]:px-4 [&>th]:py-3 [&>th]:text-left [&>th]:font-medium text-muted-foreground">
                    <th>Token</th>
                    <th>Exchange</th>
                    <th>Action</th>
                    <th>Montant</th>
                    <th>PNL</th>
                    <th>Horodatage</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {sorted.map((t, i) => (
                    <tr key={i} className="[&>td]:px-4 [&>td]:py-3">
                      <td className="font-medium capitalize">
                        {t.token ?? "-"}
                      </td>
                      <td className="text-muted-foreground">
                        {t.exchange ?? "-"}
                      </td>
                      <td>{t.action ?? "-"}</td>
                      <td>{formatCurrency(t.amount)}</td>
                      <td className={(Number(t.pnl) || 0) >= 0 ? "text-green-600" : "text-red-600"}>
                        {formatCurrency(t.pnl)}
                      </td>
                      <td className="text-muted-foreground">
                        {formatDate(t.timestamp)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      <Card className="border rounded-2xl shadow-sm">
        <CardContent className="p-6 space-y-2 text-sm text-muted-foreground">
          <p>Format attendu pour <code className="mx-1 px-1 py-0.5 rounded bg-muted text-xs">best_trades.json</code> :</p>
          <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
{`[
  {
    "token": "solana",
    "exchange": "binance",
    "timestamp": "2025-08-08T12:34:56Z",
    "amount": 1000,
    "action": "sell",
    "pnl": 245.30
  }
]`}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}

// Utils
function formatCurrency(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "-";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 2,
    }).format(n);
  } catch {
    return `${n.toFixed(2)} €`;
  }
}
function formatDate(v) {
  if (!v) return "-";
  try {
    const d = new Date(v);
    if (isNaN(d.getTime())) return String(v);
    return d.toLocaleString();
  } catch {
    return String(v);
  }
}