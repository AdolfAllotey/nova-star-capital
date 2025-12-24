import { useEffect, useRef, useState } from "react";

/**
 * Hook de polling générique.
 * - Appelle `url` toutes les `interval` ms (15s par défaut)
 * - Gère l’AbortController, erreurs, et cleanup propre
 */
export default function usePolling(url, interval = 15000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    let mounted = true;

    const fetchOnce = async () => {
      if (!url) return;
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch(url, { signal: controller.signal, credentials: "include" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (mounted) {
          setData(json);
          setError(null);
        }
      } catch (err) {
        if (mounted && err.name !== "AbortError") setError(err);
      }
    };

    // premier fetch immédiat
    fetchOnce();

    // intervalle
    timerRef.current = setInterval(fetchOnce, interval);

    return () => {
      mounted = false;
      clearInterval(timerRef.current);
      abortRef.current?.abort();
    };
  }, [url, interval]);

  return { data, error };
}
