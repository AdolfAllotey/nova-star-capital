// src/pages/TopMovers.jsx
import React, { useEffect, useMemo, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import DataState from "../components/ui/DataState";
import { fetchJson } from "../lib/apiClient";

function getChg24h(item) {
  const v =
    item?.chg_24h ??
    item?.change_24h ??
    item?.pct_24h ??
    item?.percent_24h ??
    null;
  const n = typeof v === "number" ? v : v !== null ? Number(v) : NaN;
  return Number.isNaN(n) ? null : n;
}

function num(v) {
  if (v === null || v === undefined) return null;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isNaN(n) ? null : n;
}

function TokenRow({ rank, item }) {
  const chg = getChg24h(item);
  const price = num(item?.price);

  return (
    <tr className="border-b border-zinc-800/70">
      <td className="py-2 text-xs text-zinc-500">{rank}</td>
      <td className="py-2">
        <div className="flex flex-col">
          <span className="text-sm text-zinc-100">
            {item.name || item.id || item.symbol || "N/A"}
          </span>
          <span className="text-xs text-zinc-500">
            {item.symbol ? String(item.symbol).toUpperCase() : "–"}
          </span>
        </div>
      </td>
      <td className="py-2 text-right text-sm text-zinc-100">
        {price !== null ? price.toFixed(4) : "n/d"}
      </td>
      <td className="py-2 text-right text-sm">
        {chg !== null ? (
          <span className={chg > 0 ? "text-emerald-400" : chg < 0 ? "text-red-400" : "text-zinc-400"}>
            {chg.toFixed(2)} %
          </span>
        ) : (
          <span className="text-zinc-500">n/d</span>
        )}
      </td>
      <td className="py-2 text-xs text-right text-zinc-500">
        {item.source || "—"}
      </td>
    </tr>
  );
}

export default function TopMovers() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [rawData, setRawData] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const r = await fetchJson("/market/top-movers", { timeoutMs: 8000 });
      if (cancelled) return;

      if (!r.ok) {
        setErr(r.error);
        setRawData(null);
        setLoading(false);
        return;
      }

      // si l’API renvoie un objet avec message => on l’affiche en error "soft"
      if (r.data && typeof r.data === "object" && r.data.message) {
        setRawData(r.data);
        setErr({ message: String(r.data.message), status: 200, url: r.url });
        setLoading(false);
        return;
      }

      setRawData(r.data);
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const updatedAt = useMemo(() => {
    if (rawData && typeof rawData === "object") return rawData.updated_at || null;
    return null;
  }, [rawData]);

  const items = useMemo(() => {
    if (!rawData) return [];
    if (Array.isArray(rawData)) return rawData;
    if (Array.isArray(rawData.items)) return rawData.items;
    return [];
  }, [rawData]);

  const { gainers, losers } = useMemo(() => {
    const withChange = items
      .map((it) => ({ ...it, __chg: getChg24h(it) }))
      .filter((it) => typeof it.__chg === "number" && it.__chg !== null);

    const gainersSorted = [...withChange]
      .filter((it) => it.__chg > 0)
      .sort((a, b) => b.__chg - a.__chg)
      .slice(0, 10);

    const losersSorted = [...withChange]
      .filter((it) => it.__chg < 0)
      .sort((a, b) => a.__chg - b.__chg)
      .slice(0, 10);

    return { gainers: gainersSorted, losers: losersSorted };
  }, [items]);

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">Top Movers</h1>
          <p className="text-sm text-zinc-400">Vue des plus fortes hausses et baisses sur 24h.</p>
        </div>
        {updatedAt && (
          <div className="text-xs text-zinc-500">
            Dernière mise à jour : {new Date(updatedAt).toLocaleString("fr-FR")}
          </div>
        )}
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <SectionCard title="Top Gainers 24h">
          <DataState
            loading={loading}
            error={err}
            empty={!loading && !err && gainers.length === 0}
            emptyText="Aucun gainer détecté (données vides ou non disponibles)."
          >
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-xs uppercase text-zinc-500 border-b border-zinc-800">
                    <th className="py-2 text-left w-10">#</th>
                    <th className="py-2 text-left">Token</th>
                    <th className="py-2 text-right">Prix</th>
                    <th className="py-2 text-right">24h</th>
                    <th className="py-2 text-right">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {gainers.map((it, idx) => (
                    <TokenRow key={it.id || it.symbol || idx} rank={idx + 1} item={it} />
                  ))}
                </tbody>
              </table>
            </div>
          </DataState>
        </SectionCard>

        <SectionCard title="Top Losers 24h">
          <DataState
            loading={loading}
            error={err}
            empty={!loading && !err && losers.length === 0}
            emptyText="Aucun loser significatif détecté (données vides ou non disponibles)."
          >
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-xs uppercase text-zinc-500 border-b border-zinc-800">
                    <th className="py-2 text-left w-10">#</th>
                    <th className="py-2 text-left">Token</th>
                    <th className="py-2 text-right">Prix</th>
                    <th className="py-2 text-right">24h</th>
                    <th className="py-2 text-right">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {losers.map((it, idx) => (
                    <TokenRow key={it.id || it.symbol || idx} rank={idx + 1} item={it} />
                  ))}
                </tbody>
              </table>
            </div>
          </DataState>
        </SectionCard>
      </div>
    </div>
  );
}
