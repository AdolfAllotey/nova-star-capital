import React, { useEffect, useState } from "react";
import { Activity, Brain, ShieldCheck, Target, TrendingUp } from "lucide-react";
import NscSidebar from "../components/layout/NscSidebar";
import { apiUrl } from "../lib/apiClient";

async function fetchDecisionSource(path) {
  const url = apiUrl(path);

  try {
    const response = await fetch(url, {
      credentials: "include",
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    });

    let payload = null;

    try {
      payload = await response.json();
    } catch {
      payload = null;
    }

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        data: null,
        error:
          payload?.detail ||
          payload?.message ||
          response.statusText ||
          "Request failed",
      };
    }

    if (!payload || typeof payload !== "object") {
      return {
        ok: false,
        status: response.status,
        data: null,
        error: "Invalid decision payload",
      };
    }

    return {
      ok: true,
      status: response.status,
      data: payload,
      error: null,
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      data: null,
      error: String(
        error?.message ||
        error ||
        "Decision source unavailable"
      ),
    };
  }
}

function Card({ title, icon: Icon = Activity, children }) {
  return (
    <div className="rounded-2xl border border-[#172231] bg-[#0b131d] p-4">
      <div className="mb-3 flex items-center gap-2">
        <Icon size={16} className="text-cyan-300" />
        <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-200">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function Metric({ label, value, tone = "cyan" }) {
  const tones = {
    cyan: "text-cyan-300 border-cyan-400/20 bg-cyan-400/10",
    emerald: "text-emerald-300 border-emerald-400/20 bg-emerald-400/10",
    amber: "text-amber-300 border-amber-400/20 bg-amber-400/10",
    red: "text-red-300 border-red-400/20 bg-red-400/10",
    slate: "text-slate-300 border-slate-400/20 bg-slate-400/10",
  };
  return (
    <div className={`rounded-xl border px-3 py-2 ${tones[tone] || tones.cyan}`}>
      <div className="text-[10px] uppercase tracking-[0.16em] opacity-70">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  );
}

export default function ExecutiveDecisionCenter() {
  const [data, setData] = useState(null);
  const [sourceState, setSourceState] = useState({
    loading: true,
    online: false,
    status: null,
    error: null,
    lastSuccessAt: null,
  });

  useEffect(() => {
    let alive = true;
    async function load() {
      const result = await fetchDecisionSource(
        "/api/executive-decision"
      );

      if (!alive) return;

      if (result.ok) {
        setData(result.data);
        setSourceState({
          loading: false,
          online: true,
          status: result.status,
          error: null,
          lastSuccessAt: new Date().toISOString(),
        });
        return;
      }

      setSourceState((previous) => ({
        ...previous,
        loading: false,
        online: false,
        status: result.status,
        error: result.error,
      }));
    }
    load();
    const id = setInterval(load, 15000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const sourceOnline =
    sourceState.online && Boolean(data);

  const decision = sourceOnline
    ? data?.decision || "UNKNOWN"
    : "UNAVAILABLE";

  const actionPolicy = sourceOnline
    ? data?.action_policy || "UNAVAILABLE"
    : "UNAVAILABLE";

  const executionPosture = sourceOnline
    ? data?.execution_posture ||
      data?.action_policy ||
      "UNAVAILABLE"
    : "UNAVAILABLE";

  const realExecutionAuthorized =
    sourceOnline &&
    data?.real_execution_authorized === true;

  const simulationAuthorized =
    sourceOnline &&
    data?.simulation_authorized === true;

  const preprodSafetyState = !sourceOnline
    ? "UNAVAILABLE"
    : realExecutionAuthorized
      ? "REVIEW"
      : simulationAuthorized
        ? "ACTIVE"
        : "BLOCKED";

  const sourceStatusLabel = sourceState.loading
    ? "LOADING"
    : sourceOnline
      ? String(data?.status || "ONLINE").toUpperCase()
      : "UNAVAILABLE";
  const score = sourceOnline
    ? Number(data?.decision_score ?? 0)
    : 0;
  const tone = decision === "BUY" || decision === "HOLD" ? "emerald" : decision === "WAIT" || decision === "OBSERVE" ? "amber" : "red";

  const history = data?.history || [];
  const sameDecisionCount = history.filter((h) => h.decision === decision).length;
  const stabilityPct = history.length ? Math.round((sameDecisionCount / history.length) * 100) : 0;
  const decisionChanges = history.slice(1).reduce((acc, h, idx) => acc + (h.decision !== history[idx]?.decision ? 1 : 0), 0);
  const currentStreak = (() => {
    let count = 0;
    for (const h of history) {
      if (h.decision === decision) count += 1;
      else break;
    }
    return count;
  })();

  const confidenceLoss = Math.max(0, 100 - score);
  const limitingFactors = [
    ["Activity Score", Math.max(0, 100 - Number((data?.drivers || []).find((d) => d.driver === "Activity Score")?.value || 0))],
    ["Meta Rank", Math.max(0, 100 - Number((data?.waterfall || []).find((w) => w.step === "Meta Ranking")?.score || 0))],
    ["Persistence", Math.max(0, 100 - Number((data?.waterfall || []).find((w) => w.step === "Persistence")?.score || 0))],
    ["Portfolio Fit", Math.abs(Number(data?.crypto_gap_pct || 0))],
    ["Execution", data?.execution_ready ? 0 : 25],
  ].sort((a, b) => b[1] - a[1]);

  return (
    <div className="min-h-screen bg-[#05080d] text-slate-100">
      <NscSidebar footerText="Decision layer online" />
      <main className="ml-[235px] w-[calc(100%-235px)] p-4 max-xl:ml-[220px] max-xl:w-[calc(100%-220px)] max-lg:ml-0 max-lg:w-full">

        <div className="mb-4 rounded-3xl border border-cyan-400/10 bg-gradient-to-r from-[#07111c] via-[#0b1623] to-[#05080d] p-5">
          <div className="text-[10px] uppercase tracking-[0.28em] text-cyan-300">Nova Star Capital</div>
          <h1 className="mt-1 text-2xl font-semibold uppercase tracking-wide">Executive Decision Center</h1>
          <p className="mt-1 text-sm text-slate-400">
            Decision brain explaining portfolio action, conviction, rejection logic and execution alignment.
          </p>
          <div className={`mt-3 inline-flex rounded-md border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${
            sourceOnline
              ? "border-amber-400/30 bg-amber-400/10 text-amber-300"
              : "border-slate-400/20 bg-slate-400/10 text-slate-400"
          }`}>
            Decision Source — {sourceStatusLabel}
          </div>
        </div>

        <div className="mb-4">
          <Card title="Decision Mode" icon={ShieldCheck}>
            <div className="grid gap-3 md:grid-cols-4">
              <Metric
                label="Decision Signal"
                value={decision}
                tone={sourceOnline ? tone : "slate"}
              />
              <Metric
                label="Execution Mode"
                value={executionPosture}
                tone={sourceOnline ? "amber" : "slate"}
              />
              <Metric
                label="Real Execution"
                value={
                  !sourceOnline
                    ? "UNAVAILABLE"
                    : realExecutionAuthorized
                      ? "AUTHORIZED"
                      : "BLOCKED"
                }
                tone={
                  !sourceOnline
                    ? "slate"
                    : realExecutionAuthorized
                      ? "red"
                      : "emerald"
                }
              />
              <Metric
                label="Preprod Safety"
                value={preprodSafetyState}
                tone={
                  !sourceOnline
                    ? "slate"
                    : preprodSafetyState === "ACTIVE"
                      ? "emerald"
                      : "amber"
                }
              />
            </div>
            <div className="mt-3 text-xs text-slate-500">
              {sourceOnline
                ? `Runtime policy: ${actionPolicy}. Simulation ${
                    simulationAuthorized
                      ? "authorized"
                      : "not authorized"
                  }; real execution ${
                    realExecutionAuthorized
                      ? "authorized"
                      : "blocked"
                  }.`
                : sourceState.error ||
                  "Executive decision source unavailable."}
            </div>
          </Card>
        </div>

        <div className="mb-4 grid gap-4 xl:grid-cols-[1.2fr_1fr]">
          <Card title="Executive Decision" icon={Brain}>
            <div className="grid gap-4 xl:grid-cols-[180px_1fr]">
              <div className={`rounded-2xl border p-4 text-center ${
                tone === "emerald" ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300" :
                tone === "amber" ? "border-amber-400/30 bg-amber-400/10 text-amber-300" :
                "border-red-400/30 bg-red-400/10 text-red-300"
              }`}>
                <div className="text-[10px] uppercase tracking-[0.18em] opacity-70">Decision</div>
                <div className="mt-2 text-4xl font-bold">{decision}</div>
                <div className="mt-1 text-xs opacity-70">{sourceOnline ? `${score.toFixed(0)}/100` : "N/A"}</div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Metric label="Symbol" value={data?.recommended_symbol || "—"} tone="cyan" />
                <Metric label="Confidence" value={`${Number(data?.confidence || 0).toFixed(0)}%`} tone={tone} />
                <Metric label="Execution Ready" value={data?.execution_ready ? "YES" : "NO"} tone={data?.execution_ready ? "emerald" : "amber"} />
                <Metric label="Risk Level" value={data?.risk_level || "—"} tone={data?.risk_level === "LOW" ? "emerald" : "amber"} />
              </div>
            </div>
          </Card>

          <Card title="Portfolio Context" icon={Target}>
            <div className="grid grid-cols-2 gap-2">
              <Metric label="Posture" value={data?.portfolio_posture || "—"} tone="emerald" />
              <Metric label="Orders" value={data?.orders_count ?? 0} tone="cyan" />
              <Metric label="Crypto Current" value={`${Number(data?.crypto_current_pct || 0).toFixed(2)}%`} tone="cyan" />
              <Metric label="Crypto Gap" value={`${Number(data?.crypto_gap_pct || 0).toFixed(2)} pts`} tone={Number(data?.crypto_gap_pct || 0) < 0 ? "emerald" : "amber"} />
            </div>
          </Card>
        </div>

        <div className="mb-4 grid gap-4 xl:grid-cols-[1fr_1.2fr]">
          <Card title="Executive Confidence Gauge" icon={TrendingUp}>
            <div className="rounded-2xl border border-slate-800 bg-[#071019] p-4">
              <div className="mb-3 flex items-end justify-between">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Confidence</div>
                  <div className="mt-1 text-4xl font-bold text-cyan-300">{score.toFixed(1)}</div>
                </div>
                <div className="text-right text-xs text-slate-500">
                  <div>0-40 weak</div>
                  <div>40-70 neutral</div>
                  <div>70-85 good</div>
                  <div>85-100 institutional</div>
                </div>
              </div>
              <div className="h-3 rounded-full bg-slate-800">
                <div
                  className={score >= 85 ? "h-3 rounded-full bg-emerald-400" : score >= 70 ? "h-3 rounded-full bg-cyan-400" : score >= 40 ? "h-3 rounded-full bg-amber-400" : "h-3 rounded-full bg-red-400"}
                  style={{ width: `${Math.max(3, Math.min(100, score))}%` }}
                />
              </div>
              <div className="mt-3 text-xs text-slate-500">
                Current confidence is classified as {score >= 85 ? "institutional" : score >= 70 ? "good" : score >= 40 ? "neutral" : "weak"}.
              </div>
            </div>
          </Card>

          <Card title="Executive Confidence Analysis" icon={Brain}>
            <div className="grid gap-3 md:grid-cols-2">
              <Metric label="Confidence Loss" value={`${confidenceLoss.toFixed(2)} pts`} tone={confidenceLoss <= 10 ? "emerald" : "amber"} />
              <Metric label="Largest Limiter" value={limitingFactors[0]?.[0] || "—"} tone="amber" />
            </div>
            <div className="mt-4 space-y-3">
              {limitingFactors.slice(0, 5).map(([label, value]) => (
                <div key={label}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="text-slate-300">{label}</span>
                    <span className="text-slate-500">-{Number(value).toFixed(2)}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-800">
                    <div className="h-2 rounded-full bg-amber-400" style={{ width: `${Math.min(100, Math.max(3, Number(value)))}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Decision Stability" icon={ShieldCheck}>
            <div className="grid gap-3 md:grid-cols-4">
              <Metric label="Consistency" value={`${stabilityPct}%`} tone={stabilityPct >= 80 ? "emerald" : "amber"} />
              <Metric label="Decision Changes" value={`${decisionChanges}/${Math.max(0, history.length - 1)}`} tone={decisionChanges <= 1 ? "emerald" : "amber"} />
              <Metric label="Current Streak" value={`${decision} x${currentStreak}`} tone="cyan" />
              <Metric label="History Depth" value={`${history.length} runs`} tone="slate" />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {history.slice(0, 12).map((h, idx) => (
                <span key={`stability-${idx}`} className={
                  h.decision === "BUY" || h.decision === "HOLD"
                    ? "rounded-md border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-[10px] uppercase text-emerald-300"
                    : h.decision === "WAIT" || h.decision === "OBSERVE"
                    ? "rounded-md border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-[10px] uppercase text-amber-300"
                    : "rounded-md border border-red-400/20 bg-red-400/10 px-2 py-1 text-[10px] uppercase text-red-300"
                }>
                  {h.decision || "—"}
                </span>
              ))}
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Portfolio Impact" icon={Target}>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-slate-800 bg-[#071019] p-4">
                <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Crypto Allocation</div>
                <div className="mt-2 flex items-end gap-2">
                  <span className="text-2xl font-semibold text-cyan-300">{Number(data?.crypto_current_pct || 0).toFixed(2)}%</span>
                  <span className="pb-1 text-xs text-slate-500">current</span>
                </div>
                <div className="mt-3 h-2 rounded-full bg-slate-800">
                  <div className="h-2 rounded-full bg-cyan-400" style={{ width: `${Math.min(100, Number(data?.crypto_current_pct || 0))}%` }} />
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-[#071019] p-4">
                <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Target Allocation</div>
                <div className="mt-2 flex items-end gap-2">
                  <span className="text-2xl font-semibold text-emerald-300">{Number(data?.crypto_target_pct || 0).toFixed(2)}%</span>
                  <span className="pb-1 text-xs text-slate-500">target</span>
                </div>
                <div className="mt-3 h-2 rounded-full bg-slate-800">
                  <div className="h-2 rounded-full bg-emerald-400" style={{ width: `${Math.min(100, Number(data?.crypto_target_pct || 0))}%` }} />
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-[#071019] p-4">
                <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Decision Gap</div>
                <div className="mt-2 flex items-end gap-2">
                  <span className={Number(data?.crypto_gap_pct || 0) < 0 ? "text-2xl font-semibold text-emerald-300" : "text-2xl font-semibold text-amber-300"}>
                    {Number(data?.crypto_gap_pct || 0).toFixed(2)} pts
                  </span>
                  <span className="pb-1 text-xs text-slate-500">current - target</span>
                </div>
                <div className="mt-3 text-sm text-slate-300">
                  {Number(data?.crypto_gap_pct || 0) < -2
                    ? "Crypto remains under target, supporting additional deployment."
                    : Number(data?.crypto_gap_pct || 0) > 2
                    ? "Crypto is above target, favouring hold or risk reduction."
                    : "Crypto allocation is close to target."}
                </div>
              </div>
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Decision Waterfall" icon={ShieldCheck}>
            <div className="grid gap-3 md:grid-cols-4 xl:grid-cols-8">
              {(data?.waterfall || []).map((w, idx) => (
                <div key={idx} className="rounded-xl border border-slate-800 bg-[#071019] p-3">
                  <div className="text-sm font-semibold text-slate-100">{w.step}</div>
                  <div className={
                    w.status === "PASS" ? "mt-1 text-xs text-emerald-300" :
                    w.status === "FAIL" ? "mt-1 text-xs text-red-300" :
                    "mt-1 text-xs text-amber-300"
                  }>{w.status}</div>
                  <div className="mt-2 text-[10px] uppercase tracking-[0.12em] text-slate-500">score {String(w.score)}</div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="mb-4 grid gap-4 xl:grid-cols-2">
          <Card title="Why This Decision?" icon={Brain}>
            <div className="space-y-2">
              {(data?.waterfall || []).filter((w) => w.status === "PASS" || w.status === data?.decision).slice(0, 7).map((w, idx) => (
                <div key={`why-pass-${idx}`} className="rounded-xl border border-emerald-400/10 bg-emerald-400/5 px-3 py-2 text-sm">
                  <div className="flex justify-between">
                    <span className="font-semibold text-slate-100">{w.step}</span>
                    <span className="text-emerald-300">{w.status}</span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">Score: {String(w.score)}</div>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Why Not?" icon={ShieldCheck}>
            <div className="space-y-2">
              {(data?.rejections || []).slice(0, 5).map((r, idx) => (
                <div key={`why-not-${idx}`} className="rounded-xl border border-amber-400/10 bg-amber-400/5 px-3 py-2 text-sm">
                  <div className="flex justify-between">
                    <span className="font-semibold text-slate-100">{r.symbol}</span>
                    <span className="text-cyan-300">{Number(r.meta_rank || 0).toFixed(2)}</span>
                  </div>
                  <div className="mt-1 text-xs uppercase tracking-[0.12em] text-slate-500">{r.verdict}</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(r.reasons || []).slice(0, 3).map((x) => (
                      <span key={x} className="rounded-md border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-[10px] uppercase text-amber-300">{x}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="mb-4 grid gap-4 xl:grid-cols-2">
          <Card title="Decision Drivers" icon={TrendingUp}>
            <div className="space-y-3">
              {(data?.drivers || []).map((d, idx) => {
                const v = Math.max(0, Math.min(100, Number(d.value || 0)));
                return (
                  <div key={idx}>
                    <div className="mb-1 flex justify-between text-xs">
                      <span className="text-slate-300">{d.driver}</span>
                      <span className="text-slate-500">{v.toFixed(0)}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-800">
                      <div className="h-2 rounded-full bg-cyan-400" style={{ width: `${v}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          <Card title="Rejected Opportunities" icon={ShieldCheck}>
            <div className="space-y-2">
              {(data?.rejections || []).map((r, idx) => (
                <div key={idx} className="rounded-xl border border-slate-800 bg-[#071019] px-3 py-2 text-sm">
                  <div className="flex justify-between">
                    <span className="font-semibold text-slate-100">{r.symbol}</span>
                    <span className="text-cyan-300">{Number(r.meta_rank || 0).toFixed(2)}</span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{r.verdict}</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(r.reasons || []).map((x) => (
                      <span key={x} className="rounded-md border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-[10px] uppercase text-amber-300">{x}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Decision Alert Timeline" icon={ShieldCheck}>
            <div className="space-y-2">
              {(data?.history || []).slice(0, 8).map((h, idx) => {
                const alerts = [];
                if (!h.execution_ready) alerts.push("execution not ready");
                if (!h.leader_in_execution) alerts.push("leader not in execution");
                if (Number(h.crypto_gap_pct || 0) > 5) alerts.push("crypto above target");
                if (h.risk_level && h.risk_level !== "LOW") alerts.push(`risk ${h.risk_level}`);

                return (
                  <div key={`decision-alert-${idx}`} className="rounded-xl border border-slate-800 bg-[#071019] px-3 py-3">
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="font-semibold text-slate-100">{idx === 0 ? "latest" : `-${idx}`}</span>
                      <span className={alerts.length ? "text-amber-300" : "text-emerald-300"}>
                        {alerts.length ? `${alerts.length} alert(s)` : "clear"}
                      </span>
                    </div>
                    <div className="text-xs text-slate-500">
                      {alerts.length ? alerts.join(" · ") : "No decision alert detected."}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Decision Trend Curve" icon={Activity}>
            <div className="grid gap-3 md:grid-cols-10">
              {(data?.history || []).slice(0, 10).reverse().map((h, idx) => {
                const score = Math.max(0, Math.min(100, Number(h.decision_score || 0)));
                const decision = h.decision || "—";
                return (
                  <div key={`decision-trend-${idx}`} className="rounded-xl border border-slate-800 bg-[#071019] p-3">
                    <div className="mb-2 flex h-24 items-end rounded-lg bg-slate-900/80 p-2">
                      <div
                        className={
                          decision === "BUY" || decision === "HOLD"
                            ? "w-full rounded-md bg-emerald-400"
                            : decision === "WAIT" || decision === "OBSERVE"
                            ? "w-full rounded-md bg-amber-400"
                            : "w-full rounded-md bg-red-400"
                        }
                        style={{ height: `${Math.max(8, score)}%` }}
                      />
                    </div>
                    <div className="text-center text-[10px] uppercase tracking-[0.12em] text-slate-500">
                      {idx === 9 ? "latest" : `-${9 - idx}`}
                    </div>
                    <div className="mt-1 text-center text-xs font-semibold text-slate-300">
                      {score.toFixed(0)}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-3 text-xs text-slate-500">
              Decision trend tracks conviction score across recent executive decision snapshots.
            </div>
          </Card>
        </div>

        <div className="mb-4">
          <Card title="Decision History" icon={Activity}>
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <div className="grid grid-cols-6 bg-[#071019] px-3 py-2 text-[10px] uppercase tracking-[0.14em] text-slate-500">
                <div>Run</div>
                <div>Decision</div>
                <div>Asset</div>
                <div>Score</div>
                <div>Exec Ready</div>
                <div>Risk</div>
              </div>
              <div className="divide-y divide-slate-800">
                {(data?.history || []).slice(0, 10).map((h, idx) => (
                  <div key={`decision-history-${idx}`} className="grid grid-cols-6 items-center px-3 py-3 text-sm">
                    <div className="text-slate-400">{idx === 0 ? "latest" : `-${idx}`}</div>
                    <div className="font-semibold text-cyan-300">{h.decision || "—"}</div>
                    <div className="text-slate-100">{h.recommended_symbol || "—"}</div>
                    <div className="text-emerald-300">{h.decision_score != null ? Number(h.decision_score).toFixed(0) : "—"}</div>
                    <div className={h.execution_ready ? "text-emerald-300" : "text-amber-300"}>{h.execution_ready ? "YES" : "NO"}</div>
                    <div className="text-slate-300">{h.risk_level || "—"}</div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>

        <Card title="Executive Narrative" icon={Brain}>
          <p className="text-sm leading-6 text-slate-300">{data?.narrative || "No narrative available yet."}</p>
        </Card>

      </main>
    </div>
  );
}
