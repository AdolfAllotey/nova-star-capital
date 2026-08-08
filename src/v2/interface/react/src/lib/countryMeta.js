import geoMap from "../data/geoMap.json";

export const COUNTRY_FLAGS = {
  US: "🇺🇸",
  FR: "🇫🇷",
  DE: "🇩🇪",
  NL: "🇳🇱",
  UK: "🇬🇧",
  GB: "🇬🇧",
  CN: "🇨🇳",
  IN: "🇮🇳",
  BR: "🇧🇷",
  ZA: "🇿🇦",
  MX: "🇲🇽",
  JP: "🇯🇵",
  AU: "🇦🇺",
  EM: "🌍",
  GLOBAL: "🌐",
  OTHER: "🌍"
};

export const COUNTRY_LABELS = {
  US: "United States",
  FR: "France",
  DE: "Germany",
  NL: "Netherlands",
  UK: "United Kingdom",
  GB: "United Kingdom",
  CN: "China",
  IN: "India",
  BR: "Brazil",
  ZA: "South Africa",
  MX: "Mexico",
  JP: "Japan",
  AU: "Australia",
  EM: "Emerging Markets",
  GLOBAL: "Global",
  OTHER: "Other"
};

export function getCountryCode(symbolOrCode) {
  if (!symbolOrCode) return "OTHER";

  const raw = String(symbolOrCode).toUpperCase();

  if (COUNTRY_FLAGS[raw]) return raw;
  return geoMap[raw] || "OTHER";
}

export function getCountryFlag(symbolOrCode) {
  const code = getCountryCode(symbolOrCode);
  return COUNTRY_FLAGS[code] || "🌍";
}

export function getCountryLabel(symbolOrCode) {
  const code = getCountryCode(symbolOrCode);
  return COUNTRY_LABELS[code] || code || "Other";
}

export function withFlag(symbolOrCode, label = null) {
  const code = getCountryCode(symbolOrCode);
  const flag = COUNTRY_FLAGS[code] || "🌍";
  const text = label || COUNTRY_LABELS[code] || code || "Other";
  return `${flag} ${text}`;
}
