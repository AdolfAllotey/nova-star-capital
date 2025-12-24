// src/v2/interface/react/components/MonthlyCostsChart.jsx

import React, { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import monthlyCosts from "../../data/monthly_costs.json";

const MonthlyCostsChart = () => {
  const [data, setData] = useState([]);

  useEffect(() => {
    setData(monthlyCosts);
  }, []);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="month" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="total" fill="#FF8042" name="Coûts" />
      </BarChart>
    </ResponsiveContainer>
  );
};

export default MonthlyCostsChart;