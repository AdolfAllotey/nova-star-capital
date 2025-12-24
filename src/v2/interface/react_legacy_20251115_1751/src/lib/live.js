// src/lib/live.js
// Stub simple pour le flux live des trades/signaux.
// Suffisant pour l'UI, on branchera le vrai WebSocket plus tard.

/**
 * connectLive(options)
 * options: { onMessage: (msg) => void }
 * Retourne un objet { close: () => void }
 */
export function connectLive(options = {}) {
  const { onMessage } = options;

  console.log("[live] connectLive() stub appelé");

  // Exemple : on injecte un faux message après 2s pour tester l’UI
  const timer = setTimeout(() => {
    if (typeof onMessage === "function") {
      onMessage({
        type: "heartbeat",
        timestamp: new Date().toISOString(),
        payload: {
          symbol: "BTCUSDT",
          price: 68000,
          side: "BUY",
        },
      });
    }
  }, 2000);

  return {
    close() {
      console.log("[live] fermeture du stub");
      clearTimeout(timer);
    },
  };
}
