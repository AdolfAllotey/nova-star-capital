// src/pages/ComingSoon.jsx
import React from "react";
import SectionCard from "../components/ui/SectionCard";

export default function ComingSoon({ title = "Coming soon" }) {
  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">{title}</h1>
          <p className="text-sm text-zinc-400">
            Cette brique est prévue mais pas encore déployée sur cette env.
          </p>
        </div>
        <div className="text-xs text-zinc-500">PREPROD</div>
      </header>

      <SectionCard title="En cours de déploiement">
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4 text-sm text-zinc-300">
          <div className="font-semibold text-zinc-100">Statut</div>
          <div className="mt-1 text-zinc-400">
            Placeholder actif pour éviter les fetch vers des endpoints non prêts.
          </div>

          <div className="mt-4 text-xs text-zinc-500">
            (Ce comportement est piloté par <code>src/config/features.js</code>)
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
