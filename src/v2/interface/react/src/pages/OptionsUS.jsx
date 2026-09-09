import React, { useEffect, useMemo, useState } from "react";
import { buildApiUrl } from "../lib/apiBase";

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

function KpiCard({ label, value, sub }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <div className="text-xs uppercase tracking-wide text-white/50">
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold text-white">
        {value}
      </div>
      {sub ? (
        <div className="mt-1 text-xs text-white/40">
          {sub}
        </div>
      ) : null}
    </div>
  );
}

function StatusBadge({ ok, okLabel, badLabel }) {
  return (
    <span
      className={
        ok
          ? "rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300"
          : "rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-300"
      }
    >
      {ok ? okLabel : badLabel}
    </span>
  );
}

function pct(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "0.00%";
  return `${(n * 100).toFixed(2)}%`;
}

function eur(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "€0.00";

  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}

export default function OptionsUS() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        setError("");

        const res = await fetch(buildApiUrl("/dashboard/v3"), {
          cache: "no-store",
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const json = await res.json();

        const strategies = Array.isArray(json?.strategies)
          ? json.strategies
          : [];

        const optionsUs =
          strategies.find((item) => item?.key === "options_us") || null;

        if (!optionsUs) {
          throw new Error(
            "options_us absent du contrat /dashboard/v3"
          );
        }

        if (active) {
          setData(optionsUs);
        }
      } catch (e) {
        if (active) {
          setError(e?.message || "Unknown error");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();

    const id = setInterval(load, 15000);

    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const softVetos = useMemo(
    () => (Array.isArray(data?.softVetos) ? data.softVetos : []),
    [data]
  );

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-white">
      <div className="mx-auto max-w-7xl space-y-6">

        <div className="rounded-3xl border border-cyan-500/20 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-cyan-300/80">
                Options US · Governed Funded Simulation
              </div>

              <h1 className="mt-2 text-3xl font-semibold">
                Options US
              </h1>

              <p className="mt-2 max-w-3xl text-sm text-white/70">
                Sleeve Options US gouvernée par l'allocation globale NSC,
                financée sur le pool IBKR simulé et bloquée pour toute
                exécution réelle pendant la préproduction.
              </p>
            </div>

            <div className="text-sm text-white/60">
              <div>
                Status:{" "}
                <span className="font-medium text-white">
                  {data?.status || "N/A"}
                </span>
              </div>
              <div>
                Environment:{" "}
                <span className="font-medium text-white">
                  {data?.env || "N/A"}
                </span>
              </div>
              <div>
                Runtime:{" "}
                <span className="font-medium text-white">
                  {data?.runtimeMode || data?.mode || "N/A"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {loading && (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-white/70">
            Chargement de la sleeve Options US...
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4 text-red-200">
            Erreur de chargement : {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <KpiCard
            label="Allocation cible"
            value={pct(data?.targetExposure)}
            sub={`Raw target ${pct(data?.rawTargetExposure)}`}
          />

          <KpiCard
            label="Montant cible"
            value={eur(data?.targetAmountEur)}
            sub={data?.fundingPool || "N/A"}
          />

          <KpiCard
            label="Exposition actuelle"
            value={eur(data?.currentExposureEur)}
            sub={pct(data?.currentExposure)}
          />

          <KpiCard
            label="Positions ouvertes"
            value={data?.openPositions ?? 0}
            sub={`${data?.orders ?? 0} ordre(s)`}
          />

          <KpiCard
            label="PnL total"
            value={eur(data?.pnl)}
            sub={`Réalisé ${eur(data?.realizedPnl)} · Non réalisé ${eur(
              data?.unrealizedPnl
            )}`}
          />
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">

          <SectionCard title="Governance & execution">
            <div className="space-y-4">

              <div className="flex flex-wrap gap-2">
                <StatusBadge
                  ok={data?.governedTarget === true}
                  okLabel="Governed target active"
                  badLabel="Governed target unavailable"
                />

                <StatusBadge
                  ok={data?.executionBlocked === true}
                  okLabel="Real execution blocked"
                  badLabel="Execution not blocked"
                />

                <StatusBadge
                  ok={data?.realMoneyDisabled === true}
                  okLabel="Real money disabled"
                  badLabel="Real money enabled"
                />
              </div>

              <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
                <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                  <div className="text-white/50">Portfolio role</div>
                  <div className="mt-1 font-medium">
                    {data?.portfolioRole || "N/A"}
                  </div>
                </div>

                <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                  <div className="text-white/50">Funding pool</div>
                  <div className="mt-1 font-medium">
                    {data?.fundingPool || "N/A"}
                  </div>
                </div>

                <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                  <div className="text-white/50">Regime</div>
                  <div className="mt-1 font-medium">
                    {data?.regime || "N/A"}
                  </div>
                </div>

                <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                  <div className="text-white/50">Confidence</div>
                  <div className="mt-1 font-medium">
                    {pct(data?.confidence)}
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/70">
                {data?.statusDetail || "No governance detail available."}
              </div>
            </div>
          </SectionCard>

          <SectionCard title="Risk & safety">
            <div className="space-y-4">

              <div className="flex flex-wrap gap-2">
                <StatusBadge
                  ok={data?.safetyContractOk === true}
                  okLabel="Safety contract OK"
                  badLabel="Safety contract issue"
                />

                <StatusBadge
                  ok={data?.pipelineHealthy === true}
                  okLabel="Pipeline healthy"
                  badLabel="Pipeline degraded"
                />

                <StatusBadge
                  ok={data?.limitsOk === true}
                  okLabel="Limits OK"
                  badLabel="Limits issue"
                />
              </div>

              <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
                <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                  <div className="text-white/50">
                    Estimated open risk
                  </div>
                  <div className="mt-1 font-medium">
                    {eur(data?.estimatedRiskOpenEur)}
                  </div>
                </div>

                <div className="rounded-xl border border-white/10 bg-black/20 p-3">
                  <div className="text-white/50">
                    Used risk
                  </div>
                  <div className="mt-1 font-medium">
                    {pct(data?.usedRiskPct)}
                  </div>
                </div>
              </div>

              <div>
                <div className="mb-2 text-xs uppercase tracking-wide text-white/50">
                  Active safety vetoes
                </div>

                {softVetos.length === 0 ? (
                  <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/60">
                    Aucun veto actif.
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {softVetos.map((veto) => (
                      <span
                        key={veto}
                        className="rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1 text-xs text-amber-300"
                      >
                        {veto}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {data?.policyExclusionReason ? (
                <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-sm text-amber-200">
                  Policy exclusion: {data.policyExclusionReason}
                </div>
              ) : null}
            </div>
          </SectionCard>
        </div>

        <SectionCard title="Data provenance">
          <div className="grid grid-cols-1 gap-3 text-sm lg:grid-cols-3">

            <div className="rounded-xl border border-white/10 bg-black/20 p-3">
              <div className="text-white/50">State origin</div>
              <div className="mt-1 break-all font-medium">
                {data?.stateOrigin || "N/A"}
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-black/20 p-3">
              <div className="text-white/50">Source</div>
              <div className="mt-1 break-all font-medium">
                {data?.source || "N/A"}
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-black/20 p-3">
              <div className="text-white/50">Strategy key</div>
              <div className="mt-1 font-medium">
                {data?.key || "options_us"}
              </div>
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
