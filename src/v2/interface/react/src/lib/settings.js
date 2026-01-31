// src/lib/settings.js
const KEY = "nsc_ui_settings_v1";

const DEFAULTS = {
  apiBase: "http://127.0.0.1:8000",
  refreshMs: 30000,
  theme: "dark",
};

export function getSettings() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULTS };
    const parsed = JSON.parse(raw);
    return { ...DEFAULTS, ...parsed };
  } catch {
    return { ...DEFAULTS };
  }
}

export function setSettings(next) {
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch { /* noop */ }
}

export function resetSettings() {
  try {
    localStorage.removeItem(KEY);
  } catch { /* noop */ }
}

export function getApiBase() {
  return getSettings().apiBase;
}

export function getRefreshMs() {
  return getSettings().refreshMs;
}
