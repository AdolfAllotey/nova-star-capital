import { useEffect, useState } from "react";
import { getWhales } from "../lib/api";

export default function WhalesFeed() {
  const [feed, setFeed] = useState({ events: [], count: 0 });

  useEffect(() => {
    getWhales().then(setFeed).catch(() => setFeed({ events: [], count: 0 }));
  }, []);

  return (
    <div className="rounded-2xl border border-slate-200 p-4">
      <div className="text-sm font-semibold mb-2">Whales monitor</div>
      {feed.count === 0 && <div className="text-sm opacity-60">Aucun évènement</div>}
      <ul className="space-y-2">
        {feed.events?.slice(0, 10).map((e, i) => (
          <li key={i} className="text-sm">
            <span className="font-mono opacity-70">{e.ts}</span>{" "}
            <span className="font-semibold">{e.token}</span>{" "}
            <span className="opacity-80">{e.type}</span>{" "}
            <span className="opacity-60">@{e.exchange}</span>{" "}
            <span className="font-mono">{e.amount}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
