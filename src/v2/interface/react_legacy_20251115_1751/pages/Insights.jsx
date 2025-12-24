import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { ScrollArea } from "../components/ui/scroll-area";
import {
  ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend,
  PieChart, Pie, Cell,
  LineChart, Line,
} from "recharts";

const TG_URL = "/data/social/telegram_data.json";
const TW_URL = "/data/social/twitter_data.json";
const RD_URL = "/data/social/reddit_data.json";
const AVG_SENT_URL = "/data/sentiment/average_sentiment.json";

const safeFetchJSON = async (url) => {
  try {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const txt = await r.text();
    if (!txt?.trim()) return null;
    // Si le serveur renvoie accidentellement du HTML
    if (txt.trim().startsWith("<!DOCTYPE")) throw new Error("HTML reçu au lieu de JSON");
    return JSON.parse(txt);
  } catch (e) {
    console.warn(`⚠️ Impossible de charger ${url}:`, e?.message || e);
    return null;
  }
};

export default function Insights() {
  const [telegram, setTelegram] = useState(null);
  const [twitter, setTwitter] = useState(null);
  const [reddit, setReddit] = useState(null);
  const [avgSent, setAvgSent] = useState(null);
  const [loading, setLoading] = useState(true);

  // Rafraîchissement manuel (si tu veux l’ajouter plus tard)
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      const [tg, tw, rd, av] = await Promise.all([
        safeFetchJSON(TG_URL),
        safeFetchJSON(TW_URL),
        safeFetchJSON(RD_URL),
        safeFetchJSON(AVG_SENT_URL),
      ]);
      if (!mounted) return;
      setTelegram(Array.isArray(tg) ? tg : []);
      setTwitter(Array.isArray(tw) ? tw : []);
      setReddit(Array.isArray(rd) ? rd : []);
      setAvgSent(av && typeof av === "object" ? av : null);
      setLoading(false);
    })();
    return () => { mounted = false; };
  }, [tick]);

  // Comptages simples
  const counts = useMemo(() => {
    return {
      telegram: telegram?.length || 0,
      twitter: twitter?.length || 0,
      reddit: reddit?.length || 0,
    };
  }, [telegram, twitter, reddit]);

  // Données activité pour BarChart
  const activityData = useMemo(() => {
    return [
      { source: "Telegram", value: counts.telegram },
      { source: "Twitter", value: counts.twitter },
      { source: "Reddit",  value: counts.reddit  },
    ];
  }, [counts]);

  // Sentiment donut (si fichier dispo). On supporte deux formats:
  //  - { average_sentiment: 0.42 }
  //  - { positive: 12, neutral: 5, negative: 3 }
  const sentimentPie = useMemo(() => {
    if (!avgSent) return null;

    if (typeof avgSent.average_sentiment === "number") {
      // Map un score [-1..1] vers {positive/neutral/negative}
      const s = avgSent.average_sentiment;
      const pos = s > 0.15 ? 1 : 0;
      const neg = s < -0.15 ? 1 : 0;
      const neu = pos === 0 && neg === 0 ? 1 : 0;
      return [
        { name: "Positif", value: pos },
        { name: "Neutre", value: neu },
        { name: "Négatif", value: neg },
      ];
    }

    const p = Math.max(0, avgSent.positive ?? 0);
    const n = Math.max(0, avgSent.neutral ?? 0);
    const g = Math.max(0, avgSent.negative ?? 0);
    if (p + n + g === 0) return null;
    return [
      { name: "Positif", value: p },
      { name: "Neutre", value: n },
      { name: "Négatif", value: g },
    ];
  }, [avgSent]);

  // Timeline simple (ex: nombre de messages par "jour" si timestamp présent)
  const timelineData = useMemo(() => {
    // utilitaire pour grouper par jour (YYYY-MM-DD)
    const byDay = {};
    const add = (arr, key) => {
      (arr || []).forEach((m) => {
        const d = m.date || m.timestamp || m.time;
        if (!d) return;
        let day;
        try {
          day = new Date(d).toISOString().slice(0, 10);
        } catch {
          return;
        }
        byDay[day] = byDay[day] || { day, telegram: 0, twitter: 0, reddit: 0 };
        byDay[day][key] += 1;
      });
    };
    add(telegram, "telegram");
    add(twitter, "twitter");
    add(reddit, "reddit");
    return Object.values(byDay).sort((a, b) => (a.day < b.day ? -1 : 1));
  }, [telegram, twitter, reddit]);

  const COLORS = ["#22c55e", "#eab308", "#ef4444"]; // Positif / Neutre / Négatif

  return (
    <ScrollArea className="h-[calc(100vh-80px)]">
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Insights</h1>
          <button
            onClick={() => setTick((t) => t + 1)}
            className="px-3 py-1.5 text-sm rounded-md bg-gray-900 text-white hover:bg-gray-800"
          >
            Rafraîchir
          </button>
        </div>

        {/* Cartes de métriques */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardHeader><CardTitle>Telegram</CardTitle></CardHeader>
            <CardContent className="text-3xl font-bold">{counts.telegram}</CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Twitter</CardTitle></CardHeader>
            <CardContent className="text-3xl font-bold">{counts.twitter}</CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Reddit</CardTitle></CardHeader>
            <CardContent className="text-3xl font-bold">{counts.reddit}</CardContent>
          </Card>
        </div>

        {/* Graphiques */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle>Activité (messages par source)</CardTitle></CardHeader>
            <CardContent className="h-72">
              {loading ? (
                <div className="text-sm text-muted-foreground">Chargement…</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={activityData}>
                    <XAxis dataKey="source" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="value" name="Messages" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Sentiment (répartition)</CardTitle></CardHeader>
            <CardContent className="h-72">
              {!sentimentPie ? (
                <div className="text-sm text-muted-foreground">
                  Aucune donnée de sentiment.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={sentimentPie}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      label
                    >
                      {sentimentPie.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader><CardTitle>Tendance d’activité (par jour)</CardTitle></CardHeader>
          <CardContent className="h-80">
            {timelineData?.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={timelineData}>
                  <XAxis dataKey="day" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="telegram" name="Telegram" />
                  <Line type="monotone" dataKey="twitter" name="Twitter" />
                  <Line type="monotone" dataKey="reddit" name="Reddit" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-sm text-muted-foreground">
                Pas assez de données temporelles pour tracer la tendance.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Debug minimal */}
        <Card>
          <CardHeader><CardTitle>Debug</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div>Telegram: {telegram ? telegram.length : "—"}</div>
            <div>Twitter: {twitter ? twitter.length : "—"}</div>
            <div>Reddit: {reddit ? reddit.length : "—"}</div>
            <div>Sentiment: {avgSent ? JSON.stringify(avgSent) : "—"}</div>
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  );
}