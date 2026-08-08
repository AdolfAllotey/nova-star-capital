import React from "react";

function fmtEUR(v) {
  const n = Number(v || 0);
  const sign = n > 0 ? "+" : n < 0 ? "-" : "";
  return `${sign}${Math.abs(n).toFixed(2).replace(".", ",")} €`;
}

function getRows(strategies = []) {
  const rows = (Array.isArray(strategies) ? strategies : [])
    .filter((s) => String(s?.status || "").toUpperCase() !== "NOT_DEPLOYED")
    .map((s) => ({
      key: s.key,
      name: s.name || s.key || "Unknown",
      pnl: Number(s.pnl || 0),
      status: s.status || "N/A",
    }));

  const sorted = [...rows].sort((a, b) => b.pnl - a.pnl);

  return {
    top: sorted.slice(0, 3),
    bottom: [...sorted].sort((a, b) => a.pnl - b.pnl).slice(0, 3),
  };
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

function BrickRow({ row, rank }) {
  return (
    <div className={["rounded-[22px] border px-4 py-4 backdrop-blur-sm", toneClass(row.pnl)].join(" ")}>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <div className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[10px] uppercase tracking-[0.16em] text-zinc-400">
              #{rank}
            </div>
            <div className="truncate text-sm font-medium text-zinc-100">{row.name}</div>
          </div>
          <div className="mt-2 text-xs text-zinc-500">{row.status}</div>
        </div>
        <div className={["text-sm font-semibold tabular-nums", textTone(row.pnl)].join(" ")}>
          {fmtEUR(row.pnl)}
        </div>
      </div>
    </div>
  );
}

function Panel({ title, subtitle, rows }) {
  return (
    <div className="rounded-[24px] border border-white/10 bg-black/20 p-4 backdrop-blur-sm">
      <div className="mb-4">
        <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">{title}</div>
        <div className="mt-1 text-sm text-zinc-400">{subtitle}</div>
      </div>

      <div className="space-y-3">
        {rows.length === 0 && (
          <div className="rounded-[18px] border border-white/10 bg-black/20 px-4 py-4 text-sm text-zinc-500">
            No data available.
          </div>
        )}
        {rows.map((row, idx) => (
          <BrickRow key={`${row.key}-${idx}`} row={row} rank={idx + 1} />
        ))}
      </div>
    </div>
  );
}

export default function TopBottomBricks({ strategies = [] }) {
  const { top, bottom } = getRows(strategies);

  return (
    <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-zinc-950/55 p-6 backdrop-blur-md">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/[0.04] via-transparent to-transparent" />
      <div className="relative space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">Relative Performance</div>
            <div className="mt-2 text-lg font-semibold text-zinc-100">Top / Bottom Bricks</div>
          </div>
          <div className="rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-xs text-zinc-400">
            Ranking View
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <Panel title="Top Bricks" subtitle="Strongest contributors across active bricks" rows={top} />
          <Panel title="Bottom Bricks" subtitle="Weakest contributors across active bricks" rows={bottom} />
        </div>
      </div>
    </div>
  );
}
