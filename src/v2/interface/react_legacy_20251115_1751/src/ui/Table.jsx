import React from "react";

export function Table({ children }) {
  return <div className="overflow-x-auto rounded-2xl border border-zinc-800/60">{children}</div>;
}
export function THead({ children }) {
  return <thead className="bg-zinc-900/60 text-zinc-300 text-xs">{children}</thead>;
}
export function TBody({ children }) {
  return <tbody className="divide-y divide-zinc-800/60 bg-zinc-950/30">{children}</tbody>;
}
export function TR({ children }) {
  return <tr className="hover:bg-zinc-900/40">{children}</tr>;
}
export function TH({ children, className="" }) {
  return <th className={`px-3 py-2 font-medium text-left ${className}`}>{children}</th>;
}
export function TD({ children, className="" }) {
  return <td className={`px-3 py-2 text-sm text-zinc-200 ${className}`}>{children}</td>;
}

export function SkeletonRow({ cols = 5 }) {
  return (
    <TR>
      {Array.from({ length: cols }).map((_, i) => (
        <TD key={i}><div className="h-4 w-24 animate-pulse rounded bg-zinc-800/80" /></TD>
      ))}
    </TR>
  );
}
