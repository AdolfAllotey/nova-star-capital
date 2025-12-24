import React from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

const COLORS = ["#34D399", "#60A5FA", "#FBBF24", "#F87171", "#A78BFA", "#F472B6"];

const StrategyBreakdownChart = ({ data }) => {
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
        Répartition par stratégie
      </h2>
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="strategy"
            cx="50%"
            cy="50%"
            outerRadius={80}
            label
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, name) => [`${value} %`, name]}
            contentStyle={{ backgroundColor: "#1F2937", borderRadius: "8px", border: "none" }}
            labelStyle={{ color: "#D1D5DB" }}
            itemStyle={{ color: "#F9FAFB" }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default StrategyBreakdownChart;