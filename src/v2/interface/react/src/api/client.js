const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export async function apiGet(path) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const res = await fetch(url, { headers: { "Content-Type": "application/json" } });
  if (!res.ok) {
    // renvoie {} plutôt qu’une exception pour que l’UI dégrade en douceur
    try {
      const err = await res.json();
      return err;
    } catch {
      return {};
    }
  }
  return res.json();
}
