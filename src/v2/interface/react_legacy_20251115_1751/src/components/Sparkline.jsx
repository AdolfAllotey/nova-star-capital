// src/components/Sparkline.jsx
// Mini graphique inline pour les courbes (ICO, PnL, etc.)

import React from "react";

export default function Sparkline({ points = [], width = 80, height = 24 }) {
  if (!points || points.length === 0) {
    return (
      <div className="text-xs text-zinc-500 italic">
        (pas de données)
      </div>
    );
  }

  const xs = points.map((_, i) => i);
  const ys = points;

  const minX = 0;
  const maxX = xs.length - 1 || 1;
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const scaleX = (x) =>
    ((x - minX) / (maxX - minX || 1)) * (width - 4) + 2;
  const scaleY = (y) =>
    height - (((y - minY) / (maxY - minY || 1)) * (height - 4) + 2);

  const d = xs
    .map((x, i) => {
      const px = scaleX(x);
      const py = scaleY(ys[i]);
      return `${i === 0 ? "M" : "L"} ${px} ${py}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} className="overflow-visible">
      <path
        d={d}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.3"
      />
    </svg>
  );
}
