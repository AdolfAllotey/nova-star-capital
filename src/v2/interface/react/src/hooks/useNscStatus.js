import { apiUrl } from "../lib/apiClient";
import { useEffect, useMemo, useRef, useState } from "react";

async function fetchJson(path) {
  try {
    const r = await fetch(path, { cache: "no-store" });
    if (!r.ok) return null;
    return await r.json();
  } catch (_) {
    return null;
  }
}

async function fetchStatus() {
  // 1) Canonical API status when available.
  try {
    const r = await fetch(apiUrl("/api/status"), { cache: "no-store" });

    if (r.ok) {
      const payload = await r.json();

      return {
        ...payload,
        statusSource: "api",
        degraded: false,
      };
    }
  } catch (_) {
    // Explicit static fallback below.
  }

  // 2) Static runtime artefacts, with explicit degradation metadata.
  const [system, governance, orchestrator] = await Promise.all([
    fetchJson("/data/telemetry/system_metrics_pro.json"),
    fetchJson("/data/analysis/governance_engine_pro.json"),
    fetchJson("/data/telemetry/orchestrator_pro.json"),
  ]);

  const missing = [];

  if (!system) missing.push("system_metrics");
  if (!governance) missing.push("governance");
  if (!orchestrator) missing.push("orchestrator");

  return {
    system,
    governance,
    orchestrator,
    statusSource: "static_fallback",
    degraded: missing.length > 0,
    missing,
  };
}

export function useNscStatus({ refreshMs = 5000 } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const timer = useRef(null);

  useEffect(() => {
    let alive = true;

    const run = async () => {
      try {
        setLoading(true);
        const res = await fetchStatus();
        if (alive) setData(res);
      } finally {
        if (alive) setLoading(false);
      }
    };

    run();
    timer.current = setInterval(run, refreshMs);

    return () => {
      alive = false;
      if (timer.current) clearInterval(timer.current);
    };
  }, [refreshMs]);

  return useMemo(() => ({
    loading,
    system: data?.system,
    summary: data?.system?.summary ?? {},
    governance: data?.governance,
    orchestrator: data?.orchestrator,
  }), [data, loading]);
}
