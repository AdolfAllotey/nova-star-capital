// src/pages/Profitability.jsx
import React, { useEffect, useMemo, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import DataState from "../components/ui/DataState";
import { fetchJson } from "../lib/apiClient";

function formatCurrency(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = typeof v === "number" ? v : Number(v);
  return `${n.toFixed(2)} €`;
}

function formatPct(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = typeof v === "number" ? v : Number(v);
  return `${n.toFixed(2)} %`;
}

function monthLabel(m) {
  if (!m) return "—";
  if (m.label) return m.label;
  if (m.year && m.month) return `${m.year}-${String(m.month).padStart(2, "0")}`;
  return m.date || "—";
}

export default function ProfitabilityPage() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [monthly, setMonthly] = useState([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setErr(null);

      const r = await fetchJson("/profitability/monthly", { timeoutMs: 8000 });
      if (cancelled) return;

      // 404 / no data => on considère empty (ou error doux si detail)
      if (!r.ok) {
        // Certains endpoints renvoient {"detail":"No profitability data"} avec 200/404 selon impl
        const msg =
          r?.error?.detail?.detail ??
          r?.error?.detail ??
          r?.error?.message ??
          (typeof r?.error === "string" ? r.error : null) ??
          null;

        if (msg && String(msg).toLowerCase().includes("no profitability")) {
          setMonthly([]);
          setErr(null);
          setLoading(false);
          return;
        }

        setErr(r.error);
        setMonthly([]);
        setLoading(false);
        return;
      }

      const data = r.data;

      // Si l’API renvoie un objet {detail:"No profitability data"} en 200
      if (data && typeof data === "object" && data.detail) {
        if (String(data.detail).toLowerCase().includes("no profitability")) {
          setMonthly([]);
          setErr(null);
          setLoading(false);
          return;
        }
      }

      const items = Array.isArray(data?.monthly) ? data.monthly : [];
      setMonthly(items);
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const aggregates = useMemo(() => {
    if (!monthly.length) {
      return { pnlGross: null, pnlNet: null, costs: null, months: 0 };
    }
    let pnlGross = 0;
    let pnlNet = 0;
    let costs = 0;

    for (const m of monthly) {
      const g = Number(m?.pnl_gross_eur ?? 0) || 0;
      const n = Number(m?.pnl_net_eur ?? 0) || 0;
      const c = Number(m?.costs_eur ?? 0) || 0;
      pnlGross += g;
      pnlNet += n;
      costs += c;
    }

    return { pnlGross, pnlNet, costs, months: monthly.length };
  }, [monthly]);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">Profitability</h1>
          <p className="text-sm text-zinc-400">
            Suivi rentabilité mensuelle (P&amp;L vs coûts). Source: <code>/profitability/monthly</code>
          </p>
        </div>
        <div className="text-xs text-zinc-500">PREPROD</div>
      </header>

      <SectionCard title="Synthèse globale">
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && monthly.length === 0}
          emptyText="Aucune donnée de rentabilité pour le moment (monthly_pnl.json non généré)."
        >
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">P&amp;L brut cumulé</div>
              <div className="mt-1 text-xl font-semibold text-zinc-50">{formatCurrency(aggregates.pnlGross)}</div>
              <div className="mt-1 text-xs text-zinc-500">Somme des P&amp;L bruts mensuels</div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">Coûts cumulés</div>
              <div className="mt-1 text-xl font-semibold text-zinc-50">{formatCurrency(aggregates.costs)}</div>
              <div className="mt-1 text-xs text-zinc-500">APIs, serveurs, stockage, envoi…</div>
            </div>

            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4">
              <div className="text-xs text-zinc-400">P&amp;L net cumulé</div>
              <div className="mt-1 text-xl font-semibold text-zinc-50">{formatCurrency(aggregates.pnlNet)}</div>
              <div className="mt-1 text-xs text-zinc-500">P&amp;L brut - coûts</div>
            </div>
          </div>
        </DataState>
      </SectionCard>

      <SectionCard title="Détail par mois">
        <DataState
          loading={loading}
          error={err}
          empty={!loading && !err && monthly.length === 0}
          emptyText="Le tableau apparaîtra dès qu’un premier monthly_pnl.json sera produit."
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-zinc-500">
                <tr className="border-b border-zinc-800">
                  <th className="py-2 text-left pr-2">Mois</th>
                  <th className="py-2 text-right pr-2">P&amp;L brut (€)</th>
                  <th className="py-2 text-right pr-2">Coûts (€)</th>
                  <th className="py-2 text-right pr-2">P&amp;L net (€)</th>
                  <th className="py-2 text-right pr-2">Brut (%)</th>
                  <th className="py-2 text-right pr-2">Net (%)</th>
                  <th className="py-2 text-right pl-2">Equity (€)</th>
                </tr>
              </thead>
              <tbody>
                {monthly.map((m, idx) => {
                  const gross = Number(m?.pnl_gross_eur ?? NaN);
                  const costs = Number(m?.costs_eur ?? NaN);
                  const net = Number(m?.pnl_net_eur ?? NaN);
                  const grossPct = Number(m?.pnl_gross_pct ?? NaN);
                  const netPct = Number(m?.pnl_net_pct ?? NaN);
                  const equity = Number(m?.equity_eur ?? NaN);

                  return (
                    <tr key={idx} className="border-b border-zinc-900/60">
                      <td className="py-2 pr-2">{monthLabel(m)}</td>
                      <td className={`py-2 text-right pr-2 ${!Number.isNaN(gross) && gross >= 0 ? "text-emerald-400" : !Number.isNaN(gross) ? "text-red-400" : "text-zinc-500"}`}>
                        {formatCurrency(gross)}
                      </td>
                      <td className="py-2 text-right pr-2 text-zinc-200">
                        {formatCurrency(costs)}
                      </td>
                      <td className={`py-2 text-right pr-2 ${!Number.isNaN(net) && net >= 0 ? "text-emerald-400" : !Number.isNaN(net) ? "text-red-400" : "text-zinc-500"}`}>
                        {formatCurrency(net)}
                      </td>
                      <td className="py-2 text-right pr-2 text-zinc-200">{formatPct(grossPct)}</td>
                      <td className="py-2 text-right pr-2 text-zinc-200">{formatPct(netPct)}</td>
                      <td className="py-2 text-right pl-2 text-zinc-200">{formatCurrency(equity)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </DataState>
      </SectionCard>
    </div>
  );
}
