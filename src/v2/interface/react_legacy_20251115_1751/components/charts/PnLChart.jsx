import React, { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const PnLChart = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch("/data/global_performance.json")
      .then((res) => res.json())
      .then((json) => {
        const formatted = json.map((item) => ({
          date: item.date,
          pnl: item.total_gain_eur,
        }));
        setData(formatted);
      })
      .catch((error) => console.error("Error loading PnL data:", error));
  }, []);

  return (
    <div className="bg-white dark:bg-neutral-800 p-4 rounded-2xl shadow">
      <h2 className="text-xl font-semibold mb-4">📈 Performance Cumulative (PnL)</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis domain={["auto", "auto"]} />
          <Tooltip />
          <Line type="monotone" dataKey="pnl" stroke="#10b981" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PnLChart;