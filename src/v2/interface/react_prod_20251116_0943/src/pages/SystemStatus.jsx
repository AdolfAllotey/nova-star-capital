// src/pages/SystemStatus.jsx
import React from "react";
import { api } from "../lib/api";

function Row({ k, v }) {
  return (
    <tr className="border-b border-zinc-800/60">
      <td className="py-2 pr-3 text-zinc-300">{k}</td>
      <td className="py-2 pr-3">{v.exists ? "✅" : "—"}</td>
      <td className="py-2 pr-3 tabular-nums">{v.items ?? 0}</td>
      <td className="py-2 pr-3 tabular-nums">{v.size_bytes ?? 0}</td>
      <td className="py-2 pr-3 text-zinc-400 text-xs">{v.mtime ?? "—"}</td>
      <td className="py-2 pr-3 text-zinc-600 text-xs">{v.path}</td>
    </tr>
  );
}

export default function SystemStatus() {
  const [data, setData] = React.useState(null);
  const [err, setErr] = React.useState("");

  React.useEffect(() => {
    let live = true;
    api.metrics()
      .then((d) => live && setData(d))
      .catch((e) => live && setErr(e.message));
    return () => (live = false);
  }, []);

  if (err) return <div className="text-red-400">Erreur: {err}</div>;
  if (!data) return <div className="text-zinc-400">Chargement…</div>;

  return (
    <div className="space-y-6">
      <div className="text-sm text-zinc-400">
        Uptime: <span className="tabular-nums">{Math.floor(data.uptime_seconds)}s</span> — {data.utc}
      </div>
      <div className="rounded-2xl border border-zinc-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-zinc-900/60">
            <tr>
              <th className="text-left py-2 px-3 font-medium">Key</th>
              <th className="text-left py-2 px-3 font-medium">Exists</th>
              <th className="text-left py-2 px-3 font-medium">Items</th>
              <th className="text-left py-2 px-3 font-medium">Size (B)</th>
              <th className="text-left py-2 px-3 font-medium">MTime</th>
              <th className="text-left py-2 px-3 font-medium">Path</th>
            </tr>
          </thead>
          <tbody className="px-3">
            {Object.entries(data.files).map(([k, v]) => (
              <Row key={k} k={k} v={v} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
