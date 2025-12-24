import { useEffect, useState } from "react";
import { api } from "../api/client";

type Health = {
  status: string;
  version: string;
  env: string;
  host: string;
  python: string;
  uptime_s: number;
};

type Version = { version: string };

type Regime = {
  date: string;
  regime: "bull"|"bear"|"range";
  score: number;
  factors?: any;
};

export default function PreprodStatus() {
  const [health, setHealth]   = useState<Health|null>(null);
  const [version, setVersion] = useState<Version|null>(null);
  const [regime, setRegime]   = useState<Regime|null>(null);

  const [errHealth, setErrHealth]   = useState<string|null>(null);
  const [errVersion, setErrVersion] = useState<string|null>(null);
  const [errRegime, setErrRegime]   = useState<string|null>(null);

  useEffect(() => {
    api.health()
      .then(setHealth)
      .catch((e) => setErrHealth(String(e)));

    api.version()
      .then(setVersion)
      .catch((e) => setErrVersion(String(e)));

    api.regime()
      .then(setRegime)
      .catch((e) => setErrRegime(String(e)));
  }, []);

  return (
    <div className="p-6 grid gap-4 md:grid-cols-3">
      {/* Santé API */}
      <div className="rounded-2xl shadow p-4 border">
        <h2 className="text-lg font-semibold mb-2">Santé API</h2>
        {errHealth && <p className="text-red-600 text-sm">Erreur: {errHealth}</p>}
        {!errHealth && !health && <p>Chargement…</p>}
        {health && (
          <ul className="text-sm space-y-1">
            <li><strong>status:</strong> {health.status}</li>
            <li><strong>version:</strong> {health.version}</li>
            <li><strong>env:</strong> {health.env}</li>
            <li><strong>host:</strong> {health.host}</li>
            <li><strong>python:</strong> {health.python}</li>
            <li><strong>uptime:</strong> {Math.round(health.uptime_s)}s</li>
          </ul>
        )}
      </div>

      {/* Version déployée */}
      <div className="rounded-2xl shadow p-4 border">
        <h2 className="text-lg font-semibold mb-2">Version déployée</h2>
        {errVersion && <p className="text-red-600 text-sm">Erreur: {errVersion}</p>}
        {!errVersion && !version && <p>Chargement…</p>}
        {version && (
          <p className="text-sm">
            <strong>version:</strong> {version.version}
          </p>
        )}
      </div>

      {/* Régime */}
      <div className="rounded-2xl shadow p-4 border">
        <h2 className="text-lg font-semibold mb-2">Régime de marché</h2>
        {errRegime && <p className="text-red-600 text-sm">Erreur: {errRegime}</p>}
        {!errRegime && !regime && <p>Chargement…</p>}
        {regime && (
          <ul className="text-sm space-y-1">
            <li><strong>date:</strong> {regime.date}</li>
            <li><strong>regime:</strong> {regime.regime}</li>
            <li><strong>score:</strong> {regime.score}</li>
          </ul>
        )}
      </div>
    </div>
  );
}
