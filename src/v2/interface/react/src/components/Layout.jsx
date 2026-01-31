// src/components/Layout.jsx

import React from "react";
import { Outlet as _Outlet } from "react-router-dom";

import _Sidebar from "./Sidebar";
import _Header from "./Header";

export default function Layout() {
  return (
    <div className="flex h-screen w-full bg-zinc-950 text-zinc-100">
      {/* _Sidebar */}
      <_Sidebar />

      {/* Main content */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <_Header />

        {/* IMPORTANT : _Outlet permet d'afficher les pages ! */}
        <main className="flex-1 overflow-y-auto p-6">
          <_Outlet />
        </main>
      </div>
    </div>
  );
}
