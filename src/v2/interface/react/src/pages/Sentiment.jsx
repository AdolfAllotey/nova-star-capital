
const normalizeRegime = (r) => {
  if (!r) return "UNKNOWN";
  const v = r.toLowerCase();
  if (v === "risk_on") return "BULL";
  if (v === "risk_off") return "BEAR";
  if (v === "neutral") return "NEUTRAL";
  return "UNKNOWN";
};
// src/pages/Sentiment.jsx
// Vue du sentiment agrégé à partir de /sentiment

import { API_BASE, buildApiUrl as apiUrl } from "../lib/apiBase";
import React, { useEffect, useMemo, useState } from "react";


function buildUrl(path) {
  return `${API_BASE.replace(/\/+$/, "")}${path}`;
}

function sentimentLabel(score) {
  if (score >= 0.6) {
    return {
      label: "Haussier",
      className:
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/40",
    };
  }
  if (score <= 0.4) {
    return {
      label: "Baissier",
      className:
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/40",
    };
  }
  return {
    label: "Neutre",
    className:
      "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-zinc-500/10 text-zinc-300 border border-zinc-500/40",
  };
}

function Section({ title, description, children }) {
  return (
    <section className="mb-8">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-lg font-semibold text-zinc-100 border-b border-zinc-800 pb-1">
          {title}
        </h2>
        {description && (
          <p className="text-xs text-zinc-500 ml-4">{description}</p>
        )}
      </div>
      <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
        {children}
      </div>
    </section>
  );
}

function Stat({ label, value, hint }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-sm font-semibold text-zinc-100">{value}</span>
      {hint && <span className="text-[11px] text-zinc-500 mt-0.5">{hint}</span>}
    </div>
  );
}

function formatScore(score) {
  if (score === null || score === undefined || isNaN(score)) return "–";
  return score.toFixed(2);
}

function formatDate(d) {
  if (!d) return "–";
  const dt = new Date(d);
  if (Number.isNaN(dt.getTime())) return d;
  return dt.toLocaleString();
}

