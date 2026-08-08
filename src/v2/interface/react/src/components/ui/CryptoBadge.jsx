import React from "react";
import { formatCryptoDisplay, formatCryptoSymbol } from "../../utils/formatters";

function getBase(symbol) {
  const formatted = formatCryptoSymbol(symbol || "");
  return formatted.split("/")[0] || "";
}

function IconShell({ children, bg, ring }) {
  return (
    <span
      className={`inline-flex h-7 w-7 items-center justify-center rounded-full border ${bg} ${ring} shadow-sm`}
    >
      <svg viewBox="0 0 24 24" className="h-4.5 w-4.5" fill="none" xmlns="http://www.w3.org/2000/svg">
        {children}
      </svg>
    </span>
  );
}

function CryptoIcon({ symbol }) {
  const base = getBase(symbol);

  switch (base) {
    case "BTC":
      return (
        <IconShell bg="bg-amber-500/15" ring="border-amber-500/30">
          <circle cx="12" cy="12" r="10" fill="#F7931A" />
          <path d="M10 6.8v10.4M13.5 6.8v10.4" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M8.5 9.3h5.2a2 2 0 010 4H8.5h5.7a2 2 0 010 4H8.5" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </IconShell>
      );
    case "ETH":
      return (
        <IconShell bg="bg-slate-500/15" ring="border-slate-400/30">
          <path d="M12 2.5L6.8 12l5.2 3 5.2-3L12 2.5z" fill="#C9CDD4" />
          <path d="M12 15l-5.2-3 5.2 9.5 5.2-9.5-5.2 3z" fill="#8A92B2" />
        </IconShell>
      );
    case "SOL":
      return (
        <IconShell bg="bg-fuchsia-500/15" ring="border-fuchsia-500/30">
          <defs>
            <linearGradient id="solg" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#00FFA3" />
              <stop offset="100%" stopColor="#DC1FFF" />
            </linearGradient>
          </defs>
          <rect x="5" y="6" width="14" height="3" rx="1.5" fill="url(#solg)" transform="skewX(-18)" />
          <rect x="5" y="10.5" width="14" height="3" rx="1.5" fill="url(#solg)" transform="skewX(-18)" />
          <rect x="5" y="15" width="14" height="3" rx="1.5" fill="url(#solg)" transform="skewX(-18)" />
        </IconShell>
      );
    case "BNB":
      return (
        <IconShell bg="bg-yellow-500/15" ring="border-yellow-500/30">
          <path d="M12 4l2.2 2.2L12 8.4 9.8 6.2 12 4zM7.3 8.7L9.5 11 7.3 13.2 5 11l2.3-2.3zm9.4 0L19 11l-2.3 2.2-2.2-2.2 2.2-2.3zM12 13.6l2.2 2.2L12 18l-2.2-2.2 2.2-2.2z" fill="#F3BA2F" />
          <path d="M12 8.9l2.1 2.1-2.1 2.1-2.1-2.1L12 8.9z" fill="#F3BA2F" />
        </IconShell>
      );
    case "MATIC":
      return (
        <IconShell bg="bg-violet-500/15" ring="border-violet-500/30">
          <path d="M8.2 8.2l2.7-1.6c.7-.4 1.5-.4 2.2 0l2.7 1.6c.7.4 1.1 1.1 1.1 1.9v3.2c0 .8-.4 1.5-1.1 1.9l-2.7 1.6c-.7.4-1.5.4-2.2 0l-2.7-1.6c-.7-.4-1.1-1.1-1.1-1.9v-3.2c0-.8.4-1.5 1.1-1.9z" stroke="#8247E5" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M9.2 9.6l2.8 1.6 2.8-1.6M12 11.2v3.2" stroke="#8247E5" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </IconShell>
      );
    case "XRP":
      return (
        <IconShell bg="bg-zinc-500/15" ring="border-zinc-400/30">
          <path d="M6 7c1.1 0 1.7.4 2.4 1.2l1.2 1.3c.7.8 1.3 1.2 2.4 1.2s1.7-.4 2.4-1.2l1.2-1.3C16.3 7.4 16.9 7 18 7" stroke="#F5F5F5" strokeWidth="1.7" strokeLinecap="round" />
          <path d="M18 17c-1.1 0-1.7-.4-2.4-1.2l-1.2-1.3c-.7-.8-1.3-1.2-2.4-1.2s-1.7.4-2.4 1.2l-1.2 1.3C7.7 16.6 7.1 17 6 17" stroke="#F5F5F5" strokeWidth="1.7" strokeLinecap="round" />
        </IconShell>
      );
    case "AVAX":
      return (
        <IconShell bg="bg-red-500/15" ring="border-red-500/30">
          <circle cx="12" cy="12" r="10" fill="#E84142" />
          <path d="M12 6l3.9 6.8c.3.5-.1 1.2-.7 1.2H8.8c-.6 0-1-.7-.7-1.2L12 6z" fill="#fff" />
          <path d="M15.2 15.3l1.1 1.9c.3.5-.1 1.1-.7 1.1h-2.2c-.6 0-1-.6-.7-1.1l1.1-1.9c.3-.5 1-.5 1.4 0z" fill="#fff" />
        </IconShell>
      );
    case "ADA":
      return (
        <IconShell bg="bg-blue-500/15" ring="border-blue-500/30">
          <circle cx="12" cy="12" r="1.6" fill="#2A7DE1" />
          <circle cx="12" cy="6.2" r="1" fill="#2A7DE1" />
          <circle cx="12" cy="17.8" r="1" fill="#2A7DE1" />
          <circle cx="6.7" cy="9" r="1" fill="#2A7DE1" />
          <circle cx="17.3" cy="9" r="1" fill="#2A7DE1" />
          <circle cx="6.7" cy="15" r="1" fill="#2A7DE1" />
          <circle cx="17.3" cy="15" r="1" fill="#2A7DE1" />
          <circle cx="9" cy="6.8" r="0.9" fill="#2A7DE1" />
          <circle cx="15" cy="6.8" r="0.9" fill="#2A7DE1" />
          <circle cx="9" cy="17.2" r="0.9" fill="#2A7DE1" />
          <circle cx="15" cy="17.2" r="0.9" fill="#2A7DE1" />
        </IconShell>
      );
    default:
      return (
        <IconShell bg="bg-zinc-500/15" ring="border-zinc-400/30">
          <circle cx="12" cy="12" r="10" fill="#52525B" />
          <text x="12" y="15" textAnchor="middle" fontSize="9" fill="#fff" fontFamily="Arial, sans-serif">
            {base?.slice(0, 2) || "?"}
          </text>
        </IconShell>
      );
  }
}

export default function CryptoBadge({ symbol }) {
  return (
    <div className="inline-flex items-center gap-2">
      <CryptoIcon symbol={symbol} />
      <span>{formatCryptoDisplay(symbol)}</span>
    </div>
  );
}
