import React from "react";

function safeValue(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "n/a";
  return Number(v).toFixed(2);
}

function toneClass(alpha, beta) {
  const a = Number(alpha);
  const b = Number(beta);

  if (!Number.isNaN(a) && a > 0 && !Number.isNaN(b) && b < 1) {
    return "border-emerald-500/15 bg-emerald-500/[0.05]";
  }
  if (!Number.isNaN(a) && a < 0) {
    return "border-red-500/15 bg-red-500/[0.05]";
  }
  return "border-white/10 bg-black/20";
}

function MetricBox({ label, value }) {
  return (
    <div className="rounded-[18px] border border-white/10 bg-black/25 px-4 py-4">
      <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-tight text-zinc-100">{value}</div>
    </div>
  );
}

function BrickCard({ title, alpha, beta }) {
  return (
    <div className={["rounded-[24px] border p-4 backdrop-blur-sm", toneClass(alpha, beta)].join(" ")}>
      <div className="flex items-center justify-between gap-3">
        <div className="text-lg font-medium text-zinc-100">{title}</div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.16em] text-zinc-400">
          Snapshot
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <MetricBox label="Alpha" value={safeValue(alpha)} />
        <MetricBox label="Beta" value={safeValue(beta)} />
      </div>
    </div>
  );
}

export default function AlphaBetaSnapshot({ strategies = [] }) {
  const rows = (Array.isArray(strategies) ? strategies : []).map((s) => ({
    key: s.key,
    name: s.name || s.key || "Unknown",
    alpha: s.alpha,
    beta: s.beta,
  }));

  return (
    <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-zinc-950/55 p-6 backdrop-blur-md">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/[0.04] via-transparent to-transparent" />
      <div className="relative space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">Analytical Layer</div>
            <div className="mt-2 text-lg font-semibold text-zinc-100">Alpha / Beta Snapshot</div>
          </div>
          <div className="rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-xs text-zinc-400">
            Factor View
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-3">
          {rows.map((row) => (
            <BrickCard key={row.key} title={row.name} alpha={row.alpha} beta={row.beta} />
          ))}
        </div>
      </div>
    </div>
  );
}
