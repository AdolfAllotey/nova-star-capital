import { Outlet } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header"; // ⬅️ nouveau
import { useState } from "react";

export default function Layout() {
  const [open, setOpen] = useState(true);

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100">
      {/* Sidebar */}
      {open && (
        <div className="hidden md:flex">
          <Sidebar />
        </div>
      )}

      {/* Layout principal */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header onToggleSidebar={() => setOpen(!open)} />

        <main className="flex-1 overflow-y-auto bg-zinc-950">
          <div className="max-w-7xl mx-auto px-4 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
