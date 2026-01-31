// src/components/DataState.jsx
import React from "react";

export function ErrorBanner({ title = "Erreur", message, hint }) {
  return (
    <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
      <div className="font-semibold">{title}</div>
      {message && <div className="mt-1">{message}</div>}
      {hint && <div className="mt-2 text-xs text-amber-200/80">{hint}</div>}
    </div>
  );
}

export function LoadingState({ label = "Chargement…" }) {
  return (
    <div className="flex items-center justify-center py-14 text-zinc-400">
      {label}
    </div>
  );
}

export function EmptyState({ title = "Aucune donnée", subtitle }) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4 text-sm text-zinc-400">
      <div className="font-medium text-zinc-200">{title}</div>
      {subtitle && <div className="mt-1 text-zinc-500">{subtitle}</div>}
    </div>
  );
}
