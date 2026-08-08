import StatusBadgeCore from "./ui/StatusBadge";
// src/components/UiKit.jsx
import React from "react";

function cls(...parts) {
  return parts.filter(Boolean).join(" ");
}

export function SectionCard({ title, right, children, className = "" }) {
  return (
    <section
      className={cls(
        "relative overflow-hidden rounded-[28px] border border-white/10 bg-zinc-950/55 backdrop-blur-md p-5 shadow-[0_0_0_1px_rgba(255,255,255,0.01)] transition-all duration-200",
        className
      )}
    >
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/[0.04] via-transparent to-transparent" />

      {(title || right) && (
        <div className="relative mb-5 flex items-start justify-between gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">
              Panel
            </div>
            <h2 className="mt-2 text-lg font-semibold tracking-tight text-zinc-100">
              {title}
            </h2>
          </div>

          {right ? (
            <div className="rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-xs text-zinc-400">
              {right}
            </div>
          ) : null}
        </div>
      )}

      <div className="relative">
        {children}
      </div>
    </section>
  );
}

export function StatusBadge({ status = "N/A" }) {
  return <StatusBadgeCore label={status} />;
}


export function BrickHeader({ title, subtitle, status = "COMING", right }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-semibold text-zinc-50">{title}</h1>
          <StatusBadge status={status} />
        </div>
        {subtitle && <p className="mt-1 text-sm text-zinc-400">{subtitle}</p>}
      </div>
      {right && <div className="text-xs text-zinc-500">{right}</div>}
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  status,
  right,
  className = "",
}) {
  return (
    <div className={cls("relative rounded-2xl border border-zinc-800 bg-gradient-to-br from-zinc-950 via-zinc-950 to-zinc-900/80 p-5 overflow-hidden", className)}>
  <div className="absolute inset-0 opacity-[0.05] bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.4),transparent_60%)]" />
      <div className="flex items-start justify-between gap-4">
        <div>
          {eyebrow && (
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-zinc-500">
              {eyebrow}
            </div>
          )}
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-50">{title}</h1>
            {status ? <StatusBadge status={status} /> : null}
          </div>
          {subtitle && <p className="mt-2 max-w-3xl text-sm text-zinc-400">{subtitle}</p>}
        </div>
        {right ? <div className="text-xs text-zinc-500">{right}</div> : null}
      </div>
    </div>
  );
}

export function KpiCard({
  label,
  value,
  subvalue,
  tone = "default",
  className = "",
}) {
  const toneMap = {
    default: "text-zinc-50",
    positive: "text-emerald-400",
    negative: "text-red-400",
    caution: "text-amber-300",
    accent: "text-sky-300",
  };

  return (
    <div className={cls("rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4", className)}>
      <div className="text-xs uppercase tracking-wide text-zinc-500">{label}</div>
      <div className={cls("mt-2 text-2xl font-semibold", toneMap[tone] || toneMap.default)}>
        {value}
      </div>
      {subvalue ? <div className="mt-1 text-xs text-zinc-500">{subvalue}</div> : null}
    </div>
  );
}

export function ExplainPanel({
  title = "Explainability",
  items = [],
  className = "",
}) {
  return (
    <div className={cls("rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4", className)}>
      <div className="mb-3 text-sm font-semibold text-zinc-100">{title}</div>
      <div className="space-y-3">
        {items.map((item, idx) => (
          <div key={`${item.label}-${idx}`} className="grid grid-cols-1 gap-1 md:grid-cols-[160px,1fr]">
            <div className="text-xs uppercase tracking-wide text-zinc-500">{item.label}</div>
            <div className="text-sm text-zinc-300">{item.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
