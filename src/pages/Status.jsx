import React, { useEffect, useState } from "react";
import { getStatus } from "../lib/api.js";

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between border-b border-gray-200 py-2">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium">{String(value)}</span>
    </div>
  );
}

export default function Status() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let abort = new AbortController();
    setLoading(true);
    getStatus({ signal: abort.signal })
      .then(setData)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
    return () => abort.abort();
  }, []);

  if (loading) return <div>Chargement du statut…</div>;
  if (err) return <div className="text-red-600">Erreur: {err}</div>;
  if (!data) return <div>Aucune donnée.</div>;

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-xl font-semibold mb-4">Statut du Bot</h1>
      <div className="rounded-xl border p-4">
        <Row label="status" value={data.status} />
        <Row label="version" value={data.version} />
        <Row label="env" value={data.env} />
        {"uptime_s" in data && <Row label="uptime_s" value={data.uptime_s} />}
        {"host" in data && <Row label="host" value={data.host} />}
        {"python" in data && <Row label="python" value={data.python} />}
      </div>
    </div>
  );
}
