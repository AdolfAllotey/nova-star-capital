// src/pages/Whales.jsx
import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card";
import { ScrollArea } from "../../components/ui/scroll-area";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "../../components/ui/table";
import { Loader2 } from "lucide-react";

export default function Whales() {
  const [whales, setWhales] = useState([]);
  const [loading, setLoading] = useState(true);

  async function fetchWhales() {
    try {
      const resp = await fetch("/whales/leaderboard");
      const json = await resp.json();
      // On reste tolérant : certains backends renvoient { items: [...] }
      const items = Array.isArray(json)
        ? json
        : Array.isArray(json.items)
        ? json.items
        : [];
      setWhales(items);
    } catch (e) {
      console.error("Error fetching whales leaderboard:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchWhales();
  }, []);

  if (loading) {
    return (
      <div className="w-full flex justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
      </div>
    );
  }

  if (!whales || whales.length === 0) {
    return (
      <div className="max-w-6xl mx-auto">
        <Card className="border border-white/10 bg-black/20">
          <CardHeader>
            <CardTitle>Whales &amp; Smart Money</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-400">
              Aucun wallet &quot;whale&quot; détecté pour l’instant.
              Dès que le bot aura suffisamment de données on-chain, le tableau
              des whales actives apparaîtra ici.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const scoreColor = (val) => {
    const v = typeof val === "number" ? val : 0;
    if (v >= 0.7) return "text-green-400";
    if (v >= 0.5) return "text-yellow-400";
    return "text-red-400";
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Résumé rapide */}
      <Card className="border border-white/10 bg-black/20">
        <CardHeader>
          <CardTitle className="text-xl">
            Whales &amp; Smart Money – Leaderboard
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-400 text-sm">
            Vue consolidée des principaux wallets suivis par Nova Star Capital.
            Les scores et indicateurs sont calculés à partir de leur historique
            de performance et de leur activité récente.
          </p>
        </CardContent>
      </Card>

      {/* Tableau détaillé */}
      <Card className="border border-white/10 bg-black/20">
        <CardHeader>
          <CardTitle>Top wallets suivis</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="w-full">
            <Table className="min-w-[900px]">
              <TableHeader>
                <TableRow>
                  <TableHead>Wallet</TableHead>
                  <TableHead>Label</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead className="text-right">PNL total (€)</TableHead>
                  <TableHead className="text-right">Win rate</TableHead>
                  <TableHead className="text-right">Volume (€)</TableHead>
                  <TableHead className="text-right">Dernière activité</TableHead>
                  <TableHead>Tags</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {whales.map((w, idx) => {
                  const addr =
                    w.address || w.wallet || w.id || "N/A";
                  const label = w.label || w.alias || "—";
                  const score = typeof w.score === "number" ? w.score : w.whale_score || 0;
                  const pnl = w.total_pnl_eur ?? w.realized_pnl_eur ?? 0;
                  const winRate = w.win_rate ?? w.winrate ?? null;
                  const volume = w.total_volume_eur ?? w.volume_eur ?? null;
                  const last = w.last_activity || w.last_seen || "—";
                  const tags = Array.isArray(w.tags) ? w.tags : [];

                  return (
                    <TableRow key={idx}>
                      <TableCell className="font-mono text-xs">
                        {addr.length > 16
                          ? `${addr.slice(0, 6)}...${addr.slice(-4)}`
                          : addr}
                      </TableCell>
                      <TableCell className="text-sm">{label}</TableCell>
                      <TableCell
                        className={`text-right font-semibold ${scoreColor(
                          score
                        )}`}
                      >
                        {(score * 100).toFixed(0)}%
                      </TableCell>
                      <TableCell className="text-right">
                        {pnl !== null && pnl !== undefined
                          ? `${pnl.toFixed(2)} €`
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        {winRate !== null && winRate !== undefined
                          ? `${(winRate * 100).toFixed(0)}%`
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        {volume !== null && volume !== undefined
                          ? `${volume.toFixed(0)} €`
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right text-xs text-gray-400">
                        {last}
                      </TableCell>
                      <TableCell className="text-xs">
                        {tags.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {tags.map((t, i) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/30"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-gray-500">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
