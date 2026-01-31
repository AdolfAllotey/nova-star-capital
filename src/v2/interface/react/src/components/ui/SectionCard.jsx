// src/components/ui/SectionCard.jsx
import React from "react";

export default function SectionCard({
  title,
  description,
  right,
  children,
  className = "",
}) {
  return (
    <section className={`space-y-3 ${className}`}>
      {(title || right) && (
        <div className="flex items-end justify-between gap-4">
          <div>
            {title && (
              <h2 className="text-lg font-semibold text-zinc-100">{title}</h2>
            )}
            {description && (
              <p className="mt-1 text-sm text-zinc-400">{description}</p>
            )}
          </div>
          {right ? <div className="shrink-0">{right}</div> : null}
        </div>
      )}

      <div className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4">
        {children}
      </div>
    </section>
  );
}
