// src/v2/interface/react/pages/About.jsx
import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";
import { Input } from "../components/ui/input";

export default function About() {
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setErr("");
      try {
        // Fichier optionnel: public/data/meta.json
        // Exemple de contenu:
        // { "appName":"Nova Star Capital", "version":"0.9.0",
        //   "author":"Adolf Allotey", "lastSync":"2025-08-09T05:40:48Z" }
        const res = await fetch("/data/meta.json", { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const j = await res.json();
        if (mounted) setMeta(j);
      } catch (e) {
        // Silencieux: la page fonctionne même sans meta.json
        if (mounted) setMeta(null);
        console.warn("About: meta.json manquant (ok):", e.message);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  const appName = meta?.appName || "Nova Star Capital – Trading Suite";
  const version = meta?.version || "dev";
  const author = meta?.author || "—";
  const lastSync = meta?.lastSync
    ? new Date(meta.lastSync).toLocaleString()
    : "—";

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">À propos</h1>
        <div className="text-xs text-muted-foreground">
          {loading ? "Chargement des infos…" : `Version ${version}`}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{appName}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>
            Suite interne pour le suivi des signaux, la génération de rapports quotidiens,
            l’analyse des pires trades par LLM et le suivi de la rentabilité. Interface
            React (Vite) + pipeline Python (v2).
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border p-3">
              <div className="text-xs text-muted-foreground">Auteur</div>
              <div className="font-medium">{author}</div>
            </div>
            <div className="rounded-lg border p-3">
              <div className="text-xs text-muted-foreground">Dernière synchro</div>
              <div className="font-medium">{lastSync}</div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 pt-2">
            <Button asChild variant="secondary">
              <a href="/" rel="noreferrer">Accueil</a>
            </Button>
            <Button asChild>
              <a href="/dashboard" rel="noreferrer">Ouvrir le Dashboard</a>
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Emplacements des données</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <ScrollArea className="max-h-[40vh] rounded-md border">
            <div className="p-4 space-y-3">
              <PathRow label="Données publiques (servies par Vite)" path="/public/data" />
              <PathRow label="Rapport quotidien (JSON)" path="/public/data/reports/daily_report_YYYY-MM-DD.json" />
              <PathRow label="PNL mensuel" path="/public/data/reports/monthly_pnl.json" />
              <PathRow label="Trades simulés" path="/public/data/simulation/trade_simulation.json" />
              <PathRow label="Pires trades" path="/public/data/risk/worst_trades.json" />
              <PathRow label="Résumé LLM" path="/public/data/risk/worst_trades_summary.json" />
              <PathRow label="Airdrops" path="/public/data/airdrops.json" />
              <PathRow label="Meta (optionnel)" path="/public/data/meta.json" />
            </div>
          </ScrollArea>
          <div className="pt-3">
            <Button
              onClick={async () => {
                // simple ping de reload; le vrai sync se fait via scripts/sync_data.sh côté repo
                try {
                  // Force un refetch global en rechargant la page
                  window.location.reload();
                } catch (e) {
                  console.error(e);
                }
              }}
              variant="outline"
            >
              Recharger les données
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Dépannage rapide</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
          <Tip
            title="Overlay d’erreur Vite"
            content="Si l’overlay bloque l’écran, corrige l’import puis rafraîchis. Tu peux le désactiver via server.hmr.overlay=false dans vite.config.js."
          />
          <Tip
            title="Chemins des imports UI"
            content='Utilise des imports relatifs: ../components/ui/*. Ex: { Card } depuis "../components/ui/card".'
          />
          <Tip
            title="Données non trouvées"
            content="Vérifie que scripts/sync_data.sh a bien copié src/v2/data → public/data. Relance le script, puis refresh."
          />
          <Tip
            title="Cache navigateur"
            content="Les JSON sont servis sans cache ici, mais un hard-refresh (⌘⇧R) peut aider si le contenu ne change pas."
          />
        </CardContent>
      </Card>
    </div>
  );
}

function PathRow({ label, path }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border p-3">
      <div>
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="font-mono text-xs">{path}</div>
      </div>
      <div className="w-48">
        <Input
          readOnly
          value={path}
          onFocus={(e) => e.target.select()}
          className="font-mono text-xs"
        />
      </div>
    </div>
  );
}

function Tip({ title, content }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="font-medium">{title}</div>
      <div className="text-muted-foreground">{content}</div>
    </div>
  );
}