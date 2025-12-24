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

const StrategyPerformanceChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-900 p-4 rounded-2xl shadow-md">
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Aucune donnée disponible
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-900 p-4 rounded-2xl shadow-md">
      <h2 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
        Performance par stratégie
      </h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="strategy"
            tick={{ fill: "#D1D5DB", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#D1D5DB", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            domain={["auto", "auto"]}
          />
          <Tooltip
            formatter={(value) => [`${value.toFixed(2)} €`, "Performance"]}
            contentStyle={{ backgroundColor: "#1F2937", borderRadius: "8px", border: "none" }}
            labelStyle={{ color: "#D1D5DB" }}
            itemStyle={{ color: "#F9FAFB" }}
          />
          <Line
            type="monotone"
            dataKey="performance"
            stroke="#34D399"
            strokeWidth={2}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default StrategyPerformanceChart;