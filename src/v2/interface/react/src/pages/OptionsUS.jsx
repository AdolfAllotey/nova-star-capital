import { buildApiUrl } from "../lib/apiBase";
import React, { useEffect, useMemo, useState } from "react";

function SectionCard({ title, children }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-sm">
      <div className="mb-3 text-sm font-semibold uppercase tracking-wide text-white/70">
        {title}
      </div>
      {children}
    </div>
  );
}

function KpiCard({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <div className="text-xs uppercase tracking-wide text-white/50">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
    </div>
  );
}

export default function OptionsUS() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        setLoading(true);
        setError("");
        const res = await fetch(buildApiUrl("/options/v2/dashboard"), { cache: "no-store" });
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const json = await res.json();
        if (active) setData(json);
      } catch (e) {
        if (active) setError(e.message || "Unknown error");
      } finally {
        if (active) setLoading(false);
      }
    }

    load();
    const id = setInterval(load, 15000);

    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const kpis = data?.kpis || {};
  const leaders = data?.leaders || {};
  const blockers = data?.blockers || {};
  const positions = data?.positions || {};
  const decisions = data?.decisions || [];
  const insights = data?.insights || {};
  const funnel = insights?.funnel || {};
  const decisionSentences = insights?.decision_sentences || [];
  const dailyNarrative = insights?.daily_narrative || "";
  const delta = data?.delta || {};
  const readiness = data?.readiness || {};
  const readinessReasons = readiness?.reasons || [];
  const readinessPenalties = readiness?.penalties || [];
  const readinessBonuses = readiness?.bonuses || [];
  const readinessTrend = readiness?.trend || {};
  const switchPolicy = data?.switch_policy || {};

  const topStrategies = useMemo(
    () => leaders.top_strategy_by_realized_pnl || [],
    [leaders]
  );
  const topTickers = useMemo(
    () => leaders.top_ticker_by_realized_pnl || [],
    [leaders]
  );
  const rejectionReasons = useMemo(
    () => blockers.top_rejection_reasons || [],
    [blockers]
  );

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-white">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="rounded-3xl border border-cyan-500/20 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 p-6">
          <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-cyan-300/80">
                Options US · Funded Simulation
              </div>
              <h1 className="mt-2 text-3xl font-semibold">Options US</h1>
              <p className="mt-2 text-sm text-white/70">
                Sleeve Options US financée en capital simulé, raccordée à l’allocation globale NSC et bloquée pour toute exécution réelle.
              </p>
            </div>
            <div className="text-sm text-white/60">
              Status: <span className="font-medium text-white">{data?.status?.pipeline_status || "N/A"}</span>
              {" · "}
              Version: <span className="font-medium text-white">{data?.status?.version || "N/A"}</span>
              {" · "}
              Mode: <span className="font-medium text-white">{data?.status?.mode || "N/A"}</span>
            </div>
          </div>
        </div>

        {loading && (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-white/70">
            Chargement du dashboard Options US...
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4 text-red-200">
            Erreur de chargement: {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <KpiCard label="Positions ouvertes" value={kpis.positions_open ?? 0} />
          <KpiCard label="Positions clôturées" value={kpis.positions_closed ?? 0} />
          <KpiCard label="PnL réalisé (€)" value={kpis.realized_pnl_eur ?? 0} />
          <KpiCard label="PnL non réalisé (€)" value={kpis.unrealized_pnl_eur ?? 0} />
          <KpiCard label="Win rate (%)" value={kpis.win_rate_pct ?? 0} />
        </div>

        <SectionCard title="Évolution récente">
  <div className="grid grid-cols-2 gap-3 text-sm">
    <div className="p-3 rounded-xl border border-white/10 bg-black/20">
      Δ PnL: {delta?.delta_realized_pnl_eur ?? 0} €
    </div>
    <div className="p-3 rounded-xl border border-white/10 bg-black/20">
      Δ trades: {delta?.delta_trades ?? 0}
    </div>
    <div className="p-3 rounded-xl border border-white/10 bg-black/20">
      Δ open: {delta?.delta_positions_open ?? 0}
    </div>
    <div className="p-3 rounded-xl border border-white/10 bg-black/20">
      Δ closed: {delta?.delta_positions_closed ?? 0}
    </div>
    <div className="col-span-2 p-3 rounded-xl border border-cyan-500/20 bg-cyan-500/10 text-cyan-100">
      Status: {delta?.status || "N/A"}
    </div>
  </div>
</SectionCard>

<SectionCard title="Should I trade now?">
          <div className="space-y-4">
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4">
              <div className="text-xs uppercase tracking-wide text-emerald-200/80">
                Readiness Score
              </div>
              <div className="mt-2 text-3xl font-semibold text-white">
                {readiness?.score ?? 0}/100
              </div>
              <div className="mt-2 text-sm text-emerald-100">
                Status: {readiness?.status || "N/A"}
              </div>
              <div className="mt-2 text-sm text-emerald-100/80">
                Trend: {readinessTrend?.trend || "N/A"}
              </div>
              <div className="mt-1 text-xs text-emerald-100/70">
                Prev: {readinessTrend?.previous_score ?? "N/A"} | Δ score: {readinessTrend?.delta_score ?? 0}
              </div>
            </div>

            <div className="space-y-2">
              {readinessReasons.length === 0 ? (
                <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/60">
                  Aucun motif disponible
                </div>
              ) : (
                readinessReasons.map((reason, idx) => (
                  <div
                    key={`${reason}-${idx}`}
                    className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/80"
                  >
                    {reason}
                  </div>
                ))
              )}
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Pourquoi je ne trade pas aujourd’hui ?">
          <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-4 text-sm leading-7 text-cyan-50">
            {dailyNarrative || "Aucune lecture narrative disponible pour le moment."}
          </div>
        </SectionCard>

        <SectionCard title="Official NSC Switch Policy">
          <div className="space-y-4">
            <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-4">
              <div className="text-xs uppercase tracking-wide text-cyan-200/80">
                Maturity Level
              </div>
              <div className="mt-2 text-2xl font-semibold text-white">
                {switchPolicy?.maturity_level || "N/A"}
              </div>
              <div className="mt-2 text-sm text-cyan-100">
                replace_v1_allowed: {String(switchPolicy?.replace_v1_allowed ?? false)}
              </div>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm leading-7 text-white/80">
              {switchPolicy?.recommendation || "Aucune recommandation de bascule disponible."}
            </div>

            <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
              <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/80">
                readiness_score: {switchPolicy?.criteria_snapshot?.readiness_score ?? "N/A"}
              </div>
              <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/80">
                close_trades_total: {switchPolicy?.criteria_snapshot?.close_trades_total ?? "N/A"}
              </div>
              <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/80">
                win_rate_pct: {switchPolicy?.criteria_snapshot?.win_rate_pct ?? "N/A"}
              </div>
              <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/80">
                trend: {switchPolicy?.criteria_snapshot?.trend ?? "N/A"}
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Readiness Explainability">
          <div className="space-y-4">
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm leading-7 text-emerald-50">
              {readiness?.summary_sentence || "Aucune synthèse de readiness disponible."}
            </div>

            <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-4 text-sm leading-7 text-cyan-50">
              {readinessTrend?.trend_sentence || "Aucune lecture de tendance disponible."}
            </div>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <div>
                <div className="mb-3 text-sm font-semibold uppercase tracking-wide text-white/70">
                  Pénalités
                </div>
                <div className="space-y-3">
                  {readinessPenalties.length === 0 ? (
                    <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/60">
                      Aucune pénalité
                    </div>
                  ) : (
                    readinessPenalties.map((item, idx) => (
                      <div
                        key={`${item.label}-${idx}`}
                        className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-100"
                      >
                        <div className="font-medium">{item.label} ({item.impact})</div>
                        <div className="mt-1 text-red-100/80">{item.detail}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div>
                <div className="mb-3 text-sm font-semibold uppercase tracking-wide text-white/70">
                  Bonus
                </div>
                <div className="space-y-3">
                  {readinessBonuses.length === 0 ? (
                    <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/60">
                      Aucun bonus
                    </div>
                  ) : (
                    readinessBonuses.map((item, idx) => (
                      <div
                        key={`${item.label}-${idx}`}
                        className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-sm text-emerald-100"
                      >
                        <div className="font-medium">{item.label} (+{item.impact})</div>
                        <div className="mt-1 text-emerald-100/80">{item.detail}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </SectionCard>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <SectionCard title="Explainability">
            <div className="space-y-3 text-sm text-white/80">
              <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                <div className="text-white/50">Top stratégie</div>
                <div className="mt-1 font-medium">
                  {insights?.top_strategy_name || "N/A"}
                </div>
                <div className="text-white/60">
                  realized={insights?.top_strategy_realized_pnl_eur ?? 0} €
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                <div className="text-white/50">Top ticker</div>
                <div className="mt-1 font-medium">
                  {insights?.top_ticker_name || "N/A"}
                </div>
                <div className="text-white/60">
                  realized={insights?.top_ticker_realized_pnl_eur ?? 0} €
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                <div className="text-white/50">Principal bloqueur</div>
                <div className="mt-1 font-medium">
                  {insights?.top_blocker_reason || "N/A"}
                </div>
                <div className="text-white/60">
                  count={insights?.top_blocker_count ?? 0}
                </div>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Opportunity Funnel">
            <div className="space-y-3">
              <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/80">
                candidates_total: {funnel?.candidates_total ?? 0}
              </div>
              <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/80">
                candidates_approved: {funnel?.candidates_approved ?? 0}
              </div>
              <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/80">
                trades_total: {funnel?.trades_total ?? 0}
              </div>
              <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/80">
                close_trades_total: {funnel?.close_trades_total ?? 0}
              </div>
              <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-3 text-sm text-cyan-100">
                opportunity_conversion_pct: {funnel?.opportunity_conversion_pct ?? 0}%
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Decision Insights">
            <div className="space-y-3">
              {decisionSentences.length === 0 ? (
                <div className="text-white/60">Aucune lecture disponible</div>
              ) : (
                decisionSentences.map((item, idx) => (
                  <div
                    key={`${item.ticker}-${item.strategy}-${idx}`}
                    className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/80"
                  >
                    {item.sentence}
                  </div>
                ))
              )}
            </div>
          </SectionCard>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <SectionCard title="Top stratégies">
            <div className="space-y-3">
              {topStrategies.length === 0 ? (
                <div className="text-white/60">Aucune donnée</div>
              ) : (
                topStrategies.map((item) => (
                  <div
                    key={item.name}
                    className="flex items-center justify-between rounded-xl border border-white/10 bg-black/20 p-3"
                  >
                    <div>
                      <div className="font-medium">{item.name}</div>
                      <div className="text-sm text-white/50">
                        Win rate: {item.win_rate_pct ?? 0}%
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">{item.realized_pnl_eur ?? 0} €</div>
                      <div className="text-sm text-white/50">
                        Closed: {item.positions_closed ?? 0}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </SectionCard>

          <SectionCard title="Top tickers">
            <div className="space-y-3">
              {topTickers.length === 0 ? (
                <div className="text-white/60">Aucune donnée</div>
              ) : (
                topTickers.map((item) => (
                  <div
                    key={item.name}
                    className="flex items-center justify-between rounded-xl border border-white/10 bg-black/20 p-3"
                  >
                    <div>
                      <div className="font-medium">{item.name}</div>
                      <div className="text-sm text-white/50">
                        Win rate: {item.win_rate_pct ?? 0}%
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">{item.realized_pnl_eur ?? 0} €</div>
                      <div className="text-sm text-white/50">
                        Closed: {item.positions_closed ?? 0}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </SectionCard>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <SectionCard title="Principaux bloqueurs">
            <div className="space-y-3">
              {rejectionReasons.length === 0 ? (
                <div className="text-white/60">Aucun bloqueur</div>
              ) : (
                rejectionReasons.map((item) => (
                  <div
                    key={item.reason}
                    className="flex items-center justify-between rounded-xl border border-white/10 bg-black/20 p-3"
                  >
                    <div className="font-medium">{item.reason}</div>
                    <div className="text-sm text-white/60">count: {item.count}</div>
                  </div>
                ))
              )}
            </div>
          </SectionCard>

          <SectionCard title="Décisions récentes">
            <div className="space-y-3">
              {decisions.length === 0 ? (
                <div className="text-white/60">Aucune décision</div>
              ) : (
                decisions.map((item, idx) => (
                  <div
                    key={`${item.ticker}-${item.strategy}-${idx}`}
                    className="rounded-xl border border-white/10 bg-black/20 p-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-medium">
                        {item.ticker} · {item.strategy}
                      </div>
                      <div className="text-xs text-white/50">{item.status}</div>
                    </div>
                    <div className="mt-1 text-sm text-white/60">{item.reason}</div>
                  </div>
                ))
              )}
            </div>
          </SectionCard>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <SectionCard title="Positions ouvertes">
            <div className="space-y-3">
              {(positions.open || []).length === 0 ? (
                <div className="text-white/60">Aucune position ouverte</div>
              ) : (
                positions.open.map((p, idx) => (
                  <div key={`${p.ticker}-${idx}`} className="rounded-xl border border-white/10 bg-black/20 p-3">
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{p.ticker} · {p.strategy}</div>
                      <div className="text-sm text-white/60">{p.status}</div>
                    </div>
                    <div className="mt-2 text-sm text-white/60">
                      pnl_eur={p.pnl_eur} · pnl_pct={p.pnl_pct} · risk={p.estimated_risk_eur}
                    </div>
                  </div>
                ))
              )}
            </div>
          </SectionCard>

          <SectionCard title="Positions clôturées">
            <div className="space-y-3">
              {(positions.closed || []).length === 0 ? (
                <div className="text-white/60">Aucune position clôturée</div>
              ) : (
                positions.closed.map((p, idx) => (
                  <div key={`${p.ticker}-${idx}`} className="rounded-xl border border-white/10 bg-black/20 p-3">
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{p.ticker} · {p.strategy}</div>
                      <div className="text-sm text-white/60">{p.close_reason || p.status}</div>
                    </div>
                    <div className="mt-2 text-sm text-white/60">
                      pnl_eur={p.pnl_eur} · pnl_pct={p.pnl_pct} · days_in_trade={p.days_in_trade}
                    </div>
                  </div>
                ))
              )}
            </div>
          </SectionCard>
        </div>

        <SectionCard title="Conclusion">
          <div className="text-sm leading-6 text-white/80">
            {data?.conclusion || "Aucune conclusion disponible"}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
