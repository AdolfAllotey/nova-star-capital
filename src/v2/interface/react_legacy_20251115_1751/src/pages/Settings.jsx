// src/pages/Settings.jsx
import React, { useState } from "react";

export default function Settings() {
  const [darkMode] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30);

  return (
    <div className="p-6 space-y-6">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Settings</h1>
          <p className="text-sm text-zinc-400">
            Préférences locales de l’interface (sans impact sur le moteur de
            trading).
          </p>
        </div>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Affichage */}
        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 space-y-3">
          <h2 className="text-sm font-medium text-zinc-200">Affichage</h2>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-zinc-200">Mode sombre</div>
              <div className="text-xs text-zinc-500">
                Activé par défaut pour la salle de marché.
              </div>
            </div>
            <span className="px-2 py-0.5 rounded-full text-xs bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
              {darkMode ? "On" : "Off"}
            </span>
          </div>
        </section>

        {/* Rafraîchissement */}
        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 space-y-3">
          <h2 className="text-sm font-medium text-zinc-200">Rafraîchissement</h2>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-zinc-200">
                Auto-refresh du dashboard
              </div>
              <div className="text-xs text-zinc-500">
                Quand activé, certaines cartes pourront se rafraîchir
                automatiquement.
              </div>
            </div>
            <button
              type="button"
              onClick={() => setAutoRefresh((v) => !v)}
              className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs border transition ${
                autoRefresh
                  ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
                  : "bg-zinc-800 text-zinc-300 border-zinc-600"
              }`}
            >
              {autoRefresh ? "Activé" : "Désactivé"}
            </button>
          </div>

          <div className="flex items-center justify-between gap-4">
            <label className="text-sm text-zinc-200">
              Intervalle (secondes)
            </label>
            <input
              type="number"
              min={5}
              max={300}
              step={5}
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value) || 30)}
              className="w-24 rounded-lg bg-zinc-900 border border-zinc-700 px-2 py-1 text-sm text-zinc-100 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
        </section>
      </div>

      <p className="text-xs text-zinc-500">
        ⚠️ Ces réglages sont pour l’interface uniquement. Les paramètres du bot
        (risk, stratégies, routing exchanges) restent pilotés côté backend
        Nova Star Capital.
      </p>
    </div>
  );
}
