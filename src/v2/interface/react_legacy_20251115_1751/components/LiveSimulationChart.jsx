import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

const sampleData = [
  { time: "09:00", value: 10000 },
  { time: "10:00", value: 10450 },
  { time: "11:00", value: 10200 },
  { time: "12:00", value: 10600 },
  { time: "13:00", value: 10820 },
  { time: "14:00", value: 10700 },
  { time: "15:00", value: 11000 },
];

const LiveSimulationChart = () => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={sampleData} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="time" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} domain={["auto", "auto"]} />
        <Tooltip
          formatter={(value) => [`${value.toLocaleString()} €`, "Valeur"]}
          labelFormatter={(label) => `Heure : ${label}`}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#4f46e5"
          strokeWidth={2}
          dot={{ r: 3 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export { LiveSimulationChart };