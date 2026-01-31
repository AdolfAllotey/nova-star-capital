// src/pages/Settings.jsx
// NSC Trading Desk – Settings (V2 Preprod, style Dashboard)
// Page de réglages locale (localStorage) : rafraîchissement, mode, debug, etc.

import React, { useEffect, useState } from "react";
import { API_BASE } from "../lib/apiBase";

// ---------------------------
// UI Components (Dashboard)
// ---------------------------
function Section({ title, children }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold text-zinc-100 mb-3 border-b border-zinc-800 pb-1">
        {title}
      </h2>
      <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4 space-y-4">
        {children}
      </div>
    </section>
  );
}

function Label({ children }) {
  return (
    <label className="block text-sm font-medium text-zinc-200 mb-1">
      {children}
    </label>
  );
}

function Helper({ children }) {
  return <p className="text-xs text-zinc-500 mt-1">{children}</p>;
}

// ---------------------------
// Const / helpers
// ---------------------------
const LS_KEY = "nsc_settings_v2";

function loadSettingsFromStorage() {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (e) {
    console.warn("[Settings] Impossible de lire localStorage", e);
    return null;
  }
}

function saveSettingsToStorage(settings) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LS_KEY, JSON.stringify(settings));
  } catch (e) {
    console.warn("[Settings] Impossible d'écrire dans localStorage", e);
  }
}

// ---------------------------
// Main page
// ---------------------------
export default function Settings() {
  const [refreshSeconds, setRefreshSeconds] = useState(60);
  const [tradingMode, setTradingMode] = useState("simulation"); // simulation | real
  const [showDebug, setShowDebug] = useState(false);
  const [theme, setTheme] = useState("dark");
  const [savedMessage, setSavedMessage] = useState("");

  // Charger depuis localStorage au montage
  useEffect(() => {
    const stored = loadSettingsFromStorage();
    if (!stored) return;

    if (typeof stored.refreshSeconds === "number") {
      queueMicrotask(() => setRefreshSeconds(stored.refreshSeconds));
    }
    if (stored.tradingMode === "simulation" || stored.tradingMode === "real") {
      queueMicrotask(() => setTradingMode(stored.tradingMode));
    }
    if (typeof stored.showDebug === "boolean") {
      queueMicrotask(() => setShowDebug(stored.showDebug));
    }
    if (stored.theme === "dark" || stored.theme === "light") {
      queueMicrotask(() => setTheme(stored.theme));
    }
  }, []);

  const handleSave = () => {
    const settings = {
      refreshSeconds,
      tradingMode,
      showDebug,
      theme,
    };
    saveSettingsToStorage(settings);
    setSavedMessage("Paramètres enregistrés localement.");
    setTimeout(() => setSavedMessage(""), 2500);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <header>
        <h1 className="text-2xl font-semibold text-zinc-50">
          NSC Trading Desk – Settings
        </h1>
        <p className="text-sm text-zinc-400">
          Réglages locaux de l’interface NSC (préproduction). Ces paramètres
          sont stockés dans ton navigateur (localStorage) et n’impactent pas
          encore directement le backend.
        </p>
      </header>

      {/* Info env */}
      <Section title="Environnement & API">
        <div className="text-sm text-zinc-300 space-y-2">
          <div>
            <span className="text-zinc-400">Base API détectée :</span>
            <div className="font-mono text-xs break-all text-zinc-200 mt-1">
              {API_BASE}
            </div>
          </div>
          <div>
            <span className="text-zinc-400">Mode :</span>
            <span className="ml-2 text-emerald-400 font-medium">
              Préproduction
            </span>
          </div>
          <Helper>
            Le changement de mode (simulation / réel) ci-dessous est pour
            l’instant purement indicatif côté interface. L’activation réelle se
            fera via la configuration du backend NSC.
          </Helper>
        </div>
      </Section>

      {/* Paramètres UI & rafraîchissement */}
      <Section title="Rafraîchissement & interface">
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <Label>Intervalle de rafraîchissement des données</Label>
            <input
              type="number"
              min={10}
              max={3600}
              value={refreshSeconds}
              onChange={(e) => setRefreshSeconds(Number(e.target.value) || 60)}
              className="w-full rounded-lg bg-zinc-900 border border-zinc-700 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            />
            <Helper>
              Valeur indicative (en secondes). Les pages du Desk pourront
              utiliser ce paramètre pour ajuster leur fréquence de refresh.
            </Helper>
          </div>

          <div>
            <Label>Thème de l’interface</Label>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="w-full rounded-lg bg-zinc-900 border border-zinc-700 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="dark">Dark (recommandé)</option>
              <option value="light">Light (prévu ultérieurement)</option>
            </select>
            <Helper>
              Le thème est mémorisé localement. Le support complet du thème
              light pourra être ajouté plus tard dans la V2.5.
            </Helper>
          </div>
        </div>
      </Section>

      {/* Trading mode */}
      <Section title="Mode de trading (indicatif)">
        <div className="space-y-4 text-sm text-zinc-200">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <Label>Mode actuel</Label>
              <div className="flex items-center gap-4 mt-1">
                <button
                  type="button"
                  onClick={() => setTradingMode("simulation")}
                  className={`px-3 py-2 rounded-lg text-sm border ${
                    tradingMode === "simulation"
                      ? "bg-emerald-500/20 border-emerald-500 text-emerald-100"
                      : "bg-zinc-900 border-zinc-700 text-zinc-300"
                  }`}
                >
                  Simulation
                </button>
                <button
                  type="button"
                  onClick={() => setTradingMode("real")}
                  className={`px-3 py-2 rounded-lg text-sm border ${
                    tradingMode === "real"
                      ? "bg-red-500/20 border-red-500 text-red-100"
                      : "bg-zinc-900 border-zinc-700 text-zinc-300"
                  }`}
                >
                  Réel (indicatif)
                </button>
              </div>
            </div>

            <div className="md:text-right text-xs text-zinc-500">
              Ce réglage n’active <span className="font-semibold">PAS</span>{" "}
              encore le trading réel. Il servira de base à une synchronisation
              future avec le backend (feature flags, mode préprod / prod).
            </div>
          </div>
        </div>
      </Section>

      {/* Debug & logs */}
      <Section title="Debug & logs">
        <div className="space-y-3 text-sm text-zinc-200">
          <div className="flex items-center gap-3">
            <input
              id="debug-toggle"
              type="checkbox"
              checked={showDebug}
              onChange={(e) => setShowDebug(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-600 bg-zinc-900 text-emerald-500 focus:ring-emerald-500"
            />
            <Label>
              <span>Afficher les informations de debug API dans l’interface</span>
            </Label>
          </div>
          <Helper>
            Quand cette option est activée, les pages pourront afficher des
            consoles de debug (URLs d’API, statuts HTTP, messages d’erreur
            détaillés). Utile en préproduction, à désactiver en usage normal.
          </Helper>
        </div>
      </Section>

      {/* Bouton d'enregistrement */}
      <div className="flex items-center justify-between">
        {savedMessage && (
          <span className="text-xs text-emerald-400">{savedMessage}</span>
        )}
        <button
          type="button"
          onClick={handleSave}
          className="ml-auto inline-flex items-center px-4 py-2 rounded-lg border border-emerald-500 bg-emerald-600/80 text-sm font-medium text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 focus:ring-offset-zinc-950"
        >
          Enregistrer les paramètres
        </button>
      </div>
    </div>
  );
}
