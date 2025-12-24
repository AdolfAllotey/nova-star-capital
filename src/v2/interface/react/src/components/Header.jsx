// src/components/Header.jsx
// Header global minimal et élégant, cohérent avec TopMovers.jsx

import React from "react";

export default function Header() {
  return (
    <header className="w-full border-b border-zinc-800 bg-zinc-900/60 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-zinc-100 tracking-wide">
          Nova Star Capital — Dashboard
        </h1>

        <div className="text-xs text-zinc-400">
          Préproduction · v2.0
        </div>
      </div>
    </header>
  );
}
