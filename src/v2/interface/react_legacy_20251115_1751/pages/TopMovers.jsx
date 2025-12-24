import React, { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDownWideNarrow, ArrowUpWideNarrow, RotateCcw, RefreshCcw, TrendingDown, TrendingUp, Search } from "lucide-react";

// shadcn/ui
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { ScrollArea } from "../../components/ui/scroll-area";
import { Skeleton } from "../../components/ui/skeleton";

// --- Helpers
const fmtNumber = (n) =>
  typeof n === "number"
    ? n >= 1_000_000_000
      ? (n / 1_000_000_000).toFixed(2) + "B"
      : n >= 1_000_000
      ? (n / 1_000_000).toFixed(2) + "M"
      : n >= 1_000
      ? (n / 1_000).toFixed(2) + "k"
      : String(n)
    : "-";

const fmtPrice = (p) => {
  if (p === null || p === undefined || Number.isNaN(p)) return "-";
  if (p >= 1000) return p.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (p >= 1) return p.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (p >= 0.01) return p.toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  return p.toLocaleString(undefined, { minimumFractionDigits: 6, maximumFractionDigits: 6 });
};

const sinceText = (iso) => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const s = Math.max(0, (Date.now() - d.getTime()) / 1000);
    if (s < 90) return `${Math.round(s)}s`;
    const m = s / 60;
    if (m < 90) return `${Math.round(m)}m`;
    const h = m / 60;
    if (h < 48) return `${Math.round(h)}h`;
    const dd = h / 24;
    return `${Math.round(dd)}d`;
  } catch {
    return "—";
  }
};

const apiURL = () => `${window.location.origin}/market/top-movers`;

const DEFAULT_LIMIT = 20;

