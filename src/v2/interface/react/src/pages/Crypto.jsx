import React, { useEffect, useMemo, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import StatusBadge from "../components/ui/StatusBadge";
import DataState from "../components/ui/DataState";
import { fetchJson } from "../lib/apiClient";

function fmtCurrency(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "N/A";
  return `${Number(v).toFixed(2)} €`;
}

function fmtPct(v, digits = 1) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "N/A";
  return `${(Number(v) * 100).toFixed(digits)}%`;
}

function MicroCard({ label, value, valueClassName = "text-zinc-50" }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="text-xs uppercase tracking-wider text-zinc-500">{label}</div>
      <div className={`mt-2 text-2xl font-semibold ${valueClassName}`}>{value}</div>
    </div>
  );
}

function PageHeader({ title, subtitle, badges = [] }) {
  return (
    <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
      <div>
        <h1 className="text-[30px] font-semibold tracking-tight text-white">{title}</h1>
        <p className="mt-1 text-sm text-zinc-400">{subtitle}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {badges.map((badge, idx) => (
          <StatusBadge
            key={`${badge.label || badge.status || "badge"}-${idx}`}
            status={badge.status}
            label={badge.label}
          />
        ))}
      </div>
    </div>
  );
}

export default function Crypto() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [data, setData] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const r = await fetchJson("/api/crypto/overview", { timeoutMs: 8000 });
      if (cancelled) return;

      if (!r.ok) {
        setErr(r.error);
        setData(null);
        setLoading(false);
        return;
      }

      setData(r.data || null);
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const header = data?.header || {};
  const kpis = data?.kpis || {};
  const signals = data?.signals || {};
  const execution = data?.execution || {};
  const explainability = data?.explainability || {};
  const ico = data?.ico || {};
  const whales = data?.whales || {};

  const selectedTokens = useMemo(
    () => (Array.isArray(signals?.selected_tokens) ? signals.selected_tokens : []),
    [signals]
  );

  const trades = useMemo(
    () => (Array.isArray(execution?.trades) ? execution.trades : []),
    [execution]
  );

  const topTokens = useMemo(
    () => (Array.isArray(signals?.top_tokens) ? signals.top_tokens : []),
    [signals]
  );

  return (
    <div className="space-y-6 p-5">
      <PageHeader
        title="Crypto"
        subtitle="Runtime-first crypto page: signals, sentiment, simulated execution, exposure, then ICO and whales as secondary exploration blocks."
        badges={[
          { label: header?.status || "PREPROD" },
          { label: header?.mode || "UNAVAILABLE" },
          { label: signals?.sentiment_state?.bucket || kpis?.sentiment_bucket || "UNKNOWN" },
        ]}
      />

      <SectionCard title="Crypto KPIs" subtitle="Live preprod monitoring for the crypto sleeve">
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && !data}
          emptyText="No crypto overview available."
        />
        {!loading && !err && data && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-6">
            <MicroCard label="Selected Tokens" value={kpis?.selected_tokens ?? 0} />
            <MicroCard label="Orders" value={kpis?.orders ?? 0} />
            <MicroCard label="Open Positions" value={kpis?.open_positions ?? 0} />
            <MicroCard label="Exposure" value={fmtCurrency(kpis?.exposure_eur)} />
            <MicroCard label="Sentiment" value={kpis?.sentiment_bucket || "N/A"} />
            <MicroCard label="PnL" value={fmtCurrency(kpis?.pnl_eur)} />
          </div>
        )}
      </SectionCard>

      <SectionCard title="Signal Layer" subtitle="Selected tokens, sentiment state, and dominant token flow">
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && selectedTokens.length === 0 && topTokens.length === 0}
          emptyText="No signal-layer data available."
        />
        {!loading && !err && data && (
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="mb-3 text-sm font-semibold text-zinc-100">Selected Tokens</div>
              <div className="flex flex-wrap gap-2">
                {selectedTokens.length ? (
                  selectedTokens.map((token) => (
                    <span
                      key={token}
                      className="inline-flex rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-xs text-cyan-200"
                    >
                      {String(token).toUpperCase()}
                    </span>
                  ))
                ) : (
                  <span className="text-sm text-zinc-500">No selected token available.</span>
                )}
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3">
                <MicroCard
                  label="Avg Score"
                  value={
                    kpis?.sentiment_score === null || kpis?.sentiment_score === undefined
                      ? "N/A"
                      : Number(kpis.sentiment_score).toFixed(3)
                  }
                />
                <MicroCard label="Bucket" value={kpis?.sentiment_bucket || "N/A"} />
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="mb-3 text-sm font-semibold text-zinc-100">Top Mentioned Tokens</div>
              <div className="space-y-2">
                {topTokens.length ? (
                  topTokens.map((row, idx) => (
                    <div
                      key={`${row.token || "token"}-${idx}`}
                      className="flex items-center justify-between rounded-xl border border-zinc-800 bg-black/20 px-3 py-2 text-sm"
                    >
                      <span className="text-zinc-200">{row.token || "—"}</span>
                      <span className="text-zinc-400">{row.mentions ?? 0} mentions</span>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-zinc-500">No top token data available.</div>
                )}
              </div>
            </div>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Execution Layer" subtitle="Simulated trades produced by the crypto runtime">
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && trades.length === 0}
          emptyText="No simulated crypto trade available."
        />
        {!loading && !err && trades.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-zinc-500">
                <tr className="border-b border-zinc-800">
                  <th className="py-2 text-left">Token</th>
                  <th className="py-2 text-right">Amount</th>
                  <th className="py-2 text-right">Notional (€)</th>
                  <th className="py-2 text-right">Exchange</th>
                  <th className="py-2 text-right">Regime</th>
                  <th className="py-2 text-right">Risk Mode</th>
                  <th className="py-2 text-right">Status</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t, idx) => (
                  <tr key={`${t.token || "trade"}-${idx}`} className="border-b border-zinc-900/60">
                    <td className="py-2 text-zinc-100">{String(t.token || "—").toUpperCase()}</td>
                    <td className="py-2 text-right text-zinc-200">{t.amount ?? "—"}</td>
                    <td className="py-2 text-right text-zinc-200">{fmtCurrency(t.notional_eur ?? t.amount)}</td>
                    <td className="py-2 text-right text-zinc-400">{t.exchange || "—"}</td>
                    <td className="py-2 text-right text-zinc-400">{t.regime || "—"}</td>
                    <td className="py-2 text-right text-zinc-400">{t.risk_mode || "—"}</td>
                    <td className="py-2 text-right">
                      <StatusBadge label={String(t.status || "UNAVAILABLE").toUpperCase()} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Positions & Performance" subtitle="Current exposure and performance readiness">
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && !data}
          emptyText="No crypto performance block available."
        />
        {!loading && !err && data && (
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="mb-3 text-sm font-semibold text-zinc-100">Exposure Snapshot</div>
              <div className="grid grid-cols-2 gap-3">
                <MicroCard label="Open Positions" value={kpis?.open_positions ?? 0} />
                <MicroCard label="Exposure (€)" value={fmtCurrency(kpis?.exposure_eur)} />
              </div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="mb-3 text-sm font-semibold text-zinc-100">PnL Readiness</div>
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-amber-100">
                PnL is not yet fully mark-to-market ready for crypto because current simulated trades do not expose a usable entry price layer for valuation.
              </div>
            </div>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Explainability" subtitle="Why the crypto page is currently structured this way">
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && !(Array.isArray(explainability?.summary) && explainability.summary.length)}
          emptyText="No explainability summary available."
        />
        {!loading && !err && Array.isArray(explainability?.summary) && explainability.summary.length > 0 && (
          <div className="space-y-2">
            {explainability.summary.map((line, idx) => (
              <div
                key={`explain-${idx}`}
                className="rounded-xl border border-zinc-800 bg-zinc-950/40 px-4 py-3 text-sm text-zinc-300"
              >
                {line}
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard title="ICO Pipeline" subtitle="Secondary exploration block kept below runtime execution">
        <DataState
          loading={loading}
          error={err}
          empty={
            !loading &&
            !err &&
            !ico?.candidates_count &&
            !ico?.screened_count &&
            !ico?.scored_count &&
            !ico?.allocation_count
          }
          emptyText="No ICO pipeline data available."
        />
        {!loading && !err && data && (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
              <MicroCard label="Candidates" value={ico?.candidates_count ?? 0} />
              <MicroCard label="Screened" value={ico?.screened_count ?? 0} />
              <MicroCard label="Scored" value={ico?.scored_count ?? 0} />
              <MicroCard label="Allocation" value={ico?.allocation_count ?? 0} />
            </div>
          </>
        )}
      </SectionCard>

      <SectionCard title="Whales & Smart Money" subtitle="Secondary intelligence block kept below execution and PnL tracking">
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && !(whales?.tracked_wallets > 0)}
          emptyText="No whale leaderboard available."
        />
        {!loading && !err && data && (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <MicroCard label="Tracked Wallets" value={whales?.tracked_wallets ?? 0} />
              <MicroCard
                label="Average Win Rate"
                value={whales?.average_win_rate === null || whales?.average_win_rate === undefined ? "N/A" : fmtPct(whales.average_win_rate, 1)}
              />
              <MicroCard
                label="Best 30D PnL"
                value={whales?.best_30d_pnl === null || whales?.best_30d_pnl === undefined ? "N/A" : fmtCurrency(whales.best_30d_pnl)}
              />
            </div>
          </>
        )}
      </SectionCard>
    </div>
  );
}
