// src/components/ui/ErrorBanner.jsx
import React from "react";

export default function ErrorBanner({ error }) {
  const msg = typeof error === "string" ? error : error?.message || "Erreur";
  const url = typeof error === "object" ? error?.url : null;
  const status = typeof error === "object" ? error?.status : null;

  return (
    <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
      <div className="font-medium">
        {msg}
        {status ? <span className="ml-2 text-amber-200/80">(HTTP {status})</span> : null}
      </div>

      {url ? (
        <div className="mt-2 text-xs text-amber-200/80">
          Source: <code>{url}</code>
        </div>
      ) : null}

      {error?.rawText ? (
        <details className="mt-3">
          <summary className="cursor-pointer text-xs text-amber-200/80">
            Détails (raw)
          </summary>
          <pre className="mt-2 max-h-56 overflow-auto rounded-lg border border-amber-500/20 bg-black/30 p-3 text-[11px] text-amber-100/80">
{String(error.rawText).slice(0, 3000)}
          </pre>
        </details>
      ) : null}
    </div>
  );
}
