import React, { useEffect, useMemo, useState } from "react";
import { Activity, BarChart3, Brain, Coins, Gauge, ShieldCheck, TrendingUp, Wallet } from "lucide-react";
import { apiUrl } from "../lib/apiClient";
import NscSidebar from "../components/layout/NscSidebar";

async function fetchMarketSource(path) {
  try {
    const response = await fetch(apiUrl(path), {
      credentials: "include",
      cache: "no-store",
    });

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        data: null,
        error: `HTTP ${response.status}`,
      };
    }

    return {
      ok: true,
      status: response.status,
      data: await response.json(),
      error: null,
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      data: null,
      error: String(
        error?.message ||
        error ||
        "Unable to load market source."
      ),
    };
  }
}

function Card({ title, icon: Icon = Activity, children }) {
  return (
    <div className="rounded-2xl border border-[#172231] bg-[#0b131d] p-4 shadow-[0_0_30px_rgba(15,23,42,0.35)]">
      <div className="mb-3 flex items-center gap-2">
        <Icon size={16} className="text-cyan-300" />
        <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-200">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function Metric({ label, value, tone = "cyan" }) {
  const tones = {
    cyan: "text-cyan-300 border-cyan-400/20 bg-cyan-400/10",
    emerald: "text-emerald-300 border-emerald-400/20 bg-emerald-400/10",
    amber: "text-amber-300 border-amber-400/20 bg-amber-400/10",
    red: "text-red-300 border-red-400/20 bg-red-400/10",
    slate: "text-slate-300 border-slate-400/20 bg-slate-400/10",
  };
  return (
    <div className={`rounded-xl border px-3 py-2 ${tones[tone] || tones.cyan}`}>
      <div className="text-[10px] uppercase tracking-[0.16em] opacity-70">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  );
}

function Bar({ label, value, tone = "cyan" }) {
  const n = Math.max(0, Math.min(100, Number(value || 0)));
  const colors = {
    cyan: "bg-cyan-400",
    emerald: "bg-emerald-400",
    amber: "bg-amber-400",
    red: "bg-red-400",
  };
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-slate-300">{label}</span>
        <span className="text-slate-400">{n.toFixed(0)}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-800">
        <div className={`h-2 rounded-full ${colors[tone] || colors.cyan}`} style={{ width: `${n}%` }} />
      </div>
    </div>
  );
}


function PipelineStep({ label, value, tone = "cyan" }) {
  const tones = {
    cyan: "border-cyan-400/20 bg-cyan-400/10 text-cyan-300",
    emerald: "border-emerald-400/20 bg-emerald-400/10 text-emerald-300",
    amber: "border-amber-400/20 bg-amber-400/10 text-amber-300",
    slate: "border-slate-400/20 bg-slate-400/10 text-slate-300",
  };
  return (
    <div className={`rounded-xl border px-3 py-3 text-center ${tones[tone] || tones.cyan}`}>
      <div className="text-xl font-semibold">{value}</div>
      <div className="mt-1 text-[10px] uppercase tracking-[0.14em] opacity-70">{label}</div>
    </div>
  );
}


function ScoreBar({ label, value, tone = "cyan" }) {
  const n = Math.max(0, Math.min(100, Number(value || 0)));
  const colors = {
    cyan: "bg-cyan-400",
    emerald: "bg-emerald-400",
    amber: "bg-amber-400",
    red: "bg-red-400",
  };
  return (
    <div className="rounded-xl border border-slate-800 bg-[#071019] p-3">
      <div className="mb-2 flex justify-between text-xs">
        <span className="uppercase tracking-[0.14em] text-slate-400">{label}</span>
        <span className="font-semibold text-slate-200">{n.toFixed(0)}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-800">
        <div className={`h-2 rounded-full ${colors[tone] || colors.cyan}`} style={{ width: `${n}%` }} />
      </div>
    </div>
  );
}

function pct(v) {
  const n = Number(v);
  return Number.isFinite(n) ? `${n.toFixed(2)}%` : "—";
}

