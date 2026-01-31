import React from "react";
import { useNscStatus } from "../hooks/useNscStatus";

import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";

function Flag({ v }) {
  const variant =
    v === "critical" ? "destructive" :
    v === "warning" || v === "caution" ? "outline" :
    "secondary";
  return <Badge variant={variant}>{v ?? "—"}</Badge>;
}

export default function ControlRoom() {
  const { loading, summary, governance, orchestrator } = useNscStatus();

  if (loading) return <div className="p-6">Chargement…</div>;

  return (
    <div className="p-6 grid grid-cols-1 xl:grid-cols-3 gap-6">

      <Card className="xl:col-span-3">
        <CardHeader>
          <CardTitle>🧠 Control Room – Go / No-Go</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Badge variant="secondary">ENV: {orchestrator?.env}</Badge>
          <Flag v={summary.system_flag} />
          <Badge variant={summary.can_trade ? "secondary" : "outline"}>
            CAN_TRADE: {summary.can_trade ? "YES" : "NO"}
          </Badge>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Governance</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div>Flag: <Flag v={summary.governance_flag} /></div>
          <div>Score: {summary.governance_score}</div>
          <div>Soft veto: {String(governance?.soft_veto)}</div>
          <div>Policy: {governance?.action_policy}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Risk / Correlation</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div>Risk mode: {summary.risk_mode}</div>
          <div>Correlation: <Flag v={summary.correlation_flag} /></div>
          <div>Gate active: {String(summary.correlation_gate_active)}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Execution</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div>Exec flag: <Flag v={summary.execution_flag} /></div>
          <div>Signals: {summary.nb_signals}</div>
          <div>Positions: {summary.nb_positions}</div>
        </CardContent>
      </Card>

      <Card className="xl:col-span-3">
        <CardHeader><CardTitle>Raisons système</CardTitle></CardHeader>
        <CardContent>
          {(summary.system_flag_reasons || []).map((r, i) => (
            <div key={i} className="text-sm">• {r}</div>
          ))}
        </CardContent>
      </Card>

    </div>
  );
}
