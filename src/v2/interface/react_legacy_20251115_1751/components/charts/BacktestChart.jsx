import React, { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

const BacktestChart = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch("/data/backtests/backtest_strategies.json")
      .then((res) => res.json())
      .then((json) => {
        // On reformate les données pour Recharts
        const formatted = json.dates.map((date, i) => {
          const entry = { date };
          for (const strat of Object.keys(json.strategies)) {
            entry[strat] = json.strategies[strat][i];
          }
          return entry;
        });
        setData(formatted);
      })
      .catch((err) => console.error("Erreur lors du chargement du backtest :", err));
  }, []);

  return (
    <div className="bg-white dark:bg-neutral-800 p-4 rounded-2xl shadow">
      <h2 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">📈 Backtest Multi-Stratégies</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          {data[0] &&
            Object.keys(data[0])
              .filter((key) => key !== "date")
              .map((strategy, index) => (
                <Line
                  key={strategy}
                  type="monotone"
                  dataKey={strategy}
                  stroke={`hsl(${index * 60}, 70%, 50%)`}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default BacktestChart;