import { useEffect, useState } from "react";
import { getRegime } from "../lib/api";

const colors = {
  bull: "bg-emerald-100 text-emerald-800 border-emerald-300",
  bear: "bg-rose-100 text-rose-800 border-rose-300",
  neutral: "bg-slate-100 text-slate-800 border-slate-300",
};

export default function RegimeBadge() {
  const [data, setData] = useState(null);

  useEffect(() => {
    getRegime().then(setData).catch(() => setData({ regime: "neutral", score: 0 }));
  }, []);

  const regime = (data?.regime || "neutral").toLowerCase();
  const score = typeof data?.score === "number" ? data.score : null;
  const cls = colors[regime] || colors.neutral;

  return (
    <div className={`border ${cls} rounded-2xl px-4 py-3 flex items-center gap-3`}>
      <span className="text-sm font-medium uppercase tracking-wide">Market regime</span>
      <span className="text-base font-semibold">{regime}</span>
      {score !== null && <span className="text-xs opacity-70">score {score.toFixed(2)}</span>}
    </div>
  );
}
