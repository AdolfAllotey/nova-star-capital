import React from "react";

const Link = ({ href, children }) => (
  <a
    href={href}
    className="px-3 py-2 rounded-md text-sm font-medium hover:underline"
  >
    {children}
  </a>
);

export default function Nav() {
  return (
    <header className="sticky top-0 z-40 bg-white/80 dark:bg-neutral-950/80 backdrop-blur border-b border-neutral-200/50 dark:border-neutral-800">
      <div className="max-w-7xl mx-auto px-4 h-12 flex items-center gap-4">
        <a href="/" className="flex items-center gap-2 font-extrabold tracking-tight">
          <img src="/logo-nsc.svg" alt="NSC" className="h-6 w-6" />
          <span className="hidden sm:inline">NSC</span>
        </a>
        <nav className="flex items-center gap-1">
          <Link href="/">Dashboard</Link>
          <Link href="/trades">Trades</Link>
          <Link href="/positions">Positions</Link>
          <Link href="/whales">Whales</Link>
          <Link href="/reports">Reports</Link>
          <Link href="/status">Statut</Link>
        </nav>
      </div>
    </header>
  );
}
