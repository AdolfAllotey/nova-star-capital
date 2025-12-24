import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const COLORS = [
  "#34D399", "#60A5FA", "#FBBF24", "#F87171", "#A78BFA",
  "#10B981", "#F472B6", "#FCD34D", "#38BDF8", "#C084FC"
];

const TokenAllocationChart = ({ data }) => {
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
        Répartition par token
      </h2>
      <ResponsiveContainer width="100%" height={320}>
        <PieChart>
          <Pie
            data={data}
            dataKey="amount"
            nameKey="token"
            cx="50%"
            cy="50%"
            outerRadius={100}
            fill="#8884d8"
            label={({ token, percent }) =>
              `${token} ${(percent * 100).toFixed(1)}%`
            }
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => [`${value.toFixed(2)} €`, "Montant"]}
            contentStyle={{
              backgroundColor: "#1F2937",
              borderRadius: "8px",
              border: "none",
            }}
            labelStyle={{ color: "#D1D5DB" }}
            itemStyle={{ color: "#F9FAFB" }}
          />
          <Legend
            verticalAlign="bottom"
            iconType="circle"
            formatter={(value) => <span className="text-sm text-gray-300">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default TokenAllocationChart;