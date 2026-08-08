const CRYPTO_NAMES = {
  BTC: "Bitcoin",
  ETH: "Ethereum",
  SOL: "Solana",
  BNB: "BNB",
  MATIC: "Polygon",
  XRP: "XRP",
  AVAX: "Avalanche",
  ADA: "Cardano"
};

export function formatCryptoSymbol(symbol) {
  if (!symbol) return "";

  const s = String(symbol).toUpperCase();
  const pairs = ["USDT", "USDC", "BTC", "ETH", "EUR"];

  for (const p of pairs) {
    if (s.endsWith(p) && s.length > p.length) {
      const base = s.slice(0, -p.length);
      return `${base}/${p}`;
    }
  }

  return s;
}

export function formatCryptoDisplay(symbol) {
  if (!symbol) return "";

  const formatted = formatCryptoSymbol(symbol);
  const base = formatted.split("/")[0];

  const name = CRYPTO_NAMES[base];

  if (!name) return formatted;

  return `${name} (${formatted})`;
}

export function formatEur(value) {
  const n = Number(value || 0);
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0
  }).format(n);
}

export function formatPct(value, digits = 1) {
  const n = Number(value || 0) * 100;
  return `${n.toFixed(digits)}%`;
}
