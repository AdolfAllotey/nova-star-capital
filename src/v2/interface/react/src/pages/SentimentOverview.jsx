/* eslint-disable no-unused-vars */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "../components/ui/card";
import { ScrollArea } from "../components/ui/scroll-area";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "../components/ui/table";
import { Loader2 } from "lucide-react";

function safeNumber(v, fallback = null) {
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  return fallback;
}

function formatPct(v) {
  if (typeof v !== "number" || Number.isNaN(v)) return "-";
  return `${v.toFixed(1)} %`;
}

function formatScore(v) {
  if (typeof v !== "number" || Number.isNaN(v)) return "-";
  return v.toFixed(2);
}

function safeItems(json) {
  if (!json) return [];
  if (Array.isArray(json)) return json;
  if (Array.isArray(json.items)) return json.items;
  if (Array.isArray(json.top_tokens)) return json.top_tokens;
  return [];
}

export default function SentimentOverview() {
  const [loading, setLoading] = useState(true);
  const [global, setGlobal] = useState(null);
  const [tokens, setTokens] = useState([]);
  const [sources, setSources] = useState([]);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(buildUrl("/sentiment"));
        const json = await res.json().catch(() => ({}));

        // On reste ultra tolérant sur la structure
        const g =
          json.global ||
          json.overview ||
          {
            score: safeNumber(json.score, 0.0),
            bullish_pct: safeNumber(json.bullish_pct, null),
            bearish_pct: safeNumber(json.bearish_pct, null),
            neutral_pct: safeNumber(json.neutral_pct, null),
            updated_at: json.updated_at || json.server_ts || null,
          };

        setGlobal(g);

        setTokens(
          safeItems(json.tokens || json.top_tokens || json.token_sentiment)
        );
        setSources(safeItems(json.sources || json.channels || json.streams));
      } catch (err) {
        console.error("Error loading /sentiment", err);
        setGlobal(null);
        setTokens([]);
        setSources([]);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  const globalScore = safeNumber(global?.score, null);
  const bullish = safeNumber(global?.bullish_pct, null);
  const bearish = safeNumber(global?.bearish_pct, null);
  const neutral = safeNumber(global?.neutral_pct, null);
  const updatedAt = global?.updated_at || global?.server_ts || null;

  let regimeLabel = "Neutre";
  let regimeVariant = "outline";

  if (globalScore !== null) {
    if (globalScore >= 0.6) {
      regimeLabel = "Bullish";
      regimeVariant = "default";
    } else if (globalScore <= 0.4) {
      regimeLabel = "Bearish";
      regimeVariant = "destructive";
    }
  }

  return (
    <div className="space-y-6 p-4">
      {/* HEADER */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Sentiment Marché (Social & News)
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/dashboard">Dashboard</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/intelligence/sentiment">Signaux</Link>
          </Button>
        </div>
      </div>

      {/* GLOBAL SENTIMENT */}
      <Card>
        <CardHeader className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle className="text-base font-semibold">
              Vue globale du sentiment
            </CardTitle>
            <CardDescription>
              Synthèse des signaux Telegram, X (Twitter), Reddit et news crypto
              agrégés par le bot NSC.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {globalScore !== null && (
              <Badge variant={regimeVariant}>
                Score Global : {formatScore(globalScore)}
              </Badge>
            )}
            {updatedAt && (
              <span className="text-xs text-muted-foreground">
                Maj&nbsp;: {updatedAt}
              </span>
            )}
          </div>
        </CardHeader>

        <CardContent>
          {loading && (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              <span>Calcul du sentiment global…</span>
            </div>
          )}

          {!loading && !global && (
            <div className="rounded-md border border-dashed border-muted-foreground/30 p-6 text-sm text-muted-foreground">
              <p className="font-medium mb-1">Aucune donnée de sentiment.</p>
              <p>
                Les scrapers (Telegram/Twitter/Reddit) ou l'analyse du
                sentiment ne semblent pas encore avoir tourné. Une fois la
                préproduction en place, le score global apparaîtra ici.
              </p>
            </div>
          )}

          {!loading && global && (
            <div className="grid gap-4 md:grid-cols-3">
              <Card className="border border-border/60">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">
                    Bullish
                  </CardTitle>
                  <CardDescription>
                    Part des messages à tonalité positive
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-semibold">
                    {bullish !== null ? formatPct(bullish) : "-"}
                  </p>
                </CardContent>
              </Card>

              <Card className="border border-border/60">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">
                    Neutre
                  </CardTitle>
                  <CardDescription>
                    Messages équilibrés ou indécis
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-semibold">
                    {neutral !== null ? formatPct(neutral) : "-"}
                  </p>
                </CardContent>
              </Card>

              <Card className="border border-border/60">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">
                    Bearish
                  </CardTitle>
                  <CardDescription>
                    Part des messages à tonalité négative
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-semibold">
                    {bearish !== null ? formatPct(bearish) : "-"}
                  </p>
                </CardContent>
              </Card>
            </div>
          )}
        </CardContent>
      </Card>

      {/* TOKEN SENTIMENT TABLE */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Sentiment par token
          </CardTitle>
          <CardDescription>
            Classement des tokens les plus discutés, ordonnés par score de
            sentiment et intensité de volume social.
          </CardDescription>
        </CardHeader>

        <CardContent>
          {!loading && tokens.length === 0 && (
            <div className="rounded-md border border-dashed border-muted-foreground/30 p-6 text-sm text-muted-foreground">
              <p className="font-medium mb-1">
                Aucun token avec sentiment exploitable.
              </p>
              <p>
                Dès que les scrapers auront collecté suffisamment de messages,
                les tokens les plus “hype” apparaîtront ici avec leur score
                NSC.
              </p>
            </div>
          )}

          {!loading && tokens.length > 0 && (
            <ScrollArea className="w-full max-h-[420px]">
              <Table className="min-w-[780px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Token</TableHead>
                    <TableHead>Source dominante</TableHead>
                    <TableHead className="text-right">
                      Score Sentiment
                    </TableHead>
                    <TableHead className="text-right">
                      Volume social
                    </TableHead>
                    <TableHead className="text-right">
                      Bullish (%)
                    </TableHead>
                    <TableHead className="text-right">
                      Bearish (%)
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tokens.map((t, idx) => {
                    const symbol = t.symbol || t.token || t.id || "-";
                    const src =
                      t.main_source ||
                      t.dominant_source ||
                      t.top_channel ||
                      "Mix";
                    const score = safeNumber(t.score ?? t.sentiment_score, null);
                    const vol =
                      t.message_count ??
                      t.volume ??
                      t.social_volume ??
                      null;
                    const bull = safeNumber(t.bullish_pct, null);
                    const bear = safeNumber(t.bearish_pct, null);

                    return (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">
                          <Badge variant="outline">{symbol}</Badge>
                        </TableCell>
                        <TableCell>{src}</TableCell>
                        <TableCell className="text-right">
                          {score !== null ? formatScore(score) : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          {vol !== null
                            ? vol.toLocaleString("fr-FR")
                            : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          {bull !== null ? formatPct(bull) : "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          {bear !== null ? formatPct(bear) : "-"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </ScrollArea>
          )}

          {loading && (
            <div className="mt-4 text-xs text-muted-foreground">
              Chargement du détail par token…
            </div>
          )}
        </CardContent>
      </Card>

      {/* SOURCES / CANAUX */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">
            Canaux analysés
          </CardTitle>
          <CardDescription>
            Vue synthétique des sources analysées (groupes Telegram, comptes X,
            subreddits…).
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!loading && sources.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Les scrapers n&apos;ont pas encore persisté de détail
              canal-par-canal. Cette section sera remplie automatiquement en
              préproduction.
            </p>
          )}

          {!loading && sources.length > 0 && (
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {sources.map((s, idx) => {
                const label = s.name || s.channel || s.id || `Canal #${idx + 1}`;
                const platform =
                  s.platform ||
                  s.type ||
                  (label.toLowerCase().includes("tg") ? "Telegram" : "Social");
                const msgCount = s.message_count ?? s.count ?? null;
                return (
                  <Card
                    key={idx}
                    className="border border-border/60 bg-muted/40"
                  >
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">
                        {label}
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Plateforme&nbsp;: {platform}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-1 text-xs text-muted-foreground">
                      {msgCount !== null ? (
                        <p>{msgCount.toLocaleString("fr-FR")} messages analysés</p>
                      ) : (
                        <p>Volume non disponible en préprod.</p>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

          {loading && (
            <p className="text-xs text-muted-foreground">
              Chargement des canaux analysés…
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
