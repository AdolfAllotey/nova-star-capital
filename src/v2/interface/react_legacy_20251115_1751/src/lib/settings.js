// src/lib/settings.js
// Petit gestionnaire de settings côté navigateur (localStorage).

const STORAGE_KEY = "nsc_ui_settings_v1";

const DEFAULT_SETTINGS = {
  theme: "dark",
  autoRefresh: true,
  refreshIntervalSec: 15,
};

function loadSettings() {
  if (typeof window === "undefined") return { ...DEFAULT_SETTINGS };
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    const parsed = JSON.parse(raw);
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch (e) {
    console.warn("[settings] erreur de parse:", e);
    return { ...DEFAULT_SETTINGS };
  }
}

function saveSettings(settings) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch (e) {
    console.warn("[settings] erreur de sauvegarde:", e);
  }
}

export function getSettings() {
  return loadSettings();
}

export function setSettings(partial) {
  const current = loadSettings();
  const next = { ...current, ...partial };
  saveSettings(next);
  return next;
}

export function resetSettings() {
  saveSettings(DEFAULT_SETTINGS);
  return { ...DEFAULT_SETTINGS };
}
