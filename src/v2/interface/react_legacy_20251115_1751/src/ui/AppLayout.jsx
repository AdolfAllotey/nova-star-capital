import React from "react";
import Sidebar from "./Sidebar.jsx";

export default function AppLayout({ children }) {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex">
      <Sidebar />

      <div className="flex-1 flex flex-col">
        <header className="h-12 border-b border-zinc-800 flex items-center px-4 text-sm">
          <span className="text-zinc-400">NSC Trading Desk</span>
        </header>

        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
