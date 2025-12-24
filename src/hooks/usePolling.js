import { useEffect, useRef, useState } from "react";

// Hook de polling générique
export function usePolling(fn, { interval = 10000, immediate = true } = {}) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(!!immediate);
  const timer = useRef(null);

  async function tick() {
    try {
      const res = await fn();
      setData(res);
      setErr(null);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (immediate) tick();
    timer.current = setInterval(tick, interval);
    return () => clearInterval(timer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interval]);

  return { data, err, loading, refresh: tick };
}
