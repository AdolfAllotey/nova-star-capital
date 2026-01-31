// src/components/ui/BrickHeader.jsx
import React from "react";
import StatusBadge from "./StatusBadge";

export default function BrickHeader({
  title,
  subtitle,
  status,
  right,
  lastUpdate,
  env = "PREPROD",
}) {
  return (
    <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold text-zinc-50">{title}</h1>
          {status ? <StatusBadge status={status} /> : null}
        </div>
        {subtitle ? <p className="mt-1 text-sm text-zinc-400">{subtitle}</p> : null}
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
          <span className="rounded-full border border-zinc-800 bg-zinc-950/40 px-2 py-0.5">
            {env}
          </span>
          {lastUpdate ? (
            <span>
              Last update:{" "}
              {new Date(lastUpdate).toLocaleString("fr-FR")}
            </span>
          ) : null}
        </div>
      </div>
      {right ? <div className="shrink-0">{right}</div> : null}
    </header>
  );
}
