// src/v2/interface/react/pages/Airdrops.jsx
import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { ScrollArea } from "../components/ui/scroll-area";

function formatDate(d) {
  if (!d) return "-";
  try {
    const dt = new Date(d);
    if (Number.isNaN(dt.getTime())) return "-";
    return dt.toLocaleDateString();
  } catch {
    return "-";
  }
}

export default function Airdrops() {
  const [airdrops, setAirdrops] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all"); // all | active | ended | upcoming
  const [chain, setChain] = useState("all");
  const [sortBy, setSortBy] = useState("deadline"); // deadline | reward | name
  const [sortDir, setSortDir] = useState("asc"); // asc | desc
  const [lastSync, setLastSync] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setErr("");
    try {
      const res = await fetch("/data/airdrops.json", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // data attendu: [{ name, project, chain, reward, deadline, status, link }, ...]
      setAirdrops(Array.isArray(data) ? data : []);
      setLastSync(new Date().toISOString());
    } catch (e) {
      setErr("Impossible de charger les airdrops.");
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const chains = useMemo(() => {
    const set = new Set(airdrops.map(a => (a.chain || "N/A").toString()));
    return ["all", ...Array.from(set).sort()];
  }, [airdrops]);

  const filtered = useMemo(() => {
    let items = [...airdrops];

    // recherche
    if (q.trim()) {
      const needle = q.toLowerCase();
      items = items.filter(a =>
        [a.name, a.project, a.chain, a.status]
          .filter(Boolean)
          .some(v => v.toString().toLowerCase().includes(needle))
      );
    }

    // filtre status
    if (status !== "all") {
      items = items.filter(a => (a.status || "unknown").toLowerCase() === status);
    }

    // filtre chain
    if (chain !== "all") {
      items = items.filter(a => (a.chain || "N/A").toString() === chain);
    }

    // tri
    items.sort((a, b) => {
      let av, bv;
      switch (sortBy) {
        case "reward":
          av = Number(a.reward) || 0;
          bv = Number(b.reward) || 0;
          break;
        case "name":
          av = (a.name || "").toLowerCase();
          bv = (b.name || "").toLowerCase();
          break;
        case "deadline":
        default:
          av = new Date(a.deadline || 0).getTime() || 0;
          bv = new Date(b.deadline || 0).getTime() || 0;
          break;
      }
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

    return items;
  }, [airdrops, q, status, chain, sortBy, sortDir]);

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Airdrops</h1>
        <div className="text-xs text-muted-foreground">
          {lastSync ? <>Dernière synchro : {new Date(lastSync).toLocaleTimeString()}</> : "—"}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filtrer & Rechercher</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-5">
          <Input
            placeholder="Rechercher (nom, projet, chaîne...)"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="md:col-span-2"
          />

          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger><SelectValue placeholder="Statut" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les statuts</SelectItem>
              <SelectItem value="active">Actifs</SelectItem>
              <SelectItem value="upcoming">À venir</SelectItem>
              <SelectItem value="ended">Terminés</SelectItem>
            </SelectContent>
          </Select>

          <Select value={chain} onValueChange={setChain}>
            <SelectTrigger><SelectValue placeholder="Chaîne" /></SelectTrigger>
            <SelectContent>
              {chains.map(c => (
                <SelectItem key={c} value={c}>{c === "all" ? "Toutes les chaînes" : c}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="flex gap-2">
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-36"><SelectValue placeholder="Trier par" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="deadline">Deadline</SelectItem>
                <SelectItem value="reward">Récompense</SelectItem>
                <SelectItem value="name">Nom</SelectItem>
              </SelectContent>
            </Select>
            <Select value={sortDir} onValueChange={setSortDir}>
              <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="asc">Asc</SelectItem>
                <SelectItem value="desc">Desc</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="md:col-span-5 flex justify-end">
            <Button onClick={fetchData} disabled={loading}>
              {loading ? "Actualisation..." : "Actualiser"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Liste des airdrops ({filtered.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {err ? (
            <div className="p-6 text-sm text-red-600">{err}</div>
          ) : loading ? (
            <div className="p-6 text-sm text-muted-foreground">Chargement…</div>
          ) : filtered.length === 0 ? (
            <div className="p-6 text-sm text-muted-foreground">Aucun airdrop trouvé avec ces critères.</div>
          ) : (
            <ScrollArea className="max-h-[60vh]">
              <div className="min-w-full overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-background border-b">
                    <tr>
                      <th className="text-left p-3">Nom</th>
                      <th className="text-left p-3">Projet</th>
                      <th className="text-left p-3">Chaîne</th>
                      <th className="text-right p-3">Récompense</th>
                      <th className="text-left p-3">Deadline</th>
                      <th className="text-left p-3">Statut</th>
                      <th className="text-left p-3">Lien</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((a, i) => (
                      <tr key={`${a.name || "airdrop"}-${i}`} className="border-b last:border-0">
                        <td className="p-3 font-medium">{a.name || "-"}</td>
                        <td className="p-3">{a.project || "-"}</td>
                        <td className="p-3">{a.chain || "-"}</td>
                        <td className="p-3 text-right">{a.reward ?? "-"}</td>
                        <td className="p-3">{formatDate(a.deadline)}</td>
                        <td className="p-3">
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs bg-muted">
                            {(a.status || "unknown").toString()}
                          </span>
                        </td>
                        <td className="p-3">
                          {a.link ? (
                            <a
                              href={a.link}
                              target="_blank"
                              rel="noreferrer"
                              className="underline underline-offset-2"
                            >
                              Ouvrir
                            </a>
                          ) : (
                            "-"
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}