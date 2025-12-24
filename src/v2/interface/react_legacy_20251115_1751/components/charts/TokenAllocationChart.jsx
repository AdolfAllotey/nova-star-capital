import React, { useEffect, useState } from "react";
import {
  PieChart,
  Pie,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts";

const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6"];

const TokenAllocationChart = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch("/data/simulation/token_allocation.json")
      .then((res) => res.json())
      .then((json) => {
        const formatted = Object.entries(json).map(([key, value]) => ({
          name: key,
          value: value,
        }));
        setData(formatted);
      })
      .catch((error) => console.error("Error loading allocation data:", error));
  }, []);

  return (
    <div className="bg-white dark:bg-neutral-800 p-4 rounded-2xl shadow">
      <h2 className="text-xl font-semibold mb-4">🧩 Token Allocation</h2>
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

export default TokenAllocationChart;