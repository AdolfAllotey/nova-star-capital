// src/lib/apiBase.js
// Point central pour la base URL de l'API NSC côté frontend.

const API_BASE =
  (typeof window !== "undefined" && window.__NSC_API_BASE__) ||
  import.meta.env.VITE_API_BASE ||
  "https://api.preprod.novastarcapital.fr";

export { API_BASE };
