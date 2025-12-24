import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const DrawdownChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="bg-card rounded-2xl shadow-md p-4 sm:p-6">
        <h2 className="text-lg sm:text-xl font-semibold mb-4">Drawdown</h2>
        <p className="text-muted-foreground">Aucune donnée disponible.</p>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-2xl shadow-md p-4 sm:p-6">
      <h2 className="text-lg sm:text-xl font-semibold mb-4">Drawdown</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis
            tickFormatter={(value) => `${value}%`}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(value) => `${value.toFixed(2)}%`}
            labelFormatter={(label) => `Date : ${label}`}
          />
          <Line
            type="monotone"
            dataKey="drawdown"
            stroke="#EF4444"
            strokeWidth={2}
            dot={false}
            name="Drawdown (%)"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export { DrawdownChart };