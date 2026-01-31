// src/pages/RiskOverview.jsx
import React, { useEffect, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import DataState from "../components/ui/DataState";
import { fetchJson, apiUrl } from "../lib/apiClient";

export default function RiskOverview() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [m, setM] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const r = await fetchJson("/metrics", { timeoutMs: 8000 });
      if (cancelled) return;

      if (!r.ok) {
        setErr(r.error);
        setM(null);
        setLoading(false);
        return;
      }

      setM(r.data || null);
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">Risk</h1>
          <p className="text-sm text-zinc-400">
            Vue “system + risk shell” (on branchera ensuite drawdown / kill-switch / vetos).
          </p>
        </div>
        <div className="text-xs text-zinc-500">Source: {apiUrl("/metrics")}</div>
      </header>

      <SectionCard title="Health & Runtime">
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && !m}
          emptyText="Aucune donnée /metrics."
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Env</div>
              <div className="mt-1 font-semibold text-zinc-50">{m?.env || "—"}</div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Status</div>
              <div className={`mt-1 font-semibold ${m?.status === "ok" ? "text-emerald-400" : "text-amber-300"}`}>
                {m?.status || "—"}
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Uptime (s)</div>
              <div className="mt-1 font-semibold text-zinc-50">
                {typeof m?.uptime_s === "number" ? Math.round(m.uptime_s) : "—"}
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Version</div>
              <div className="mt-1 font-semibold text-zinc-50">{m?.version || "—"}</div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Host</div>
              <div className="mt-1 text-sm font-semibold text-zinc-50">{m?.host || "—"}</div>
              <div className="mt-1 text-xs text-zinc-500">{m?.platform || "—"}</div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Python</div>
              <div className="mt-1 text-sm font-semibold text-zinc-50">{m?.python || "—"}</div>
              <div className="mt-1 text-xs text-zinc-500">Runtime</div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Prochain</div>
              <div className="mt-1 text-sm font-semibold text-zinc-50">Kill-switch / Vetos</div>
              <div className="mt-1 text-xs text-zinc-500">
                Brancher ici: governance_engine_pro.json + correlation_gate_state soft_veto
              </div>
            </div>
          </div>
        </DataState>
      </SectionCard>
    </div>
  );
}
