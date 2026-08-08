import { buildApiUrl } from "../../lib/apiBase";
import React, { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

const PERIODS = ["1D", "7D", "30D", "1Y", "5Y", "ALL"];
const SERIES = ["TOTAL", "CRYPTO", "OFFENSIVE", "LT"];
const VIEW_MODES = ["LINE", "STACKED"];

const COMPONENT_META = {
  crypto: { label: "Crypto", color: "#22c55e" },
  offensive: { label: "Offensive", color: "#38bdf8" },
  defensive: { label: "Defensive", color: "#a78bfa" },
  bonds: { label: "Bonds", color: "#f59e0b" },
  metals: { label: "Metals", color: "#facc15" },
  lt: { label: "Long Term", color: "#e879f9" },
  options_us: { label: "Options US", color: "#fb7185" },
};

const strategyKeyToComponent = {
  crypto: "crypto",
  equities_offensive: "offensive",
  defensive: "defensive",
  bonds: "bonds",
  metals: "metals",
  long_term: "lt",
  options_us: "options_us",
};

function fmtEUR(v) {
  const val = Number(v || 0);
  const sign = val > 0 ? "+" : val < 0 ? "-" : "";
  return `${sign}${Math.abs(val).toFixed(2).replace(".", ",")} €`;
}

function fmtEURUnsigned(v) {
  return `${Number(v || 0).toFixed(2).replace(".", ",")} €`;
}

function fmtPct(v) {
  return `${Number(v || 0).toFixed(1).replace(".", ",")} %`;
}

function periodSlice(points, period) {
  if (!Array.isArray(points)) return [];
  if (period === "1D") return points.slice(-2);
  if (period === "7D") return points.slice(-7);
  if (period === "30D") return points.slice(-30);
  if (period === "1Y") return points.slice(-365);
  if (period === "5Y") return points.slice(-1825);
  return points;
}

function toneClass(v) {
  return Number(v || 0) >= 0 ? "text-emerald-400" : "text-red-400";
}

function componentTone(name, value) {
  if (Number(value || 0) === 0) return "text-zinc-400";
  if (["crypto", "offensive", "lt"].includes(name)) return "text-zinc-100";
  return "text-zinc-300";
}

function prettyName(name) {
  return COMPONENT_META[name]?.label || name;
}

function TotalTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;

  const row = payload[0]?.payload || {};
  const components = row?.components || {};

  return (
    <div className="rounded-2xl border border-zinc-700 bg-zinc-950/95 px-4 py-3 shadow-2xl">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-zinc-100">
        Total: {fmtEURUnsigned(row?.cumulative_profit || 0)}
      </div>

      <div className="mt-3 space-y-1">
        {Object.entries(components).map(([name, value]) => (
          <div key={name} className="flex items-center justify-between gap-6 text-xs">
            <span className="text-zinc-400">{prettyName(name)}</span>
            <span className={`tabular-nums ${componentTone(name, value)}`}>
              {fmtEURUnsigned(value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function EquityCurve({ strategies = [], global = {} }) {
  const [seriesKey, setSeriesKey] = useState("TOTAL");
  const [period, setPeriod] = useState("ALL");
  const [viewMode, setViewMode] = useState("LINE");
  const [points, setPoints] = useState([]);
  const [meta, setMeta] = useState({});
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError("");
        let res;

        if (seriesKey === "TOTAL") {
          res = await fetch(buildApiUrl("/api/total-curve"));
        } else if (seriesKey === "LT") {
          res = await fetch(buildApiUrl("/api/lt-curve"));
        } else if (seriesKey === "CRYPTO") {
          res = await fetch(buildApiUrl("/api/brick-curve/crypto"));
        } else if (seriesKey === "OFFENSIVE") {
          res = await fetch(buildApiUrl("/api/brick-curve/offensive"));
        }

        if (!res || !res.ok) {
          throw new Error(`curve HTTP ${res?.status || "n/a"}`);
        }

        const payload = await res.json();
        if (!cancelled) {
          setPoints(Array.isArray(payload?.points) ? payload.points : []);
          setMeta(payload || {});
        }
      } catch (e) {
        if (!cancelled) {
          console.error("Equity curve fetch failed", e);
          setError("Unable to load equity curve.");
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [seriesKey]);

  const visiblePoints = useMemo(() => periodSlice(points, period), [points, period]);

  const finalPoint = useMemo(() => {
    if (!visiblePoints.length) return null;
    return visiblePoints[visiblePoints.length - 1];
  }, [visiblePoints]);

  const firstPoint = useMemo(() => {
    if (!visiblePoints.length) return null;
    return visiblePoints[0];
  }, [visiblePoints]);

  const finalValue = useMemo(() => {
    if (!finalPoint) return 0;
    return Number(finalPoint?.cumulative_profit || 0);
  }, [finalPoint]);

  const firstValue = useMemo(() => {
    if (!firstPoint) return 0;
    return Number(firstPoint?.cumulative_profit || 0);
  }, [firstPoint]);

  const dailyChange = useMemo(() => {
    if (!finalPoint) return 0;
    if (typeof finalPoint?.daily_change === "number") return finalPoint.daily_change;
    return Number(finalValue - firstValue);
  }, [finalPoint, finalValue, firstValue]);

  const attributionRows = useMemo(() => {
    const componentPnlMap = (Array.isArray(strategies) ? strategies : []).reduce((acc, s) => {
      const componentKey = strategyKeyToComponent[s?.key];
      if (!componentKey) return acc;
      acc[componentKey] = Number(s?.pnl || 0);
      return acc;
    }, {});

    const total = Object.values(componentPnlMap).reduce((sum, v) => sum + Number(v || 0), 0);

    return Object.entries(componentPnlMap)
      .map(([name, value]) => {
        const numeric = Number(value || 0);
        const pct = total !== 0 ? (numeric / total) * 100 : 0;

        return {
          key: name,
          label: prettyName(name),
          value: numeric,
          delta: 0,
          pct,
          color: COMPONENT_META[name]?.color || "#71717a",
        };
      })
      .sort((a, b) => b.value - a.value);
  }, [strategies]);

  const periodChange = useMemo(() => Number(finalValue - firstValue), [finalValue, firstValue]);

  const positive = finalValue >= 0;
  const strokeColor = positive ? "#34d399" : "#f87171";
  const topFill = positive ? "rgba(52,211,153,0.30)" : "rgba(248,113,113,0.30)";
  const bottomFill = positive ? "rgba(52,211,153,0.02)" : "rgba(248,113,113,0.02)";

  const lastRefresh = meta?.updated_at || meta?.timestamp || meta?.ts || global?.lastRefresh || "n/a";


  const strategyRows = Array.isArray(strategies) ? strategies : [];

  const realSources = strategyRows
    .filter((s) => !["NOT_DEPLOYED", "DISABLED", "OFF"].includes(String(s?.status || "").toUpperCase()))
    .map((s) => strategyKeyToComponent[s?.key])
    .filter(Boolean);

  const pendingSources = strategyRows
    .filter((s) => ["NOT_DEPLOYED", "DISABLED", "OFF"].includes(String(s?.status || "").toUpperCase()))
    .map((s) => strategyKeyToComponent[s?.key])
    .filter(Boolean);

  const latestComponents = strategyRows.reduce((acc, s) => {
    const componentKey = strategyKeyToComponent[s?.key];
    if (!componentKey) return acc;
    const exposure = Number(s?.targetExposure || 0);
    const capital = Number(global?.capitalObserved || 0);
    acc[componentKey] = Number((exposure * capital).toFixed(2));
    return acc;
  }, {});


  if (error) {
    return <div className="h-56 flex items-center justify-center text-sm text-red-400">{error}</div>;
  }

  if (!points.length) {
    return <div className="h-56 flex items-center justify-center text-sm text-zinc-500">Loading equity curve...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-[0.16em] text-zinc-500">
            {seriesKey} Curve
          </div>
          <div className={`mt-1 text-2xl font-semibold tabular-nums ${toneClass(finalValue)}`}>
            {fmtEUR(finalValue)}
          </div>
          {seriesKey === "TOTAL" && (
            <div className="mt-2 flex items-center gap-3">
              <div className="text-sm text-zinc-400">Daily</div>
              <div className={`text-sm font-medium ${toneClass(dailyChange)}`}>
                {fmtEUR(dailyChange)}
              </div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-2 text-right sm:grid-cols-3 sm:gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
              {period === "1D" ? "Daily Change" : `${period} Change`}
            </div>
            <div className={`mt-1 text-sm font-semibold tabular-nums ${toneClass(periodChange)}`}>
              {fmtEUR(periodChange)}
            </div>
          </div>

          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">Displayed Points</div>
            <div className="mt-1 text-sm font-semibold text-zinc-300">{visiblePoints.length}</div>
          </div>

          <div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">Last Refresh</div>
            <div className="mt-1 text-sm font-medium text-zinc-300">
              {String(lastRefresh).slice(0, 19).replace("T", " ")}
            </div>
          </div>
        </div>
      </div>

      {seriesKey === "TOTAL" && (
        <>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-emerald-500/15 bg-emerald-500/5 px-4 py-3">
              <div className="text-[10px] uppercase tracking-[0.16em] text-emerald-300/80">Real Sources</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {realSources.map((x) => (
                  <span
                    key={x}
                    className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-300"
                  >
                    {x}
                  </span>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-amber-500/15 bg-amber-500/5 px-4 py-3">
              <div className="text-[10px] uppercase tracking-[0.16em] text-amber-300/80">Pending Sources</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {pendingSources.map((x) => (
                  <span
                    key={x}
                    className="rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-300"
                  >
                    {x}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-800/70 bg-zinc-950/30 p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
                Portfolio Composition
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {VIEW_MODES.map((mode) => {
                  const active = mode === viewMode;
                  return (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setViewMode(mode)}
                      className={[
                        "rounded-full border px-3 py-1 text-xs font-medium transition-all duration-200",
                        active
                          ? "border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-300"
                          : "border-zinc-800 bg-zinc-950/40 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                      ].join(" ")}
                    >
                      {mode}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
              {Object.entries(latestComponents).map(([name, value]) => (
                <div
                  key={name}
                  className="rounded-2xl border border-zinc-800/70 bg-zinc-950/40 px-3 py-3"
                >
                  <div className="text-[10px] uppercase tracking-[0.14em] text-zinc-500">
                    {prettyName(name)}
                  </div>
                  <div className={`mt-2 text-sm font-semibold tabular-nums ${componentTone(name, value)}`}>
                    {fmtEURUnsigned(value)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-800/70 bg-zinc-950/30 p-4">
            <div className="mb-4 text-[10px] uppercase tracking-[0.16em] text-zinc-500">
              Performance Attribution
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800 text-left text-zinc-500">
                    <th className="pb-3 pr-4 font-medium">Brick</th>
                    <th className="pb-3 pr-4 font-medium">Contribution</th>
                    <th className="pb-3 pr-4 font-medium">Share</th>
                    <th className="pb-3 pr-4 font-medium">
                      {period === "1D" ? "Daily Delta" : `${period} Delta`}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {attributionRows.map((row) => (
                    <tr key={row.key} className="border-b border-zinc-900 last:border-0">
                      <td className="py-3 pr-4">
                        <div className="inline-flex items-center gap-2">
                          <span
                            className="h-2.5 w-2.5 rounded-full"
                            style={{ backgroundColor: row.color }}
                          />
                          <span className="text-zinc-200">{row.label}</span>
                        </div>
                      </td>
                      <td className="py-3 pr-4 font-medium tabular-nums text-zinc-100">
                        {fmtEURUnsigned(row.value)}
                      </td>
                      <td className="py-3 pr-4 tabular-nums text-zinc-300">
                        {fmtPct(row.pct)}
                      </td>
                      <td className={`py-3 pr-4 tabular-nums ${toneClass(row.delta)}`}>
                        {fmtEUR(row.delta)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-800/70 bg-zinc-950/30 p-4">
            <div className="mb-4 text-[10px] uppercase tracking-[0.16em] text-zinc-500">
              Composition Legend
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(COMPONENT_META).map(([key, metaItem]) => (
                <div
                  key={key}
                  className="inline-flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-950/40 px-3 py-1.5 text-xs text-zinc-300"
                >
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: metaItem.color }}
                  />
                  <span>{metaItem.label}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {SERIES.map((s) => {
          const active = s === seriesKey;
          return (
            <button
              key={s}
              type="button"
              onClick={() => setSeriesKey(s)}
              className={[
                "rounded-full border px-3 py-1 text-xs font-medium transition-all duration-200",
                active
                  ? "border-sky-500/30 bg-sky-500/10 text-sky-300"
                  : "border-zinc-800 bg-zinc-950/40 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
              ].join(" ")}
            >
              {s}
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {PERIODS.map((p) => {
          const active = p === period;
          return (
            <button
              key={p}
              type="button"
              onClick={() => setPeriod(p)}
              className={[
                "rounded-full border px-3 py-1 text-xs font-medium transition-all duration-200",
                active
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : "border-zinc-800 bg-zinc-950/40 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
              ].join(" ")}
            >
              {p}
            </button>
          );
        })}
      </div>

      <div className="h-64 w-full rounded-2xl border border-zinc-800/70 bg-zinc-950/30 p-3">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={visiblePoints} margin={{ top: 10, right: 14, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={topFill} />
                <stop offset="100%" stopColor={bottomFill} />
              </linearGradient>
              <filter id="equityGlow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.07)" />

            <XAxis
              dataKey="date"
              tick={{ fill: "#71717a", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />

            <YAxis
              tick={{ fill: "#71717a", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${Number(v).toFixed(0)}€`}
            />

            <Tooltip
              content={seriesKey === "TOTAL" ? <TotalTooltip /> : undefined}
              contentStyle={{
                backgroundColor: "rgba(9, 9, 11, 0.96)",
                border: "1px solid rgba(63,63,70,1)",
                borderRadius: "14px",
                color: "#fafafa",
              }}
              formatter={(value, name) => [
                fmtEURUnsigned(value),
                name === "cumulative_profit" ? "Value" : name,
              ]}
              labelStyle={{ color: "#a1a1aa" }}
            />

            {seriesKey === "TOTAL" && viewMode === "STACKED" &&
              Object.entries(COMPONENT_META).map(([key, metaItem]) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={`components.${key}`}
                  stackId="composition"
                  stroke={metaItem.color}
                  fill={metaItem.color}
                  fillOpacity={0.12}
                  strokeOpacity={0.35}
                  dot={false}
                  activeDot={false}
                />
              ))}

            <Area
              type="monotone"
              dataKey="cumulative_profit"
              stroke={strokeColor}
              strokeWidth={3}
              fill={viewMode === "LINE" || seriesKey !== "TOTAL" ? "url(#equityFill)" : "rgba(0,0,0,0)"}
              dot={false}
              activeDot={{ r: 5 }}
              filter="url(#equityGlow)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
