// src/v2/interface/react/pages/WorstTrades.jsx
import React, { useEffect, useMemo, useState, useCallback } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "../components/ui/select";
import { Download, RefreshCw, AlertTriangle, ArrowUpDown } from "lucide-react";

const WORST_URL = "/data/risk/worst_trades.json";

const fmtDate = (iso) => {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString();
};

const toCSV = (rows) => {
  if (!rows?.length) return "token,exchange,timestamp,amount,action,status\n";
  const header = ["token", "exchange", "timestamp", "amount", "action", "status"];
  const lines = [header.join(",")];
  for (const r of rows) {
    lines.push([
      r.token ?? "",
      r.exchange ?? "",
      r.timestamp ?? "",
      r.amount ?? "",
      r.action ?? "",
      r.status ?? "",
    ].map((v) => `"${String(v).replace(/"/g, '""')}"`).join(","));
  }
  return lines.join("\n");
};

export default function WorstTrades() {
  const [data, setData] = useState([]);
  const [raw, setRaw] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  // Filtres
  const [q, setQ] = useState(""); // recherche texte
  const [token, setToken] = useState("all");
  const [exchange, setExchange] = useState("all");
  const [action, setAction] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  // Tri
  const [sortKey, setSortKey] = useState("timestamp");
  const [sortDir, setSortDir] = useState("desc");

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const r = await fetch(WORST_URL, { cache: "no-store" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = await r.json();
      setRaw(j);
      // j peut être {trades:[...]} ou [...]
      const rows = Array.isArray(j) ? j : Array.isArray(j?.trades) ? j.trades : [];
      setData(rows);
    } catch (e) {
      setErr(`Impossible de charger les pires trades : ${e?.message ?? e}`);
      setData([]);
      setRaw(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // valeurs uniques pour filtres
  const tokens = useMemo(() => Array.from(new Set(data.map(d => d.token).filter(Boolean))).sort(), [data]);
  const exchanges = useMemo(() => Array.from(new Set(data.map(d => d.exchange).filter(Boolean))).sort(), [data]);
  const actions = useMemo(() => Array.from(new Set(data.map(d => d.action).filter(Boolean))).sort(), [data]);

  const filtered = useMemo(() => {
    let rows = [...data];

    if (q.trim()) {
      const s = q.toLowerCase();
      rows = rows.filter(r =>
        (r.token ?? "").toLowerCase().includes(s) ||
        (r.exchange ?? "").toLowerCase().includes(s) ||
        (r.status ?? "").toLowerCase().includes(s) ||
        (r.action ?? "").toLowerCase().includes(s)
      );
    }
    if (token !== "all") rows = rows.filter(r => r.token === token);
    if (exchange !== "all") rows = rows.filter(r => r.exchange === exchange);
    if (action !== "all") rows = rows.filter(r => r.action === action);

    const fromT = dateFrom ? new Date(dateFrom).getTime() : null;
    const toT = dateTo ? (new Date(dateTo).getTime() + 24 * 3600 * 1000 - 1) : null;
    if (fromT) rows = rows.filter(r => new Date(r.timestamp).getTime() >= fromT);
    if (toT) rows = rows.filter(r => new Date(r.timestamp).getTime() <= toT);

    rows.sort((a, b) => {
      const A = a[sortKey];
      const B = b[sortKey];
      let cmp = 0;
      if (sortKey === "amount") {
        cmp = (Number(A) || 0) - (Number(B) || 0);
      } else if (sortKey === "timestamp") {
        cmp = new Date(A).getTime() - new Date(B).getTime();
      } else {
        cmp = String(A ?? "").localeCompare(String(B ?? ""));
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return rows;
  }, [data, q, token, exchange, action, dateFrom, dateTo, sortKey, sortDir]);

  // Mini‑stats
  const stats = useMemo(() => {
    const total = filtered.length;
    const totalAmount = filtered.reduce((s, r) => s + (Number(r.amount) || 0), 0);
    const topTokens = Object.entries(filtered.reduce((acc, r) => {
      if (r.token) acc[r.token] = (acc[r.token] || 0) + 1;
      return acc;
    }, {})).sort((a, b) => b[1] - a[1]).slice(0, 3);
    return { total, totalAmount, topTokens };
  }, [filtered]);

  const toggleSort = (k) => {
    if (sortKey === k) setSortDir(d => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(k);
      setSortDir("asc");
    }
  };

  const exportCSV = () => {
    const csv = toCSV(filtered);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const ts = new Date().toISOString().slice(0, 10);
    a.download = `worst_trades_${ts}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const Th = ({ label, k, grow }) => (
    <th className={`px-3 py-2 text-left text-sm font-medium text-gray-600 ${grow ? "w-full" : "whitespace-nowrap"}`}>
      <button onClick={() => toggleSort(k)} className="inline-flex items-center gap-1 hover:underline">
        {label}
        <ArrowUpDown className="w-4 h-4" />
      </button>
    </th>
  );

  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Pires trades</h1>
        <div className="flex items-center gap-2">
          <Button onClick={load} variant="outline" disabled={loading} className="gap-2">
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Rafraîchir
          </Button>
          <Button onClick={exportCSV} className="gap-2">
            <Download className="w-4 h-4" />
            Export CSV
          </Button>
        </div>
      </div>

      {err && (
        <div className="flex items-center gap-2 text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 rounded">
          <AlertTriangle className="w-4 h-4" />
          <span>{err}</span>
        </div>
      )}

      {/* Filtres */}
      <Card>
        <CardHeader>
          <CardTitle>Filtres</CardTitle>
        </CardHeader>
        <CardContent className="grid md:grid-cols-6 gap-3">
          <div className="md:col-span-2">
            <div className="text-xs text-muted-foreground mb-1">Recherche</div>
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="token, exchange, action, statut..." />
          </div>

          <div>
            <div className="text-xs text-muted-foreground mb-1">Token</div>
            <Select value={token} onValueChange={setToken}>
              <SelectTrigger><SelectValue placeholder="Tous" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous</SelectItem>
                {tokens.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div>
            <div className="text-xs text-muted-foreground mb-1">Exchange</div>
            <Select value={exchange} onValueChange={setExchange}>
              <SelectTrigger><SelectValue placeholder="Tous" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous</SelectItem>
                {exchanges.map(ex => <SelectItem key={ex} value={ex}>{ex}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div>
            <div className="text-xs text-muted-foreground mb-1">Action</div>
            <Select value={action} onValueChange={setAction}>
              <SelectTrigger><SelectValue placeholder="Toutes" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Toutes</SelectItem>
                {actions.map(a => <SelectItem key={a} value={a}>{a}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div>
            <div className="text-xs text-muted-foreground mb-1">Du</div>
            <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-1">Au</div>
            <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid md:grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Nombre de trades</div>
            <div className="text-2xl font-semibold">{stats.total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Montant total</div>
            <div className="text-2xl font-semibold">
              {stats.totalAmount.toLocaleString(undefined, { maximumFractionDigits: 2 })} €
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Top tokens</div>
            <div className="text-sm">
              {stats.topTokens.length
                ? stats.topTokens.map(([t, n]) => `${t} (${n})`).join(" · ")
                : "—"}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tableau */}
      <Card>
        <CardHeader>
          <CardTitle>Liste des pires trades ({filtered.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="max-h-[60vh]">
            <table className="min-w-full text-sm">
              <thead className="sticky top-0 bg-white border-b">
                <tr>
                  <Th label="Token" k="token" />
                  <Th label="Exchange" k="exchange" />
                  <Th label="Date" k="timestamp" />
                  <Th label="Montant" k="amount" />
                  <Th label="Action" k="action" />
                  <Th label="Statut" k="status" />
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td className="px-3 py-6 text-center text-muted-foreground" colSpan={6}>
                      Aucune ligne à afficher.
                    </td>
                  </tr>
                ) : (
                  filtered.map((r, i) => (
                    <tr key={`${r.token}-${r.timestamp}-${i}`} className="border-b hover:bg-gray-50">
                      <td className="px-3 py-2 font-medium">{r.token ?? "-"}</td>
                      <td className="px-3 py-2">{r.exchange ?? "-"}</td>
                      <td className="px-3 py-2">{fmtDate(r.timestamp)}</td>
                      <td className="px-3 py-2">{(Number(r.amount) || 0).toLocaleString()}</td>
                      <td className="px-3 py-2 uppercase">{r.action ?? "-"}</td>
                      <td className="px-3 py-2">{r.status ?? "-"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Debug optionnel */}
      <details className="text-xs text-muted-foreground">
        <summary>Debug : JSON brut</summary>
        <pre className="p-3 bg-gray-50 border rounded overflow-auto">{JSON.stringify(raw ?? data, null, 2)}</pre>
      </details>
    </div>
  );
}