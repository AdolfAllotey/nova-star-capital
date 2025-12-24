import { useEffect, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card";
import { ScrollArea } from "../../components/ui/scroll-area";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "../../components/ui/table";
import { Loader2 } from "lucide-react";

export default function WhalesLeaderboard() {
  const [loading, setLoading] = useState(true);
  const [whales, setWhales] = useState([]);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/data/intelligence/whales_leaderboard.json");
        const json = await res.json();

        if (Array.isArray(json.items)) {
          setWhales(json.items);
        }
      } catch (err) {
        console.error("Error loading whales_leaderboard.json", err);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  return (
    <div className="space-y-6 p-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold">🏆 Classement des Whales</CardTitle>
        </CardHeader>

        <CardContent>
          {loading && (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          )}

          {!loading && whales.length === 0 && (
            <div className="text-sm text-muted-foreground">
              Aucune donnée disponible. Le classement sera rempli après les premiers scanners en pré-production.
            </div>
          )}

          {!loading && whales.length > 0 && (
            <ScrollArea className="w-full max-h-[70vh]">
              <Table className="min-w-[700px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Wallet</TableHead>
                    <TableHead>Token</TableHead>
                    <TableHead className="text-right">PnL 30j (€)</TableHead>
                    <TableHead className="text-right">Volume (30j)</TableHead>
                    <TableHead className="text-right">Trades gagnants (%)</TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {whales.map((w, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-xs">{w.wallet || "-"}</TableCell>
                      <TableCell>{w.token || "-"}</TableCell>
                      <TableCell className="text-right">{w.pnl_30d ?? "-"}</TableCell>
                      <TableCell className="text-right">{w.volume_30d ?? "-"}</TableCell>
                      <TableCell className="text-right">{w.winrate ?? "-"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
