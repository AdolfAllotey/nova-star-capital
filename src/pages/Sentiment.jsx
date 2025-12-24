// src/pages/Sentiment.jsx
import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card";
import { ScrollArea } from "../../components/ui/scroll-area";

export default function Sentiment() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  async function loadData() {
    try {
      const res = await fetch("https://api.preprod.novastarcapital.fr/sentiment/overview");
      const json = await res.json();
      setData(json || {});
    } catch (err) {
      console.error("Sentiment API error:", err);
      setData({});
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const sentiment = data?.sentiment ?? "N/A";
  const score = data?.score ?? 0;
  const sources = data?.sources ?? [];

  return (
    <div className="flex flex-col gap-6 w-full p-4 md:p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Sentiment du marché</h1>

      <Card className="w-full">
        <CardHeader>
          <CardTitle>Résumé global</CardTitle>
        </CardHeader>
        <CardContent>

          {loading && (
            <div className="text-muted-foreground text-sm">Chargement…</div>
          )}

          {!loading && (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Sentiment :</span>
                <span className="font-bold">
                  {sentiment === "N/A" ? "Indisponible" : sentiment}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="font-medium">Score :</span>
                <span className="font-bold">{score}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="w-full">
        <CardHeader>
          <CardTitle>Détails par source</CardTitle>
        </CardHeader>
        <CardContent>
          {loading && (
            <div className="text-muted-foreground text-sm">Chargement…</div>
          )}

          {!loading && sources.length === 0 && (
            <div className="text-muted-foreground text-sm">
              Aucune donnée disponible pour le moment.
            </div>
          )}

          {!loading && sources.length > 0 && (
            <ScrollArea className="max-h-[400px] rounded-md border p-2">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left">
                    <th className="py-2 px-2">Source</th>
                    <th className="py-2 px-2 text-right">Score</th>
                    <th className="py-2 px-2">Tendance</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((s, i) => (
                    <tr key={i} className="border-t">
                      <td className="py-2 px-2">{s.name}</td>
                      <td className="py-2 px-2 text-right">{s.score}</td>
                      <td className="py-2 px-2">{s.trend ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
