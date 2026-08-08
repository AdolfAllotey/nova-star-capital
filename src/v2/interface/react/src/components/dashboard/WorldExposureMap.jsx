import React, { useMemo } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import worldAtlas from "world-atlas/countries-110m.json";
import countryMap from "../../data/countryMap.json";
import CryptoBadge from "../ui/CryptoBadge";
import { withFlag } from "../../lib/countryMeta";

const COUNTRY_LABELS = {
  US: "United States",
  FR: "France",
  DE: "Germany",
  NL: "Netherlands",
  GB: "United Kingdom",
  CN: "China",
  IN: "India",
  BR: "Brazil",
  ZA: "South Africa",
  MX: "Mexico",
  JP: "Japan",
  AU: "Australia",
  GLOBAL: "Global / Cross-Asset",
  OTHER: "Other"
};

const COUNTRY_REGION = {
  US: "North America",
  FR: "Europe",
  DE: "Europe",
  NL: "Europe",
  GB: "Europe",
  CN: "Emerging Markets",
  IN: "Emerging Markets",
  BR: "Emerging Markets",
  ZA: "Emerging Markets",
  MX: "Emerging Markets",
  JP: "Emerging Markets",
  AU: "Emerging Markets"
};

const DRILLABLE_REGIONS = ["North America", "Europe"];

const REGION_COLORS = {
  "North America": "#22d3ee",
  "Europe": "#34d399",
  "Emerging Markets": "#f59e0b",
  "Global": "#e879f9",
  "Other": "#71717a"
};

const ATLAS_ID_BY_ALPHA2 = {
  US: "840",
  FR: "250",
  DE: "276",
  NL: "528",
  GB: "826",
  CN: "156",
  IN: "356",
  BR: "076",
  ZA: "710",
  MX: "484",
  JP: "392",
  AU: "036"
};

function pct(v) {
  return `${(Number(v || 0) * 100).toFixed(1)}%`;
}

function clamp01(v) {
  const x = Number(v || 0);
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  return x;
}

function getAssetType(symbol) {
  const s = String(symbol || "").toUpperCase();

  if (/USDT$|USDC$|BTC$|ETH$|EUR$/i.test(s)) return "Crypto";
  if (["USMV", "VDC", "VIG", "XLV", "EEM", "VWO", "SHY", "IEF", "TLT", "LQD", "GLD", "SLV"].includes(s)) return "ETF";
  if (/^[A-Z]{1,6}$/.test(s)) return "Equity";
  return "Other";
}

function isCryptoPair(symbol) {
  return /usdt$|usdc$|btc$|eth$|eur$/i.test(symbol || "");
}

function alphaFromExposure(v) {
  const x = clamp01(v);
  if (x >= 0.35) return 0.95;
  if (x >= 0.2) return 0.82;
  if (x >= 0.1) return 0.66;
  if (x > 0) return 0.38;
  return 0.16;
}

