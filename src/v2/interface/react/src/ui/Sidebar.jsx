// TEST BRUTAL : Sidebar DEBUG
// Si cette sidebar s'affiche, ce fichier est bien utilisé par l'application

import React from "react";

export default function Sidebar() {
  return (
    <aside className="flex h-full flex-col bg-black text-red-500 border-r-4 border-red-600 p-4">
      <div className="text-xl font-bold uppercase tracking-widest mb-6">
        🚨 DEBUG SIDEBAR UI 🚨
      </div>

      <p className="text-red-400">
        Si tu vois CETTE sidebar rouge fluo dans l’interface,
        alors <strong>src/ui/Sidebar.jsx</strong> est bien utilisé.
      </p>

      <p className="mt-4 text-red-300">
        Sinon, c’est que l’application utilise un autre fichier Sidebar,
        et on passera à l’étape suivante pour l’identifier.
      </p>
    </aside>
  );
}
