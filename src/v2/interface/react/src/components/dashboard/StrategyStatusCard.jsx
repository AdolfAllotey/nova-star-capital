import React from "react";
import StatusBadge from "../ui/StatusBadge";
import SectionCard from "../ui/SectionCard";

function truncate(value, max = 42) {
  if (!value) return "—";
  const s = String(value);
  return s.length > max ? `${s.slice(0, max)}…` : s;
}

function truncateSoft(value, max = 16) {
  if (!value) return "—";
  const s = String(value);
  return s.length > max ? `${s.slice(0, max)}…` : s;
}

function norm(value) {
  return String(value || "").trim().toUpperCase();
}

function formatPercent(value, digits = 0) {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

function formatNumber(value, digits = 2) {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function pnlClass(value) {
  return Number(value || 0) >= 0 ? "text-emerald-400" : "text-red-400";
}

function MetricBox({ label, value, valueClass = "text-zinc-100", compact = false }) {
  return (
    <div className="rounded-2xl border border-zinc-800/70 bg-zinc-950/30 px-4 py-3 min-h-[86px] flex flex-col justify-between">
      <div className="text-[10px] uppercase tracking-[0.14em] text-zinc-500">{label}</div>
      <div className={`mt-2 font-semibold leading-tight ${compact ? "text-sm" : "text-xl"} ${valueClass}`}>
        {value}
      </div>
    </div>
  );
}

export default function StrategyStatusCard({ strategy }) {
  const hasVetos = Array.isArray(strategy.softVetos) && strategy.softVetos.length > 0;

  const status = strategy.status || "N/A";
  const env = strategy.env || "N/A";
  const mode = strategy.mode || "N/A";

  const statusNorm = norm(status);
  const envNorm = norm(env);
  const modeNorm = norm(mode);

  const showEnvInfo = envNorm !== "N/A" && envNorm !== statusNorm;
  const showModeBadge = modeNorm !== "N/A";

  return (
    <SectionCard title={strategy.name} className="h-full">
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge label={status} />
          {showModeBadge && <StatusBadge label={truncateSoft(mode, 20)} />}
        </div>

        {showEnvInfo && (
          <div className="text-xs text-zinc-500">
            Environment: <span className="text-zinc-300">{env}</span>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <MetricBox label="Candidates" value={strategy.candidates ?? 0} />
          <MetricBox label="Orders" value={strategy.orders ?? 0} />
          <MetricBox label="Positions" value={strategy.openPositions ?? 0} />
          <MetricBox
            label="PnL"
            value={formatNumber(Number(strategy.pnl ?? 0), 2)}
            valueClass={pnlClass(strategy.pnl)}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <MetricBox
            label="Exposure"
            value={
              typeof strategy.targetExposure === "number"
                ? formatPercent(strategy.targetExposure, 0)
                : "—"
            }
          />
          <MetricBox
            label="Confidence"
            value={
              typeof strategy.confidence === "number"
                ? formatPercent(strategy.confidence, 0)
                : "—"
            }
          />
          <MetricBox
            label={typeof strategy.portfolioBeta === "number" ? "Beta" : "Mode"}
            value={
              typeof strategy.portfolioBeta === "number"
                ? formatNumber(strategy.portfolioBeta, 2)
                : truncateSoft(strategy.mode || "—", 18)
            }
            compact={typeof strategy.portfolioBeta !== "number"}
          />
          <MetricBox
            label="Limits"
            value={strategy.limitsOk ? "OK" : "CHECK"}
            valueClass={strategy.limitsOk ? "text-emerald-400" : "text-red-400"}
          />
        </div>

        {hasVetos && (
          <div className="rounded-2xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-300">
            <span className="font-medium">Vetos:</span> {strategy.softVetos.join(", ")}
          </div>
        )}

        {(strategy.regime || strategy.planId) && (
          <div className="border-t border-zinc-800/70 pt-3 space-y-1 text-xs text-zinc-500">
            {strategy.regime && (
              <div>
                Regime: <span className="text-zinc-300">{strategy.regime}</span>
                {typeof strategy.regimeConfidence === "number" && (
                  <span className="ml-1 text-zinc-400">
                    ({(strategy.regimeConfidence * 100).toFixed(0)}%)
                  </span>
                )}
              </div>
            )}
            {strategy.planId && (
              <div title={strategy.planId}>
                Plan: <span className="text-zinc-400">{truncate(strategy.planId)}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </SectionCard>
  );
}
