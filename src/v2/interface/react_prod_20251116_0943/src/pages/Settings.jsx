// src/pages/Settings.jsx
import React, { useEffect, useState } from "react";
import { getSettings, setSettings, resetSettings } from "../lib/settings";

function Row({ label, children }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="text-sm text-zinc-300">{label}</div>
      {children}
    </div>
  );
}

export default function Settings() {
  const [s, setS] = useState(getSettings());
  const [saved, setSaved] = useState(false);

  const onSave = () => {
    setSettings(s);
    setSaved(true);
    setTimeout(() => setSaved(false), 1200);
  };

  const onReset = () => {
    resetSettings();
    setS(getSettings());
  };

  useEffect(() => {
    // applique immédiatement en mémoire
    setSettings(s);
  }, [s]);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Settings</h1>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="rounded-2xl bg-zinc-900/60 ring-1 ring-white/10 p-4 space-y-4">
          <Row label="API Base URL">
            <input
              className="bg-zinc-950 border border-white/10 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 ring-white/20"
              value={s.apiBase}
              onChange={(e) => setS({ ...s, apiBase: e.target.value })}
              placeholder="http://127.0.0.1:8000"
            />
          </Row>
          <Row label="Auto-refresh (ms)">
            <input
              type="number"
              min={0}
              className="bg-zinc-950 border border-white/10 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 ring-white/20"
              value={s.refreshMs}
              onChange={(e) => setS({ ...s, refreshMs: Number(e.target.value || 0) })}
              placeholder="30000"
            />
          </Row>
          <Row label="Thème">
            <select
              className="bg-zinc-950 border border-white/10 rounded-xl px-3 py-2 text-sm"
              value={s.theme}
              onChange={(e) => setS({ ...s, theme: e.target.value })}
            >
              <option value="dark">Dark</option>
              <option value="auto">Auto</option>
            </select>
          </Row>

          <div className="flex gap-3">
            <button
              onClick={onSave}
              className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/15 border border-white/10 text-sm"
            >
              Sauvegarder
            </button>
            <button
              onClick={onReset}
              className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 border border-white/10 text-sm"
            >
              Réinitialiser
            </button>
            {saved && <div className="text-emerald-400 text-sm self-center">OK</div>}
          </div>
        </div>

        <div className="rounded-2xl bg-zinc-900/60 ring-1 ring-white/10 p-4">
          <div className="text-sm text-zinc-400">
            Ces paramètres sont stockés dans <span className="text-zinc-200">localStorage</span> côté navigateur
            et n’impactent pas le backend. Idéal pour basculer entre un **API base URL** local/remote
            ou ajuster la fréquence d’auto-rafraîchissement.
          </div>
        </div>
      </div>
    </div>
  );
}