export default function TopMovers() {
  const [items, setItems] = useState([]);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [query, setQuery] = useState("");
  const [side, setSide] = useState("all"); // all | winners | losers
  const [sortBy, setSortBy] = useState("change"); // change | volume | symbol
  const [sortDir, setSortDir] = useState("desc"); // asc | desc
  const [limit, setLimit] = useState(DEFAULT_LIMIT);

  const [auto, setAuto] = useState(true);
  const [intervalMs, setIntervalMs] = useState(60_000);
  const timerRef = useRef(null);

  const fetchData = async (signal) => {
    setError("");
    try {
      const res = await fetch(apiURL(), { signal, headers: { "Cache-Control": "no-cache" } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(Array.isArray(data?.items) ? data.items : []);
      setUpdatedAt(data?.updated_at ?? null);
    } catch (e) {
      if (e.name !== "AbortError") setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  };

  // initial load
  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    fetchData(ctrl.signal);
    return () => ctrl.abort();
  }, []);

  // auto refresh
  useEffect(() => {
    if (!auto) return;
    timerRef.current && clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      const ctrl = new AbortController();
      fetchData(ctrl.signal);
      setTimeout(() => ctrl.abort(), 8000);
    }, intervalMs);
    return () => timerRef.current && clearInterval(timerRef.current);
  }, [auto, intervalMs]);

  const toggleSort = (key) => {
    if (sortBy === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortBy(key);
      setSortDir("desc");
    }
  };

  const filtered = useMemo(() => {
    let data = [...items];
    if (side === "winners") data = data.filter((x) => (x.change_24h ?? 0) > 0);
    if (side === "losers") data = data.filter((x) => (x.change_24h ?? 0) < 0);
    if (query) {
      const q = query.trim().toLowerCase();
      data = data.filter((x) => String(x.symbol || "").toLowerCase().includes(q));
    }

    const getKey = (x) => {
      if (sortBy === "volume") return x.volume_24h ?? -Infinity;
      if (sortBy === "symbol") return String(x.symbol || "");
      return x.change_24h ?? -Infinity; // change
    };

    data.sort((a, b) => {
      const av = getKey(a);
      const bv = getKey(b);
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

    return data.slice(0, limit);
  }, [items, side, query, sortBy, sortDir, limit]);

  const ChangeBadge = ({ v }) => {
    const pos = (v ?? 0) >= 0;
    const cl = pos ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500";
    const Icon = pos ? TrendingUp : TrendingDown;
    return (
      <Badge className={`${cl} font-medium px-2 py-1`}> 
        <span className="inline-flex items-center gap-1">
          <Icon className="h-4 w-4" />
          {v === null || v === undefined ? "—" : `${v.toFixed(2)}%`}
        </span>
      </Badge>
    );
  };

  const HeaderStat = ({ label, value, hint }) => (
    <div className="p-3 rounded-xl bg-muted/40 border border-border/40">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold leading-snug">{value}</div>
      {hint ? <div className="text-[11px] text-muted-foreground mt-0.5">{hint}</div> : null}
    </div>
  );

  return (
    <Card className="shadow-sm">
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <CardTitle className="text-xl">Top Movers (24h)</CardTitle>
          <div className="text-xs text-muted-foreground">
            {updatedAt ? (
              <>
                Dernière mise à jour: <span className="font-medium">{updatedAt}</span>
                <span className="ml-2">({sinceText(updatedAt)} ago)</span>
              </>
            ) : (
              "En attente de la première mise à jour…"
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-8 w-44"
              placeholder="Rechercher…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          <Select value={side} onValueChange={setSide}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Filtre" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous</SelectItem>
              <SelectItem value="winners">Gagnants</SelectItem>
              <SelectItem value="losers">Perdants</SelectItem>
            </SelectContent>
          </Select>

          <Select value={String(limit)} onValueChange={(v) => setLimit(Number(v))}>
            <SelectTrigger className="w-28">
              <SelectValue placeholder="Limite" />
            </SelectTrigger>
            <SelectContent>
              {[10, 20, 30, 40, 50].map((v) => (
                <SelectItem key={v} value={String(v)}>
                  {v} lignes
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button variant="outline" size="icon" title="Actualiser" onClick={() => fetchData()}> 
            <RefreshCcw className="h-4 w-4" />
          </Button>

          <Button
            variant={auto ? "default" : "outline"}
            size="sm"
            onClick={() => setAuto((v) => !v)}
            className="gap-2"
          >
            <RotateCcw className="h-4 w-4" />
            {auto ? "Auto ON" : "Auto OFF"}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-2">
          <HeaderStat label="Entrées" value={items.length} hint="après filtre & tri" />
          <HeaderStat label="Tri" value={`${sortBy} · ${sortDir}`} hint="clique sur les entêtes pour changer" />
          <HeaderStat label="Auto refresh" value={auto ? `${intervalMs / 1000}s` : "désactivé"} />
        </div>

        {error ? (
          <div className="text-sm text-rose-500 bg-rose-500/10 border border-rose-500/30 rounded-lg p-3">
            Erreur: {error}
          </div>
        ) : null}

        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : (
          <ScrollArea className="w-full">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[120px]">
                    <button className="inline-flex items-center gap-1" onClick={() => toggleSort("symbol")}>Symbole</button>
                  </TableHead>
                  <TableHead>
                    <button className="inline-flex items-center gap-1" onClick={() => toggleSort("change")}>Var 24h {sortBy === "change" ? (sortDir === "desc" ? <ArrowDownWideNarrow className="h-4 w-4" /> : <ArrowUpWideNarrow className="h-4 w-4" />) : null}</button>
                  </TableHead>
                  <TableHead>
                    <button className="inline-flex items-center gap-1" onClick={() => toggleSort("volume")}>Volume 24h {sortBy === "volume" ? (sortDir === "desc" ? <ArrowDownWideNarrow className="h-4 w-4" /> : <ArrowUpWideNarrow className="h-4 w-4" />) : null}</button>
                  </TableHead>
                  <TableHead>Prix</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((row) => (
                  <TableRow key={`${row.symbol}-${row.price}-${row.volume_24h}`}>
                    <TableCell className="font-medium">{row.symbol}</TableCell>
                    <TableCell>
                      <ChangeBadge v={row.change_24h} />
                    </TableCell>
                    <TableCell className="tabular-nums">{fmtNumber(row.volume_24h)}</TableCell>
                    <TableCell className="tabular-nums">{fmtPrice(row.price)}</TableCell>
                  </TableRow>
                ))}
                {filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-sm text-muted-foreground py-8">
                      Aucun élément à afficher. Modifie tes filtres ou réessaie plus tard.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
