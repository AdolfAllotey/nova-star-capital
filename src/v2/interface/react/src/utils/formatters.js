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

export function formatEur(value, options = {}) {
  if (value === null || value === undefined || value === "") return "N/A";

  const n = Number(value);
  if (!Number.isFinite(n)) return "N/A";

  const { signed = false, maximumFractionDigits = 0 } = options || {};

  const formatted = new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits
  }).format(n);

  return signed && n > 0 ? `+${formatted}` : formatted;
}

export function formatPct(value, options = {}) {
  if (value === null || value === undefined || value === "") return "N/A";

  const n = Number(value);
  if (!Number.isFinite(n)) return "N/A";

  const normalized =
    typeof options === "number"
      ? { digits: options }
      : (options || {});

  const { digits = 1, signed = false } = normalized;
  const pct = n * 100;
  const formatted = `${pct.toFixed(digits)}%`;

  return signed && pct > 0 ? `+${formatted}` : formatted;
}
