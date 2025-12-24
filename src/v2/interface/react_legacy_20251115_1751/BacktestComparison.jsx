import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export default function BacktestComparison() {
  const [strategies, setStrategies] = useState([]);

  useEffect(() => {
    async function loadBacktests() {
      try {
        const res = await fetch("/data/backtests/backtests_sample.json");
        if (!res.ok) throw new Error("Backtest file not found");
        const data = await res.json();
        setStrategies(data.strategies || []);
      } catch (e) {
        console.error("Failed to load backtest data:", e);
      }
    }
    loadBacktests();
  }, []);

  return (
    <div className="p-4 bg-white rounded shadow">
      <h3 className="text-lg font-semibold mb-4">\ud83d\udcca Backtest Strategy Comparison</h3>

      {strategies.length === 0 ? (
        <p>No backtest data available.</p>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={strategies}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="pnl" fill="#4ade80" />
            </BarChart>
          </ResponsiveContainer>

          <table className="mt-6 min-w-full text-sm text-left">
            <thead className="bg-gray-100">
              <tr>
                <th className="p-2">Strategy</th>
                <th className="p-2">Total P&L (€)</th>
                <th className="p-2">Trades</th>
                <th className="p-2">Win Rate (%)</th>
              </tr>
            </thead>
            <tbody>
              {strategies.map((s, i) => (
                <tr key={i} className="border-b">
                  <td className="p-2">{s.name}</td>
                  <td className="p-2">{s.pnl.toFixed(2)}</td>
                  <td className="p-2">{s.trades}</td>
                  <td className="p-2">{s.win_rate.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
