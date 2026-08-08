import React from "react";

export default function DecisionExplainability({ global, strategies = [] }) {
  const active = (Array.isArray(strategies) ? strategies : []).filter(
    (s) => (s?.status || "").toUpperCase() !== "DISABLED"
  );

  const blocked = active.filter(
    (s) =>
      String(s?.mode || "").toUpperCase().includes("OFF") ||
      String(s?.mode || "").toUpperCase().includes("SIMULATED")
  );

  const explainRows = [
    {
      label: "Market Reading",
      value: `${global?.regime || "UNKNOWN"} regime detected with governance mode ${global?.governanceMode || "UNKNOWN"}.`,
    },
    {
      label: "Execution Posture",
      value: blocked.length
        ? `${blocked.length} brick(s) are currently constrained or simulated.`
        : "No constrained brick detected.",
    },
    {
      label: "Capital Intent",
      value: "NSC allocates capital across active bricks while preserving a patrimonial long-term pocket funded by gains.",
    },
    {
      label: "Protection",
      value: `${global?.riskFlags || 0} global risk flag(s) observed. Monitoring remains active in PREPROD.`,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4">
      {explainRows.map((row, idx) => (
        <div
          key={idx}
          className="rounded-2xl border border-zinc-800/70 bg-zinc-950/30 px-4 py-4"
        >
          <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
            {row.label}
          </div>
          <div className="mt-2 text-sm leading-relaxed text-zinc-300">
            {row.value}
          </div>
        </div>
      ))}
    </div>
  );
}
