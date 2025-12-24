import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export default function PerformanceChart() {
  const [data, setData] = useState([]);

  useEffect(() => {
    async function loadPerformance() {
      const daysToLoad = 7;
      const today = new Date();
      const dates = [...Array(daysToLoad)].map((_, i) => {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        return d.toISOString().slice(0, 10);
      }).reverse();

      const results = [];

      for (const date of dates) {
        try {
          const res = await fetch(`/data/simulation/${date}.json`);
          if (!res.ok) continue;
          const json = await res.json();

          const totalPnl = json.trades?.reduce((acc, trade) => acc + (trade.pnl || 0), 0) || 0;
          results.push({ date, pnl: parseFloat(totalPnl.toFixed(2)) });
        } catch (err) {
          console.error("Error loading", date, err);
        }
      }

      setData(results);
    }

    loadPerformance();
  }, []);

  return (
    <div className="p-4 bg-white rounded shadow mb-6">
      <h3 className="text-lg font-semibold mb-2">\ud83d\udcc8 7-Day Cumulative P&L</h3>
      {data.length === 0 ? (
        <p>No data available</p>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="pnl" stroke="#8884d8" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
