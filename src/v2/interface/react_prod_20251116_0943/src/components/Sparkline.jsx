// src/components/Sparkline.jsx
import React from "react";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/**
 * Sparkline minimal :
 *  - data: [{ t: <ISO|number>, v: <number> }, ...]
 *  - height: 40 à 80 recommandé
 */
export default function Sparkline({ data = [], height = 48, strokeWidth = 2 }) {
  // Normalisation basique
  const safe = Array.isArray(data)
    ? data
        .map((d) => ({
          t: typeof d.t === "string" ? new Date(d.t).getTime() : Number(d.t),
          v: Number(d.v),
        }))
        .filter((d) => Number.isFinite(d.t) && Number.isFinite(d.v))
    : [];

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={safe} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
          <XAxis hide dataKey="t" type="number" domain={["auto", "auto"]} />
          <YAxis hide domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{
              background: "rgba(24,24,27,0.9)",
              border: "1px solid #27272a",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(v) => [v, "val"]}
            labelFormatter={(label) => new Date(label).toLocaleTimeString()}
          />
          <Line type="monotone" dataKey="v" dot={false} strokeWidth={strokeWidth} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
