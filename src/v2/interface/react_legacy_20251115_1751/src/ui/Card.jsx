import React from "react";

export function Card({ title, right, children }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-zinc-900/50 p-4">
      {(title || right) && (
        <div className="mb-3 flex items-center justify-between">
          {title && <h3 className="font-medium text-zinc-100">{title}</h3>}
          {right}
        </div>
      )}
      {children}
    </div>
  );
}

export function Table({ columns = [], rows = [] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-zinc-300">
            {columns.map((c) => (
              <th key={c.key} className="px-3 py-2 text-left font-medium">{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-white/5 hover:bg-white/5">
              {columns.map((c) => (
                <td key={c.key} className="px-3 py-2">
                  {c.render ? c.render(r[c.key], r) : r[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
