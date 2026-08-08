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

function formatEur(v) {
  return `${Number(v || 0).toFixed(2).replace(".", ",")} €`;
}

export default function LongTermMiniCurve() {
  const [points, setPoints] = useState([]);
  const [meta, setMeta] = useState({});
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError("");
        const res = await fetch(buildApiUrl("/api/lt-curve"));
        if (!res.ok) throw new Error(`lt-curve ${res.status}`);
        const payload = await res.json();
        if (!cancelled) {
          setPoints(Array.isArray(payload?.points) ? payload.points : []);
          setMeta(payload || {});
        }
      } catch (e) {
        if (!cancelled) {
          console.error("LongTermMiniCurve fetch failed", e);
          setError("Unable to load LT curve.");
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const finalValue = useMemo(() => {
    if (!points.length) return 0;
    return Number(points[points.length - 1]?.cumulative_profit || 0);
  }, [points]);

  if (error) {
    return (
      <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-300">
        {error}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-zinc-800/70 bg-zinc-950/30 p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
            Long Term Curve
          </div>
          <div className="mt-1 text-xl font-semibold text-zinc-100">
            {formatEur(finalValue)}
          </div>
        </div>

        <div className="text-right">
          <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
            Engine
          </div>
          <div className="mt-1 text-sm text-zinc-300">
            {meta?.engine || "lt_curve"}
          </div>
        </div>
      </div>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="ltCurveFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="rgba(232,121,249,0.28)" />
                <stop offset="100%" stopColor="rgba(232,121,249,0.02)" />
              </linearGradient>
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
              contentStyle={{
                backgroundColor: "rgba(9, 9, 11, 0.96)",
                border: "1px solid rgba(63,63,70,1)",
                borderRadius: "14px",
                color: "#fafafa",
              }}
              formatter={(value) => [formatEur(value), "Long Term"]}
              labelStyle={{ color: "#a1a1aa" }}
            />

            <Area
              type="monotone"
              dataKey="cumulative_profit"
              stroke="#e879f9"
              strokeWidth={3}
              fill="url(#ltCurveFill)"
              dot={false}
              activeDot={{ r: 5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
