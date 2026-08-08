import { API_BASE, buildApiUrl as apiUrl } from "../lib/apiBase";
import React, { useEffect, useMemo, useState } from "react";
import NscSidebar from "../components/layout/NscSidebar";
import {
  Building2,
  ShieldCheck,
  Landmark,
  GitBranch,
  Wallet,
  AlertTriangle,
  RefreshCw,
  Lock,
} from "lucide-react";


function formatEUR(value) {
  const n = Number(value || 0);
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(n);
}

function formatPct(value) {
  const n = Number(value || 0);
  return `${(n * 100).toFixed(1)}%`;
}

function badgeClass(value) {
  const v = String(value || "").toLowerCase();

  if (["ok", "normal", "safe", "preprod", "virtual", "simulated"].includes(v)) {
    return "border-emerald-400/30 bg-emerald-400/10 text-emerald-200";
  }

  if (["proposed", "manual_review_required", "caution", "controlled"].includes(v)) {
    return "border-amber-400/30 bg-amber-400/10 text-amber-200";
  }

  if (["danger", "blocked", "error", "survival"].includes(v)) {
    return "border-red-400/30 bg-red-400/10 text-red-200";
  }

  return "border-slate-500/40 bg-slate-500/10 text-slate-200";
}

function Card({ title, icon: Icon, children, right }) {
  return (
    <section className="rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 p-3 shadow-[0_0_28px_rgba(15,23,42,0.35)] transition-all duration-300 hover:border-cyan-500/25 hover:shadow-[0_0_32px_rgba(34,211,238,0.08)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {Icon ? (
            <div className="rounded-xl border border-cyan-400/20 bg-cyan-400/10 p-2 text-cyan-300">
              <Icon size={18} />
            </div>
          ) : null}
          <h2 className="text-[13px] font-semibold uppercase tracking-[0.18em] text-white">
            {title}
          </h2>
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

function Metric({ label, value, helper }) {
  return (
    <div className="rounded-xl border border-[#172231] bg-[#0d1520] px-3 py-2 transition-all duration-300 hover:border-cyan-500/25 hover:bg-[#101b29]">
      <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-1 text-base font-semibold text-white">{value}</p>
      {helper ? <p className="mt-1 text-[11px] text-slate-400">{helper}</p> : null}
    </div>
  );
}

function Badge({ children }) {
  return (
    <span className={`inline-flex rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide ${badgeClass(children)}`}>
      {children || "unknown"}
    </span>
  );
}

