import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const WinLossChart = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch("/data/simulation/win_loss_stats.json")
      .then((res) => res.json())
      .then((json) => {
        setData([
          { name: "Winning Trades", value: json.winning_trades || 0 },
          { name: "Losing Trades", value: json.losing_trades || 0 },
        ]);
      })
      .catch((error) => console.error("Error loading win/loss data:", error));
  }, []);

  return (
    <div className="bg-white dark:bg-neutral-800 p-4 rounded-2xl shadow">
      <h2 className="text-xl font-semibold mb-4">🏆 Win / Loss Ratio</h2>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="value" fill="#3b82f6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default WinLossChart;