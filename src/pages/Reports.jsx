import React, { useEffect, useState } from "react";
import { getWorstTrades, getWorstTradesSummary } from "../lib/api.js";

export default function Reports() {
  const [worst, setWorst] = useState([]);
  const [summary, setSummary] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const w = await getWorstTrades();
        setWorst(Array.isArray(w) ? w : (w?.items ?? []));
        const s = await getWorstTradesSummary();
        setSummary(typeof s === "string" ? s : (s?.summary ?? JSON.stringify(s)));
      } catch (e) {
        setErr(String(e));
      }
    })();
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-extrabold tracking-tight mb-6">Reports</h1>
      {err && <p className="text-red-600 mb-4">Erreur: {err}</p>}

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-2">Worst trades — résumé</h2>
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 p-4 text-sm whitespace-pre-wrap">
          {summary || "—"}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Détails</h2>
        {!worst?.length ? (
          <p className="text-sm opacity-70">Aucune donnée.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
            <table className="min-w-full text-sm">
              <thead className="bg-neutral-50 dark:bg-neutral-900">
                <tr>
                  <Th>Symbol</Th><Th>Loss (€)</Th><Th>In</Th><Th>Out</Th><Th>Reason</Th>
                </tr>
              </thead>
              <tbody>
                {worst.map((r, i) => (
                  <tr key={i} className="border-t border-neutral-200 dark:border-neutral-800">
                    <Td>{r.symbol}</Td>
                    <Td className="text-red-600">{fmt(r.loss_eur)}</Td>
                    <Td>{r.ts_in || r.date_in || "—"}</Td>
                    <Td>{r.ts_out || r.date_out || "—"}</Td>
                    <Td>{r.reason || "—"}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
function Th({ children }) { return <th className="text-left px-3 py-2 font-semibold">{children}</th>; }
function Td({ children }) { return <td className="px-3 py-2">{children}</td>; }
function fmt(x){ return (x ?? x===0) ? Number(x).toLocaleString() : "—"; }