export default function WorldExposureMap({ portfolioTarget }) {
  const [selectedRegion, setSelectedRegion] = React.useState(null);
  const [selectedCountry, setSelectedCountry] = React.useState(null);

  const [tooltip, setTooltip] = React.useState(null);
  const [tooltipPos, setTooltipPos] = React.useState({ x: 0, y: 0 });
  const {
    countryRows,
    regionRows,
    regionCountryRows,
    mappedWeight,
    totalCovered,
    offMapWeight,
    atlasExposureMap
  } = useMemo(() => {
    if (!portfolioTarget) {
      return {
        countryRows: [],
        regionRows: [],
        mappedWeight: 0,
        totalCovered: 0,
        offMapWeight: 0,
        atlasExposureMap: {}
      };
    }

    const allocations = portfolioTarget?.brick_allocations || {};
    const weights = portfolioTarget?.final_brick_weights || {};

    const countryAgg = {};
    const countryAssets = {};

    Object.entries(allocations).forEach(([brick, assets]) => {
      const brickWeight = Number(weights[brick] || 0);

      Object.entries(assets || {}).forEach(([symbol, alloc]) => {
        const isCrypto = /usdt$|usdc$|btc$|eth$/i.test(symbol || "");
        const country = isCrypto
          ? "GLOBAL"
          : (countryMap[symbol] || "OTHER");
        const exposure = brickWeight * Number(alloc || 0);
        countryAgg[country] = (countryAgg[country] || 0) + exposure;

        if (!countryAssets[country]) countryAssets[country] = [];
        countryAssets[country].push({
          symbol,
          exposure
        });
      });
    });

    const rows = Object.entries(countryAgg)
      .map(([country, value]) => ({
        country,
        value: Number(value || 0),
        label: COUNTRY_LABELS[country] || country,
        region: COUNTRY_REGION[country] || (country === "GLOBAL" ? "Global" : "Other"),
        topAssets: (countryAssets[country] || [])
          .filter(x => x.exposure > 0.001)
          .sort((a, b) => b.exposure - a.exposure)
          .slice(0, 5)
          .map((x) => x.symbol),
        assets: (countryAssets[country] || [])
          .sort((a, b) => b.exposure - a.exposure)
          .map((x) => ({
            symbol: x.symbol,
            exposure: Number(x.exposure || 0),
            type: getAssetType(x.symbol)
          })),
        dominantType: (() => {
          const typed = (countryAssets[country] || []).map((x) => getAssetType(x.symbol));
          const counts = {};
          typed.forEach((x) => { counts[x] = (counts[x] || 0) + 1; });
          return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || "Other";
        })()
      }))
      .sort((a, b) => b.value - a.value);

    const regionAgg = {};
    rows.forEach((row) => {
      regionAgg[row.region] = (regionAgg[row.region] || 0) + row.value;
    });

    const regions = Object.entries(regionAgg)
      .map(([region, value]) => ({
        region,
        value: Number(value || 0)
      }))
      .sort((a, b) => b.value - a.value);

    const atlasMap = {};
    rows.forEach((row) => {
      const atlasId = ATLAS_ID_BY_ALPHA2[row.country];
      if (atlasId) atlasMap[atlasId] = row;
    });

    const total = rows.reduce((acc, row) => acc + row.value, 0);
    const mapped = rows
      .filter((row) => !!ATLAS_ID_BY_ALPHA2[row.country])
      .reduce((acc, row) => acc + row.value, 0);

    const regionCountryRows = {};
    rows.forEach((row) => {
      if (!regionCountryRows[row.region]) regionCountryRows[row.region] = [];
      regionCountryRows[row.region].push(row);
    });

    Object.keys(regionCountryRows).forEach((k) => {
      regionCountryRows[k] = regionCountryRows[k].sort((a, b) => b.value - a.value);
    });

    return {
      countryRows: rows.filter((row) => row.country !== "GLOBAL").slice(0, 8),
      regionRows: regions,
      regionCountryRows,
      mappedWeight: mapped,
      totalCovered: total,
      offMapWeight: Math.max(0, total - mapped),
      atlasExposureMap: atlasMap
    };
  }, [portfolioTarget]);

  const insights = useMemo(() => {
    const byRegion = Object.fromEntries((regionRows || []).map((r) => [r.region, Number(r.value || 0)]));

    const us = byRegion["North America"] || 0;
    const eu = byRegion["Europe"] || 0;
    const em = byRegion["Emerging Markets"] || 0;
    const globalExposure = byRegion["Global"] || 0;

    const items = [];

    if (us >= 0.45) {
      items.push({
        level: "warning",
        title: "US exposure dominant",
        text: `North America represents ${(us * 100).toFixed(1)}% of mapped allocation. Portfolio sensitivity to US macro regime remains elevated.`
      });
    } else if (us >= 0.25) {
      items.push({
        level: "info",
        title: "US exposure meaningful",
        text: `North America represents ${(us * 100).toFixed(1)}% of mapped allocation and remains a key driver of portfolio behaviour.`
      });
    }

    if (eu <= 0.08) {
      items.push({
        level: "warning",
        title: "Europe underweight",
        text: `Europe represents only ${(eu * 100).toFixed(1)}% of mapped allocation. Geographic diversification remains limited on the European sleeve.`
      });
    } else if (eu >= 0.15) {
      items.push({
        level: "positive",
        title: "Europe allocation present",
        text: `Europe contributes ${(eu * 100).toFixed(1)}% of mapped allocation and improves cross-region diversification.`
      });
    }

    if (globalExposure >= 0.05) {
      items.push({
        level: "positive",
        title: "Global hedge active",
        text: `Global / cross-asset exposure stands at ${(globalExposure * 100).toFixed(1)}%, providing diversification outside country-specific sleeves.`
      });
    }

    if (em >= 0.10) {
      items.push({
        level: "info",
        title: "Emerging markets sleeve active",
        text: `Emerging Markets contribute ${(em * 100).toFixed(1)}% of mapped allocation and add non-US growth exposure.`
      });
    }

    if (!items.length) {
      items.push({
        level: "info",
        title: "Balanced geographic structure",
        text: "No major concentration or diversification anomaly detected from current mapped allocation."
      });
    }

    return items.slice(0, 3);
  }, [regionRows]);

  const selectedCountryRow = selectedCountry
    ? (countryRows.find((row) => row.country === selectedCountry) ||
       (regionCountryRows?.[selectedRegion] || []).find((row) => row.country === selectedCountry) ||
       null)
    : null;

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-5 shadow-[0_10px_30px_rgba(0,0,0,0.25)]">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="text-sm font-semibold text-zinc-100">World Exposure Map</div>
          <div className="mt-1 text-xs text-zinc-500">
            Institutional dark world map with highlighted investment countries and regions. Click United States or Europe-related countries to drill down.
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2 text-right">
          <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wider text-zinc-500">Covered Weight</div>
            <div className="text-sm font-semibold text-zinc-100">{pct(totalCovered)}</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/20 px-3 py-2">
            <div className="text-[11px] uppercase tracking-wider text-zinc-500">Mapped on Map</div>
            <div className="text-sm font-semibold text-zinc-100">{pct(mappedWeight)}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 2xl:grid-cols-[1.55fr_0.75fr]">
        <div className="relative min-h-[560px] rounded-2xl border border-white/10 bg-[#05070b] p-4">
          <div className="rounded-2xl border border-white/5 bg-black/20 p-2">
            
          {tooltip && (
            <div
              className="pointer-events-none absolute z-50 rounded-xl border border-white/10 bg-black/90 px-4 py-3 text-sm text-white shadow-2xl backdrop-blur"
              style={{
                left: `${tooltipPos.x + 12}px`,
                top: `${tooltipPos.y + 12}px`,
                maxWidth: "250px"
              }}
            >
              <div className="font-semibold">{tooltip.name}</div>
              <div className="text-zinc-400">{tooltip.region}</div>

              <div className="mt-2 font-semibold text-cyan-400">
                {(tooltip.value * 100).toFixed(2)}%
              </div>

              <div className="mt-1 text-xs text-zinc-400">
                Dominant: {tooltip.dominantType || "Other"}
              </div>

              {Array.isArray(tooltip.topAssets) && tooltip.topAssets.length > 0 && (
                <div className="mt-3">
                  <div className="mb-1 text-[11px] uppercase tracking-wider text-zinc-500">
                    Top Assets
                  </div>
                  <div className="space-y-1 text-xs text-zinc-300">
                    {tooltip.topAssets.map((asset, idx) => {
                      const symbol = String(asset?.symbol || asset || "").toUpperCase();
                      const exposure = Number(asset?.exposure || 0);
                      const type = asset?.type || "Other";

                      return (
                        <div
                          key={`tooltip-asset-${idx}`}
                          className="grid grid-cols-[1fr_58px_48px] items-center gap-2"
                        >
                          <span className="truncate font-medium text-zinc-200">{symbol}</span>
                          <span className="text-[10px] uppercase text-zinc-500">{type}</span>
                          <span className="text-right text-cyan-300">{pct(exposure)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          <ComposableMap
              projection="geoEqualEarth"
              projectionConfig={{ scale: 210 }}
              width={1100}
              height={610}
              style={{ width: "100%", height: "auto", background: "transparent" }}
            >
              <Geographies geography={worldAtlas}>
                {({ geographies }) =>
                  geographies.map((geo) => {
                    const geoId = String(geo.id).padStart(3, "0");
                    const row = atlasExposureMap[geoId];

                    const fill = row
                      ? REGION_COLORS[row.region] || REGION_COLORS.Other
                      : "#161b22";

                    const opacity = row ? alphaFromExposure(row.value) : 0.92;
                    const stroke = row ? fill : "#2a313c";

                    return (
                      <Geography
                        onMouseEnter={(evt) => {
                          if (row) {
                            const rect = evt.currentTarget.ownerSVGElement?.getBoundingClientRect?.();
                            const x = rect ? evt.clientX - rect.left : 0;
                            const y = rect ? evt.clientY - rect.top : 0;

                            setTooltip({
                              name: row.label,
                              value: row.value,
                              region: row.region,
                              topAssets: Array.isArray(row.assets) ? row.assets.slice(0, 5) : [],
                              dominantType: row.dominantType || "Other"
                            });
                            setTooltipPos({ x, y });
                          }
                        }}
                        onMouseMove={(evt) => {
                          const rect = evt.currentTarget.ownerSVGElement?.getBoundingClientRect?.();
                          const x = rect ? evt.clientX - rect.left : 0;
                          const y = rect ? evt.clientY - rect.top : 0;
                          setTooltipPos({ x, y });
                        }}
                        onMouseLeave={() => setTooltip(null)}
                        onClick={() => {
                          if (row && DRILLABLE_REGIONS.includes(row.region)) {
                            setSelectedRegion((prev) => prev === row.region ? null : row.region);
                          }
                        }}
                        key={geo.rsmKey}
                        geography={geo}
                        style={{
                          default: {
                            fill,
                            fillOpacity: opacity,
                            stroke,
                            strokeWidth: 0.5,
                            outline: "none",
                            filter: row
                              ? `drop-shadow(0 0 12px ${fill})`
                              : "none",
                            cursor: row && DRILLABLE_REGIONS.includes(row.region) ? "pointer" : "default"
                          },
                          hover: {
                            fill,
                            fillOpacity: opacity,
                            stroke,
                            strokeWidth: 0.7,
                            outline: "none"
                          },
                          pressed: {
                            fill,
                            fillOpacity: opacity,
                            stroke,
                            strokeWidth: 0.7,
                            outline: "none"
                          }
                        }}
                      />
                    );
                  })
                }
              </Geographies>
            </ComposableMap>
          </div>




          <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-zinc-100">Geographic Insight</div>
                <div className="mt-1 text-xs text-zinc-500">
                  Automatic readout of the current geographic concentration and diversification profile.
                </div>
              </div>
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] uppercase tracking-wider text-zinc-400">
                Auto Insight
              </span>
            </div>

            <div className="grid grid-cols-1 gap-3 2xl:grid-cols-3">
              {insights.map((item, idx) => (
                <div
                  key={`geo-insight-${idx}`}
                  className={`rounded-2xl border px-4 py-4 text-sm shadow-sm ${
                    item.level === "warning"
                      ? "border-amber-500/20 bg-amber-500/5 text-amber-100"
                      : item.level === "positive"
                        ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-100"
                        : "border-cyan-500/20 bg-cyan-500/5 text-cyan-100"
                  }`}
                >
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <div className="font-medium leading-tight">{item.title}</div>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${
                        item.level === "warning"
                          ? "border-amber-500/30 bg-amber-500/10 text-amber-200"
                          : item.level === "positive"
                            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
                            : "border-cyan-500/30 bg-cyan-500/10 text-cyan-200"
                      }`}
                    >
                      {item.level}
                    </span>
                  </div>

                  <div className="text-xs leading-5 text-balance opacity-90">
                    {item.text}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-zinc-100">Geographic Risk Signal</div>
                <div className="mt-1 text-xs text-zinc-500">
                  Concentration and diversification readout by region.
                </div>
              </div>
              <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2.5 py-1 text-[11px] uppercase tracking-wider text-cyan-200">
                Portfolio Risk
              </span>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              {[
                {
                  label: "US Concentration",
                  value: ((regionRows.find(r => r.region === "North America")?.value || 0) >= 0.45) ? "HIGH" : "NORMAL",
                  tone: ((regionRows.find(r => r.region === "North America")?.value || 0) >= 0.45) ? "amber" : "green",
                },
                {
                  label: "Europe Diversification",
                  value: ((regionRows.find(r => r.region === "Europe")?.value || 0) <= 0.08) ? "LOW" : "ACTIVE",
                  tone: ((regionRows.find(r => r.region === "Europe")?.value || 0) <= 0.08) ? "amber" : "green",
                },
                {
                  label: "Emerging Markets",
                  value: ((regionRows.find(r => r.region === "Emerging Markets")?.value || 0) > 0.05) ? "ACTIVE" : "LOW",
                  tone: ((regionRows.find(r => r.region === "Emerging Markets")?.value || 0) > 0.05) ? "cyan" : "zinc",
                },
                {
                  label: "Global Hedge",
                  value: ((regionRows.find(r => r.region === "Global")?.value || 0) > 0.03) ? "ACTIVE" : "DORMANT",
                  tone: ((regionRows.find(r => r.region === "Global")?.value || 0) > 0.03) ? "emerald" : "zinc",
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className={`rounded-xl border px-4 py-3 ${
                    item.tone === "amber"
                      ? "border-amber-500/20 bg-amber-500/5"
                      : item.tone === "green" || item.tone === "emerald"
                        ? "border-emerald-500/20 bg-emerald-500/5"
                        : item.tone === "cyan"
                          ? "border-cyan-500/20 bg-cyan-500/5"
                          : "border-white/10 bg-white/5"
                  }`}
                >
                  <div className="text-[11px] uppercase tracking-wider text-zinc-500">{item.label}</div>
                  <div
                    className={`mt-1 text-sm font-semibold ${
                      item.tone === "amber"
                        ? "text-amber-200"
                        : item.tone === "green" || item.tone === "emerald"
                          ? "text-emerald-200"
                          : item.tone === "cyan"
                            ? "text-cyan-200"
                            : "text-zinc-300"
                    }`}
                  >
                    {item.value}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-zinc-100">Geographic Risk Signal</div>
                <div className="mt-1 text-xs text-zinc-500">
                  Concentration and diversification readout by region.
                </div>
              </div>
              <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2.5 py-1 text-[11px] uppercase tracking-wider text-cyan-200">
                Portfolio Risk
              </span>
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              {[
                {
                  label: "US Concentration",
                  value: ((regionRows.find(r => r.region === "North America")?.value || 0) >= 0.45) ? "HIGH" : "NORMAL",
                  tone: ((regionRows.find(r => r.region === "North America")?.value || 0) >= 0.45) ? "amber" : "green",
                },
                {
                  label: "Europe Diversification",
                  value: ((regionRows.find(r => r.region === "Europe")?.value || 0) <= 0.08) ? "LOW" : "ACTIVE",
                  tone: ((regionRows.find(r => r.region === "Europe")?.value || 0) <= 0.08) ? "amber" : "green",
                },
                {
                  label: "Emerging Markets",
                  value: ((regionRows.find(r => r.region === "Emerging Markets")?.value || 0) > 0.05) ? "ACTIVE" : "LOW",
                  tone: ((regionRows.find(r => r.region === "Emerging Markets")?.value || 0) > 0.05) ? "cyan" : "zinc",
                },
                {
                  label: "Global Hedge",
                  value: ((regionRows.find(r => r.region === "Global")?.value || 0) > 0.03) ? "ACTIVE" : "DORMANT",
                  tone: ((regionRows.find(r => r.region === "Global")?.value || 0) > 0.03) ? "emerald" : "zinc",
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className={`rounded-xl border px-4 py-3 ${
                    item.tone === "amber"
                      ? "border-amber-500/20 bg-amber-500/5"
                      : item.tone === "green" || item.tone === "emerald"
                        ? "border-emerald-500/20 bg-emerald-500/5"
                        : item.tone === "cyan"
                          ? "border-cyan-500/20 bg-cyan-500/5"
                          : "border-white/10 bg-white/5"
                  }`}
                >
                  <div className="text-[11px] uppercase tracking-wider text-zinc-500">{item.label}</div>
                  <div
                    className={`mt-1 text-sm font-semibold ${
                      item.tone === "amber"
                        ? "text-amber-200"
                        : item.tone === "green" || item.tone === "emerald"
                          ? "text-emerald-200"
                          : item.tone === "cyan"
                            ? "text-cyan-200"
                            : "text-zinc-300"
                    }`}
                  >
                    {item.value}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {selectedCountryRow && (
            <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-zinc-100">
                    {withFlag(selectedCountryRow.country, selectedCountryRow.label)} · Top Assets
                  </div>
                  <div className="mt-1 text-xs text-zinc-500">
                    Country exposure breakdown and leading assets.
                  </div>
                </div>
                <button
                  className="rounded-lg border border-white/10 px-3 py-1 text-xs text-zinc-300 hover:bg-white/5"
                  onClick={() => setSelectedCountry(null)}
                >
                  Close
                </button>
              </div>

              <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
                <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                  <div className="text-xs text-zinc-500">Country</div>
                  <div className="mt-1 text-sm font-semibold text-zinc-100">{selectedCountryRow.label}</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                  <div className="text-xs text-zinc-500">Region</div>
                  <div className="mt-1 text-sm font-semibold text-zinc-100">{selectedCountryRow.region}</div>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                  <div className="text-xs text-zinc-500">Exposure</div>
                  <div className="mt-1 text-sm font-semibold text-zinc-100">{pct(selectedCountryRow.value)}</div>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {(selectedCountryRow.assets || []).length === 0 && (
                  <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-zinc-500">
                    No asset details available.
                  </div>
                )}

                {(selectedCountryRow.assets || []).map((asset, idx) => (
                  <div
                    key={`asset-${selectedCountryRow.country}-${idx}`}
                    className="rounded-xl border border-white/10 bg-white/5 px-4 py-3"
                  >
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <div className="text-sm text-zinc-200">
                        {isCryptoPair(asset.symbol) ? (
                          <CryptoBadge symbol={asset.symbol} />
                        ) : (
                          <div className="flex flex-col">
                            <span>{withFlag(selectedCountryRow.country)}</span>
                            <span className="text-xs text-zinc-500">{asset.symbol}</span>
                          </div>
                        )}
                      </div>
                      <span className="text-sm font-medium text-zinc-100">{pct(asset.exposure)}</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.max(0, Math.min(asset.exposure * 100, 100))}%`,
                          backgroundColor: REGION_COLORS[selectedCountryRow.region] || REGION_COLORS.Other
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {selectedRegion && (
            <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-zinc-100">
                    {selectedRegion} Drill-down
                  </div>
                  <div className="mt-1 text-xs text-zinc-500">
                    Country allocation breakdown for the selected region.
                  </div>
                </div>
                <button
                  className="rounded-lg border border-white/10 px-3 py-1 text-xs text-zinc-300 hover:bg-white/5"
                  onClick={() => setSelectedRegion(null)}
                >
                  Close
                </button>
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {(regionCountryRows?.[selectedRegion] || []).map((row) => (
                  <button
                    key={`drill-${row.country}`}
                    type="button"
                    onClick={() => setSelectedCountry((prev) => prev === row.country ? null : row.country)}
                    className={`w-full rounded-xl border px-4 py-3 text-left ${
                      selectedCountry === row.country
                        ? "border-cyan-500/40 bg-cyan-500/10"
                        : "border-white/10 bg-white/5"
                    }`}
                  >
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <span className="text-sm text-zinc-200">{row.label}</span>
                      <span className="text-sm font-medium text-zinc-100">{pct(row.value)}</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.max(0, Math.min(row.value * 100, 100))}%`,
                          backgroundColor: REGION_COLORS[row.region] || REGION_COLORS.Other
                        }}
                      />
                    </div>
                    {Array.isArray(row.topAssets) && row.topAssets.length > 0 && (
                      <div className="mt-2 text-xs text-zinc-400">
                        {row.topAssets.join(" · ")}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            {regionRows.slice(0, 4).map((row) => (
              <div
                key={row.region}
                className="rounded-xl border border-white/10 bg-black/20 px-3 py-2"
              >
                <div className="text-xs text-zinc-500">{row.region}</div>
                <div className="mt-1 text-sm font-semibold text-zinc-100">{pct(row.value)}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          {countryRows.length === 0 && (
            <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-zinc-500">
              No country data available.
            </div>
          )}

          {countryRows.map((row) => (
            <div
              key={row.country}
              className="rounded-xl border border-white/10 bg-black/20 px-4 py-3"
            >
              <div className="mb-2 flex items-center justify-between gap-3">
                <span className="text-sm text-zinc-200">{row.label}</span>
                <span className="text-sm font-medium text-zinc-100">{pct(row.value)}</span>
              </div>

              <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.max(0, Math.min(row.value * 100, 100))}%`,
                    backgroundColor: REGION_COLORS[row.region] || REGION_COLORS.Other
                  }}
                />
              </div>
            </div>
          ))}

          <div className="rounded-xl border border-white/10 bg-black/20 px-4 py-3">
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="text-sm text-zinc-200">Global / Off-map Exposure</span>
              <span className="text-sm font-medium text-zinc-100">{pct(offMapWeight)}</span>
            </div>

            <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.max(0, Math.min(offMapWeight * 100, 100))}%`,
                  backgroundColor: REGION_COLORS.Global
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
