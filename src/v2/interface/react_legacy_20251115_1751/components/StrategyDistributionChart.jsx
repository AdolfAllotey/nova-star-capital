import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const StrategyDistributionChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-900 p-4 rounded-2xl shadow-md">
        <p className="text-sm text-gray-600 dark:text-gray-300">Aucune donnée disponible</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-900 p-4 rounded-2xl shadow-md">
      <h2 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
        Distribution par stratégie
      </h2>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
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
          />
          <Tooltip
            formatter={(value) => [`${value} %`, "Part"]}
            contentStyle={{ backgroundColor: "#1F2937", borderRadius: "8px", border: "none" }}
            labelStyle={{ color: "#D1D5DB" }}
            itemStyle={{ color: "#F9FAFB" }}
          />
          <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="#60A5FA" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default StrategyDistributionChart;