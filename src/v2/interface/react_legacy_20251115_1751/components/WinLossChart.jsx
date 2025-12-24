import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
} from "recharts";

const WinLossChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-900 p-4 rounded-2xl shadow-md">
        <p className="text-sm text-gray-500 dark:text-gray-300">
          Aucune donnée disponible
        </p>
      </div>
    );
  }

  const COLORS = {
    win: "#10B981",   // vert
    loss: "#EF4444",  // rouge
  };

  return (
    <div className="bg-white dark:bg-gray-900 p-4 rounded-2xl shadow-md">
      <h2 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
        Gagnants vs Perdants
      </h2>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data}>
          <XAxis
            dataKey="strategy"
            stroke="#D1D5DB"
            tick={{ fill: "#9CA3AF", fontSize: 12 }}
          />
          <YAxis
            allowDecimals={false}
            stroke="#D1D5DB"
            tick={{ fill: "#9CA3AF", fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1F2937",
              borderRadius: 8,
              border: "none",
            }}
            labelStyle={{ color: "#D1D5DB" }}
            itemStyle={{ color: "#F9FAFB" }}
          />
          <Legend
            verticalAlign="top"
            height={36}
            iconType="circle"
            formatter={(value) => (
              <span className="text-sm text-gray-300">{value}</span>
            )}
          />
          <Bar dataKey="wins" name="Gagnants" stackId="a" fill={COLORS.win} />
          <Bar dataKey="losses" name="Perdants" stackId="a" fill={COLORS.loss} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default WinLossChart;