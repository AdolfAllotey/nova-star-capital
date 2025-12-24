import React from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

const sample = [
  { t: "2025-08", pnl: 1240.55 },
  { t: "2025-09", pnl: -320.10 },
  { t: "2025-10", pnl: 860.75 },
];

export default function PnlChart() {
  return (
    <div style={{height: 240}}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={sample}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="t" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="pnl" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
