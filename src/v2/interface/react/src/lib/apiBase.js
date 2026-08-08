// Canonical NSC frontend API configuration.
//
// Resolution order:
// 1. Runtime injection from window.__NSC_API_BASE__
// 2. Standard VITE_API_BASE
// 3. Legacy variables retained temporarily for compatibility
// 4. Same-origin fallback, compatible with the production reverse proxy

function normalizeApiBase(value) {
  const raw = String(value || "").trim();

  if (!raw || raw === "/") {
    return "";
  }

  return raw.replace(/\/+$/, "");
}

const runtimeBase =
  typeof window !== "undefined"
    ? window.__NSC_API_BASE__
    : undefined;

const API_BASE = normalizeApiBase(
  runtimeBase ||
    import.meta.env.VITE_API_BASE ||
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL ||
    ""
);

function buildApiUrl(path = "") {
  const rawPath = String(path || "");

  if (
    rawPath.startsWith("http://") ||
    rawPath.startsWith("https://")
  ) {
    return rawPath;
  }

  const normalizedPath = rawPath.startsWith("/")
    ? rawPath
    : `/${rawPath}`;

  return `${API_BASE}${normalizedPath}`;
}

export {
  API_BASE,
  buildApiUrl,
  buildApiUrl as apiUrl,
};
