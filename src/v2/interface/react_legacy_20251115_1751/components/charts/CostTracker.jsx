import React, { useEffect, useState } from "react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import axios from "axios"

const CostTrackerChart = () => {
  const [data, setData] = useState([])

  useEffect(() => {
    const fetchCosts = async () => {
      try {
        const response = await axios.get("/data/monthly_costs.json")
        setData(response.data)
      } catch (error) {
        console.error("Erreur lors du chargement des coûts mensuels :", error)
      }
    }
    fetchCosts()
  }, [])

  return (
    <div className="bg-card p-4 rounded-2xl shadow-md">
      <h2 className="text-xl font-semibold mb-4">Monthly API & Ops Costs</h2>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="month" />
          <YAxis unit="€" />
          <Tooltip />
          <Legend />
          <Bar dataKey="openai" fill="#8884d8" name="OpenAI API" />
          <Bar dataKey="etherscan" fill="#82ca9d" name="Etherscan API" />
          <Bar dataKey="hetzner" fill="#ffc658" name="Hetzner Server" />
          <Bar dataKey="telegram" fill="#ff7f50" name="Telegram Bot" />
          <Bar dataKey="email" fill="#8dd1e1" name="Email / SMTP" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default CostTrackerChart