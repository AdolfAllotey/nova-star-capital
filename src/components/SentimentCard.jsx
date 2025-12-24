import { useEffect, useState } from "react";
import { getSentiment } from "../lib/api";

function Bar({ label, value }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="opacity-70">{label}</span>
        <span className="font-mono">{pct}%</span>
      </div>
      <div className="w-full h-2 bg-slate-200 rounded">
        <div className="h-2 rounded bg-slate-800" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function SentimentCard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    getSentiment().then(setData).catch(() => setData({ sentiment: 0, momentum: 0 }));
  }, []);

  return (
    <div className="rounded-2xl border border-slate-200 p-4 space-y-3">
      <div className="text-sm font-semibold">Sentiment & Momentum</div>
      <Bar label="Sentiment" value={data?.sentiment ?? 0} />
      <Bar label="Momentum" value={data?.momentum ?? 0} />
      {data?.date && <div className="text-xs opacity-60">maj {new Date(data.date).toLocaleString()}</div>}
      {data?.updated_at && <div className="text-xs opacity-60">maj {new Date(data.updated_at).toLocaleString()}</div>}
    </div>
  );
}
