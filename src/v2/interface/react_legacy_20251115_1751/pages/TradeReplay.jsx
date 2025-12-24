import React, { useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { ScrollArea } from "../components/ui/scroll-area";
import { Slider } from "../components/ui/slider";
import { Pause, Play, RotateCcw, StepBack, StepForward, TimerReset } from "lucide-react";

// Fichier synchronisé par scripts/sync_data.sh
const TRADES_URL = "/data/trade_simulation.json";

// Helper: format date courte
const fmt = (s) => {
  try { return new Date(s).toLocaleString(); } catch { return s; }
};

// Petite "perf cumulée" naïve à partir des montants (ex: buy -> -amount, sell -> +amount)
function buildCumulativeSeries(trades) {
  let cum = 0;
  const series = trades
    .slice()
    .sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp))
    .map((t) => {
      const delta = t.action === "sell" ? (t.amount || 0) : -(t.amount || 0);
      cum += delta;
      return { t: new Date(t.timestamp), cum };
    });
  return series;
}

export default function TradeReplay() {
  const [rawTrades, setRawTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [speed, setSpeed] = useState(1); // 1x, 2x, 4x…
  const [playing, setPlaying] = useState(false);
  const [idx, setIdx] = useState(0);

  const timerRef = useRef(null);

  // Chargement des trades
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const res = await fetch(`${TRADES_URL}?ts=${Date.now()}`);
        if (res.ok) {
          const json = await res.json();
          if (!cancelled) setRawTrades(Array.isArray(json) ? json : []);
        } else {
          if (!cancelled) setRawTrades([]);
        }
      } catch {
        if (!cancelled) setRawTrades([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Liste des tokens distincts
  const tokens = useMemo(() => {
    const set = new Set(rawTrades.map(t => t.token || "unknown"));
    return ["all", ...Array.from(set)];
  }, [rawTrades]);

  // Filtrage
  const filtered = useMemo(() => {
    let list = rawTrades.slice().sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
    if (token !== "all") list = list.filter(t => (t.token || "unknown") === token);
    if (dateFrom) list = list.filter(t => new Date(t.timestamp) >= new Date(dateFrom));
    if (dateTo) list = list.filter(t => new Date(t.timestamp) <= new Date(dateTo));
    return list;
  }, [rawTrades, token, dateFrom, dateTo]);

  // Série cumulée pour graphe
  const cumSeries = useMemo(() => buildCumulativeSeries(filtered), [filtered]);

  // Contrôles de replay
  const start = () => {
    if (!filtered.length) return;
    setPlaying(true);
  };

  const pause = () => {
    setPlaying(false);
  };

  const reset = () => {
    setPlaying(false);
    setIdx(0);
  };

  const stepForward = () => {
    setIdx((i) => Math.min(i + 1, Math.max(filtered.length - 1, 0)));
  };

  const stepBack = () => {
    setIdx((i) => Math.max(i - 1, 0));
  };

  // Boucle de lecture
  useEffect(() => {
    clearInterval(timerRef.current);
    if (playing && filtered.length > 0) {
      const base = 800; // ms entre deux trades à 1x
      const dt = Math.max(100, base / speed);
      timerRef.current = setInterval(() => {
        setIdx((i) => {
          if (i >= filtered.length - 1) {
            // fin
            clearInterval(timerRef.current);
            return i;
          }
          return i + 1;
        });
      }, dt);
    }
    return () => clearInterval(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, speed, filtered.length]);

  const current = filtered[idx] || null;

  return (
    <div className="p-4 md:p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">Trade Replay</h1>
          <p className="text-sm text-muted-foreground">Rejoue les trades simulés, avec filtres et timeline.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={reset}>
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset
          </Button>
        </div>
      </div>

      {/* Filtres */}
      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Filtres</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="md:col-span-1">
            <Label>Token</Label>
            <Select value={token} onValueChange={setToken}>
              <SelectTrigger><SelectValue placeholder="Token" /></SelectTrigger>
              <SelectContent>
                {tokens.map((t) => (
                  <SelectItem key={t} value={t}>{t}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Du</Label>
            <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div>
            <Label>Au</Label>
            <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
          <div className="flex flex-col">
            <Label>Vitesse: {speed}x</Label>
            <div className="px-1">
              <Slider
                value={[speed]}
                min={0.5}
                max={5}
                step={0.5}
                onValueChange={(v) => setSpeed(v[0])}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Zone de replay */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Timeline & Graph */}
        <Card className="shadow-sm lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Timeline & Cumul</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Timeline simple */}
            <div className="w-full h-2 bg-muted rounded overflow-hidden">
              {/* curseur */}
              <div
                className="h-full bg-primary transition-all"
                style={{
                  width: filtered.length ? `${(idx / (filtered.length - 1)) * 100}%` : "0%",
                }}
              />
            </div>
            <div className="text-xs text-muted-foreground">
              {filtered.length
                ? `${idx + 1}/${filtered.length} • ${fmt(filtered[idx]?.timestamp)}`
                : "Aucun trade pour ces filtres"}
            </div>

            {/* Graph cumulé ultra-lean (SVG) */}
            <div className="w-full h-48 rounded border bg-muted/30 p-2">
              <MiniCumulativeChart series={cumSeries} highlightIndex={idx} />
            </div>

            {/* Contrôles */}
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={stepBack} disabled={!filtered.length || idx <= 0}>
                <StepBack className="w-4 h-4 mr-2" /> Prev
              </Button>
              {playing ? (
                <Button onClick={pause} disabled={!filtered.length}>
                  <Pause className="w-4 h-4 mr-2" /> Pause
                </Button>
              ) : (
                <Button onClick={start} disabled={!filtered.length}>
                  <Play className="w-4 h-4 mr-2" /> Play
                </Button>
              )}
              <Button variant="outline" onClick={stepForward} disabled={!filtered.length || idx >= filtered.length - 1}>
                <StepForward className="w-4 h-4 mr-2" /> Next
              </Button>
              <Button variant="ghost" onClick={() => setIdx(0)} disabled={!filtered.length}>
                <TimerReset className="w-4 h-4 mr-2" /> Début
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Détails du trade courant */}
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Détail du trade</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-sm text-muted-foreground">Chargement…</div>
            ) : !filtered.length ? (
              <div className="text-sm text-muted-foreground">Aucun trade.</div>
            ) : current ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between border-b pb-1">
                  <span className="text-muted-foreground">Date</span>
                  <span className="font-medium">{fmt(current.timestamp)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Token</span>
                  <span className="font-medium">{current.token}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Exchange</span>
                  <span className="font-medium">{current.exchange}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Action</span>
                  <span className={`font-semibold ${current.action === "buy" ? "text-emerald-600" : "text-rose-600"}`}>
                    {current.action?.toUpperCase()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Montant</span>
                  <span className="font-medium">{Number(current.amount || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status</span>
                  <span className="font-medium">{current.status || "n/a"}</span>
                </div>
                {"price" in current && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Prix</span>
                    <span className="font-medium">{current.price}</span>
                  </div>
                )}
                {"pnl" in current && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">PnL</span>
                    <span className={`font-medium ${current.pnl >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                      {current.pnl}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">Sélectionne un trade…</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Liste brute en bas pour debug / audit */}
      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Journal des trades filtrés</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-56 w-full rounded-md border p-3 bg-muted/30">
            <pre className="text-xs leading-relaxed">
              {JSON.stringify(filtered, null, 2)}
            </pre>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}

/** Mini graphe cumulé ultra léger (SVG) */
function MiniCumulativeChart({ series, highlightIndex }) {
  if (!series?.length) {
    return <div className="w-full h-full flex items-center justify-center text-xs text-muted-foreground">—</div>;
  }

  const w = 800;
  const h = 160;
  const pad = 12;

  const xs = series.map(d => d.t.getTime());
  const ys = series.map(d => d.cum);

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const dx = maxX - minX || 1;
  const dy = maxY - minY || 1;

  const xScale = (x) => pad + ((x - minX) / dx) * (w - 2 * pad);
  const yScale = (y) => h - pad - ((y - minY) / dy) * (h - 2 * pad);

  const path = series
    .map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(d.t.getTime())} ${yScale(d.cum)}`)
    .join(" ");

  const hiX =
    highlightIndex >= 0 && highlightIndex < series.length
      ? xScale(series[highlightIndex].t.getTime())
      : null;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-full">
      <rect x="0" y="0" width={w} height={h} fill="transparent" />
      {/* line */}
      <path d={path} fill="none" stroke="currentColor" strokeWidth="2" />
      {/* zero line */}
      {minY < 0 && maxY > 0 && (
        <line
          x1={pad}
          x2={w - pad}
          y1={yScale(0)}
          y2={yScale(0)}
          stroke="currentColor"
          strokeOpacity="0.3"
          strokeDasharray="4 4"
        />
      )}
      {/* highlight cursor */}
      {hiX != null && (
        <line
          x1={hiX}
          x2={hiX}
          y1={pad}
          y2={h - pad}
          stroke="currentColor"
          strokeOpacity="0.5"
        />
      )}
    </svg>
  );
}