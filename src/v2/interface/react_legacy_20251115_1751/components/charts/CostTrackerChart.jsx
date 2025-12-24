import React from "react"
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts"

const formatData = (costData) => {
  return Object.entries(costData).map(([month, values]) => ({
    month,
    OpenAI: parseFloat(values.OpenAI ?? 0),
    Etherscan: parseFloat(values.Etherscan ?? 0),
    Hetzner: parseFloat(values.Hetzner ?? 0),
    Messaging: parseFloat(values.Messaging ?? 0),
    Storage: parseFloat(values.Storage ?? 0),
  }))
}

const CostTrackerChart = ({ data }) => {
  const formattedData = formatData(data)

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={formattedData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="month" />
        <YAxis unit="€" />
        <Tooltip formatter={(value) => `${value.toFixed(2)} €`} />
        <Legend />
        <Line type="monotone" dataKey="OpenAI" stroke="#8884d8" name="OpenAI" />
        <Line type="monotone" dataKey="Etherscan" stroke="#82ca9d" name="Etherscan" />
        <Line type="monotone" dataKey="Hetzner" stroke="#ffc658" name="Hetzner" />
        <Line type="monotone" dataKey="Messaging" stroke="#ff8042" name="Messaging" />
        <Line type="monotone" dataKey="Storage" stroke="#00C49F" name="Storage" />
      </LineChart>
    </ResponsiveContainer>
  )
}

export default CostTrackerChart