// src/pages/TopMovers.jsx
// Vue des plus fortes hausses/baisses 24h à partir de /market/top-movers

import React, { useEffect, useState, useMemo } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://api.preprod.novastarcapital.fr";

function buildUrl(path) {
  return `${API_BASE.replace(/\/+$/, "")}${path}`;
}

function Section({ title, children }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold text-zinc-100 mb-3 border-b border-zinc-800 pb-1">
        {title}
      </h2>
      <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
        {children}
      </div>
    </section>
  );
}

function TokenRow({ rank, item }) {
  return (
    <tr className="border-b border-zinc-800/70">
      <td className="py-2 text-xs text-zinc-500">{rank}</td>
      <td className="py-2">
        <div className="flex flex-col">
          <span className="text-sm text-zinc-100">
            {item.name || item.id || "N/A"}
          </span>
          <span className="text-xs text-zinc-500">
            {item.symbol ? item.symbol.toUpperCase() : "–"}
          </span>
        </div>
      </td>
      <td className="py-2 text-right text-sm text-zinc-100">
        {typeof item.price === "number" ? item.price.toFixed(4) : "n/d"}
      </td>
      <td className="py-2 text-right text-sm">
        {typeof item.chg_24h === "number" ? (
          <span
            className={
              item.chg_24h > 0
                ? "text-emerald-400"
                : item.chg_24h < 0
                ? "text-red-400"
                : "text-zinc-400"
            }
          >
            {item.chg_24h.toFixed(2)} %
          </span>
        ) : (
          <span className="text-zinc-500">n/d</span>
        )}
      </td>
      <td className="py-2 text-xs text-right text-zinc-500">
        {item.source || "n/d"}
      </td>
    </tr>
  );
}

export default function TopMovers() {
  const [rawData, setRawData] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const res = await fetch(buildUrl("/market/top-movers"));
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        if (cancelled) return;
        setRawData(data);
        setUpdatedAt(data?.updated_at || null);
      } catch (e) {
        console.error("Erreur fetch /market/top-movers:", e);
        if (!cancelled) {
          setError("Impossible de charger les Top Movers.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const items = useMemo(() => {
    if (!rawData) return [];
    if (Array.isArray(rawData)) return rawData;
    if (Array.isArray(rawData.items)) return rawData.items;
    return [];
  }, [rawData]);

  const { gainers, losers } = useMemo(() => {
    const withChange = items.filter(
      (it) => typeof it.chg_24h === "number" && !Number.isNaN(it.chg_24h)
    );

    const gainersSorted = [...withChange]
      .filter((it) => it.chg_24h > 0)
      .sort((a, b) => b.chg_24h - a.chg_24h)
      .slice(0, 10);

    const losersSorted = [...withChange]
      .filter((it) => it.chg_24h < 0)
      .sort((a, b) => a.chg_24h - b.chg_24h)
      .slice(0, 10);

    return { gainers: gainersSorted, losers: losersSorted };
  }, [items]);

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">
            Top Movers (Gainers / Losers)
          </h1>
          <p className="text-sm text-zinc-400">
            Vue synthétique des plus fortes hausses et baisses sur les tokens
            suivis.
          </p>
        </div>
        {updatedAt && (
          <div className="text-xs text-zinc-500">
            Dernière mise à jour :{" "}
            {new Date(updatedAt).toLocaleString("fr-FR")}
          </div>
        )}
      </header>

      {error && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-400">
          Chargement des Top Movers…
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          <Section title="Top Gainers 24h">
            {gainers.length === 0 ? (
              <p className="text-sm text-zinc-500">
                Aucun gainer détecté pour le moment (selon les données
                disponibles sur 24h).
              </p>
            ) : (
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
                      <TokenRow
                        key={it.id || it.symbol || idx}
                        rank={idx + 1}
                        item={it}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          <Section title="Top Losers 24h">
            {losers.length === 0 ? (
              <p className="text-sm text-zinc-500">
                Aucun loser significatif détecté pour le moment (selon les
                données disponibles sur 24h).
              </p>
            ) : (
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
                      <TokenRow
                        key={it.id || it.symbol || idx}
                        rank={idx + 1}
                        item={it}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>
        </div>
      )}
    </div>
  );
}