export default function FamilyOfficeDashboard() {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");

  async function load() {
    try {
      setStatus("loading");
      const res = await fetch(`${API_BASE}/api/family-office`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setStatus("ok");
      setError("");
    } catch (e) {
      setStatus("error");
      setError(e?.message || "Erreur inconnue");
    }
  }

  useEffect(() => {
    load();
  }, []);

  const headline = data?.headline || {};
  const cards = data?.ui_cards || {};
  const context = data?.capital_context || {};
  const treasuryState = data?.treasury_state || data?.treasuryState || {};
  const treasury = treasuryState?.treasury || {};
  const collateral = data?.collateral_state || {};
  const funding = data?.funding_plan || {};
  const rebalance = data?.rebalance_plan || {};
  const portfolio = data?.portfolio_state || {};

  const allocationRows = useMemo(() => {
    const targets = portfolio?.target_weights || {};
    const current = portfolio?.current_weights || {};
    const drift = portfolio?.drift || {};

    return Object.keys({ ...targets, ...current, ...drift })
      .filter((k) => !["options_v2_shadow"].includes(k))
      .map((key) => ({
        key,
        target: Number(targets[key] || 0),
        current: Number(current[key] || 0),
        drift: Number(drift[key] || 0),
      }))
      .sort((a, b) => Math.abs(b.current) + Math.abs(b.target) - (Math.abs(a.current) + Math.abs(a.target)));
  }, [portfolio]);

  const bucketLabel = (key) => ({
    cash: "Cash",
    crypto_trading: "Crypto Trading",
    crypto_lt: "Crypto LT",
    equities_offensive: "Offensive Equities",
    equities_defensive: "Defensive Equities",
    equities_lt: "Equities LT",
    bonds: "Bonds",
    gold: "Gold",
    options: "Options",
    tax_reserve: "Tax Reserve",
    bfr_reserve: "BFR Reserve",
    security_reserve: "Security Reserve",
  }[key] || String(key || "—").replaceAll("_", " "));

  const capitalMatrixRows = useMemo(() => {
    const weights = portfolio?.current_weights || {};
    const targets = portfolio?.target_weights || {};
    const keys = Object.keys({ ...weights, ...targets })
      .filter((k) => k !== "options_v2_shadow")
      .filter((k) => Number(weights[k] || 0) > 0 || Number(targets[k] || 0) > 0)
      .sort((a, b) => Number(weights[b] || 0) - Number(weights[a] || 0));

    const spans = ["col-span-5 row-span-2", "col-span-4", "col-span-3", "col-span-3", "col-span-3", "col-span-2"];

    return keys.slice(0, 6).map((key, idx) => {
      const w = Number(weights[key] || 0);
      const tone = key.includes("cash") || key.includes("lt") ? "emerald" : key.includes("crypto") ? "cyan" : "amber";
      return [bucketLabel(key), `${(w * 100).toFixed(1)}%`, tone, spans[idx] || "col-span-3"];
    });
  }, [portfolio]);

  const strategicAssetRows = useMemo(() => {
    const values = portfolio?.current_values_eur || {};
    const nav = Number(portfolio?.nav_eur || headline?.nav_eur || 0);
    const preferred = ["crypto_lt", "equities_lt", "gold", "cash", "security_reserve"];

    return preferred
      .filter((key) => Number(values[key] || 0) > 0)
      .map((key) => {
        const value = Number(values[key] || 0);
        const alloc = nav > 0 ? `${((value / nav) * 100).toFixed(1)}%` : "—";
        const tone = key === "cash" || key.includes("lt") ? "emerald" : key === "gold" ? "amber" : "cyan";
        return [bucketLabel(key), formatEUR(value), alloc, tone];
      });
  }, [portfolio, headline]);

  const treasuryFlowRows = useMemo(() => {
    const cashWeight = Number(treasuryState?.weights?.cash_weight ?? treasuryState?.treasury?.liquid_cash_eur / Math.max(1, treasuryState?.nav_eur || 1) ?? 0);
    const proposedOutflows = Number(treasuryState?.funding_impact?.proposed_outflows_from_cash_eur || 0);
    const nav = Number(treasuryState?.nav_eur || headline?.nav_eur || 0);
    const fundingPressure = nav > 0 ? Math.min(100, Math.round((proposedOutflows / nav) * 100)) : 0;
    const treasuryStable = treasuryState?.health?.treasury_health === "normal" ? 88 : treasuryState?.health?.cash_negative_after_proposed ? 25 : 60;
    const liquidityReserve = Math.round(Math.max(0, Math.min(100, cashWeight * 100)));
    const rebalanceLoad = Number(rebalance?.kpis?.actions_proposed || 0) > 0
      ? Math.min(100, Number(rebalance?.kpis?.actions_proposed || 0) * 25)
      : 0;

    return [
      ["Cash Liquidity", liquidityReserve, liquidityReserve >= 70 ? "emerald" : "amber"],
      ["Funding Pressure", fundingPressure, fundingPressure >= 30 ? "amber" : "emerald"],
      ["Treasury Stability", treasuryStable, treasuryStable >= 75 ? "cyan" : "amber"],
      ["Liquidity Reserve", liquidityReserve, liquidityReserve >= 70 ? "emerald" : "amber"],
      ["Rebalance Load", rebalanceLoad, rebalanceLoad > 0 ? "amber" : "emerald"],
    ];
  }, [treasuryState, headline, rebalance]);

  const timelineRows = useMemo(() => {
    return [
      ["Rebalance governance", `Status: ${(rebalance?.status || "unknown").toUpperCase()} · proposed actions: ${rebalance?.kpis?.actions_proposed || 0}`, rebalance?.engine || "rebalance engine", "cyan"],
      ["Treasury validation", `Health: ${(treasuryState?.health?.treasury_health || "unknown").toUpperCase()} · cash: ${formatEUR(treasury?.liquid_cash_eur)}`, treasuryState?.updated_at || "latest API state", "emerald"],
      ["Funding request", `Manual reviews: ${funding?.kpis?.manual_review_required || 0} · transfers: ${funding?.kpis?.transfers_total || 0}`, funding?.engine || "funding engine", "amber"],
      ["Collateral state", `Debt: ${collateral?.governance?.new_debt_allowed ? "OPEN" : "RESTRICTED"} · LTV: ${formatPct(collateral?.ltv_current)}`, collateral?.updated_at || "latest API state", "amber"],
      ["PREPROD governance", `Capital mode: ${(headline?.capital_mode || "unknown").toUpperCase()} · valuation: ${(headline?.valuation_mode || "unknown").toUpperCase()}`, context?.engine || "capital context", "cyan"],
    ];
  }, [rebalance, treasuryState, treasury, funding, collateral, headline, context]);

  if (status === "error") {
    return (
      <main className="min-h-screen bg-[#050811] p-3 text-slate-100">
        <Card title="Family Office Dashboard" icon={AlertTriangle}>
          <p className="text-red-300">Impossible de charger /api/family-office : {error}</p>
          <button
            onClick={load}
            className="mt-4 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800"
          >
            Réessayer
          </button>
        </Card>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar />
      <main className="min-h-screen p-3 pl-64 text-slate-100">
        <div className="mx-auto max-w-[1560px] space-y-3">
        <header className="rounded-2xl border border-[#1f2a37] bg-[radial-gradient(circle_at_top_left,#0f2a3a_0%,#09111a_42%,#05080d_100%)] p-3 shadow-[0_0_40px_rgba(34,211,238,0.08)]">
          <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-start">
            <div>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Badge>{headline.environment}</Badge>
                <Badge>{headline.capital_mode}</Badge>
                <Badge>{headline.valuation_mode}</Badge>
                {data?.warnings?.length ? (
                  <span className="inline-flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-xs text-amber-200">
                    <AlertTriangle size={13} />
                    Capital virtuel PREPROD
                  </span>
                ) : null}
              </div>
              <h1 className="text-base font-semibold tracking-tight text-white">
                Family Office Control Room
              </h1>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">
                Vue patrimoniale NSC alignée sur le standard V4 : valeur d’entreprise simulée, trésorerie,
                collatéral, funding, rebalance et gouvernance capital.
              </p>
            </div>

            <button
              onClick={load}
              className="inline-flex items-center gap-2 rounded-xl border border-cyan-500/25 bg-cyan-500/10 px-3 py-2 text-sm font-semibold text-cyan-200 transition-all duration-300 hover:scale-[1.015] hover:bg-cyan-500/15"
            >
              <RefreshCw size={16} />
              Actualiser
            </button>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-4">
            <Metric
              label="Enterprise Value"
              value={formatEUR(headline.enterprise_net_value_eur)}
              helper="Simulated enterprise net value"
            />
            <Metric label="NAV" value={formatEUR(headline.nav_eur)} helper="Capital PREPROD virtuel" />
            <Metric label="Cash liquide" value={formatEUR(headline.liquid_cash_eur)} helper="Non déployé réel" />
            <Metric label="Survival Mode" value={headline.survival_mode || "UNKNOWN"} helper="Gouvernance capital" />
          </div>
        </header>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-6 gap-3">
          {[
            ["Enterprise NAV", formatEUR(headline.enterprise_net_value_eur), "cyan"],
            ["Treasury", formatEUR(treasury.total_treasury_eur), "emerald"],
            ["Collateral", formatEUR(collateral.eligible_collateral_value_eur), "cyan"],
            ["Survival", headline.survival_mode || "NORMAL", "amber"],
            ["Funding", funding.status || "PROPOSED", "amber"],
            ["Governance", headline.capital_mode || "SIMULATED", "emerald"],
          ].map(([label, value, tone], idx) => {
            const cls =
              tone === "emerald"
                ? "border-emerald-500/20 bg-emerald-500/8"
                : tone === "amber"
                  ? "border-amber-500/20 bg-amber-500/8"
                  : "border-cyan-500/20 bg-cyan-500/8";

            return (
              <div
                key={idx}
                className={`rounded-2xl border px-3 py-2 shadow-[0_0_24px_rgba(15,23,42,0.45)] transition-all duration-300 hover:scale-[1.01] ${cls}`}
              >
                <div className="text-[9px] uppercase tracking-[0.22em] text-slate-500">
                  {label}
                </div>

                <div className="mt-2 text-base font-semibold tracking-tight text-white">
                  {value}
                </div>
              </div>
            );
          })}
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.05fr_0.95fr]">
          <section className="rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 p-3 shadow-[0_0_30px_rgba(34,211,238,0.05)]">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-300/70">
                  Family Office War Room
                </div>

                <div className="mt-1 text-base font-semibold text-white">
                  Capital Governance Active
                </div>
              </div>

              <div className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-300">
                PREPROD
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {[
                ["Treasury Stability", "Stable", "emerald"],
                ["Collateral Safety", cards?.collateral?.status || "SAFE", "cyan"],
                ["Debt Capacity", collateral?.governance?.new_debt_allowed ? "Open" : "Restricted", "amber"],
                ["Funding Governance", funding.status || "Controlled", "amber"],
              ].map(([label, value, tone], idx) => {
                const cls =
                  tone === "emerald"
                    ? "border-emerald-500/20 bg-emerald-500/8 text-emerald-300"
                    : tone === "amber"
                      ? "border-amber-500/20 bg-amber-500/8 text-amber-300"
                      : "border-cyan-500/20 bg-cyan-500/8 text-cyan-300";

                return (
                  <div
                    key={idx}
                    className={`rounded-xl border px-3 py-2 ${cls}`}
                  >
                    <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">
                      {label}
                    </div>

                    <div className="mt-2 text-base font-semibold text-white">
                      {value}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 rounded-xl border border-cyan-500/15 bg-cyan-500/5 p-3 text-[12px] leading-6 text-slate-300">
              Family Office governance layer remains fully simulated under PREPROD capital rules.
              Funding, treasury, collateral and rebalance decisions are monitored through the NSC policy layer.
            </div>
          </section>

          <section className="rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 p-3 shadow-[0_0_30px_rgba(34,211,238,0.05)]">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-300/70">
                  Allocation Intelligence
                </div>

                <div className="mt-1 text-base font-semibold text-white">
                  Family Capital Distribution
                </div>
              </div>

              <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/25 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-cyan-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.75)]" />
                LIVE
              </div>
            </div>

            <div className="space-y-3">
              {allocationRows.slice(0, 6).map((row) => {
                const pct = Math.max(4, row.current * 100);

                return (
                  <div key={row.key}>
                    <div className="mb-1 flex items-center justify-between text-[12px]">
                      <span className="text-slate-300">{row.key}</span>
                      <span className="text-white">{(row.current * 100).toFixed(1)}%</span>
                    </div>

                    <div className="h-2 overflow-hidden rounded-full bg-[#0f1722]">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-cyan-300 to-emerald-300 shadow-[0_0_14px_rgba(34,211,238,0.45)]"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-[12px] text-amber-200">
              Cross-universe funding remains manually governed between crypto venues and IBKR pools.
            </div>
          </section>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-7 gap-2">
          {[
            ["NAV", formatEUR(headline.nav_eur), "cyan"],
            ["Enterprise", formatEUR(headline.enterprise_net_value_eur), "emerald"],
            ["Treasury", formatEUR(treasury.total_treasury_eur), "cyan"],
            ["Collateral", cards?.collateral?.status || "SAFE", "emerald"],
            ["Funding", (funding.status || "PROPOSED").toUpperCase(), "amber"],
            ["Governance", (headline.capital_mode || "SIMULATED").toUpperCase(), "amber"],
            ["PREPROD", "LOCKED", "cyan"],
          ].map(([label, value, tone], idx) => {
            const cls =
              tone === "emerald"
                ? "border-emerald-500/20 bg-emerald-500/8"
                : tone === "amber"
                  ? "border-amber-500/20 bg-amber-500/8"
                  : "border-cyan-500/20 bg-cyan-500/8";

            return (
              <div
                key={idx}
                className={`rounded-2xl border px-3 py-2 shadow-[0_0_20px_rgba(15,23,42,0.35)] backdrop-blur-sm transition-all duration-300 hover:scale-[1.015] hover:border-cyan-500/30 hover:shadow-[0_0_32px_rgba(34,211,238,0.12)] ${cls}`}
              >
                <div className="text-[9px] uppercase tracking-[0.22em] text-slate-500">
                  {label}
                </div>

                <div className="mt-2 truncate text-base font-semibold text-white">
                  {value}
                </div>
              </div>
            );
          })}
        </div>

        <section className="relative overflow-hidden rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 p-3 shadow-[0_0_34px_rgba(34,211,238,0.06)]">
          <div className="pointer-events-none absolute inset-0 opacity-25 [background-image:linear-gradient(rgba(34,211,238,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.04)_1px,transparent_1px)] [background-size:42px_42px]" />
          <div className="pointer-events-none absolute left-1/2 top-1/2 h-72 w-72 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full bg-cyan-400/5 blur-3xl" />

          <div className="relative mb-3 flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-300/70">
                NSC Global Structure Graph
              </div>
              <div className="mt-1 text-base font-semibold text-white">
                Holding, Capital Pools & Operating Sleeves
              </div>
            </div>

            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/25 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-cyan-300">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.75)]" />
              STRUCTURE LIVE
            </div>
          </div>

          <div className="relative h-[340px] overflow-hidden rounded-2xl border border-[#172231] bg-[radial-gradient(circle_at_center,#0f1d2e_0%,#09111b_70%)]">
            <div className="absolute left-[50%] top-[14%] h-[330px] w-[2px] -translate-x-1/2 bg-cyan-400/20" />
            <div className="absolute left-[18%] top-[45%] h-[2px] w-[64%] bg-cyan-400/20" />
            <div className="absolute left-[28%] top-[70%] h-[2px] w-[44%] bg-cyan-400/15" />
            <div className="absolute left-[50%] top-[45%] h-[2px] w-[48%] -translate-x-1/2 rotate-12 bg-cyan-400/10" />
            <div className="absolute left-[50%] top-[45%] h-[2px] w-[48%] -translate-x-1/2 -rotate-12 bg-cyan-400/10" />

            {[
              ["Nova Star Capital", "holding governance", "emerald", "50%", "7%"],
              ["NSC Trading", "alpha engines", "cyan", "18%", "36%"],
              ["Family Office", "capital governance", "emerald", "50%", "36%"],
              ["NSC Private Equity", "future illiquid sleeve", "cyan", "82%", "36%"],
              ["Treasury Reserve", "liquidity & safety", "emerald", "31%", "66%"],
              ["IBKR Pool", "equities / bonds / metals", "cyan", "50%", "66%"],
              ["Crypto Venues", "Binance / MEXC", "amber", "69%", "66%"],
              ["Long-Term Vault", "strategic holdings", "emerald", "50%", "84%"],
            ].map(([label, detail, tone, x, y], idx) => {
              const cls =
                tone === "emerald"
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : tone === "amber"
                    ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                    : "border-cyan-500/30 bg-cyan-500/10 text-cyan-300";

              return (
                <div
                  key={idx}
                  className={`absolute w-[165px] -translate-x-1/2 rounded-2xl border px-3 py-2 backdrop-blur-sm transition-all duration-300 hover:scale-[1.03] hover:shadow-[0_0_28px_rgba(34,211,238,0.14)] ${cls}`}
                  style={{ left: x, top: y }}
                >
                  <div className="flex items-center justify-between">
                    <div className="text-[10px] font-semibold uppercase tracking-wide">{label}</div>
                    <span className="h-2 w-2 animate-pulse rounded-full bg-current opacity-80 shadow-[0_0_10px_currentColor]" />
                  </div>
                  <div className="mt-2 text-[12px] opacity-85">{detail}</div>
                </div>
              );
            })}
          </div>

          <div className="relative mt-3 rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-3 text-[12px] leading-6 text-cyan-100">
            NSC global structure connects holding governance, capital pools, execution venues and long-term preservation sleeves under one supervised Family Office layer.
          </div>
        </section>

        <div className="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="relative overflow-hidden rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 p-3 shadow-[0_0_30px_rgba(34,211,238,0.05)]">
            <div className="pointer-events-none absolute inset-0 opacity-20 [background-image:linear-gradient(rgba(34,211,238,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.04)_1px,transparent_1px)] [background-size:42px_42px]" />
            <div className="pointer-events-none absolute right-10 top-10 h-32 w-32 animate-pulse rounded-full bg-cyan-400/5 blur-3xl" />
            <div className="relative mb-3 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-300/70">
                  Institutional Capital Heatmap
                </div>

                <div className="mt-1 text-base font-semibold text-white">
                  NSC Capital Distribution Matrix
                </div>
              </div>

              <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/25 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-cyan-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.75)]" />
                LIVE
              </div>
            </div>

            <div className="relative grid grid-cols-12 gap-3">
              {capitalMatrixRows.map(([label, value, tone, span], idx) => {
                const cls =
                  tone === "emerald"
                    ? "border-emerald-500/20 bg-emerald-500/10"
                    : tone === "amber"
                      ? "border-amber-500/20 bg-amber-500/10"
                      : "border-cyan-500/20 bg-cyan-500/10";

                return (
                  <div
                    key={idx}
                    className={`rounded-2xl border p-3 transition-all duration-300 hover:scale-[1.02] hover:border-cyan-500/35 hover:shadow-[0_0_28px_rgba(34,211,238,0.16)] ${cls} ${span}`}
                  >
                    <div className="flex h-full flex-col justify-between">
                      <div className="text-[10px] uppercase tracking-[0.18em] text-slate-400">
                        {label}
                      </div>

                      <div className="mt-4 text-base font-semibold tracking-tight text-white">
                        {value}
                      </div>

                      <div className="mt-3 h-1.5 rounded-full bg-black/30">
                        <div
                          className="h-1.5 animate-pulse rounded-full bg-current opacity-80 shadow-[0_0_12px_currentColor]"
                          style={{ width: value }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-3 text-[12px] leading-6 text-cyan-100">
              Capital allocation remains dynamically supervised by governance caps, liquidity requirements and PREPROD treasury constraints.
            </div>
          </section>

          <section className="rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 p-3 shadow-[0_0_30px_rgba(34,211,238,0.05)]">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-300/70">
                  Long-Term Holdings Layer
                </div>

                <div className="mt-1 text-base font-semibold text-white">
                  Strategic Asset Preservation
                </div>
              </div>

              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.75)]" />
                ACTIVE
              </div>
            </div>

            <div className="space-y-3">
              {strategicAssetRows.map(([asset, desc, alloc, tone], idx) => {
                const dot =
                  tone === "emerald"
                    ? "bg-emerald-400"
                    : tone === "amber"
                      ? "bg-amber-400"
                      : "bg-cyan-400";

                return (
                  <div
                    key={idx}
                    className="rounded-xl border border-[#172231] bg-[#0b1420] p-3 transition-all duration-300 hover:scale-[1.01] hover:border-cyan-500/30 hover:bg-[#101b29]"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className={`h-3 w-3 rounded-full ${dot} shadow-[0_0_10px_currentColor]`} />

                        <div>
                          <div className="font-semibold text-white">
                            {asset}
                          </div>

                          <div className="text-[12px] text-slate-400">
                            {desc}
                          </div>
                        </div>
                      </div>

                      <div className="text-base font-semibold text-white">
                        {alloc}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-[12px] leading-6 text-emerald-100">
              Long-term holdings remain isolated from short-term execution engines and are governed through preservation-oriented allocation rules.
            </div>
          </section>
        </div>

        <div className="grid gap-3 lg:grid-cols-[1fr_1fr]">
          <section className="rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 p-3 shadow-[0_0_30px_rgba(34,211,238,0.05)]">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-300/70">
                  AI Governance Commentary
                </div>

                <div className="mt-1 text-base font-semibold text-white">
                  Family Office Decision Rationale
                </div>
              </div>

              <div className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-300">
                AI WATCH
              </div>
            </div>

            <div className="space-y-3">
              {[
                ["Capital Protection", "Treasury and collateral states remain stable under PREPROD governance.", "emerald"],
                ["Funding Logic", "Cross-universe transfers remain manual to avoid uncontrolled capital movement.", "amber"],
                ["Debt Capacity", "New debt remains restricted until collateral and liquidity buffers are validated.", "amber"],
                ["Rebalance Interpretation", "Current rebalance actions are proposed but not automatically executed.", "cyan"],
              ].map(([label, text, tone], idx) => {
                const cls =
                  tone === "emerald"
                    ? "border-emerald-500/20 bg-emerald-500/8"
                    : tone === "amber"
                      ? "border-amber-500/20 bg-amber-500/8"
                      : "border-cyan-500/20 bg-cyan-500/8";

                return (
                  <div key={idx} className={`rounded-xl border p-3 ${cls}`}>
                    <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                      {label}
                    </div>
                    <div className="mt-2 text-[13px] leading-6 text-slate-300">
                      {text}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 p-3 shadow-[0_0_30px_rgba(34,211,238,0.05)]">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-300/70">
                  Cross-Universe Funding Bridge
                </div>

                <div className="mt-1 text-base font-semibold text-white">
                  IBKR / Crypto / Treasury Routing
                </div>
              </div>

              <div className="rounded-full border border-amber-500/25 bg-amber-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-300">
                MANUAL
              </div>
            </div>

            <div className="relative h-[260px] overflow-hidden rounded-2xl border border-[#172231] bg-[radial-gradient(circle_at_center,#0f1d2e_0%,#09111b_70%)]">
              <div className="pointer-events-none absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(34,211,238,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.05)_1px,transparent_1px)] [background-size:38px_38px]" />

              <div className="absolute left-[50%] top-[50%] h-[2px] w-[460px] -translate-x-1/2 bg-cyan-400/20" />
              <div className="absolute left-[50%] top-[50%] h-[180px] w-[2px] -translate-y-1/2 bg-cyan-400/20" />

              {[
                ["Treasury", "capital reserve", "emerald", "50%", "10%"],
                ["IBKR Pool", "equities / bonds / metals", "cyan", "18%", "50%"],
                ["Crypto Pool", "Binance / MEXC", "amber", "82%", "50%"],
                ["Policy Layer", "manual approval", "cyan", "50%", "72%"],
              ].map(([label, detail, tone, x, y], idx) => {
                const cls =
                  tone === "emerald"
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                    : tone === "amber"
                      ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                      : "border-cyan-500/30 bg-cyan-500/10 text-cyan-300";

                return (
                  <div
                    key={idx}
                    className={`absolute w-[150px] -translate-x-1/2 rounded-2xl border px-3 py-2 backdrop-blur-sm transition-all duration-300 hover:scale-[1.03] ${cls}`}
                    style={{ left: x, top: y }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="text-[10px] font-semibold uppercase tracking-wide">{label}</div>
                      <span className="h-2 w-2 animate-pulse rounded-full bg-current opacity-80" />
                    </div>
                    <div className="mt-2 text-[12px] opacity-85">{detail}</div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-[12px] leading-6 text-amber-200">
              Automated routing remains disabled. Any funding bridge between universes requires manual governance validation.
            </div>
          </section>
        </div>

        <div className="grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
          <section className="rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 p-3 shadow-[0_0_30px_rgba(34,211,238,0.05)]">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-300/70">
                  Treasury Flow Engine
                </div>

                <div className="mt-1 text-base font-semibold text-white">
                  Liquidity & Funding Flows
                </div>
              </div>

              <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/25 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-cyan-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.75)]" />
                LIVE
              </div>
            </div>

            <div className="space-y-3">
              {treasuryFlowRows.map(([label, score, tone], idx) => {
                const width = Math.max(4, Number(score));

                const bar =
                  tone === "emerald"
                    ? "from-emerald-400 to-emerald-300"
                    : tone === "amber"
                      ? "from-amber-300 to-yellow-200"
                      : "from-cyan-400 to-cyan-300";

                return (
                  <div key={idx}>
                    <div className="mb-1 flex items-center justify-between text-[12px]">
                      <span className="text-slate-300">{label}</span>
                      <span className="text-white">{score}%</span>
                    </div>

                    <div className="h-2 overflow-hidden rounded-full bg-[#111a25]">
                      <div
                        className={`h-full rounded-full bg-gradient-to-r ${bar} shadow-[0_0_14px_rgba(34,211,238,0.35)] transition-all duration-700`}
                        style={{ width: `${width}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-[12px] leading-6 text-amber-200">
              Treasury orchestration remains supervised by PREPROD governance and manual inter-universe funding controls.
            </div>
          </section>

          <section className="rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 p-3 shadow-[0_0_30px_rgba(34,211,238,0.05)]">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-300/70">
                  Institutional Timeline
                </div>

                <div className="mt-1 text-base font-semibold text-white">
                  Governance & Capital Events
                </div>
              </div>

              <div className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-300">
                STREAM
              </div>
            </div>

            <div className="relative space-y-3 border-l border-cyan-500/20 pl-6">
              {timelineRows.map(([title, detail, time, tone], idx) => {
                const dot =
                  tone === "emerald"
                    ? "bg-emerald-400"
                    : tone === "amber"
                      ? "bg-amber-300"
                      : "bg-cyan-400";

                return (
                  <div key={idx} className="relative">
                    <div className={`absolute -left-[31px] top-1 h-3 w-3 rounded-full ${dot} shadow-[0_0_10px_rgba(34,211,238,0.5)]`} />

                    <div className="rounded-xl border border-[#172231] bg-[#0d1520] p-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-sm font-semibold text-white">
                          {title}
                        </div>

                        <div className="text-[11px] uppercase tracking-wide text-slate-500">
                          {time}
                        </div>
                      </div>

                      <div className="mt-1 text-[12px] text-slate-400">
                        {detail}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>

        <div className="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 p-3 shadow-[0_0_30px_rgba(34,211,238,0.05)]">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-300/70">
                  Enterprise Structure Map
                </div>
                <div className="mt-1 text-base font-semibold text-white">
                  Nova Star Capital Architecture
                </div>
              </div>

              <div className="rounded-full border border-cyan-500/25 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-cyan-300">
                STRUCTURE
              </div>
            </div>

            <div className="relative h-[260px] overflow-hidden rounded-2xl border border-[#172231] bg-[radial-gradient(circle_at_center,#0f1d2e_0%,#09111b_68%)]">
              <div className="pointer-events-none absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(34,211,238,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.05)_1px,transparent_1px)] [background-size:38px_38px]" />
              <div className="pointer-events-none absolute left-1/2 top-1/2 h-48 w-48 -translate-x-1/2 -translate-y-1/2 animate-pulse rounded-full bg-cyan-400/5 blur-3xl" />

              {[
                ["Nova Star Capital", "holding layer", "emerald", "50%", "10%"],
                ["NSC Trading", "alpha engine", "cyan", "22%", "38%"],
                ["NSC Real Estate", "asset layer", "amber", "50%", "38%"],
                ["NSC Private Equity", "future sleeve", "cyan", "78%", "38%"],
                ["Long Term Holdings", "patrimonial core", "emerald", "36%", "70%"],
                ["IBKR Pool", "equities / bonds / metals", "cyan", "64%", "70%"],
                ["Crypto Pool", "Binance / MEXC", "amber", "50%", "84%"],
              ].map(([label, detail, tone, x, y], idx) => {
                const cls =
                  tone === "emerald"
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                    : tone === "amber"
                      ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                      : "border-cyan-500/30 bg-cyan-500/10 text-cyan-300";

                return (
                  <div
                    key={idx}
                    className={`absolute w-[160px] -translate-x-1/2 rounded-2xl border px-3 py-2 backdrop-blur-sm transition-all duration-300 hover:scale-[1.03] ${cls}`}
                    style={{ left: x, top: y }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="text-[10px] font-semibold uppercase tracking-wide">{label}</div>
                      <span className="h-2 w-2 animate-pulse rounded-full bg-current opacity-80" />
                    </div>
                    <div className="mt-2 text-[12px] opacity-85">{detail}</div>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="rounded-2xl border border-[#1f2a37] bg-[#09111a]/95 p-3 shadow-[0_0_30px_rgba(34,211,238,0.05)]">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase tracking-[0.24em] text-cyan-300/70">
                  Family Governance Matrix
                </div>
                <div className="mt-1 text-base font-semibold text-white">
                  Capital Protection State
                </div>
              </div>

              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.75)]" />
                ACTIVE
              </div>
            </div>

            <div className="space-y-3">
              {[
                ["Treasury Governance", "STABLE", 88, "emerald"],
                ["Collateral Governance", (cards?.collateral?.status || "SAFE").toUpperCase(), 82, "cyan"],
                ["Debt Governance", collateral?.governance?.new_debt_allowed ? "OPEN" : "RESTRICTED", 64, "amber"],
                ["Funding Governance", (funding.status || "PROPOSED").toUpperCase(), 68, "amber"],
                ["Rebalance Governance", (rebalance.status || "PROPOSED").toUpperCase(), 72, "cyan"],
                ["Capital Preservation", "CONTROLLED", 86, "emerald"],
              ].map(([label, state, score, tone], idx) => {
                const width = Math.max(5, Math.min(100, Number(score)));
                const bar =
                  tone === "emerald"
                    ? "bg-emerald-400"
                    : tone === "amber"
                      ? "bg-amber-300"
                      : "bg-cyan-400";

                return (
                  <div key={idx}>
                    <div className="mb-1 flex items-center justify-between text-[12px]">
                      <span className="font-semibold text-slate-200">{label}</span>
                      <span className="text-slate-500">{state}</span>
                    </div>
                    <div className="h-1.5 rounded bg-[#172231]">
                      <div
                        className={`h-1.5 rounded ${bar} shadow-[0_0_10px_rgba(34,211,238,0.25)]`}
                        style={{ width: `${width}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-3 text-[12px] leading-6 text-slate-300">
              The Family Office layer monitors treasury, collateral, debt capacity and funding decisions under PREPROD governance.
            </div>
          </section>
        </div>

        <div className="grid gap-3 lg:grid-cols-3">
          <Card
            title="Enterprise Value"
            icon={Building2}
            right={<Badge>{cards?.enterprise_value?.mode}</Badge>}
          >
            <div className="space-y-3">
              <Metric label="Net Value" value={formatEUR(cards?.enterprise_value?.value)} />
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-sm text-slate-400">
                Cette valeur est simulée en préproduction. Elle n’est ni une NAV comptable,
                ni une valorisation fiscale, ni une valeur réalisable.
              </div>
            </div>
          </Card>

          <Card title="Treasury" icon={Wallet} right={<Badge>{cards?.treasury?.health}</Badge>}>
            <div className="grid grid-cols-2 gap-3">
              <Metric label="Cash" value={formatEUR(treasury.liquid_cash_eur)} />
              <Metric label="Total treasury" value={formatEUR(treasury.total_treasury_eur)} />
              <Metric label="Impôts" value={formatEUR(treasury.tax_reserve_eur)} />
              <Metric label="Sécurité" value={formatEUR(treasury.security_reserve_eur)} />
            </div>
          </Card>

          <Card title="Collateral" icon={Landmark} right={<Badge>{cards?.collateral?.status}</Badge>}>
            <div className="grid grid-cols-2 gap-3">
              <Metric label="Éligible" value={formatEUR(collateral.eligible_collateral_value_eur)} />
              <Metric label="LTV" value={formatPct(collateral.ltv_current)} />
              <Metric
                label="Capacité 25%"
                value={formatEUR(collateral?.capacity?.remaining_start_capacity_eur)}
              />
              <Metric
                label="Nouvelle dette"
                value={collateral?.governance?.new_debt_allowed ? "Allowed" : "Blocked"}
              />
            </div>
          </Card>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <Card title="Funding Plan" icon={GitBranch} right={<Badge>{funding.status}</Badge>}>
            <div className="mb-4 grid grid-cols-3 gap-3">
              <Metric label="Transferts" value={funding?.kpis?.transfers_total || 0} />
              <Metric label="Review manuel" value={funding?.kpis?.manual_review_required || 0} />
              <Metric label="Bloqués" value={funding?.kpis?.blocked || 0} />
            </div>

            <div className="space-y-3">
              {(funding.transfers || []).map((t, idx) => (
                <div
                  key={`${t.bucket}-${idx}`}
                  className="rounded-xl border border-slate-800 bg-slate-900/50 p-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-white">{t.bucket}</p>
                      <p className="text-xs text-slate-400">
                        {t.from_bucket} → {t.to_bucket} · {t.route?.join(" → ")}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge>{t.status}</Badge>
                      <span className="text-sm font-semibold text-white">{formatEUR(t.amount_eur)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Governance & Rebalance" icon={ShieldCheck} right={<Badge>{rebalance.status}</Badge>}>
            <div className="mb-4 grid grid-cols-3 gap-3">
              <Metric label="Actions" value={rebalance?.kpis?.actions_total || 0} />
              <Metric label="Proposées" value={rebalance?.kpis?.actions_proposed || 0} />
              <Metric label="Réductions" value={rebalance?.kpis?.reduce_count || 0} />
            </div>

            <div className="space-y-3">
              {(rebalance.actions || [])
                .filter((a) => a.status === "proposed")
                .map((a) => (
                  <div key={a.bucket} className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-medium text-white">{a.bucket}</p>
                        <p className="text-xs text-slate-400">{a.reason}</p>
                      </div>
                      <div className="text-right">
                        <Badge>{a.action}</Badge>
                        <p className="mt-1 text-sm font-semibold text-white">{formatEUR(a.delta_eur)}</p>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </Card>
        </div>

        <Card title="Portfolio Allocation & Drift" icon={Lock}>
          <div className="overflow-hidden rounded-xl border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900/80 text-xs uppercase tracking-[0.16em] text-slate-500">
                <tr>
                  <th className="px-4 py-3">Bucket</th>
                  <th className="px-4 py-3">Target</th>
                  <th className="px-4 py-3">Current</th>
                  <th className="px-4 py-3">Drift</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-slate-950/40">
                {allocationRows.map((row) => (
                  <tr key={row.key}>
                    <td className="px-4 py-3 font-medium text-slate-200">{row.key}</td>
                    <td className="px-4 py-3 text-slate-300">{formatPct(row.target)}</td>
                    <td className="px-4 py-3 text-slate-300">{formatPct(row.current)}</td>
                    <td className={`px-4 py-3 ${row.drift > 0 ? "text-amber-200" : row.drift < 0 ? "text-cyan-200" : "text-slate-400"}`}>
                      {formatPct(row.drift)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {data?.warnings?.length ? (
          <Card title="Warnings" icon={AlertTriangle} right={<Badge>PREPROD</Badge>}>
            <ul className="space-y-2 text-sm text-amber-200">
              {data.warnings.map((w, idx) => (
                <li key={idx}>• {w}</li>
              ))}
              <li>• Aucune valeur affichée ne doit être interprétée comme une valeur comptable réelle.</li>
              <li>• Les transferts sont des instructions simulées ou soumises à revue manuelle.</li>
            </ul>
          </Card>
        ) : null}
        </div>
      </main>
    </div>
  );
}
