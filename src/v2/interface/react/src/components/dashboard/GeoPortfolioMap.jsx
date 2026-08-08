import React, { useMemo } from "react";
import geoMap from "../../data/geoMap.json";
import { withFlag } from "../../lib/countryMeta";
import { COUNTRY_LABELS } from "../../lib/countryLabels";

function pct(v) {
  return `${(Number(v || 0) * 100).toFixed(1)}%`;
}

export default function GeoPortfolioMap({ portfolioTarget }) {
  const geoRows = useMemo(() => {
    if (!portfolioTarget) return [];

    const result = {};
    const allocations = portfolioTarget?.brick_allocations || {};
    const weights = portfolioTarget?.final_brick_weights || {};

    Object.entries(allocations).forEach(([brick, assets]) => {
      const brickWeight = Number(weights[brick] || 0);

      Object.entries(assets || {}).forEach(([symbol, alloc]) => {
        const isCrypto = /usdt$|usdc$|btc$|eth$/i.test(symbol || "");
        const country = isCrypto
          ? "GLOBAL"
          : (geoMap[symbol] || "OTHER");
        const exposure = brickWeight * Number(alloc || 0);
        result[country] = (result[country] || 0) + exposure;
      });
    });

    return Object.entries(result)
      .map(([country, value]) => ({
        country,
        label: country,
        value: Number(value || 0)
      }))
      .sort((a, b) => b.value - a.value);
  }, [portfolioTarget]);

  const totalExposure = useMemo(
    () => geoRows.reduce((acc, row) => acc + Number(row.value || 0), 0),
    [geoRows]
  );

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-5">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="text-sm font-semibold text-zinc-100">Geographic Exposure</div>
          <div className="mt-1 text-xs text-zinc-500">
            Geographic reading of the current portfolio target allocation.
          </div>
        </div>

        <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-right">
          <div className="text-[11px] uppercase tracking-wider text-zinc-500">Covered Weight</div>
          <div className="text-sm font-semibold text-zinc-100">{pct(totalExposure)}</div>
        </div>
      </div>

      <div className="space-y-4">
        {geoRows.length === 0 && (
          <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-zinc-500">
            No geographic allocation data available.
          </div>
        )}

        {geoRows.map((row) => (
          <div key={row.country} className="rounded-xl border border-white/10 bg-black/20 px-4 py-3">
            <div className="mb-2 flex items-center justify-between gap-3">
              <div className="text-sm text-zinc-200">
                <span>{withFlag(row.country, COUNTRY_LABELS[row.country] || row.country)}</span>
              </div>
              <div className="text-sm font-medium text-zinc-100">{pct(row.value)}</div>
            </div>

            <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
              <div
                className="h-full rounded-full bg-cyan-400"
                style={{ width: `${Math.max(0, Math.min(row.value * 100, 100))}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
