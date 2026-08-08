import React from "react";

function toneForItem(item) {
  const text = String(item?.type || item?.status || "").toLowerCase();

  if (text.includes("close")) {
    return {
      dot: "bg-emerald-400",
      ring: "border-emerald-500/15 bg-emerald-500/[0.04]",
      text: "text-emerald-300",
    };
  }

  if (text.includes("open")) {
    return {
      dot: "bg-sky-400",
      ring: "border-sky-500/15 bg-sky-500/[0.04]",
      text: "text-sky-300",
    };
  }

  if (text.includes("error") || text.includes("fail") || text.includes("blocked")) {
    return {
      dot: "bg-red-400",
      ring: "border-red-500/15 bg-red-500/[0.04]",
      text: "text-red-300",
    };
  }

  return {
    dot: "bg-zinc-400",
    ring: "border-white/10 bg-black/20",
    text: "text-zinc-300",
  };
}

function formatTs(ts) {
  if (!ts) return "n/a";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return String(ts);
  return d.toLocaleString("fr-FR");
}

function formatPnl(v) {
  const n = Number(v || 0);
  return `${n > 0 ? "+" : n < 0 ? "-" : ""}${Math.abs(n).toFixed(2).replace(".", ",")} €`;
}

function resolveRows(items) {
  const rows = Array.isArray(items) ? items : [];
  return rows.slice(0, 8).map((item, idx) => {
    const brick = item?.brick || "Unknown";
    const type = item?.type || "EVENT";
    const symbol = item?.symbol || "N/A";
    const strategy = item?.strategy || "n/a";
    const pnl = formatPnl(item?.pnl_eur || 0);

    return {
      id: item?.id || item?.ts || `${idx}`,
      title: `${brick} · ${type} · ${symbol}`,
      subtitle: `Strategy: ${strategy} · PnL: ${pnl}`,
      meta: formatTs(item?.ts),
      raw: item,
    };
  });
}

export default function RecentActivity({ items = [] }) {
  const rows = resolveRows(items);

  return (
    <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-zinc-950/55 p-6 backdrop-blur-md">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/[0.04] via-transparent to-transparent" />
      <div className="relative space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">
              Activity Layer
            </div>
            <div className="mt-2 text-lg font-semibold text-zinc-100">
              Recent Activity
            </div>
          </div>
          <div className="rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-xs text-zinc-400">
            Live Flow
          </div>
        </div>

        <div className="space-y-3">
          {rows.length === 0 && (
            <div className="rounded-[24px] border border-white/10 bg-black/20 px-5 py-5 text-sm text-zinc-500">
              No recent activity available.
            </div>
          )}

          {rows.map((row) => {
            const tone = toneForItem(row.raw);

            return (
              <div
                key={row.id}
                className={["rounded-[24px] border px-5 py-4 backdrop-blur-sm", tone.ring].join(" ")}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex items-start gap-3">
                    <span className={["mt-1 h-2.5 w-2.5 rounded-full flex-shrink-0", tone.dot].join(" ")} />
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-zinc-100">{row.title}</div>
                      <div className="mt-1 text-sm leading-6 text-zinc-400">{row.subtitle}</div>
                    </div>
                  </div>
                  <div className={["rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[10px] uppercase tracking-[0.16em] flex-shrink-0", tone.text].join(" ")}>
                    {row.meta}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
