// src/v2/interface/react/components/ProfitabilityTable.jsx

import React, { useEffect, useState } from "react";
import monthlyPnL from "../../data/monthly_pnl.json";
import monthlyCosts from "../../data/monthly_costs.json";

const ProfitabilityTable = () => {
  const [tableData, setTableData] = useState([]);

  useEffect(() => {
    const merged = monthlyPnL.map((pnl) => {
      const cost = monthlyCosts.find((c) => c.month === pnl.month);
      const profitability = (pnl.gains || 0) - (cost?.total || 0);
      return {
        month: pnl.month,
        gains: pnl.gains || 0,
        costs: cost?.total || 0,
        profitability,
      };
    });
    setTableData(merged);
  }, []);

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border border-gray-300 text-sm">
        <thead className="bg-gray-100">
          <tr>
            <th className="px-4 py-2 text-left">Mois</th>
            <th className="px-4 py-2 text-right">Gains (€)</th>
            <th className="px-4 py-2 text-right">Coûts (€)</th>
            <th className="px-4 py-2 text-right">Rentabilité (€)</th>
          </tr>
        </thead>
        <tbody>
          {tableData.map((row) => (
            <tr key={row.month} className="border-t">
              <td className="px-4 py-2">{row.month}</td>
              <td className="px-4 py-2 text-right">{row.gains.toFixed(2)}</td>
              <td className="px-4 py-2 text-right">{row.costs.toFixed(2)}</td>
              <td className={`px-4 py-2 text-right ${row.profitability >= 0 ? "text-green-600" : "text-red-600"}`}>
                {row.profitability.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ProfitabilityTable;