import React from "react";
import ThemeToggle from "./ThemeToggle";

export default function Header() {
  return (
    <header className="flex items-center justify-between mb-6">
      <div className="flex items-center gap-3">
        {/* Logo NSC (remplace le src si tu as un fichier local) */}
        <img
          src="/logo-nsc.svg"
          alt="NSC"
          className="h-7 w-auto"
          onError={(e)=>{ e.currentTarget.style.display="none"; }}
        />
        <h1 className="text-2xl font-semibold">Nova Star Capital — Préprod</h1>
      </div>
      <ThemeToggle />
    </header>
  );
}
