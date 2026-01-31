// src/components/ui/DataState.jsx
import React from "react";

export default function DataState({
  loading = false,
  error = null,
  empty = false,
  emptyText = "No data",
  children = null,
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-10 text-zinc-400">
        Chargement…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
        {typeof error === "string" ? error : "Erreur lors du chargement."}
      </div>
    );
  }

  if (empty) {
    return (
      <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 px-4 py-6 text-sm text-zinc-400">
        {emptyText}
      </div>
    );
  }

  // État OK : si children existe on le rend, sinon on ne rend rien.
  return children ? <>{children}</> : null;
}
