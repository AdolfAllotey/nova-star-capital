import { apiUrl } from "../lib/apiClient";
import React, { useEffect, useState } from "react";

function KpiCard({ label, value, suffix = "", status }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-[#0b1220] p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">
        {value}{suffix}
      </div>
      {status && <div className="mt-1 text-xs text-emerald-400">{status}</div>}
    </div>
  );
}

export default function DocumentationCenter() {
  const [data, setData] = useState(null);
  const [coverage, setCoverage] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [healthRes, coverageRes] = await Promise.all([
          fetch(apiUrl("/api/documentation-center")),
          fetch(apiUrl("/api/documentation-center/coverage")),
        ]);

        if (!healthRes.ok) throw new Error("Documentation Center API unavailable");

        setData(await healthRes.json());
        setCoverage(coverageRes.ok ? await coverageRes.json() : null);
      } catch (e) {
        setError(e.message || "Unable to load Documentation Center");
      }
    }

    load();
  }, []);

  if (error) {
    return (
      <div className="min-h-screen bg-[#05080d] p-8 text-slate-100">
        <h1 className="text-2xl font-bold">Documentation Center</h1>
        <div className="mt-6 rounded-xl border border-red-900 bg-red-950/30 p-4 text-red-300">
          {error}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-[#05080d] p-8 text-slate-100">
        <h1 className="text-2xl font-bold">Documentation Center</h1>
        <div className="mt-6 text-slate-400">Loading documentation health...</div>
      </div>
    );
  }

  const domains = coverage?.domains || {};

  return (
    <div className="min-h-screen bg-[#05080d] p-8 text-slate-100">
      <div className="mb-6">
        <div className="text-xs uppercase tracking-[0.25em] text-slate-500">
          Nova Star Capital
        </div>
        <h1 className="mt-2 text-3xl font-bold">Documentation Center</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Master Book health, coverage and documentation governance monitoring.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <KpiCard label="Documentation Health" value={data.documentation_health} suffix="%" status={data.status} />
        <KpiCard label="Coverage Score" value={data.coverage_score} suffix="%" />
        <KpiCard label="Documents Indexed" value={data.documents_count} />
        <KpiCard label="Too Short Docs" value={data.too_short_documents} />
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <KpiCard label="Missing Classification" value={data.missing_classification} />
        <KpiCard label="Missing Status" value={data.missing_status} />
        <KpiCard label="Generated UTC" value={data.generated_utc || "-"} />
      </div>

      <div className="mt-8 rounded-xl border border-slate-800 bg-[#0b1220] p-5">
        <h2 className="text-lg font-semibold text-white">Coverage by Domain</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {Object.entries(domains).map(([domain, info]) => (
            <div key={domain} className="rounded-lg border border-slate-800 bg-[#05080d] p-3">
              <div className="text-sm font-medium capitalize text-white">{domain}</div>
              <div className={`mt-1 text-xs ${info.status === "covered" ? "text-emerald-400" : "text-amber-400"}`}>
                {info.status} · {info.matches_count} matches
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
