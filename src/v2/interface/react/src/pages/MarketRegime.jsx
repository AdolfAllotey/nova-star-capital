// src/pages/MarketRegime.jsx
// Page dédiée au régime de marché à partir de /market/regime

import React, { useEffect, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://api.preprod.novastarcapital.fr";

function buildUrl(path) {
  return `${API_BASE.replace(/\/+$/, "")}${path}`;
}

function Stat({ label, value, helper }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-zinc-400">
        {label}
      </span>
      <span className="text-lg font-semibold text-zinc-50">{value}</span>
      {helper && <span className="text-xs text-zinc-500">{helper}</span>}
    </div>
  );
}

function mapModeToLabel(mode) {
  switch ((mode || "").toLowerCase()) {
    case "bull":
      return "Bull (risk-on)";
    case "bear":
      return "Bear (risk-off)";
    case "neutral":
      return "Neutre";
    default:
      return "Inconnu";
  }
}

function mapModeToDescription(mode) {
  switch ((mode || "").toLowerCase()) {
    case "bull":
      return "Régime haussier : tailles de positions élargies, plus de trades momentum.";
    case "bear":
      return "Régime baissier : réduction du risque, plus de cash / long terme défensif.";
    case "neutral":
      return "Marché neutre : approche équilibrée entre prise de risque et protection.";
    default:
      return "Le régime de marché n’a pas encore été détecté par le module dédié.";
  }
}

export default function MarketRegime() {
  const [regime, setRegime] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");

      try {
        const res = await fetch(buildUrl("/dashboard/market_regime"));
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled) setRegime(data);
      } catch (e) {
        console.error("Erreur fetch /dashboard/market_regime:", e);
        if (!cancelled) setError("Impossible de charger le régime de marché.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const mode = regime?.mode || null;
  const modeLabel = mapModeToLabel(mode);
  const description = mapModeToDescription(mode);
  const score =
    typeof regime?.score === "number" ? regime.score : null;
  const updatedAt = regime?.updated_at || null;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-zinc-50">
          Régime de marché
        </h1>
        <p className="text-sm text-zinc-400">
          Diagnostic global du marché (bull / bear / neutre) utilisé pour
          piloter l’intensité du bot.
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-zinc-400">
          Chargement du régime de marché…
        </div>
      ) : (
        <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-5 space-y-5">
          <div className="grid gap-6 md:grid-cols-3">
            <Stat
              label="Régime détecté"
              value={modeLabel}
              helper={description}
            />
            <Stat
              label="Score interne"
              value={
                score !== null ? score.toFixed(2) : "n/d"
              }
              helper="Plus le score est extrême, plus le bot accentue ou réduit le risque."
            />
            <Stat
              label="Source"
              value={regime?.source || "default"}
              helper={
                updatedAt
                  ? `Dernière mise à jour : ${new Date(
                      updatedAt
                    ).toLocaleString("fr-FR")}`
                  : "Horodatage non disponible."
              }
            />
          </div>
        </div>
      )}

      <section className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 space-y-2">
        <h2 className="text-sm font-semibold text-zinc-100">
          Impact sur le bot NSC
        </h2>
        <ul className="text-xs text-zinc-400 space-y-1 list-disc list-inside">
          <li>
            Ajustement des tailles de position et du levier implicite en
            fonction du régime.
          </li>
          <li>
            Répartition dynamique entre Trading / Long Terme / Sécurité.
          </li>
          <li>
            Dans les prochaines versions, le régime pilotera aussi l’activation
            de certaines stratégies (momentum, airdrops, options…).
          </li>
        </ul>
      </section>
    </div>
  );
}
