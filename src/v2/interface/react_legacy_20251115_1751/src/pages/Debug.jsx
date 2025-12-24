// src/pages/Debug.jsx
// Page de debug simple : vérifie que React + API fonctionnent

import React, { useEffect, useState } from "react";

export default function Debug() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:8000";

  useEffect(() => {
    const url = `${apiBase}/`;
    fetch(url)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((data) => setStatus(data))
      .catch((err) => setError(err.message || String(err)));
  }, [apiBase]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6">
      <h1 className="text-2xl font-bold mb-4">
        Nova Star Capital — Debug UI
      </h1>

      <div className="mb-4 text-sm text-zinc-300">
        <p>
          <strong>API base :</strong> {apiBase}
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded bg-red-900/50 text-red-200 text-sm">
          <strong>Erreur :</strong> {error}
        </div>
      )}

      {status && (
        <div className="mt-4">
          <h2 className="font-semibold mb-2 text-lg">Réponse API / :</h2>
          <pre className="bg-zinc-900 rounded p-3 text-xs overflow-x-auto">
            {JSON.stringify(status, null, 2)}
          </pre>
        </div>
      )}

      {!error && !status && (
        <p className="mt-4 text-sm text-zinc-400">Chargement…</p>
      )}
    </div>
  );
}
