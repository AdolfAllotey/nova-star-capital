// src/pages/Portfolio.jsx
import React, { useEffect, useMemo, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import DataState from "../components/ui/DataState";
import { fetchJson, apiUrl } from "../lib/apiClient";

function n(v) {
  if (v === null || v === undefined) return null;
  const x = typeof v === "number" ? v : Number(v);
  return Number.isNaN(x) ? null : x;
}

function fmt(v, digits = 2) {
  const x = n(v);
  if (x === null) return "—";
  return x.toFixed(digits);
}

function fmtCurrency(v) {
  const x = n(v);
  if (x === null) return "—";
  return `${x.toFixed(2)} €`;
}

function pickSymbol(p) {
  return p?.symbol || p?.token || p?.asset || p?.id || "—";
}

function pickQty(p) {
  return p?.qty ?? p?.amount ?? p?.size ?? null;
}

function pickPnl(p) {
  return p?.pnl ?? p?.pnl_eur ?? p?.unrealized_pnl ?? p?.pnl_unrealized ?? null;
}

function pickValue(p) {
  return p?.value_eur ?? p?.notional_eur ?? p?.position_value_eur ?? null;
}

export default function Portfolio() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [positions, setPositions] = useState([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const r = await fetchJson("/portfolio/open", { timeoutMs: 8000 });
      if (cancelled) return;

      if (!r?.ok) {
        setErr(r?.error || "Impossible de charger /portfolio/open");
        setPositions([]);
        setLoading(false);
        return;
      }

      const arr = Array.isArray(r?.data?.positions) ? r.data.positions : [];
      setPositions(arr);
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const micro = useMemo(() => {
    const count = Array.isArray(positions) ? positions.length : 0;

    let pnlSum = 0;
    let valueSum = 0;
    let winners = 0;
    let losers = 0;

    const enriched = (Array.isArray(positions) ? positions : []).map((p) => ({
      symbol: pickSymbol(p),
      qty: pickQty(p),
      pnl: n(pickPnl(p)),
      value: n(pickValue(p)),
    }));

    for (const p of enriched) {
      if (p.pnl !== null) {
        pnlSum += p.pnl;
        if (p.pnl > 0) winners += 1;
        if (p.pnl < 0) losers += 1;
      }
      if (p.value !== null) valueSum += p.value;
    }

    const winRate = winners + losers > 0 ? (winners / (winners + losers)) * 100 : null;
    const avgPnl = winners + losers > 0 ? pnlSum / (winners + losers) : null;

    const byValue = enriched
      .filter((p) => p.value !== null)
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

    const top1 = byValue[0]?.value ?? null;
    const top3 = byValue.slice(0, 3).reduce((a, p) => a + (p.value ?? 0), 0);

    const top1Pct = valueSum > 0 && top1 !== null ? (top1 / valueSum) * 100 : null;
    const top3Pct = valueSum > 0 && top3 > 0 ? (top3 / valueSum) * 100 : null;

    return {
      count,
      pnlSum,
      valueSum: valueSum > 0 ? valueSum : null,
      winners,
      losers,
      winRate,
      avgPnl,
      top1Pct,
      top3Pct,
    };
  }, [positions]);

  const showEmpty = !loading && !err && positions.length === 0;

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">Portfolio</h1>
          <p className="text-sm text-zinc-400">
            Positions ouvertes (listing + micro-indicateurs). Endpoint: <code>/portfolio/open</code>
          </p>
        </div>
        <div className="text-xs text-zinc-500">Source: {apiUrl("/portfolio/open")}</div>
      </header>

      {/* Micro-indicateurs */}
      <SectionCard title="Micro-indicateurs">
        <DataState
          loading={loading}
          error={err}
          empty={showEmpty}
          emptyText="Aucune position ouverte pour le moment."
        />

        {!loading && !err && positions.length > 0 && (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
              <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
                <div className="text-xs text-zinc-400">Positions</div>
                <div className="mt-1 text-xl font-semibold text-zinc-50">{micro.count}</div>
                <div className="mt-1 text-xs text-zinc-500">Nb de lignes ouvertes</div>
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
                <div className="text-xs text-zinc-400">PnL (unrealized)</div>
                <div className={`mt-1 text-xl font-semibold ${micro.pnlSum >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {fmtCurrency(micro.pnlSum)}
                </div>
                <div className="mt-1 text-xs text-zinc-500">Somme des PnL disponibles</div>
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
                <div className="text-xs text-zinc-400">Win rate (proxy)</div>
                <div className="mt-1 text-xl font-semibold text-zinc-50">
                  {micro.winRate === null ? "—" : `${fmt(micro.winRate, 1)} %`}
                </div>
                <div className="mt-1 text-xs text-zinc-500">
                  Gagnantes / (gagnantes + perdantes)
                </div>
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
                <div className="text-xs text-zinc-400">Concentration</div>
                <div className="mt-1 text-xl font-semibold text-zinc-50">
                  {micro.top1Pct === null ? "—" : `${fmt(micro.top1Pct, 1)} %`}
                </div>
                <div className="mt-1 text-xs text-zinc-500">
                  Top 1 ({micro.top3Pct === null ? "—" : `Top 3: ${fmt(micro.top3Pct, 1)} %`})
                </div>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
                <div className="text-xs text-zinc-400">Exposition (€)</div>
                <div className="mt-1 text-xl font-semibold text-zinc-50">
                  {micro.valueSum === null ? "—" : fmtCurrency(micro.valueSum)}
                </div>
                <div className="mt-1 text-xs text-zinc-500">Somme des values si disponibles</div>
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
                <div className="text-xs text-zinc-400">Winners / Losers</div>
                <div className="mt-1 text-xl font-semibold text-zinc-50">
                  {micro.winners} / {micro.losers}
                </div>
                <div className="mt-1 text-xs text-zinc-500">Basé sur PnL dispo</div>
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
                <div className="text-xs text-zinc-400">Avg PnL / ligne</div>
                <div className={`mt-1 text-xl font-semibold ${(micro.avgPnl ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {micro.avgPnl === null ? "—" : fmtCurrency(micro.avgPnl)}
                </div>
                <div className="mt-1 text-xs text-zinc-500">Proxy sur gagnantes+perdantes</div>
              </div>
            </div>
          </>
        )}
      </SectionCard>

      {/* Table positions */}
      <SectionCard title="Positions (détail)">
        <DataState
          loading={loading}
          error={err}
          empty={showEmpty}
          emptyText="Aucune position ouverte."
        />

        {!loading && !err && positions.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-zinc-500">
                <tr className="border-b border-zinc-800">
                  <th className="py-2 text-left">Symbol</th>
                  <th className="py-2 text-right">Qty</th>
                  <th className="py-2 text-right">Value (€)</th>
                  <th className="py-2 text-right">PnL (€)</th>
                  <th className="py-2 text-right">Exchange</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p, i) => {
                  const sym = pickSymbol(p);
                  const qty = pickQty(p);
                  const val = n(pickValue(p));
                  const pnl = n(pickPnl(p));
                  const ex = p?.exchange || p?.venue || "—";

                  return (
                    <tr key={i} className="border-b border-zinc-900/60">
                      <td className="py-2">{sym}</td>
                      <td className="py-2 text-right">{qty ?? "—"}</td>
                      <td className="py-2 text-right text-zinc-200">
                        {val === null ? "—" : fmtCurrency(val)}
                      </td>
                      <td className={`py-2 text-right ${pnl === null ? "text-zinc-500" : pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                        {pnl === null ? "—" : fmtCurrency(pnl)}
                      </td>
                      <td className="py-2 text-right text-zinc-400">{ex}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  );
}
