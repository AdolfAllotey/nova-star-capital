import React from "react";

const BestTradesTable = ({ trades }) => {
  if (!trades || trades.length === 0) {
    return (
      <div className="bg-card rounded-2xl shadow-md p-4 sm:p-6">
        <h2 className="text-lg sm:text-xl font-semibold mb-4">Meilleurs Trades</h2>
        <p className="text-muted-foreground">Aucun trade disponible pour le moment.</p>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-2xl shadow-md p-4 sm:p-6">
      <h2 className="text-lg sm:text-xl font-semibold mb-4">Meilleurs Trades</h2>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm sm:text-base">
          <thead>
            <tr className="bg-muted text-left">
              <th className="px-4 py-2">Token</th>
              <th className="px-4 py-2">Score</th>
              <th className="px-4 py-2">Sentiment</th>
              <th className="px-4 py-2">Gain (€)</th>
              <th className="px-4 py-2">Rendement (%)</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade, index) => (
              <tr
                key={index}
                className={index % 2 === 0 ? "bg-background" : "bg-muted/20"}
              >
                <td className="px-4 py-2 font-medium">{trade.token}</td>
                <td className="px-4 py-2">{trade.score.toFixed(2)}</td>
                <td className="px-4 py-2">{(trade.sentiment * 100).toFixed(1)}%</td>
                <td className="px-4 py-2 text-green-600 font-semibold">
                  +{trade.gain.toFixed(2)} €
                </td>
                <td className="px-4 py-2 text-green-500">
                  +{(trade.roi * 100).toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export { BestTradesTable };