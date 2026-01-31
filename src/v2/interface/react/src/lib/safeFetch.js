export async function safeFetch(path, opts = {}) {
  const base =
    (import.meta && import.meta.env && import.meta.env.VITE_API_BASE_URL) ||
    "https://api.preprod.novastarcapital.fr";
  const url = `${base}${path.startsWith("/") ? "" : "/"}${path}`;

  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} on ${path}${txt ? ` — ${txt.slice(0, 200)}` : ""}`);
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}
