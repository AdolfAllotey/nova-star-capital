import React from "react";

function fmtEUR(v) {
  const n = Number(v || 0);
  const sign = n > 0 ? "+" : n < 0 ? "-" : "";
  return `${sign}${Math.abs(n).toFixed(2).replace(".", ",")} €`;
}

function toneClass(v) {
  const n = Number(v || 0);
  if (n > 0) return "border-emerald-500/15 bg-emerald-500/[0.05]";
  if (n < 0) return "border-red-500/15 bg-red-500/[0.05]";
  return "border-white/10 bg-black/20";
}

function textTone(v) {
  const n = Number(v || 0);
  if (n > 0) return "text-emerald-300";
  if (n < 0) return "text-red-300";
  return "text-zinc-200";
}

function BrickCard({ title, pnl, status }) {
  return (
    <div className={["rounded-[24px] border p-4 backdrop-blur-sm", toneClass(pnl)].join(" ")}>
      <div className="flex items-center justify-between gap-3">
        <div className="text-lg font-medium text-zinc-100">{title}</div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.16em] text-zinc-400">
          {status || "N/A"}
        </div>
      </div>
      <div className="mt-4 rounded-[18px] border border-white/10 bg-black/25 px-4 py-4">
        <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">PnL</div>
        <div className={["mt-2 text-2xl font-semibold tracking-tight", textTone(pnl)].join(" ")}>
          {fmtEUR(pnl)}
        </div>
      </div>
    </div>
  );
}

export default function PnLByBrick({ strategies = [] }) {
  const rows = (Array.isArray(strategies) ? strategies : []).map((s) => ({
    key: s.key,
    name: s.name || s.key || "Unknown",
    pnl: Number(s.pnl || 0),
    status: s.status || "N/A",
  }));

  return (
    <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-zinc-950/55 p-6 backdrop-blur-md">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/[0.04] via-transparent to-transparent" />
      <div className="relative space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">Performance Layer</div>
            <div className="mt-2 text-lg font-semibold text-zinc-100">PnL by Brick</div>
          </div>
          <div className="rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-xs text-zinc-400">
            Cross-Brick View
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-3">
          {rows.map((row) => (
            <BrickCard key={row.key} title={row.name} pnl={row.pnl} status={row.status} />
          ))}
        </div>
      </div>
    </div>
  );
}
