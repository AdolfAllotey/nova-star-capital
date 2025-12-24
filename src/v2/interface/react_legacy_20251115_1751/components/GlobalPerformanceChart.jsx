import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

const GlobalPerformanceChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="p-4 border border-border rounded-2xl text-muted-foreground">
        Aucune donnée disponible pour l’instant.
      </div>
    );
  }

  return (
    <div className="w-full h-[300px] bg-background rounded-2xl shadow p-4">
      <h2 className="text-lg font-semibold mb-4">Performance Globale</h2>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#ccc" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="currentColor" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export { GlobalPerformanceChart };