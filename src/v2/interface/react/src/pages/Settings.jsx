import React, { useEffect, useMemo, useState } from "react";
import SectionCard from "../components/ui/SectionCard";
import StatusBadge from "../components/ui/StatusBadge";
import { API_BASE } from "../lib/apiBase";

const LS_KEY = "nsc_settings_v2";

function loadSettingsFromStorage() {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (e) {
    console.warn("[Settings] Unable to read localStorage", e);
    return null;
  }
}

function saveSettingsToStorage(settings) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LS_KEY, JSON.stringify(settings));
  } catch (e) {
    console.warn("[Settings] Unable to write localStorage", e);
  }
}

function PageHeader({ title, subtitle, badges = [] }) {
  return (
    <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
      <div>
        <h1 className="text-[30px] font-semibold tracking-tight text-white">{title}</h1>
        <p className="mt-1 text-sm text-zinc-400">{subtitle}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {badges.map((badge, idx) => (
          <StatusBadge
            key={`${badge.label || badge.status || "badge"}-${idx}`}
            status={badge.status}
            label={badge.label}
          />
        ))}
      </div>
    </div>
  );
}

function MicroCard({ label, value, subvalue }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
      {subvalue ? <div className="mt-1 text-sm text-zinc-400">{subvalue}</div> : null}
    </div>
  );
}

function FieldLabel({ children }) {
  return <label className="block text-sm font-medium text-zinc-200 mb-2">{children}</label>;
}

function Helper({ children }) {
  return <p className="text-xs text-zinc-500 mt-2">{children}</p>;
}

export default function Settings() {
  const [refreshSeconds, setRefreshSeconds] = useState(60);
  const [tradingMode, setTradingMode] = useState("simulation");
  const [showDebug, setShowDebug] = useState(false);
  const [theme, setTheme] = useState("dark");
  const [savedMessage, setSavedMessage] = useState("");

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
    setSavedMessage("Settings saved locally.");
    setTimeout(() => setSavedMessage(""), 2500);
  };

  const narrative = useMemo(() => {
    return [
      `Interface refresh interval is currently set to ${refreshSeconds} second(s).`,
      `Trading mode indicator currently reads ${tradingMode}.`,
      `Debug display is currently ${showDebug ? "enabled" : "disabled"}.`,
      `Active interface theme currently reads ${theme}.`,
      `All settings are currently stored locally in the browser only.`,
    ];
  }, [refreshSeconds, tradingMode, showDebug, theme]);

  return (
    <div className="p-5 space-y-6">
      <PageHeader
        title="Settings"
        subtitle="Local interface preferences for refresh cadence, visual theme, debug visibility, and indicative trading mode."
        badges={[
          { label: "PREPROD" },
          { label: tradingMode === "real" ? "REAL_INDICATIVE" : "SIMULATION" },
          { label: showDebug ? "DEBUG_ON" : "DEBUG_OFF" },
          { label: theme.toUpperCase() },
        ]}
      />

      <SectionCard title="Settings Narrative" subtitle="How the current interface configuration should be read">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
          {narrative.map((line, idx) => (
            <div
              key={idx}
              className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 px-4 py-3 text-sm text-cyan-100"
            >
              {line}
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MicroCard
          label="Refresh Interval"
          value={`${refreshSeconds}s`}
          subvalue="Local UI preference"
        />
        <MicroCard
          label="Trading Mode"
          value={tradingMode}
          subvalue="Indicative only"
        />
        <MicroCard
          label="Debug"
          value={showDebug ? "ON" : "OFF"}
          subvalue="Interface-level visibility"
        />
        <MicroCard
          label="Theme"
          value={theme}
          subvalue="Stored in localStorage"
        />
      </div>

      <SectionCard title="Environment & API" subtitle="Current detected backend base and environment posture">
        <div className="space-y-4 text-sm text-zinc-300">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-zinc-500">Detected API Base</div>
            <div className="mt-2 font-mono text-xs break-all rounded-xl border border-white/10 bg-black/20 px-3 py-3 text-zinc-200">
              {API_BASE}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <StatusBadge label="PREPROD" />
            <StatusBadge label="LOCAL_SETTINGS_ONLY" />
          </div>

          <div className="text-zinc-400">
            Trading mode selection below is currently informational for the UI and does not directly switch backend execution behavior.
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Refresh & Interface" subtitle="Local refresh cadence and theme preferences">
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <FieldLabel>Data Refresh Interval (seconds)</FieldLabel>
            <input
              type="number"
              min={10}
              max={3600}
              value={refreshSeconds}
              onChange={(e) => setRefreshSeconds(Number(e.target.value) || 60)}
              className="w-full rounded-xl bg-zinc-900 border border-zinc-700 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            />
            <Helper>
              This local value can later be reused by dashboard pages to tune automatic refresh frequency.
            </Helper>
          </div>

          <div>
            <FieldLabel>Interface Theme</FieldLabel>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="w-full rounded-xl bg-zinc-900 border border-zinc-700 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
            </select>
            <Helper>
              Theme preference is stored locally. Full light-theme support can be expanded later.
            </Helper>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Trading Mode" subtitle="Indicative mode selector for future backend synchronization">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <FieldLabel>Current Mode</FieldLabel>
            <div className="flex items-center gap-4 mt-1">
              <button
                type="button"
                onClick={() => setTradingMode("simulation")}
                className={`px-3 py-2 rounded-xl text-sm border ${
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
                className={`px-3 py-2 rounded-xl text-sm border ${
                  tradingMode === "real"
                    ? "bg-red-500/20 border-red-500 text-red-100"
                    : "bg-zinc-900 border-zinc-700 text-zinc-300"
                }`}
              >
                Real (Indicative)
              </button>
            </div>
          </div>

          <div className="md:text-right text-xs text-zinc-500 max-w-md">
            This setting does not activate live trading yet. It is intended as a future interface hook for backend feature flags and governance mode synchronization.
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Debug & Logs" subtitle="Interface-level debug visibility controls">
        <div className="space-y-3 text-sm text-zinc-200">
          <div className="flex items-center gap-3">
            <input
              id="debug-toggle"
              type="checkbox"
              checked={showDebug}
              onChange={(e) => setShowDebug(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-600 bg-zinc-900 text-emerald-500 focus:ring-emerald-500"
            />
            <FieldLabel>
              <span>Show API debug information inside the interface</span>
            </FieldLabel>
          </div>
          <Helper>
            When enabled, pages may expose more detailed API or diagnostic information. Useful in preproduction and testing, not recommended for normal monitoring use.
          </Helper>
        </div>
      </SectionCard>

      <div className="flex items-center justify-between">
        {savedMessage && (
          <span className="text-xs text-emerald-400">{savedMessage}</span>
        )}
        <button
          type="button"
          onClick={handleSave}
          className="ml-auto inline-flex items-center px-4 py-2 rounded-xl border border-emerald-500 bg-emerald-600/80 text-sm font-medium text-white hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 focus:ring-offset-zinc-950"
        >
          Save Settings
        </button>
      </div>
    </div>
  );
}
