// src/v2/interface/react/pages/KOLs.jsx
import React, { useEffect, useMemo, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { ScrollArea } from "../components/ui/scroll-area";
import {
  ResponsiveContainer,
  LineChart, Line, Tooltip, XAxis, YAxis,
} from "recharts";

const PATHS = {
  kols: "/data/kol/kols.json",
  posts: "/data/kol/posts.json",
  sentiment: "/data/analytics/sentiment_results.json",
};

async function fetchJSON(url, fallback = null) {
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return fallback;
    return await res.json();
  } catch {
    return fallback;
  }
}

const platformColor = (p) => {
  const key = String(p || "").toLowerCase();
  if (key.includes("twitter") || key.includes("x")) return "bg-sky-600";
  if (key.includes("telegram")) return "bg-teal-600";
  if (key.includes("reddit")) return "bg-orange-600";
  if (key.includes("youtube")) return "bg-red-600";
  return "bg-gray-600";
};

const fmtInt = (n) => (Number.isFinite(n) ? n.toLocaleString() : "—");
const clamp = (n, a, b) => Math.max(a, Math.min(b, n));

export default function KOLs() {
  const [loading, setLoading] = useState(false);
  const [kols, setKols] = useState([]);
  const [posts, setPosts] = useState([]);
  const [sentiment, setSentiment] = useState([]);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("followers_desc"); // followers_desc | score_desc | posts_desc

  const load = useCallback(async () => {
    setLoading(true);
    const [ks, ps, ss] = await Promise.all([
      fetchJSON(PATHS.kols, []),
      fetchJSON(PATHS.posts, []),
      fetchJSON(PATHS.sentiment, []),
    ]);
    setKols(Array.isArray(ks) ? ks : []);
    setPosts(Array.isArray(ps) ? ps : []);
    setSentiment(Array.isArray(ss) ? ss : []);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Index posts par handle + timeline simple (counts par jour)
  const byHandle = useMemo(() => {
    const map = new Map();
    for (const p of posts) {
      const handle = p.handle || p.user || p.channel || p.username;
      if (!handle) continue;
      const dateStr = p.date || p.timestamp || p.time;
      const day = dateStr ? new Date(dateStr) : null;
      const keyDay = day && !isNaN(day.getTime()) ? day.toISOString().slice(0, 10) : null;

      if (!map.has(handle)) {
        map.set(handle, { total: 0, byDay: new Map(), samples: [] });
      }
      const entry = map.get(handle);
      entry.total += 1;
      if (keyDay) {
        entry.byDay.set(keyDay, (entry.byDay.get(keyDay) || 0) + 1);
      }
      // garde quelques extraits récents
      if (entry.samples.length < 5) {
        entry.samples.push({
          text: p.text || p.message || p.title || "",
          when: dateStr || "",
        });
      }
    }
    // convert timelines en tableaux triés
    for (const [, v] of map) {
      const timeline = Array.from(v.byDay.entries())
        .map(([day, total]) => ({ day, total }))
        .sort((a, b) => (a.day < b.day ? -1 : 1));
      v.timeline = timeline;
    }
    return map;
  }, [posts]);

  // Score sentiment moyen par handle (si possible)
  const sentimentByHandle = useMemo(() => {
    const m = new Map();
    for (const s of sentiment) {
      const text = s.text || "";
      const score = Number(s.score);
      if (!Number.isFinite(score)) continue;
      // heuristique: si s.user existe ou s.source_user …
      const h =
        s.user || s.source_user || s.handle || ""; // sinon on n’associe pas
      if (!h) continue;
      const prev = m.get(h) || { sum: 0, n: 0 };
      prev.sum += score;
      prev.n += 1;
      m.set(h, prev);
    }
    // moyenne clampée [-1,1]
    const out = new Map();
    for (const [h, v] of m) {
      out.set(h, clamp(v.sum / v.n, -1, 1));
    }
    return out;
  }, [sentiment]);

  // Fusionne KOLs + posts + sentiment
  const rows = useMemo(() => {
    const base = (Array.isArray(kols) ? kols : []).map((k) => {
      const handle =
        k.handle || k.username || k.name || k.channel || k.user || "";
      const plat = k.platform || k.source || "";
      const followers = Number(k.followers ?? k.subscribers ?? k.members ?? 0);
      const kolScore = Number(k.score ?? k.kol_score ?? k.influence ?? 0);

      const postPack = byHandle.get(handle) || { total: 0, timeline: [], samples: [] };
      const senti = sentimentByHandle.get(handle);
      const sentScore = Number.isFinite(senti) ? senti : null;

      return {
        handle,
        name: k.name || handle || "—",
        platform: plat,
        followers,
        kolScore,
        posts: postPack.total,
        timeline: postPack.timeline,
        samples: postPack.samples,
        sentiment: sentScore,
      };
    });

    // Si aucun kols.json, on peut dériver depuis posts (handles uniques)
    if (!base.length && byHandle.size) {
      for (const [handle, v] of byHandle) {
        base.push({
          handle,
          name: handle,
          platform: "unknown",
          followers: 0,
          kolScore: 0,
          posts: v.total,
          timeline: v.timeline,
          samples: v.samples,
          sentiment: sentimentByHandle.get(handle) ?? null,
        });
      }
    }

    // filtre recherche
    const q = query.trim().toLowerCase();
    const filtered = q
      ? base.filter(
          (r) =>
            r.handle.toLowerCase().includes(q) ||
            String(r.name).toLowerCase().includes(q) ||
            String(r.platform).toLowerCase().includes(q)
        )
      : base;

    // tri
    const sorted = [...filtered].sort((a, b) => {
      if (sort === "followers_desc") return (b.followers || 0) - (a.followers || 0);
      if (sort === "score_desc") return (b.kolScore || 0) - (a.kolScore || 0);
      if (sort === "posts_desc") return (b.posts || 0) - (a.posts || 0);
      return 0;
    });

    return sorted;
  }, [kols, byHandle, sentimentByHandle, query, sort]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">KOLs & Influence</h1>
          <p className="text-sm text-muted-foreground">
            Vue consolidée des leaders d’opinion (activité, audience, sentiment).
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={load} disabled={loading}>
            {loading ? "Rafraîchissement…" : "Rafraîchir"}
          </Button>
          <Link to="/dashboard"><Button>Dashboard</Button></Link>
        </div>
      </div>

      {/* Outils */}
      <div className="flex flex-col sm:flex-row gap-3">
        <Input
          placeholder="Rechercher par nom, handle ou plateforme…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="sm:max-w-sm"
        />
        <div className="flex gap-2">
          <Button
            variant={sort === "followers_desc" ? "default" : "outline"}
            onClick={() => setSort("followers_desc")}
          >
            Trier: Followers
          </Button>
          <Button
            variant={sort === "score_desc" ? "default" : "outline"}
            onClick={() => setSort("score_desc")}
          >
            Trier: Score
          </Button>
          <Button
            variant={sort === "posts_desc" ? "default" : "outline"}
            onClick={() => setSort("posts_desc")}
          >
            Trier: Posts
          </Button>
        </div>
      </div>

      {/* Table / cartes */}
      <Card>
        <CardHeader>
          <CardTitle>Top KOLs</CardTitle>
        </CardHeader>
        <CardContent>
          {!rows.length ? (
            <p className="text-sm text-muted-foreground">
              Aucune donnée trouvée. Vérifie <code>{PATHS.kols}</code> ou <code>{PATHS.posts}</code>.
            </p>
          ) : (
            <ScrollArea className="max-h-[70vh]">
              <div className="min-w-[900px]">
                <div className="grid grid-cols-12 px-3 py-2 text-xs text-muted-foreground">
                  <div className="col-span-3">KOL</div>
                  <div className="col-span-2">Plateforme</div>
                  <div className="col-span-2">Followers</div>
                  <div className="col-span-1">Score</div>
                  <div className="col-span-1">Posts</div>
                  <div className="col-span-3">Activité (sparkline)</div>
                </div>
                <div className="divide-y">
                  {rows.map((r, idx) => (
                    <div key={r.handle + idx} className="grid grid-cols-12 items-center px-3 py-3">
                      <div className="col-span-3">
                        <div className="font-medium">{r.name || r.handle}</div>
                        <div className="text-xs text-muted-foreground">@{r.handle}</div>
                        {typeof r.sentiment === "number" && (
                          <div className="mt-1 text-xs">
                            Sentiment:{" "}
                            <span
                              className={
                                "font-semibold " +
                                (r.sentiment > 0.1
                                  ? "text-emerald-600"
                                  : r.sentiment < -0.1
                                  ? "text-rose-600"
                                  : "text-amber-600")
                              }
                            >
                              {r.sentiment.toFixed(2)}
                            </span>
                          </div>
                        )}
                        {r.samples?.length ? (
                          <div className="mt-2 text-xs text-muted-foreground line-clamp-2">
                            “{r.samples[0].text?.slice(0, 140) || ""}”
                          </div>
                        ) : null}
                      </div>

                      <div className="col-span-2">
                        <span className={`text-white text-xs px-2 py-1 rounded ${platformColor(r.platform)}`}>
                          {r.platform || "—"}
                        </span>
                      </div>

                      <div className="col-span-2">{fmtInt(r.followers)}</div>
                      <div className="col-span-1">{Number.isFinite(r.kolScore) ? r.kolScore.toFixed(2) : "—"}</div>
                      <div className="col-span-1">{fmtInt(r.posts)}</div>

                      <div className="col-span-3 h-14">
                        {r.timeline?.length ? (
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={r.timeline}>
                              <XAxis dataKey="day" hide />
                              <YAxis hide domain={["dataMin", "dataMax"]} />
                              <Tooltip />
                              <Line type="monotone" dataKey="total" strokeWidth={2} dot={false} />
                            </LineChart>
                          </ResponsiveContainer>
                        ) : (
                          <Badge variant="outline">N/A</Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}