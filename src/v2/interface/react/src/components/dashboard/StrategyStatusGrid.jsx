import React from "react";
import StrategyStatusCard from "./StrategyStatusCard";

export default function StrategyStatusGrid({ strategies }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-6">
      {strategies.map((s) => (
        <StrategyStatusCard key={s.key} strategy={s} />
      ))}
    </div>
  );
}
