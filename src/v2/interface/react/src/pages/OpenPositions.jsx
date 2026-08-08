import React, { useEffect, useMemo, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import StatusBadge from "../components/ui/StatusBadge";
import { fetchJson } from "../lib/apiClient";

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

function MicroCard({ label, value, subvalue }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
      {subvalue ? <div className="mt-1 text-sm text-zinc-400">{subvalue}</div> : null}
    </div>
  );
}

function formatCurrency(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return `${Number(v).toFixed(2)} €`;
}

function formatNumber(v, decimals = 4) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toFixed(decimals);
}

function formatDate(value) {
  if (!value) return "—";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);
    return d.toLocaleString("fr-FR");
  } catch {
    return String(value);
  }
}

export default function OpenPositionsPage() {
  const [data, setData] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        const res = await fetchJson("/simulation/open-positions", { timeoutMs: 8000 });
        if (!res?.ok) {
          throw new Error(`HTTP ${res?.status || "FETCH_FAILED"}`);
        }

        const json = res.data;
        const list = Array.isArray(json)
          ? json
          : Array.isArray(json?.items)
            ? json.items
            : [];

        if (!cancelled) {
          setData(json);
          setItems(list);
        }
      } catch (err) {
        console.error("Error fetching open positions:", err);
        if (!cancelled) {
          setError("Unable to load open positions.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  const aggregates = useMemo(() => {
    if (!items.length) {
      return {
        totalNotional: null,
        positionsCount: 0,
        exchangesCount: 0,
      };
    }

    let totalNotional = 0;
    const exchanges = new Set();

    for (const p of items) {
      const size =
        typeof p.size === "number" ? p.size : Number(p.size ?? NaN);
      const avgPrice =
        typeof p.avg_entry_price_eur === "number"
          ? p.avg_entry_price_eur
          : Number(p.avg_entry_price_eur ?? NaN);

      if (!Number.isNaN(size) && !Number.isNaN(avgPrice)) {
        totalNotional += size * avgPrice;
      }

      if (p.exchange) {
        exchanges.add(String(p.exchange).toUpperCase());
      }
    }

    return {
      totalNotional,
      positionsCount: items.length,
      exchangesCount: exchanges.size,
    };
  }, [items]);

  const narrative = useMemo(() => {
    return [
      `Open position count currently stands at ${aggregates.positionsCount}.`,
      `Estimated total notional currently stands at ${formatCurrency(aggregates.totalNotional)}.`,
      `The book is currently spread across ${aggregates.exchangesCount} exchange(s).`,
      `This page tracks live open positions from the aggregated simulation endpoint.`,
      `Position inventory updates should remain aligned with position manager outputs and exit events.`,
    ];
  }, [aggregates]);

  return (
    <div className="p-5 space-y-6">
      <PageHeader
        title="Open Positions"
        subtitle="Near real-time inventory of currently open positions, exchange distribution, and theoretical deployed notional."
        badges={[
          { label: items.length > 0 ? "POSITIONS_ACTIVE" : "FLAT" },
          { label: `Positions ${aggregates.positionsCount}` },
          { label: `Exchanges ${aggregates.exchangesCount}` },
        ]}
      />

      {error && (
        <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <SectionCard title="Open Position Narrative" subtitle="How the current live inventory should be read">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
          {narrative.map((line, idx) => (
            <div
              key={idx}
              className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 px-4 py-3 text-sm text-cyan-100"
            >
              {line}
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MicroCard
          label="Open Positions"
          value={aggregates.positionsCount}
          subvalue="Total active rows in the live book"
        />
        <MicroCard
          label="Estimated Notional"
          value={formatCurrency(aggregates.totalNotional)}
          subvalue="Sum of size × average entry price"
        />
        <MicroCard
          label="Exchanges"
          value={aggregates.exchangesCount}
          subvalue="Distinct venues currently in use"
        />
      </div>

      <SectionCard title="Open Positions Table" subtitle="Detailed inventory by token, venue, size, entry price, and timestamps">
        {loading && !data ? (
          <div className="text-sm text-zinc-400">Loading…</div>
        ) : error ? (
          <div className="text-sm text-red-400">{error}</div>
        ) : !items.length ? (
          <div className="text-sm text-zinc-400">
            No open positions are currently available.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1180px] border-separate border-spacing-y-2 text-sm">
              <thead>
                <tr className="text-left text-xs text-zinc-400">
                  <th className="pb-2">Token</th>
                  <th className="pb-2">Exchange</th>
                  <th className="pb-2 text-right">Size</th>
                  <th className="pb-2 text-right">Average Entry (€)</th>
                  <th className="pb-2 text-right">Theoretical Value (€)</th>
                  <th className="pb-2 text-right">Opened At</th>
                  <th className="pb-2 text-right">Last Update</th>
                </tr>
              </thead>
              <tbody>
                {items.map((p, idx) => {
                  const token = String(p.token || p.symbol || p.id || "N/A").toUpperCase();
                  const exchange = String(p.exchange || "—").toUpperCase();

                  const size =
                    typeof p.size === "number"
                      ? p.size
                      : Number(p.size ?? NaN);

                  const avgPrice =
                    typeof p.avg_entry_price_eur === "number"
                      ? p.avg_entry_price_eur
                      : Number(p.avg_entry_price_eur ?? NaN);

                  const notional =
                    !Number.isNaN(size) && !Number.isNaN(avgPrice)
                      ? size * avgPrice
                      : NaN;

                  return (
                    <tr
                      key={`${token}-${exchange}-${idx}`}
                      className="rounded-xl border border-white/10 bg-black/20"
                    >
                      <td className="rounded-l-xl px-4 py-3 text-zinc-100 font-medium">{token}</td>
                      <td className="px-4 py-3 text-zinc-300">{exchange}</td>
                      <td className="px-4 py-3 text-right text-zinc-100">
                        {formatNumber(Number.isNaN(size) ? null : size, 6)}
                      </td>
                      <td className="px-4 py-3 text-right text-zinc-100">
                        {formatCurrency(Number.isNaN(avgPrice) ? null : avgPrice)}
                      </td>
                      <td className="px-4 py-3 text-right text-zinc-100">
                        {formatCurrency(Number.isNaN(notional) ? null : notional)}
                      </td>
                      <td className="px-4 py-3 text-right text-zinc-300">
                        {formatDate(p.opened_at || p.openedAt)}
                      </td>
                      <td className="rounded-r-xl px-4 py-3 text-right text-zinc-300">
                        {formatDate(p.last_update || p.lastUpdate)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Preproduction Role" subtitle="What this screen validates before live deployment">
        <div className="space-y-2 text-sm text-zinc-300">
          <p>
            This page validates that open-position tracking remains coherent across entries,
            partial exits, and full closures.
          </p>
          <p>
            In preproduction, it should stay aligned with position manager outputs, trade simulations,
            and exit events generated by the strategy pipeline.
          </p>
          <p className="text-zinc-500">
            In production, this screen becomes one of the core live monitoring views for the desk.
          </p>
        </div>
      </SectionCard>
    </div>
  );
}
