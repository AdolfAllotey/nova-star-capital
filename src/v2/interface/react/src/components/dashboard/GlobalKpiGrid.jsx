import React from "react";

function fmtNumber(v) {
  const n = Number(v ?? 0);
  return Number.isFinite(n) ? String(n) : "0";
}

function fmtMoney(v) {
  const n = Number(v ?? 0);
  if (!Number.isFinite(n)) return "0,00 €";
  return `${n.toFixed(2).replace(".", ",")} €`;
}

function KpiCard({ label, value }) {
  return (
    <div className="rounded-[22px] border border-white/10 bg-black/20 px-5 py-5 backdrop-blur-sm">
      <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">
        {label}
      </div>
      <div className="mt-3 text-2xl font-semibold tracking-tight text-zinc-100">
        {value}
      </div>
    </div>
  );
}

export default function GlobalKpiGrid(props) {
  const globalData =
    props?.global ??
    props?.data?.global ??
    {};

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-8">
      <KpiCard label="Capital" value={fmtNumber(globalData.capitalObserved)} />
      <KpiCard label="Trading PnL" value={fmtMoney(globalData.pnlGlobal)} />
      <KpiCard label="LT PnL" value={fmtMoney(globalData.pnlLongTerm)} />
      <KpiCard label="Total Patrimonial" value={fmtMoney(globalData.pnlTotalIncludingLongTermAndShadow)} />
      <KpiCard label="Positions" value={fmtNumber(globalData.openPositions)} />
      <KpiCard label="Candidates" value={fmtNumber(globalData.candidatesCount)} />
      <KpiCard label="Orders" value={fmtNumber(globalData.ordersCount)} />
      <KpiCard label="Risk Flags" value={fmtNumber(globalData.riskFlags)} />
    </div>
  );
}