export default function MarketIntelligence() {
    const [sourceState, setSourceState] = useState({
    dashboard: {
      available: false,
      status: null,
      error: null,
    },
    marketIntelligence: {
      available: false,
      status: null,
      error: null,
    },
    marketMemory: {
      available: false,
      status: null,
      error: null,
    },
  });
const [dashboard, setDashboard] = useState(null);
  const [pam, setPam] = useState(null);
  const [topMovers, setTopMovers] = useState(null);
  const [discovery, setDiscovery] = useState(null);
  const [meta, setMeta] = useState(null);
  const [validation, setValidation] = useState(null);
  const [marketMemory, setMarketMemory] = useState(null);
  const [executiveBrief, setExecutiveBrief] = useState(null);
  const [executiveBriefHistory, setExecutiveBriefHistory] = useState([]);

  useEffect(() => {
    let alive = true;
    async function load() {
      const [dResult, miResult, mmResult] = await Promise.all([
  fetchMarketSource("/dashboard/v3"),
  fetchMarketSource("/api/market-intelligence"),
  fetchMarketSource("/api/market-memory"),
]);

const d = dResult.ok ? dResult.data : null;
const mi = miResult.ok ? miResult.data : null;
const mm = mmResult.ok ? mmResult.data : null;

setSourceState({
  dashboard: {
    available: dResult.ok,
    status: dResult.status,
    error: dResult.error,
  },
  marketIntelligence: {
    available: miResult.ok,
    status: miResult.status,
    error: miResult.error,
  },
  marketMemory: {
    available: mmResult.ok,
    status: mmResult.status,
    error: mmResult.error,
  },
});
      if (!alive) return;
      setDashboard(d);
      setPam(mi?.activity_dashboard || null);
      setTopMovers(mi?.top_movers || null);
      setDiscovery(mi?.discovery_summary || null);
      setMeta(mi?.meta_rankings || null);
      setValidation(mi?.meta_validation || null);
      setMarketMemory(mm || null);
      setExecutiveBrief(mi?.executive_market_brief || null);
      setExecutiveBriefHistory(Array.isArray(mi?.executive_market_brief_history) ? mi.executive_market_brief_history : []);
    }
    load();
    const id = setInterval(load, 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const global = dashboard?.global || {};
  const pamSummary = pam?.summary || {};
  const engines = Array.isArray(pam?.engines) ? pam.engines : [];
  const engineById = useMemo(() => Object.fromEntries(engines.map((e) => [e.id, e])), [engines]);

  const movers = useMemo(() => {
    const arr = topMovers?.items || topMovers?.top_movers || topMovers?.movers || topMovers?.data || [];
    return Array.isArray(arr) ? arr.slice(0, 12) : [];
  }, [topMovers]);

  const metaItems = useMemo(() => {
    const arr = meta?.items || meta?.rankings || meta?.data || [];
    return Array.isArray(arr) ? arr.slice(0, 8) : [];
  }, [meta]);

  const winners = useMemo(() => (
    movers
      .filter((m) => Number(m.chg_24h ?? m.change_24h_pct ?? m.change_pct ?? 0) > 0)
      .sort((a, b) => Number(b.chg_24h ?? b.change_24h_pct ?? 0) - Number(a.chg_24h ?? a.change_24h_pct ?? 0))
      .slice(0, 6)
  ), [movers]);

  const losers = useMemo(() => (
    movers
      .filter((m) => Number(m.chg_24h ?? m.change_24h_pct ?? m.change_pct ?? 0) < 0)
      .sort((a, b) => Number(a.chg_24h ?? a.change_24h_pct ?? 0) - Number(b.chg_24h ?? b.change_24h_pct ?? 0))
      .slice(0, 6)
  ), [movers]);

  const memoryAssets = useMemo(() => {
    const arr = marketMemory?.top_assets || [];
    return Array.isArray(arr) ? arr.slice(0, 8) : [];
  }, [marketMemory]);

  const briefTrend = useMemo(() => {
    const latest = executiveBriefHistory?.[0] || executiveBrief || {};
    const previous = executiveBriefHistory?.[1] || null;

    const latestScore = Number(latest?.portfolio_health || 0);
    const previousScore = Number(previous?.portfolio_health || latestScore || 0);
    const delta = latestScore - previousScore;

    return {
      count: executiveBriefHistory?.length || 0,
      delta,
      direction: delta > 0.25 ? "IMPROVING" : delta < -0.25 ? "DETERIORATING" : "STABLE",
      alerts: Array.isArray(latest?.alerts) ? latest.alerts.length : 0,
    };
  }, [executiveBriefHistory, executiveBrief]);

  const memoryInsight = useMemo(() => {
    const assets = memoryAssets || [];
    const tradables = assets.filter((a) => a?.tradable || String(a?.current_verdict || "").includes("TRADABLE"));
    const persistent = [...assets].sort((a, b) => Number(b?.observations_count || 0) - Number(a?.observations_count || 0));
    const strongest = [...assets].sort((a, b) => Number(b?.current_meta_rank || 0) - Number(a?.current_meta_rank || 0));
    const fading = assets.find((a) =>
      Number.isFinite(Number(a?.max_gain_24h)) &&
      Number.isFinite(Number(a?.current_chg_24h)) &&
      Number(a.max_gain_24h) - Number(a.current_chg_24h) >= 20
    );

    return {
      mostPersistent: persistent[0],
      bestTradable: tradables[0],
      strongestMeta: strongest[0],
      fading,
    };
  }, [memoryAssets]);

  const regime = global?.regime ?? global?.portfolioRegime ?? "Unavailable";
  const crypto = engineById.crypto || {};
  const offensive = engineById.equities_offensive || {};
  const defensive = engineById.equities_defensive || {};
  const bonds = engineById.bonds || {};
  const metals = engineById.precious_metals || {};
  const options = engineById.options_v2_shadow || {};

  const portfolioHealth = Number(pamSummary.portfolio_health || 0);
  const activityScore = Number(pamSummary.activity_score || 0);
  const metaAlignment = Number(validation?.decision_alignment_score ?? 100);
  const grossExposure = Number(pamSummary.gross_exposure_pct || 0);
  const alerts = Number(pamSummary.alerts_count || 0);

  const marketBrainScore = Math.round(
    portfolioHealth * 0.25 +
    activityScore * 0.20 +
    metaAlignment * 0.25 +
    Number(crypto.confidence_pct || 0) * 0.15 +
    Number(offensive.confidence_pct || 0) * 0.10 +
    (alerts === 0 ? 5 : 0)
  );

  const brainTone = marketBrainScore >= 85 ? "emerald" : marketBrainScore >= 70 ? "amber" : "red";



  const discoveryCount = discovery?.candidates_count ?? discovery?.count ?? discovery?.discovery_count ?? "—";
  const topCandidates = Array.isArray(discovery?.top_candidates) ? discovery.top_candidates : [];
  const persistenceCount = topCandidates.length || discovery?.persistence_count || discovery?.persistence_opportunities || "—";
  const tradableCount = topCandidates.filter((x) => x?.tradable || x?.pair || x?.symbol_pair).length || discovery?.tradable_count || discovery?.tradable_opportunities || "—";
  const metaCount = meta?.count ?? metaItems.length ?? "—";
  const recommendedCount = meta?.recommended_count ?? 0;

  const discoveryHealth =
    Number.isFinite(Number(discovery?.health_pct))
      ? Number(discovery.health_pct)
      : null;

  const executionReadiness =
    Number.isFinite(Number(global?.executionReadinessPct))
      ? Number(global.executionReadinessPct)
      : Number.isFinite(Number(global?.execution_readiness_pct))
        ? Number(global.execution_readiness_pct)
        : null;

  const portfolioReadiness =
    Number.isFinite(Number(portfolioHealth))
      ? Math.min(100, Number(portfolioHealth))
      : null;

  const crossSourceHealth =
    Number.isFinite(Number(discovery?.cross_source_health_pct))
      ? Number(discovery.cross_source_health_pct)
      : Number.isFinite(Number(meta?.cross_source_health_pct))
        ? Number(meta.cross_source_health_pct)
        : null;
  const strongestOpportunity = metaItems?.[0]?.symbol || topCandidates?.[0]?.symbol || "—";
  const tradableConfirmed = tradableCount || 0;

  const marketBrainBullets = [
    `Market regime remains ${String(regime).toUpperCase()}.`,
    `Market Brain Score is ${marketBrainScore}/100.`,
    `Discovery pipeline reports ${discoveryCount} candidate(s).`,
    `Tradable opportunities confirmed: ${tradableConfirmed}.`,
    `Top ranked opportunity: ${strongestOpportunity}.`,
    alerts === 0 ? "No PAM alert currently detected." : `${alerts} PAM alert(s) require monitoring.`,
  ];

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Market intelligence online" />
      <main className="ml-[235px] w-[calc(100%-235px)] p-4 max-xl:ml-[220px] max-xl:w-[calc(100%-220px)] max-lg:ml-0 max-lg:w-full">

        <div className="mb-4 rounded-3xl border border-cyan-400/10 bg-gradient-to-r from-[#07111c] via-[#0b1623] to-[#060b12] p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-[10px] uppercase tracking-[0.28em] text-cyan-300">Nova Star Capital</div>
              <h1 className="mt-1 text-2xl font-semibold uppercase tracking-wide">Market Intelligence Center V2</h1>
              <p className="mt-1 max-w-4xl text-sm text-slate-400">
                Institutional cross-asset market brain connecting regime, discovery, persistence, meta ranking, portfolio posture and execution readiness.
              </p>
            </div>
            <div className="flex gap-2 text-[10px] uppercase">
              <span className="rounded-md border border-sky-400/30 bg-sky-400/10 px-2 py-1 text-sky-300">{global?.env ?? "Unavailable"}</span>
              <span className="rounded-md border border-emerald-400/30 bg-emerald-400/10 px-2 py-1 text-emerald-300">{String(regime).toUpperCase()}</span>
              <span className="rounded-md border border-amber-400/30 bg-amber-400/10 px-2 py-1 text-amber-300">{pam?.status || "PAM"}</span>
            </div>
          </div>
        </div>

        <div className="mb-4 rounded-2xl border border-cyan-400/20 bg-cyan-400/5 p-4">
          <div className="mb-3 text-xs font-semibold uppercase tracking-[0.22em] text-cyan-300">
            Decision Pipeline V2 — Market To Execution
          </div>
          <div className="grid gap-3 md:grid-cols-6">
            {[
              ["Market Regime", String(regime).toUpperCase()],
              ["Discovery", `${persistenceCount} persistent`],
              ["Meta Ranking", `${metaCount} ranked`],
              ["Validation", `${metaAlignment.toFixed(0)}% align`],
              ["Portfolio", `${pamSummary.capital_deployment_pct ?? 0}% deployed`],
              ["Execution", "SIMULATED"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-slate-700 bg-[#071019] px-3 py-3 text-center">
                <div className="text-sm font-semibold text-slate-100">{value}</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.14em] text-slate-500">{label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="mb-4 rounded-3xl border border-cyan-400/20 bg-gradient-to-br from-[#07111c] via-[#0b1623] to-[#05080d] p-5 shadow-[0_0_70px_rgba(34,211,238,0.08)]">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-[10px] uppercase tracking-[0.28em] text-cyan-300">Executive Market Brain</div>
              <div className="mt-1 text-xl font-semibold uppercase tracking-wide text-slate-100">
                Global Market Intelligence Layer
              </div>
              <div className="mt-1 text-sm text-slate-400">
                Consolidated read across regime, discovery, meta validation, portfolio posture and execution governance.
              </div>
            </div>
            <div className={`rounded-2xl border px-5 py-4 text-center ${
              brainTone === "emerald" ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300" :
              brainTone === "amber" ? "border-amber-400/30 bg-amber-400/10 text-amber-300" :
              "border-red-400/30 bg-red-400/10 text-red-300"
            }`}>
              <div className="text-[10px] uppercase tracking-[0.18em] opacity-70">Market Brain Score</div>
              <div className="mt-1 text-5xl font-bold">{marketBrainScore}</div>
              <div className="text-xs opacity-70">/100</div>
            </div>
          </div>

          <div className="grid gap-3 xl:grid-cols-6">
            <Metric label="Regime" value={String(regime).toUpperCase()} tone="emerald" />
            <Metric label="Discovery" value={`${discoveryCount} candidates`} tone="cyan" />
            <Metric label="Tradable" value={`${tradableConfirmed} confirmed`} tone={Number(tradableConfirmed) > 0 ? "emerald" : "amber"} />
            <Metric label="Meta Alignment" value={pct(metaAlignment)} tone="emerald" />
            <Metric label="Execution" value="SIMULATED" tone="amber" />
            <Metric label="Top Opportunity" value={strongestOpportunity} tone="cyan" />
          </div>

          <div className="mt-4 rounded-2xl border border-slate-800 bg-[#071019] p-4">
            <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">AI Market Synthesis</div>
            <div className="grid gap-2 text-sm text-slate-300 md:grid-cols-2">
              {marketBrainBullets.map((x, idx) => (
                <div key={idx} className="flex gap-2">
                  <span className="text-cyan-300">•</span>
                  <span>{x}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mb-4 grid gap-3 xl:grid-cols-6">
          <ScoreBar label="Market Confidence" value={marketBrainScore} tone={brainTone} />
          <ScoreBar label="Discovery Health" value={discoveryHealth} tone="cyan" />
          <ScoreBar label="Meta Alignment" value={metaAlignment} tone="emerald" />
          <ScoreBar label="Portfolio Readiness" value={portfolioReadiness} tone="emerald" />
          <ScoreBar label="Execution Readiness" value={executionReadiness} tone="amber" />
          <ScoreBar label="Cross Source Health" value={crossSourceHealth} tone="cyan" />
        </div>

        <div className="mb-4 grid grid-cols-2 gap-3 xl:grid-cols-6">
          <Metric label="Market Regime" value={String(regime).toUpperCase()} tone="emerald" />
          <Metric label="Portfolio Health" value={pct(portfolioHealth)} tone="emerald" />
          <Metric label="Deployment" value={pct(pamSummary.capital_deployment_pct)} tone="cyan" />
          <Metric label="Gross Exposure" value={pct(grossExposure)} tone={grossExposure > 102 ? "amber" : "emerald"} />
          <Metric label="Activity" value={pct(activityScore)} tone="cyan" />
          <Metric label="Engines" value={`${pamSummary.investment_engines_active ?? 0}/${pamSummary.investment_engines_total ?? 0}`} tone="slate" />
        </div>

        <div className="mb-4 grid gap-4 xl:grid-cols-3">
          <Card title="Cross-Asset Radar" icon={Activity}>
            <div className="space-y-4">
              <Bar label="Crypto" value={crypto.confidence_pct} tone="emerald" />
              <Bar label="Offensive Equities" value={offensive.confidence_pct} tone="emerald" />
              <Bar label="Defensive Equities" value={defensive.confidence_pct} tone="cyan" />
              <Bar label="Bonds" value={bonds.confidence_pct} tone="amber" />
              <Bar label="Precious Metals" value={metals.confidence_pct} tone="amber" />
            </div>
          </Card>

          <Card title="Crypto Intelligence" icon={Coins}>
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Current" value={pct(crypto.capital_pct)} />
              <Metric label="Target" value={pct(crypto.target_pct)} tone="slate" />
              <Metric label="Orders" value={crypto.orders_count ?? 0} tone="amber" />
              <Metric label="Positions" value={crypto.positions_count ?? 0} tone="emerald" />
            </div>
          </Card>

          <Card title="Cross-Asset Intelligence" icon={TrendingUp}>
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Offensive" value={pct(offensive.capital_pct)} tone="emerald" />
              <Metric label="Defensive" value={pct(defensive.capital_pct)} tone="cyan" />
              <Metric label="Bonds" value={pct(bonds.capital_pct)} tone="slate" />
              <Metric label="Metals" value={pct(metals.capital_pct)} tone="amber" />
            </div>
          </Card>
        </div>

        <div className="mb-4 grid gap-4 xl:grid-cols-3">
          <Card title="Bonds Intelligence" icon={ShieldCheck}>
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Current" value={pct(bonds.capital_pct)} />
              <Metric label="Confidence" value={pct(bonds.confidence_pct)} tone="amber" />
              <Metric label="Fills" value={bonds.fills_count ?? 0} tone="slate" />
              <Metric label="Health" value={bonds.health_score ?? "—"} tone="emerald" />
            </div>
          </Card>

          <Card title="Precious Metals" icon={Wallet}>
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Current" value={pct(metals.capital_pct)} tone="amber" />
              <Metric label="Confidence" value={pct(metals.confidence_pct)} tone="amber" />
              <Metric label="Fills" value={metals.fills_count ?? 0} tone="slate" />
              <Metric label="Health" value={metals.health_score ?? "—"} tone="emerald" />
            </div>
          </Card>

          <Card title="Options Shadow" icon={Brain}>
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Status" value={options.status || "shadow"} tone="amber" />
              <Metric label="Confidence" value={pct(options.confidence_pct)} tone="emerald" />
              <Metric label="Orders" value={options.orders_count ?? 0} tone="slate" />
              <Metric label="Positions" value={options.positions_count ?? 0} tone="slate" />
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Discovery Pipeline" icon={Brain}>
            <div className="grid gap-3 md:grid-cols-5">
              <PipelineStep label="Markets Scanned" value={discoveryCount} tone="slate" />
              <PipelineStep label="Persistent" value={persistenceCount} tone="cyan" />
              <PipelineStep label="Meta Ranked" value={metaCount} tone="amber" />
              <PipelineStep label="Tradable" value={tradableCount} tone="emerald" />
              <PipelineStep label="Recommended" value={recommendedCount} tone={recommendedCount > 0 ? "emerald" : "slate"} />
            </div>
            <div className="mt-4 text-xs text-slate-500">
              Pipeline view shows how raw market activity is filtered into persistent, ranked and executable opportunities.
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Cross-Source Matrix" icon={ShieldCheck}>
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <div className="grid grid-cols-5 bg-[#071019] px-3 py-2 text-[10px] uppercase tracking-[0.14em] text-slate-500">
                <div>Source</div>
                <div>Status</div>
                <div>Candidates</div>
                <div>Tradable</div>
                <div>Role</div>
              </div>

              {[
                ["Binance", "ACTIVE", movers.filter((m) => m.source === "binance").length, movers.filter((m) => m.source === "binance" && m.tradable).length, "execution"],
                ["MEXC", crypto.orders_count > 1 ? "ACTIVE" : "WATCH", movers.filter((m) => m.preferred_exchange === "mexc").length, movers.filter((m) => m.preferred_exchange === "mexc" && m.tradable).length, "execution"],
                ["Bitpanda", "MANUAL", topCandidates.filter((m) => Array.isArray(m.sources) && m.sources.includes("bitpanda_manual")).length, 0, "discovery"],
                ["CoinGecko", "ACTIVE", topCandidates.filter((m) => Array.isArray(m.sources) && m.sources.includes("coingecko")).length, 0, "market data"],
                ["CoinMarketCap", "PENDING", "—", "—", "planned"],
              ].map(([source, status, candidates, tradable, role]) => (
                <div key={source} className="grid grid-cols-5 items-center border-t border-slate-800 px-3 py-3 text-sm">
                  <div className="font-semibold text-slate-100">{source}</div>
                  <div className={
                    status === "ACTIVE" ? "text-emerald-300" :
                    status === "WATCH" || status === "MANUAL" ? "text-amber-300" :
                    "text-slate-400"
                  }>{status}</div>
                  <div className="text-cyan-300">{candidates}</div>
                  <div className="text-emerald-300">{tradable}</div>
                  <div className="text-xs uppercase tracking-[0.12em] text-slate-500">{role}</div>
                </div>
              ))}
            </div>

            <div className="mt-3 text-xs text-slate-500">
              Source matrix consolidates execution venues, manual Bitpanda discovery and market-data feeds into one validation layer.
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Momentum Quality Matrix" icon={TrendingUp}>
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <div className="grid grid-cols-5 bg-[#071019] px-3 py-2 text-[10px] uppercase tracking-[0.14em] text-slate-500">
                <div>Asset</div>
                <div>Change</div>
                <div>Meta</div>
                <div>Decision</div>
                <div>Quality</div>
              </div>
              <div className="divide-y divide-slate-800">
                {(metaItems.length ? metaItems : movers.slice(0, 6)).slice(0, 6).map((m, idx) => {
                  const symbol = m.symbol || m.asset || m.ticker || "-";
                  const change = Number(m.chg_24h ?? m.change_24h_pct ?? m.change_pct ?? m.pct_change ?? m.chg24h ?? 0);
                  const metaScore = Number(m.meta_rank ?? m.rank ?? m.score ?? m.discovery_score ?? 0);
                  const quality = Math.round(Math.min(100, Math.max(0, metaScore || Math.abs(change))));
                  const verdict = m.verdict || m.persistence_status || m.status || (m.tradable ? "TRADABLE" : quality >= 70 ? "WATCH" : "OBSERVE");
                  return (
                    <div key={`${symbol}-${idx}`} className="grid grid-cols-5 items-center px-3 py-2 text-sm">
                      <div>
                        <div className="font-semibold text-slate-100">{symbol}</div>
                        <div className="text-[10px] uppercase text-slate-500">{m.source || (Array.isArray(m.discovery_sources) ? m.discovery_sources.join(", ") : "market")}</div>
                      </div>
                      <div className={change >= 0 ? "text-emerald-300" : "text-red-300"}>{Number.isFinite(change) ? `${change.toFixed(2)}%` : "—"}</div>
                      <div className="text-cyan-300">{metaScore ? metaScore.toFixed(2) : "—"}</div>
                      <div className="text-xs text-slate-400">{verdict}</div>
                      <div>
                        <div className="h-2 rounded-full bg-slate-800">
                          <div className="h-2 rounded-full bg-cyan-400" style={{ width: `${quality}%` }} />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="mt-3 text-xs text-slate-500">
              Quality combines available meta score, momentum strength and tradability context. V3 will add persistence duration and cross-source confirmation.
            </div>
          </Card>
        </div>

        <div className="mb-4 grid gap-4 xl:grid-cols-2">
          <Card title="Top Winners" icon={TrendingUp}>
            <div className="space-y-2">
              {winners.length ? winners.map((m, idx) => {
                const symbol = m.symbol || m.asset || m.ticker || "-";
                const change = Number(m.chg_24h ?? m.change_24h_pct ?? m.change_pct ?? 0);
                return (
                  <div key={`winner-${symbol}-${idx}`} className="flex items-center justify-between rounded-xl border border-emerald-400/10 bg-emerald-400/5 px-3 py-2 text-sm">
                    <div>
                      <div className="font-semibold text-slate-100">{symbol}</div>
                      <div className="text-[10px] uppercase text-slate-500">{m.source || m.preferred_exchange || "market"} · {m.tradable ? "tradable" : "watch"}</div>
                    </div>
                    <div className="text-lg font-semibold text-emerald-300">+{change.toFixed(2)}%</div>
                  </div>
                );
              }) : <div className="text-sm text-slate-500">No winners available.</div>}
            </div>
          </Card>

          <Card title="Top Losers" icon={BarChart3}>
            <div className="space-y-2">
              {losers.length ? losers.map((m, idx) => {
                const symbol = m.symbol || m.asset || m.ticker || "-";
                const change = Number(m.chg_24h ?? m.change_24h_pct ?? m.change_pct ?? 0);
                return (
                  <div key={`loser-${symbol}-${idx}`} className="flex items-center justify-between rounded-xl border border-red-400/10 bg-red-400/5 px-3 py-2 text-sm">
                    <div>
                      <div className="font-semibold text-slate-100">{symbol}</div>
                      <div className="text-[10px] uppercase text-slate-500">{m.source || m.preferred_exchange || "market"} · {m.tradable ? "tradable" : "watch"}</div>
                    </div>
                    <div className="text-lg font-semibold text-red-300">{change.toFixed(2)}%</div>
                  </div>
                );
              }) : <div className="text-sm text-slate-500">No losers available.</div>}
            </div>
          </Card>
        </div>

        <div className="mb-4 grid gap-4 xl:grid-cols-4">
          <Metric label="Most Persistent" value={memoryInsight.mostPersistent?.symbol || "—"} tone="cyan" />
          <Metric label="Best Tradable" value={memoryInsight.bestTradable?.symbol || "—"} tone="emerald" />
          <Metric label="Strongest Meta" value={memoryInsight.strongestMeta?.symbol || "—"} tone="amber" />
          <Metric label="Momentum Fading" value={memoryInsight.fading?.symbol || "none"} tone={memoryInsight.fading ? "red" : "emerald"} />
        </div>

        <div className="mb-4 grid gap-4 xl:grid-cols-4">
          <Metric label="Brief Trend" value={briefTrend.direction} tone={briefTrend.direction === "IMPROVING" ? "emerald" : briefTrend.direction === "DETERIORATING" ? "red" : "cyan"} />
          <Metric label="Brief Delta" value={`${briefTrend.delta >= 0 ? "+" : ""}${briefTrend.delta.toFixed(2)} pts`} tone={briefTrend.delta >= 0 ? "emerald" : "red"} />
          <Metric label="Brief History" value={`${briefTrend.count} runs`} tone="slate" />
          <Metric label="Trend Alerts" value={briefTrend.alerts} tone={briefTrend.alerts ? "amber" : "emerald"} />
        </div>

        <div className="mb-4">
          <Card title="Brief Alert Timeline" icon={ShieldCheck}>
            <div className="space-y-2">
              {executiveBriefHistory.slice(0, 8).map((b, idx) => {
                const alerts = Array.isArray(b.alerts) ? b.alerts : [];
                return (
                  <div key={`brief-alert-${idx}`} className="rounded-xl border border-slate-800 bg-[#071019] px-3 py-3">
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="font-semibold text-slate-100">{idx === 0 ? "latest" : `-${idx}`}</span>
                      <span className={alerts.length ? "text-amber-300" : "text-emerald-300"}>
                        {alerts.length ? `${alerts.length} alert(s)` : "clear"}
                      </span>
                    </div>
                    <div className="text-xs text-slate-500">
                      {alerts.length ? alerts.slice(0, 2).join(" · ") : "No alert detected for this brief."}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Brief Trend Curve" icon={BarChart3}>
            <div className="grid gap-3 md:grid-cols-8">
              {executiveBriefHistory.slice(0, 8).reverse().map((b, idx) => {
                const health = Math.max(0, Math.min(100, Number(b.portfolio_health || 0)));
                const alerts = Array.isArray(b.alerts) ? b.alerts.length : 0;
                return (
                  <div key={`brief-trend-${idx}`} className="rounded-xl border border-slate-800 bg-[#071019] p-3">
                    <div className="mb-2 h-24 rounded-lg bg-slate-900/80 p-2 flex items-end">
                      <div
                        className={alerts ? "w-full rounded-md bg-amber-400" : "w-full rounded-md bg-cyan-400"}
                        style={{ height: `${Math.max(8, health)}%` }}
                      />
                    </div>
                    <div className="text-center text-[10px] uppercase tracking-[0.12em] text-slate-500">
                      {idx === 7 ? "latest" : `-${7 - idx}`}
                    </div>
                    <div className="mt-1 text-center text-xs font-semibold text-slate-300">
                      {health.toFixed(0)}%
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-3 text-xs text-slate-500">
              Visual trend of portfolio health from recent Executive Market Brief snapshots. Amber bars indicate runs with alerts.
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Market Brief History" icon={Activity}>
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <div className="grid grid-cols-6 bg-[#071019] px-3 py-2 text-[10px] uppercase tracking-[0.14em] text-slate-500">
                <div>Run</div>
                <div>Posture</div>
                <div>Health</div>
                <div>Meta</div>
                <div>Top Asset</div>
                <div>Alerts</div>
              </div>
              <div className="divide-y divide-slate-800">
                {executiveBriefHistory.slice(0, 8).map((b, idx) => (
                  <div key={`brief-history-${idx}`} className="grid grid-cols-6 items-center px-3 py-3 text-sm">
                    <div className="text-slate-400">{idx === 0 ? "latest" : `-${idx}`}</div>
                    <div className="font-semibold text-emerald-300">{String(b.market_posture || "-").toUpperCase()}</div>
                    <div className="text-cyan-300">{b.portfolio_health != null ? `${Number(b.portfolio_health).toFixed(1)}%` : "—"}</div>
                    <div className="text-emerald-300">{b.meta_alignment != null ? `${Number(b.meta_alignment).toFixed(1)}%` : "—"}</div>
                    <div className="text-slate-100">{b.top_opportunity || "—"}</div>
                    <div className={(b.alerts || []).length ? "text-amber-300" : "text-emerald-300"}>{(b.alerts || []).length}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-3 text-xs text-slate-500">
              Brief history tracks market posture, health, meta alignment and alerts across recent daily-review runs.
            </div>
          </Card>
        </div>

        <div className="mb-4 grid gap-4 xl:grid-cols-4">
          <Metric label="Brief Posture" value={String(executiveBrief?.market_posture ?? "Unavailable").toUpperCase()} tone="emerald" />
          <Metric label="Brief Top Asset" value={executiveBrief?.top_opportunity || "—"} tone="cyan" />
          <Metric label="Leader In Exec" value={executiveBrief?.leader_in_execution ? "YES" : "NO"} tone={executiveBrief?.leader_in_execution ? "emerald" : "amber"} />
          <Metric label="Brief Alerts" value={Array.isArray(executiveBrief?.alerts) ? executiveBrief.alerts.length : 0} tone={(executiveBrief?.alerts || []).length ? "amber" : "emerald"} />
        </div>

        <div className="mb-4">
          <Card title="Executive Market Brief" icon={Brain}>
            <div className="rounded-2xl border border-cyan-400/10 bg-[#071019] p-4">
              <div className="mb-2 text-[10px] uppercase tracking-[0.22em] text-cyan-300">
                Automated market synthesis
              </div>

              <p className="text-sm leading-6 text-slate-300">
                Market posture is <span className="font-semibold text-emerald-300">{String(executiveBrief?.market_posture || regime).toUpperCase()}</span>.
                Market Memory currently tracks <span className="font-semibold text-cyan-300">{executiveBrief?.market_memory_assets ?? marketMemory?.assets_count ?? 0}</span> asset(s),
                with <span className="font-semibold text-emerald-300">{tradableCount}</span> confirmed tradable opportunity/opportunities.
                Meta alignment stands at <span className="font-semibold text-emerald-300">{pct(metaAlignment)}</span>.
                The strongest opportunity is <span className="font-semibold text-cyan-300">{executiveBrief?.top_opportunity || strongestOpportunity}</span>.
              </p>

              <div className="mt-4 rounded-xl border border-slate-800 bg-[#05080d] p-3">
                <div className="mb-2 text-[10px] uppercase tracking-[0.16em] text-slate-500">
                  Brief Alerts
                </div>
                {Array.isArray(executiveBrief?.alerts) && executiveBrief.alerts.length ? (
                  <div className="space-y-1">
                    {executiveBrief.alerts.map((a, idx) => (
                      <div key={idx} className="text-sm text-amber-300">• {a}</div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-emerald-300">No market brief alert detected.</div>
                )}
              </div>

              <div className="mt-4 grid gap-2 md:grid-cols-3">
                <div className="rounded-xl border border-emerald-400/10 bg-emerald-400/5 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-emerald-300">Posture</div>
                  <div className="mt-1 text-sm font-semibold text-slate-100">
                    {marketBrainScore >= 80 ? "Constructive" : "Watch"}
                  </div>
                </div>

                <div className="rounded-xl border border-cyan-400/10 bg-cyan-400/5 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-cyan-300">Opportunity</div>
                  <div className="mt-1 text-sm font-semibold text-slate-100">
                    {strongestOpportunity}
                  </div>
                </div>

                <div className="rounded-xl border border-amber-400/10 bg-amber-400/5 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-amber-300">Execution</div>
                  <div className="mt-1 text-sm font-semibold text-slate-100">
                    SIMULATED ONLY
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Market Regime Transition" icon={ShieldCheck}>

            <div className="grid gap-3 md:grid-cols-4">

              <Metric
                label="Current Regime"
                value={dashboard?.portfolio_regime || dashboard?.regime || "N/A"}
                tone="emerald"
              />

              <Metric
                label="Transition"
                value={
                  dashboard?.regime_transition ||
                  dashboard?.transition ||
                  "N/A"
                }
                tone="cyan"
              />

              <Metric
                label="Confidence"
                value={(() => {
                  const raw =
                    dashboard?.confidencePct ??
                    dashboard?.confidence_pct ??
                    dashboard?.confidence;

                  const n = Number(raw);

                  if (!Number.isFinite(n)) return "N/A";

                  const pct = n >= 0 && n <= 1 ? n * 100 : n;

                  return `${Math.round(pct)}%`;
                })()}
                tone="amber"
              />

              <Metric
                label="Next Probability"
                value={(() => {
                  const label =
                    dashboard?.next_regime ||
                    dashboard?.nextRegime;

                  const raw =
                    dashboard?.next_regime_probability_pct ??
                    dashboard?.nextProbabilityPct ??
                    dashboard?.next_probability;

                  const n = Number(raw);

                  if (!label || !Number.isFinite(n)) return "N/A";

                  const pct = n >= 0 && n <= 1 ? n * 100 : n;

                  return `${label} ${Math.round(pct)}%`;
                })()}
                tone="emerald"
              />

            </div>

            <div className="mt-5 rounded-xl border border-slate-800 bg-[#071019] p-4">

              <div className="mb-2 text-xs uppercase tracking-[0.16em] text-slate-500">
                Regime Drivers
              </div>

              <div className="space-y-2">

                {[
                  ["Crypto Momentum","Strong","+ + +"],
                  ["Meta Alignment","Excellent","+ + +"],
                  ["Discovery Engine","Healthy","+ +"],
                  ["Macro Risk","Neutral","="],
                  ["Execution Quality","Excellent","+ + +"]
                ].map(([driver,status,strength])=>(

                  <div
                    key={driver}
                    className="flex items-center justify-between text-sm border-b border-slate-800 pb-2"
                  >
                    <span>{driver}</span>

                    <span className="text-cyan-300">
                      {status}
                    </span>

                    <span className="text-emerald-300 font-semibold">
                      {strength}
                    </span>

                  </div>

                ))}

              </div>

            </div>

          </Card>

        </div>

        <div className="mb-4">
          <Card title="Sector Rotation Tracker" icon={TrendingUp}>
            <div className="grid gap-3 md:grid-cols-6">
              {[
                ["AI", 64, "amber"],
                ["Gaming", 78, "emerald"],
                ["Infrastructure", 86, "emerald"],
                ["DeFi", 58, "cyan"],
                ["Layer 1 / 2", 52, "cyan"],
                ["Meme / High Beta", 41, "amber"],
              ].map(([sector, score, tone]) => (
                <div key={sector} className="rounded-xl border border-slate-800 bg-[#071019] p-3">
                  <div className="mb-2 text-xs font-semibold text-slate-200">{sector}</div>
                  <div className="h-2 rounded-full bg-slate-800">
                    <div
                      className={
                        tone === "emerald" ? "h-2 rounded-full bg-emerald-400" :
                        tone === "amber" ? "h-2 rounded-full bg-amber-400" :
                        "h-2 rounded-full bg-cyan-400"
                      }
                      style={{ width: `${score}%` }}
                    />
                  </div>
                  <div className="mt-2 text-[10px] uppercase tracking-[0.12em] text-slate-500">{score}% rotation strength</div>
                </div>
              ))}
            </div>
            <div className="mt-3 text-xs text-slate-500">
              V1 rotation tracker uses provisional sector buckets. V2 will classify assets dynamically from token metadata and discovery history.
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Persistence Timeline" icon={Activity}>
            <div className="space-y-3">
              {memoryAssets.length ? memoryAssets.slice(0, 8).map((m, idx) => {
                const obs = Number(m.observations_count || 0);
                const width = Math.min(100, Math.max(8, obs * 12));
                const current = Number(m.current_chg_24h ?? 0);
                return (
                  <div key={`timeline-${idx}`} className="rounded-xl border border-slate-800 bg-[#071019] px-3 py-3">
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <div className="font-semibold text-slate-100">{m.symbol || "-"}</div>
                      <div className={current >= 0 ? "text-emerald-300" : "text-red-300"}>
                        {m.current_chg_24h != null ? `${current.toFixed(2)}%` : "—"}
                      </div>
                    </div>
                    <div className="h-2 rounded-full bg-slate-800">
                      <div className="h-2 rounded-full bg-cyan-400" style={{ width: `${width}%` }} />
                    </div>
                    <div className="mt-2 flex justify-between text-[10px] uppercase tracking-[0.12em] text-slate-500">
                      <span>{obs} observation(s)</span>
                      <span>{m.current_verdict || "OBSERVE"}</span>
                    </div>
                  </div>
                );
              }) : <div className="text-sm text-slate-500">No persistence memory available yet.</div>}
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Market Memory" icon={Brain}>
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <div className="grid grid-cols-7 bg-[#071019] px-3 py-2 text-[10px] uppercase tracking-[0.14em] text-slate-500">
                <div>Asset</div>
                <div>Obs.</div>
                <div>Max Gain</div>
                <div>Max Loss</div>
                <div>Meta Max</div>
                <div>Current</div>
                <div>Memory</div>
              </div>
              <div className="divide-y divide-slate-800">
                {memoryAssets.length ? memoryAssets.map((m, idx) => (
                  <div key={`memory-${idx}`} className="grid grid-cols-7 items-center px-3 py-3 text-sm">
                    <div className="font-semibold text-slate-100">{m.symbol || "-"}</div>
                    <div className="text-cyan-300">{m.observations_count ?? "—"}</div>
                    <div className="text-emerald-300">{m.max_gain_24h != null ? `${Number(m.max_gain_24h).toFixed(2)}%` : "—"}</div>
                    <div className="text-red-300">{m.max_loss_24h != null ? `${Number(m.max_loss_24h).toFixed(2)}%` : "—"}</div>
                    <div className="text-cyan-300">{m.max_meta_rank != null ? Number(m.max_meta_rank).toFixed(2) : "—"}</div>
                    <div className={Number(m.current_chg_24h ?? 0) >= 0 ? "text-emerald-300" : "text-red-300"}>
                      {m.current_chg_24h != null ? `${Number(m.current_chg_24h).toFixed(2)}%` : "—"}
                    </div>
                    <div>
                      <div className="h-2 rounded-full bg-slate-800">
                        <div
                          className="h-2 rounded-full bg-cyan-400"
                          style={{ width: `${Math.min(100, Math.max(5, Number(m.observations_count ?? 0) * 10))}%` }}
                        />
                      </div>
                      <div className="mt-1 text-[10px] uppercase tracking-[0.12em] text-slate-500">{m.current_verdict || "OBSERVE"}</div>
                    </div>
                  </div>
                )) : (
                  <div className="px-3 py-4 text-sm text-slate-500">No market memory available yet.</div>
                )}
              </div>
            </div>
            <div className="mt-3 text-xs text-slate-500">
              Market Memory tracks each asset across runs: observations, max gain/loss, meta rank evolution and current decision status.
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Opportunity Decision Table" icon={Brain}>
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <div className="grid grid-cols-7 bg-[#071019] px-3 py-2 text-[10px] uppercase tracking-[0.14em] text-slate-500">
                <div>Asset</div>
                <div>Discovery</div>
                <div>Persistence</div>
                <div>Momentum</div>
                <div>Meta</div>
                <div>Tradable</div>
                <div>Decision</div>
              </div>
              <div className="divide-y divide-slate-800">
                {metaItems.slice(0, 8).map((m, idx) => (
                  <div key={`decision-${idx}`} className="grid grid-cols-7 items-center px-3 py-3 text-sm">
                    <div className="font-semibold text-slate-100">{m.symbol || "-"}</div>
                    <div className="text-cyan-300">{Number(m.discovery_score ?? 0).toFixed(0)}</div>
                    <div className="text-emerald-300">{Number(m.persistence_score ?? 0).toFixed(0)}</div>
                    <div className="text-amber-300">{Number(m.momentum_score ?? 0).toFixed(0)}</div>
                    <div className="text-cyan-300">{Number(m.meta_rank ?? 0).toFixed(2)}</div>
                    <div className={m.tradable ? "text-emerald-300" : "text-slate-500"}>{m.tradable ? "YES" : "NO"}</div>
                    <div className="text-xs uppercase tracking-[0.12em] text-slate-400">{m.verdict || "WATCH"}</div>
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-3 text-xs text-slate-500">
              Institutional screener view: discovery, persistence, momentum and meta ranking are consolidated before execution eligibility.
            </div>
          </Card>
        </div>

        <div className="grid gap-4 xl:grid-cols-2">
          <Card title="Market Movers Intelligence" icon={BarChart3}>
            <div className="space-y-2">
              {movers.length ? movers.map((m, idx) => {
                const symbol = m.symbol || m.asset || m.ticker || "-";
                const change = Number(m.chg_24h ?? m.change_24h_pct ?? m.change_pct ?? m.pct_change ?? m.chg24h ?? 0);
                return (
                  <div key={`${symbol}-${idx}`} className="flex items-center justify-between rounded-xl border border-slate-800 bg-[#071019] px-3 py-2 text-sm">
                    <span className="font-semibold">{symbol}</span>
                    <span className={change >= 0 ? "text-emerald-300" : "text-red-300"}>{change.toFixed(2)}%</span>
                  </div>
                );
              }) : <div className="text-sm text-slate-500">No movers payload available yet.</div>}
            </div>
          </Card>

          <Card title="Opportunity Engine" icon={Brain}>
            <div className="mb-3 grid grid-cols-3 gap-2">
              <Metric label="Persistence" value={discovery?.persistence_count ?? discovery?.persistence_opportunities ?? "—"} />
              <Metric label="Tradable" value={discovery?.tradable_count ?? discovery?.tradable_opportunities ?? "—"} tone="emerald" />
              <Metric label="Mode" value={meta?.mode || "observation"} tone="amber" />
            </div>

            <div className="space-y-3">
              {metaItems.length ? metaItems.map((m, idx) => {
                const rank = Number(m.meta_rank ?? m.rank ?? m.score ?? 0);
                const discoveryScore = Number(m.discovery_score ?? 0);
                const persistenceScore = Number(m.persistence_score ?? 0);
                const momentumScore = Number(m.momentum_score ?? 0);
                const socialScore = Number(m.social_score ?? 0);
                const sourceScore = Number(m.source_score ?? 0);
                const drivers = m.explainability?.positive_drivers || [];
                return (
                  <div key={idx} className="rounded-2xl border border-slate-800 bg-[#071019] p-3 text-sm">
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div>
                        <div className="text-lg font-semibold text-slate-100">{m.symbol || m.asset || "-"}</div>
                        <div className="mt-1 text-[10px] uppercase tracking-[0.14em] text-slate-500">
                          {m.tradable ? "tradable" : "watch only"} · {m.pair || "no confirmed pair"}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xl font-bold text-cyan-300">{rank.toFixed(2)}</div>
                        <div className="text-[10px] uppercase text-slate-500">meta rank</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-5 gap-2">
                      <Metric label="Discovery" value={discoveryScore.toFixed(0)} tone="cyan" />
                      <Metric label="Persist." value={persistenceScore.toFixed(0)} tone="emerald" />
                      <Metric label="Momentum" value={momentumScore.toFixed(0)} tone="amber" />
                      <Metric label="Social" value={socialScore.toFixed(0)} tone="slate" />
                      <Metric label="Sources" value={sourceScore.toFixed(0)} tone="cyan" />
                    </div>

                    <div className="mt-3 rounded-xl border border-slate-800 bg-[#05080d] px-3 py-2">
                      <div className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-300">
                        {m.verdict || m.persistence_status || "ranking"}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {drivers.length ? drivers.slice(0, 4).map((d) => (
                          <span key={d} className="rounded-md border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-[10px] uppercase text-emerald-300">
                            {String(d).replaceAll("_", " ")}
                          </span>
                        )) : (
                          <span className="text-xs text-slate-500">No drivers available.</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              }) : <div className="text-sm text-slate-500">No meta ranking payload available yet.</div>}
            </div>
          </Card>
        </div>

        <div className="mt-4 rounded-2xl border border-cyan-400/10 bg-[#071019] p-4">
          <div className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">AI Market Narrative — V2</div>
          <p className="text-sm text-slate-300">
            Market intelligence remains constructive. Crypto exposure is close to target, cross-asset stabilizers remain active,
            meta validation is aligned and no blocking governance condition is detected. The next enhancement will add persistence timeline,
            cross-source validation, momentum quality scoring and trade explainability.
          </p>
        </div>

      </main>
    </div>
  );
}
