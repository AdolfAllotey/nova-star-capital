// src/v2/interface/react/components/MonthlyPnLChart.jsx

import React, { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import monthlyPnL from "../../data/monthly_pnl.json";

const MonthlyPnLChart = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    setData(monthlyPnL);
  }, []);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="month" />
        <YAxis />
        <Tooltip />
        <Line type="monotone" dataKey="gains" stroke="#00C49F" name="Gains" />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default MonthlyPnLChart;