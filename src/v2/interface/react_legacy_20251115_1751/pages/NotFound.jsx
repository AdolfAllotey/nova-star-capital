// src/v2/interface/react/pages/NotFound.jsx
import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";

export default function NotFound() {
  const { pathname } = useLocation();

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-6">
      <Card className="w-full max-w-xl">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold">404 — Page introuvable</CardTitle>
          <p className="text-sm text-muted-foreground mt-2">
            Oups… l’URL <code className="px-1 py-0.5 bg-muted rounded">{pathname}</code> n’existe pas.
          </p>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="grid gap-2 text-sm">
            <p className="text-muted-foreground">
              Voici quelques liens pour reprendre la navigation :
            </p>
            <div className="flex flex-wrap gap-2">
              <Link to="/dashboard"><Button variant="default">Aller au Dashboard</Button></Link>
              <Link to="/profitability"><Button variant="secondary">Profitability</Button></Link>
              <Link to="/live-simulation"><Button variant="outline">Live Simulation</Button></Link>
            </div>
          </div>

          <div className="pt-2 border-t text-xs text-muted-foreground">
            Besoin d’aide ? Vérifie le menu principal ou contacte l’équipe.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}