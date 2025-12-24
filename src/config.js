// Détecte l'API selon l'hôte courant (local dev vs préprod)
const host = window.location.hostname;

export const API_BASE =
  host.endsWith("preprod.novastarcapital.fr")
    ? "https://api.preprod.novastarcapital.fr"
    : (import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000");
