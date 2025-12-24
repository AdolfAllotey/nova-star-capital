import React, { useEffect, useState } from "react";
import {
  PieChart,
  Pie,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts";

const COLORS = ["#6366f1", "#22c55e", "#f43f5e", "#f97316", "#0ea5e9"];

const StrategyDistributionChart = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch("/data/simulation/strategy_distribution.json")
      .then((res) => res.json())
      .then((json) => {
        const formatted = Object.entries(json).map(([key, value]) => ({
          name: key,
          value: value,
        }));
        setData(formatted);
      })
      .catch((error) => console.error("Error loading strategy data:", error));
  }, []);

  return (
    <div className="bg-white dark:bg-neutral-800 p-4 rounded-2xl shadow">
      <h2 className="text-xl font-semibold mb-4">🧠 Strategy Distribution</h2>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" outerRadius={100}>
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default StrategyDistributionChart;