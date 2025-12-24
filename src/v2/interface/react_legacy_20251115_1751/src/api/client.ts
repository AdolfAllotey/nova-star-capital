const BASE = import.meta.env.VITE_API_BASE || "/";

type FetchOpts = {
  method?: "GET"|"POST"|"PUT"|"PATCH"|"DELETE"|"HEAD"|"OPTIONS";
  headers?: Record<string,string>;
  body?: any;
  timeoutMs?: number;
};

async function withTimeout<T>(p: Promise<T>, ms = 8000): Promise<T> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort("timeout"), ms);
  try {
    // @ts-ignore
    const out = await p.then(r => r, (e:any) => { throw e; });
    return out as T;
  } finally {
    clearTimeout(t);
  }
}

async function request<T=unknown>(path: string, opts: FetchOpts = {}): Promise<T> {
  const url = path.startsWith("http") ? path : `${BASE}${path.replace(/^\/+/,"")}`;
  const timeoutMs = opts.timeoutMs ?? 8000;

  const res = await withTimeout(
    fetch(url, {
      method: opts.method || "GET",
      headers: {
        "Accept": "application/json",
        ...(opts.body ? {"Content-Type":"application/json"} : {}),
        ...(opts.headers || {})
      },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      signal: (new AbortController()).signal
    }),
    timeoutMs
  );

  if (!res.ok) {
    const text = await res.text().catch(()=>"");
    throw new Error(`HTTP ${res.status} ${res.statusText} – ${text?.slice(0,200)}`);
  }

  // Tenter JSON, sinon renvoyer texte
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  return (await res.text()) as T as T;
}

export const api = {
  // Public
  health: () => request("/api/public/health"),

  // Protégés (Caddy ajoute l’Authorization en amont)
  version: () => request("/api/secure/version"),
  regime:  () => request("/api/secure/regime"),
};
