// src/lib/live.js
/**
 * Client WebSocket minimaliste avec auto-reconnect exponentiel.
 * Format attendu: messages JSON (une ligne = un objet).
 *
 * Exemple côté API (Option B déjà employée) :
 *   ws://localhost:8000/ws/live
 *   -> envoie des objets { type: "...", payload: {...}, t: "...iso..." }
 */
export function connectLive({
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
  maxBackoffMs = 15000,
}) {
  let ws = null;
  let backoff = 500;
  let closedManually = false;

  const open = () => {
    ws = new WebSocket(url);

    ws.addEventListener("open", (ev) => {
      backoff = 500;
      onOpen && onOpen(ev);
    });

    ws.addEventListener("message", (ev) => {
      try {
        // on accepte JSON pur ou JSONL
        const lines = String(ev.data).split("\n").filter(Boolean);
        for (const line of lines) {
          const msg = JSON.parse(line);
          onMessage && onMessage(msg);
        }
      } catch (err) {
        onError && onError(err);
      }
    });

    ws.addEventListener("close", (ev) => {
      onClose && onClose(ev);
      if (!closedManually) {
        setTimeout(() => {
          const delay = Math.min(backoff, maxBackoffMs);
          backoff = Math.min(backoff * 2, maxBackoffMs);
          open();
        }, Math.floor(Math.random() * 250) + backoff);
      }
    });

    ws.addEventListener("error", (err) => {
      onError && onError(err);
      try { ws.close(); } catch {}
    });
  };

  open();

  return {
    send: (obj) => {
      try {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(obj));
        }
      } catch {}
    },
    close: () => {
      closedManually = true;
      try { ws && ws.close(); } catch {}
    },
  };
}
