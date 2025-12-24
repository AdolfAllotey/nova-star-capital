// src/v2/interface/react/pages/CostTracker.jsx
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";

const DATA_URL = "/data/costs/cost_tracker.json";

const fmtMoney = (n, currency = "€") =>
  typeof n === "number" && !isNaN(n)
    ? `${currency} ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : "-";

const fmtDate = (s) => {
  if (!s) return "-";
  const d = new Date(s);
  return isNaN(d.getTime()) ? s : d.toLocaleDateString();
};

export default function CostTracker() {
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState([]);

  const fetchJSON = async (url, fallback = []) => {
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) return fallback;
      return await res.json();
    } catch {
      return fallback;
    }
  };

  const loadCosts = useCallback(async () => {
    setLoading(true);
    const data = await fetchJSON(DATA_URL, []);
    // Supporte deux formats :
    // 1) tableau brut d'items
    // 2) { items: [...], month_total: number }
    const items = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : [];
    setRows(items);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadCosts();
  }, [loadCosts]);

  const { total, avgPerDay, daysSpan } = useMemo(() => {
    if (!rows.length) return { total: 0, avgPerDay: 0, daysSpan: 0 };
    const totalCost = rows.reduce((acc, r) => acc + (Number(r.cost_eur ?? r.cost ?? 0) || 0), 0);

    // approx nombre de jours couverts par les lignes (min/max dates)
    const dates = rows
      .map((r) => new Date(r.date || r.timestamp || r.created_at || r.day || r.period_start))
      .filter((d) => !isNaN(d.getTime()))
      .sort((a, b) => a - b);

    let spanDays = 0;
    if (dates.length >= 2) {
      const ms = dates[dates.length - 1] - dates[0];
      spanDays = Math.max(1, Math.round(ms / (1000 * 60 * 60 * 24)) + 1);
    } else {
      spanDays = rows.length ? 1 : 0;
    }

    const avg = spanDays ? totalCost / spanDays : 0;

    return { total: totalCost, avgPerDay: avg, daysSpan: spanDays };
  }, [rows]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Cost Tracker</h1>
        <Button variant="secondary" onClick={loadCosts} disabled={loading}>
          {loading ? "Rafraîchissement…" : "Rafraîchir"}
        </Button>
      </div>

      {/* KPI */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Coût total (période détectée)</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{fmtMoney(total)}</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Coût moyen / jour</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">
            {fmtMoney(avgPerDay)}{" "}
            <span className="text-xs text-muted-foreground align-middle">({daysSpan} jour(s))</span>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Nombre d’entrées</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{rows.length || "-"}</CardContent>
        </Card>
      </div>

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>Détails des coûts</CardTitle>
        </CardHeader>
        <CardContent>
          {!rows.length ? (
            <p className="text-sm text-muted-foreground">
              Aucun fichier trouvé à <code>{DATA_URL}</code> ou aucune donnée à afficher.
            </p>
          ) : (
            <ScrollArea className="max-h-[60vh]">
              <div className="w-full overflow-x-auto rounded-lg border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/40">
                    <tr>
                      <th className="text-left px-3 py-2 font-medium">Date</th>
                      <th className="text-left px-3 py-2 font-medium">Fournisseur</th>
                      <th className="text-left px-3 py-2 font-medium">Type</th>
                      <th className="text-right px-3 py-2 font-medium">Requêtes</th>
                      <th className="text-right px-3 py-2 font-medium">Coût (€)</th>
                      <th className="text-left px-3 py-2 font-medium">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r, idx) => {
                      const provider = r.provider || r.vendor || r.service || "—";
                      const type = r.type || r.category || r.product || "—";
                      const req =
                        r.requests ??
                        r.tokens ??
                        r.calls ??
                        r.usage ??
                        r.quantity ??
                        null;
                      const cost = Number(r.cost_eur ?? r.cost ?? r.amount ?? 0) || 0;
                      const notes = r.notes || r.comment || "";
                      const date =
                        r.date || r.timestamp || r.created_at || r.day || r.period_start || "";

                      return (
                        <tr key={idx} className="border-t hover:bg-muted/20">
                          <td className="px-3 py-2">{fmtDate(date)}</td>
                          <td className="px-3 py-2">{provider}</td>
                          <td className="px-3 py-2">{type}</td>
                          <td className="px-3 py-2 text-right">{req ?? "—"}</td>
                          <td className="px-3 py-2 text-right">{fmtMoney(cost)}</td>
                          <td className="px-3 py-2">{notes || "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot className="bg-muted/30">
                    <tr>
                      <td className="px-3 py-2 font-semibold" colSpan={4}>
                        Total
                      </td>
                      <td className="px-3 py-2 text-right font-semibold">{fmtMoney(total)}</td>
                      <td />
                    </tr>
                  </tfoot>
                </table>
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Raw JSON (debug) */}
      <Card>
        <CardHeader>
          <CardTitle>JSON brut (debug)</CardTitle>
        </CardHeader>
        <CardContent>
          {rows.length ? (
            <pre className="text-xs bg-muted/30 rounded-md p-3 overflow-x-auto">
{JSON.stringify(rows, null, 2)}
            </pre>
          ) : (
            <p className="text-sm text-muted-foreground">—</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}