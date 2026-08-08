export const toneClasses = {
  emerald: {
    text: "text-emerald-400",
    border: "border-emerald-500/30",
    bg: "bg-emerald-500/10",
  },
  cyan: {
    text: "text-cyan-400",
    border: "border-cyan-500/30",
    bg: "bg-cyan-500/10",
  },
  amber: {
    text: "text-amber-300",
    border: "border-amber-500/30",
    bg: "bg-amber-500/10",
  },
  orange: {
    text: "text-orange-400",
    border: "border-orange-500/30",
    bg: "bg-orange-500/10",
  },
  red: {
    text: "text-red-400",
    border: "border-red-500/30",
    bg: "bg-red-500/10",
  },
  purple: {
    text: "text-purple-400",
    border: "border-purple-500/30",
    bg: "bg-purple-500/10",
  },
  slate: {
    text: "text-slate-400",
    border: "border-slate-500/30",
    bg: "bg-slate-500/10",
  },
}

export function getToneClasses(tone = "slate") {
  return toneClasses[tone] || toneClasses.slate
}
