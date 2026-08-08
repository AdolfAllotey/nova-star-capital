import { useEffect, useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "../components/ui/card";
import { ScrollArea } from "../components/ui/scroll-area";
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "../components/ui/table";
import { Loader2 } from "lucide-react";
import { buildApiUrl } from "../lib/apiBase";

export default function WhalesLeaderboard() {
  const [loading, setLoading] = useState(true);
  const [whales, setWhales] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const res = await fetch(
          buildApiUrl("/api/crypto/overview"),
          {
            cache: "no-store",
            credentials: "include",
            headers: {
              Accept: "application/json",
            },
          }
        );

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const payload = await res.json();
        const rows = payload?.whales?.rows;

        if (active) {
          setWhales(Array.isArray(rows) ? rows : []);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setWhales([]);
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load whales leaderboard."
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-6 p-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-bold">
            Classement des Whales
          </CardTitle>
        </CardHeader>

        <CardContent>
          {loading && (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          )}

          {!loading && error && (
            <div className="text-sm text-red-400">
              Données whales indisponibles : {error}
            </div>
          )}

          {!loading && !error && whales.length === 0 && (
            <div className="text-sm text-muted-foreground">
              Aucune donnée disponible. Le classement sera alimenté après
              les premiers scanners en préproduction.
            </div>
          )}

          {!loading && !error && whales.length > 0 && (
            <ScrollArea className="w-full max-h-[70vh]">
              <Table className="min-w-[700px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Wallet</TableHead>
                    <TableHead>Token</TableHead>
                    <TableHead className="text-right">
                      PnL 30j (€)
                    </TableHead>
                    <TableHead className="text-right">
                      Volume 30j
                    </TableHead>
                    <TableHead className="text-right">
                      Trades gagnants
                    </TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {whales.map((whale, index) => {
                    const winRate =
                      whale.win_rate_30d ??
                      whale.winrate ??
                      null;

                    return (
                      <TableRow
                        key={
                          whale.wallet ||
                          whale.address ||
                          `${whale.token || "whale"}-${index}`
                        }
                      >
                        <TableCell className="font-mono text-xs">
                          {whale.wallet || whale.address || "-"}
                        </TableCell>

                        <TableCell>
                          {whale.token || whale.symbol || "-"}
                        </TableCell>

                        <TableCell className="text-right">
                          {whale.pnl_30d ?? "-"}
                        </TableCell>

                        <TableCell className="text-right">
                          {whale.volume_30d ?? "-"}
                        </TableCell>

                        <TableCell className="text-right">
                          {winRate == null
                            ? "-"
                            : `${Number(winRate).toFixed(1)}%`}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
