import React from "react";

export default function ExecutiveSummaryPanel({ global, portfolioState, strategies }) {
  const portfolio = portfolioState?.portfolio || {};
  const activeStrategies = Array.isArray(strategies)
    ? strategies.filter((s) => (s?.status || "").toUpperCase() !== "DISABLED")
    : [];

  function fmtCurrency(v) {
    return `${Number(v || 0).toFixed(2)} €`;
  }

  const items = [
    {
      label: "Environment",
      value: `${global?.env || "UNAVAILABLE"} · API ${global?.apiStatus || "UNKNOWN"}`,
    },
    {
      label: "Market Regime",
      value: `${global?.regime || "UNKNOWN"} · Governance ${global?.governanceMode || "UNKNOWN"}`,
    },
    {
      label: "Capital",
      value: `Observed ${fmtCurrency(global?.capitalObserved)} · Trading ${fmtCurrency(global?.pnlGlobal)} · LT ${fmtCurrency(global?.pnlLongTerm)} · Total ${fmtCurrency(global?.pnlTotalIncludingLongTermAndShadow)}`,
    },
    {
      label: "Activity",
      value: `${global?.openPositions || 0} positions · ${global?.ordersCount || 0} orders · ${global?.candidatesCount || 0} signals`,
    },
    {
      label: "Allocation",
      value: `Crypto ${portfolio?.crypto?.target_weight || 0} · Offensive ${portfolio?.equities_offensive?.target_weight || 0} · Defensive ${portfolio?.equities_defensive?.target_weight || 0}`,
    },
    {
      label: "Active Bricks",
      value: activeStrategies.map((s) => s?.name || s?.key).join(" · "),
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {items.map((item, idx) => (
        <div
          key={idx}
          className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-4"
        >
          <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-2">
            {item.label}
          </div>
          <div className="text-sm text-zinc-200 leading-relaxed">
            {item.value}
          </div>
        </div>
      ))}
    </div>
  );
}