export default function SentimentPage() {
  const [data, setData] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(buildUrl("/sentiment"));
        if (res.status === 404) {
          // Pas de données: l’API renvoie {"detail":"Sentiment indisponible"}
          if (!cancelled) {
            setData(null);
            setUpdatedAt(null);
            setError("Sentiment indisponible (pas de données).");
          }
          return;
        }
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const json = await res.json();
        if (!cancelled) {
          setData(json);
          setUpdatedAt(json.updated_at || json.server_ts || null);
        }
      } catch (err) {
        console.error("Error fetching sentiment:", err);
        if (!cancelled) {
          setError(
            "Impossible de charger le sentiment global. Vérifie l’API /sentiment."
          );
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

  const globalScore = useMemo(() => {
    if (!data) return null;
    // Tolérant : average_sentiment.score ou score directement
    const avg =
      data.average_sentiment?.score ??
      data.average_sentiment ??
      data.score ??
      null;
    return typeof avg === "number" ? avg : null;
  }, [data]);

  const perSource = useMemo(() => {
    if (!data) return [];
    // Tolérant : data.sources ou data.by_source
    const src =
      (Array.isArray(data.sources) && data.sources) ||
      (Array.isArray(data.by_source) && data.by_source) ||
      [];
    return src;
  }, [data]);

  const topTokens = useMemo(() => {
    if (!data) return [];
    const t =
      (Array.isArray(data.tokens) && data.tokens) ||
      (Array.isArray(data.top_tokens) && data.top_tokens) ||
      [];
    // on garde les 10 premiers max
    return t.slice(0, 10);
  }, [data]);

  const globalLabel = sentimentLabel(globalScore ?? 0.5);

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="mb-4">
        <h1 className="text-2xl font-semibold text-zinc-100 mb-1">
          Sentiment marché &amp; signaux sociaux
        </h1>
        <p className="text-sm text-zinc-400">
          Synthèse des signaux Telegram, Twitter/X, Reddit et autres sources
          pour alimenter les décisions du bot (risk on/off, size, blacklist…).
        </p>
        {updatedAt && (
          <p className="text-[11px] text-zinc-500 mt-1">
            Dernière mise à jour : {formatDate(updatedAt)}
          </p>
        )}
      </header>

      {/* Bloc principal : sentiment global */}
      <Section
        title="Sentiment global"
        description="Score agrégé utilisé comme input pour le risk controller & le market regime."
      >
        {loading && !data ? (
          <div className="text-sm text-zinc-400">Chargement…</div>
        ) : error ? (
          <div className="text-sm text-red-400">{error}</div>
        ) : !data ? (
          <div className="text-sm text-zinc-400">
            Aucun score de sentiment n’est encore disponible. Dès que les
            scrapers tourneront en continu, le{" "}
            <span className="font-medium text-emerald-400">
              sentiment global
            </span>{" "}
            apparaîtra ici.
          </div>
        ) : (
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex flex-col">
                <span className="text-xs text-zinc-500">Score global</span>
                <span className="text-3xl font-semibold text-zinc-50">
                  {globalScore !== null ? formatScore(globalScore) : "–"}
                </span>
              </div>
              <span className={globalLabel.className}>
                {globalLabel.label}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              <Stat
                label="Messages / flux analysés"
                value={
                  data.total_messages ??
                  data.total_items ??
                  data.count ??
                  "–"
                }
                hint="Volume agrégé sur la fenêtre d’analyse"
              />
              <Stat
                label="Période couverte"
                value={data.window || data.time_window || (data.hours != null ? `${data.hours}h` : "–")}
                hint="Fenêtre utilisée pour la moyenne"
              />
              <Stat
                label="Market regime (vue sentiment)"
                value={data.regime_label || data.regime || "–"}
                hint="Bull / Bear / Neutre (côté sentiment)"
              />
            </div>
          </div>
        )}
      </Section>

      {/* Sentiment par source */}
      <Section
        title="Sentiment par source"
        description="Vue détaillée par canal (Telegram, Twitter/X, Reddit…)."
      >
        {loading && !data ? (
          <div className="text-sm text-zinc-400">Chargement…</div>
        ) : error ? (
          <div className="text-sm text-red-400">{error}</div>
        ) : !perSource.length ? (
          <div className="text-sm text-zinc-400">
            Aucune statistique par source pour l’instant.  
            Dès que les scrapers tourneront, tu verras{" "}
            <span className="font-medium">l’impact de chaque canal</span> sur le
            score global.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-xs text-zinc-500">
                  <th className="text-left py-2 pr-2">Source</th>
                  <th className="text-right py-2 pr-2">Score</th>
                  <th className="text-right py-2 pr-2">Messages</th>
                  <th className="text-right py-2 pr-2">Haussier</th>
                  <th className="text-right py-2 pr-2">Neutre</th>
                  <th className="text-right py-2 pr-2">Baissier</th>
                </tr>
              </thead>
              <tbody>
                {perSource.map((s, idx) => {
                  const score = Number(
                    s.score ??
                      s.average_sentiment ??
                      s.average_sentiment?.score ??
                      NaN
                  );
                  const label = sentimentLabel(
                    Number.isNaN(score) ? 0.5 : score
                  );
                  const name =
                    s.source ||
                    s.name ||
                    s.channel ||
                    s.id ||
                    `Source ${idx + 1}`;

                  return (
                    <tr
                      key={name}
                      className="border-b border-zinc-800/60 hover:bg-zinc-900/60"
                    >
                      <td className="py-2 pr-2">
                        <div className="flex flex-col">
                          <span className="text-sm text-zinc-100">{name}</span>
                          {s.notes && (
                            <span className="text-[11px] text-zinc-500">
                              {s.notes}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2 pr-2 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <span className="text-zinc-100">
                            {Number.isNaN(score)
                              ? "–"
                              : formatScore(score)}
                          </span>
                          <span className={label.className}>
                            {label.label}
                          </span>
                        </div>
                      </td>
                      <td className="py-2 pr-2 text-right text-zinc-100">
                        {s.count ??
                          s.messages ??
                          s.total ??
                          "–"}
                      </td>
                      <td className="py-2 pr-2 text-right text-emerald-400 text-xs">
                        {s.bullish ?? s.positive ?? "–"}
                      </td>
                      <td className="py-2 pr-2 text-right text-zinc-300 text-xs">
                        {s.neutral ?? "–"}
                      </td>
                      <td className="py-2 pr-2 text-right text-red-400 text-xs">
                        {s.bearish ?? s.negative ?? "–"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {/* Top tokens par sentiment */}
      <Section
        title="Tokens les plus marqués"
        description="Tokens qui dominent les discussions (positif ou négatif)."
      >
        {loading && !data ? (
          <div className="text-sm text-zinc-400">Chargement…</div>
        ) : error ? (
          <div className="text-sm text-red-400">{error}</div>
        ) : !topTokens.length ? (
          <div className="text-sm text-zinc-400">
            Pour l’instant, aucun token n’a encore assez de volume de messages
            pour apparaître ici.  
            Quand les scrapers tourneront, tu verras quels{" "}
            <span className="font-medium text-emerald-400">
              tokens dominent le flux
            </span>{" "}
            (bull ou bear).
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
            {topTokens.map((t, idx) => {
              const token = t.token || t.symbol || t.id || `Token ${idx + 1}`;
              const score = Number(t.score ?? t.sentiment ?? NaN);
              const lbl = sentimentLabel(Number.isNaN(score) ? 0.5 : score);

              return (
                <div
                  key={token}
                  className="border border-zinc-800 rounded-lg px-3 py-2 bg-zinc-900/60"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-zinc-100">
                      {token}
                    </span>
                    <span className={lbl.className}>{lbl.label}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-zinc-400">
                    <span>
                      Score :{" "}
                      <span className="text-zinc-100">
                        {Number.isNaN(score) ? "–" : score.toFixed(2)}
                      </span>
                    </span>
                    <span>
                      Messages :{" "}
                      <span className="text-zinc-100">
                        {t.count ?? t.messages ?? "–"}
                      </span>
                    </span>
                  </div>
                  {t.source && (
                    <p className="mt-1 text-[11px] text-zinc-500">
                      Source dominante : {t.source}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Section>
    </div>
  );
}
