// src/pages/αβ.jsx
import React, { useEffect, useMemo, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import DataState from "../components/ui/DataState";
import { fetchJson } from "../lib/apiClient";

// --- formatting helper (crash-safe) ---
const fmtNum = (v, opts = {}) => {
  const { digits = 3 } = opts || {};
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  try {
    return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: digits }).format(n);
  } catch {
    return n.toFixed(Math.min(Math.max(digits, 0), 8));
  }
};


const fmtPct = (v, digits = 2) => {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
};

const fmtSignedPct = (v, digits = 2) => {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  const sign = n > 0 ? "+" : n < 0 ? "−" : "";
  return `${sign}${Math.abs(n * 100).toFixed(digits)}%`;
};

function fmt(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = typeof v === "number" ? v : Number(v);
  return n.toFixed(3);
}


/**
 * Schéma attendu (future API):
 * {
 *   as_of: "2026-01-29T19:10:41Z",
 *   benchmark: { id: "BTC", name: "BTC" },
 *   bricks: [
 *     {
 *       id: "crypto",
 *       name: "Crypto",
 *       α: 0.0123,       // annualisé ou période définie
 *       β: 1.14,
 *       r2: 0.62,
 *       corr: 0.79,
 *       return: 0.034,
 *       volatility: 0.21,
 *       n_points: 120
 *     }
 *   ]
 * }
 */
export default function αβ() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [payload, setPayload] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      try {
        const r = await fetchJson("/alpha-beta/overview", { timeoutMs: 8000 });
        if (cancelled) return;

        // ✅ 404 Not Found => "pas encore branché" (empty state)
        if (!r.ok) {
          const msg =
            r?.error?.detail?.detail ||
            r?.error?.detail ||
            r?.error?.message ||
            null;

          const msgStr = typeof msg === "string" ? msg.toLowerCase() : "";

          if (msgStr.includes("not found") || r?.error?.status === 404) {
            setPayload(null);
            setErr(null);
            setLoading(false);
            return;
          }

          if (msgStr.includes("no α/β") || msgStr.includes("no α β")) {
            setPayload(null);
            setErr(null);
            setLoading(false);
            return;
          }

          setErr(r.error);
          setPayload(null);
          setLoading(false);
          return;
        }

        const data = r.data || null;

        // ✅ 200 avec payload "No α/β data" => empty state
        if (data && typeof data === "object" && typeof data.detail === "string") {
          const d = data.detail.toLowerCase();
          if (d.includes("no α/β") || d.includes("no α β")) {
            setPayload(null);
            setErr(null);
            setLoading(false);
            return;
          }
        }

        setPayload(data);
        setLoading(false);
      } catch (e) {
        if (cancelled) return;
        setErr(e);
        setPayload(null);
        setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const bricks = useMemo(() => {
    const arr = Array.isArray(payload?.bricks) ? payload.bricks : [];
    // tri : plus “important” d’abord (vol/corr)
    return arr.slice().sort((a, b) => (b?.n_points ?? 0) - (a?.n_points ?? 0));
  }, [payload]);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">α / β</h1>
          <p className="text-sm text-zinc-400 ring-1 ring-zinc-700/60 bg-gradient-to-br from-emerald-500/10 to-transparent">
            Analyse alpha/bêta par brique. Source: <code>/alpha-beta/overview</code>
          </p>
        </div>
        <div className="text-xs text-zinc-500">PREPROD</div>
      </header>

      <SectionCard title="Résumé">
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && bricks.length === 0}
          emptyText="Aucune donnée α/β pour le moment (endpoint backend non branché)."
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {bricks.map((b) => (
              <div key={b.id || b.name} className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-zinc-50 truncate">
                      {b.name || b.id || "—"}
                    </div>
                    <div className="text-xs text-zinc-500">
                      points: {b.n_points ?? "—"} · R²: {fmt(b.r2)} · corr: {fmt(b.corr)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-semibold text-zinc-200 tracking-tight">β</div>
                    <div className="text-3xl font-semibold text-zinc-50 tracking-tight">{fmt(fmtNum(b.β))}</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-3">
                    <div className="text-2xl font-semibold text-zinc-200 tracking-tight">α</div>
                    <div className="text-3xl font-semibold text-zinc-50 tracking-tight">{fmt(fmtPct(b.α))}</div>
                  </div>
                  <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-3">
                    <div className="text-3xl font-semibold text-zinc-200 tracking-tight">σ</div>
                    <div className="text-base font-semibold text-zinc-50 ring-1 ring-zinc-700/60 bg-gradient-to-br from-amber-500/10 to-transparent">{fmt(b.volatility)}</div>
                  </div>
                  <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-3">
                    <div className="text-xs text-zinc-500">Return</div>
                    <div className="text-base font-semibold text-zinc-50">{fmtPct(b.return)}</div>
                  </div>
                  <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-3">
                    <div className="text-xs text-zinc-500">Benchmark</div>
                    <div className="text-base font-semibold text-zinc-50">
                      {payload?.benchmark?.name || payload?.benchmark?.id || "—"}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </DataState>
      </SectionCard>

      <SectionCard title="Notes">
        <div className="text-sm text-zinc-300 space-y-2">
          <div>
            Cette page est prête côté UI. Il manque uniquement le backend{" "}
            <code>/alpha-beta/overview</code>.
          </div>
          <div className="text-xs text-zinc-500">
            À brancher ensuite sur <code>α_β_engine</code> (α, β, corr, R², vol, returns, n_points) par brique.
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
