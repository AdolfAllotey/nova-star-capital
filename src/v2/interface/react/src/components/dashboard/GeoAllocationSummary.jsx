import React, { useMemo } from "react";
import geoMap from "../../data/geoMap.json";

const COUNTRY_FLAGS = {
  US: "🇺🇸",
  FR: "🇫🇷",
  DE: "🇩🇪",
  NL: "🇳🇱",
  UK: "🇬🇧",
  EM: "🌍",
  GLOBAL: "🌐",
  OTHER: "❓"
};

const COUNTRY_LABELS = {
  US: "United States",
  FR: "France",
  DE: "Germany",
  NL: "Netherlands",
  UK: "United Kingdom",
  EM: "Emerging Markets",
  GLOBAL: "Global",
  OTHER: "Other"
};

const REGION_MAP = {
  US: "North America",
  FR: "Europe",
  DE: "Europe",
  NL: "Europe",
  UK: "Europe",
  EM: "Emerging Markets",
  GLOBAL: "Global",
  OTHER: "Other"
};

function pct(v) {
  return `${(Number(v || 0) * 100).toFixed(1)}%`;
}

function buildGeoExposure(portfolioTarget) {
  if (!portfolioTarget) return {};

  const result = {};
  const allocations = portfolioTarget?.brick_allocations || {};
  const weights = portfolioTarget?.final_brick_weights || {};

  Object.entries(allocations).forEach(([brick, assets]) => {
    const brickWeight = Number(weights[brick] || 0);

    Object.entries(assets || {}).forEach(([symbol, alloc]) => {
      const country = geoMap[symbol] || "OTHER";
      const exposure = brickWeight * Number(alloc || 0);
      result[country] = (result[country] || 0) + exposure;
    });
  });

  return result;
}

export default function GeoAllocationSummary({ portfolioTarget }) {
  const { topCountries, topRegions, coveredWeight, concentration } = useMemo(() => {
    const exposure = buildGeoExposure(portfolioTarget);

    const countryRows = Object.entries(exposure)
      .map(([country, value]) => ({
        country,
        label: COUNTRY_LABELS[country] || country,
        flag: COUNTRY_FLAGS[country] || COUNTRY_FLAGS.OTHER,
        region: REGION_MAP[country] || "Other",
        value: Number(value || 0)
      }))
      .sort((a, b) => b.value - a.value);

    const regionAgg = {};
    countryRows.forEach((row) => {
      regionAgg[row.region] = (regionAgg[row.region] || 0) + row.value;
    });

    const regionRows = Object.entries(regionAgg)
      .map(([region, value]) => ({
        region,
        value: Number(value || 0)
      }))
      .sort((a, b) => b.value - a.value);

    const total = countryRows.reduce((acc, row) => acc + row.value, 0);
    const top2 = countryRows.slice(0, 2).reduce((acc, row) => acc + row.value, 0);

    return {
      topCountries: countryRows.slice(0, 5),
      topRegions: regionRows.slice(0, 4),
      coveredWeight: total,
      concentration: top2
    };
  }, [portfolioTarget]);

  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="text-sm font-semibold text-white">Geographic Allocation Summary</div>
          <div className="mt-1 text-xs text-zinc-500">
            CIO view of countries, regions, and concentration.
          </div>
        </div>

        <div className="text-right">
          <div className="text-[11px] uppercase tracking-wider text-zinc-500">Covered Weight</div>
          <div className="text-sm font-semibold text-zinc-100">{pct(coveredWeight)}</div>
        </div>
      </div>

      <div className="mb-5 grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-white/10 bg-white/5 p-3">
          <div className="text-xs text-zinc-500">Top-2 Concentration</div>
          <div className="mt-1 text-lg font-semibold text-zinc-100">{pct(concentration)}</div>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/5 p-3">
          <div className="text-xs text-zinc-500">Countries Tracked</div>
          <div className="mt-1 text-lg font-semibold text-zinc-100">{topCountries.length}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div>
          <div className="mb-2 text-xs uppercase tracking-wider text-zinc-500">Top Countries</div>
          <div className="space-y-2">
            {topCountries.length === 0 && (
              <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-zinc-500">
                No country data.
              </div>
            )}

            {topCountries.map((row) => (
              <div
                key={row.country}
                className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
              >
                <span className="text-zinc-200">{row.flag} {row.label}</span>
                <span className="text-zinc-100">{pct(row.value)}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-2 text-xs uppercase tracking-wider text-zinc-500">Top Regions</div>
          <div className="space-y-2">
            {topRegions.length === 0 && (
              <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-zinc-500">
                No region data.
              </div>
            )}

            {topRegions.map((row) => (
              <div
                key={row.region}
                className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm"
              >
                <span className="text-zinc-200">{row.region}</span>
                <span className="text-zinc-100">{pct(row.value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
