import React from "react";

const InvestmentTimeline = ({ timelineData }) => {
  return (
    <div className="w-full p-4 rounded-2xl border bg-card shadow-sm">
      <h2 className="text-lg font-semibold mb-4 text-foreground">Historique des investissements</h2>
      <ul className="space-y-4">
        {timelineData?.length > 0 ? (
          timelineData.map((event, index) => (
            <li key={index} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div className="flex flex-col">
                <span className="font-medium text-muted-foreground">{event.date}</span>
                <span className="text-base text-foreground">{event.token}</span>
              </div>
              <div className="text-right">
                <span
                  className={`text-sm font-semibold ${
                    event.action === "Buy" ? "text-green-500" : "text-red-500"
                  }`}
                >
                  {event.action === "Buy" ? "Achat" : "Vente"}
                </span>
                <div className="text-muted-foreground text-xs">
                  Montant : {event.amount} €
                </div>
              </div>
            </li>
          ))
        ) : (
          <li className="text-sm text-muted-foreground">Aucune donnée disponible.</li>
        )}
      </ul>
    </div>
  );
};

export { InvestmentTimeline };