// src/pages/GoNoGo.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import SectionCard from "../components/ui/SectionCard";
import DataState from "../components/ui/DataState";
import { fetchJson } from "../lib/apiClient";

const OVERRIDE_KEY = "nsc_gonogo_overrides_v1";

function Pill({ tone = "muted", children, onClick, title }) {
  const cls =
    tone === "ok"
      ? "border-emerald-800 text-emerald-300 bg-emerald-950/40"
      : tone === "warn"
      ? "border-amber-800 text-amber-300 bg-amber-950/40"
      : tone === "bad"
      ? "border-red-800 text-red-300 bg-red-950/40"
      : "border-zinc-800 text-zinc-300 bg-zinc-950/40";

  const base =
    "inline-flex items-center rounded-xl border px-2 py-1 text-xs select-none";

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        title={title}
        className={`${base} ${cls} hover:brightness-110 transition`}
      >
        {children}
      </button>
    );
  }

  return (
    <span title={title} className={`${base} ${cls}`}>
      {children}
    </span>
  );
}

function statusTone(status) {
  if (status === "OK") return "ok";
  if (status === "WARN") return "warn";
  if (status === "BLOCKED") return "bad";
  return "muted"; // TODO / UNKNOWN
}

function computeProgress(statuses) {
  const total = statuses.length || 0;
  const ok = statuses.filter((x) => x === "OK").length;
  const pct = total ? Math.round((ok / total) * 100) : 0;
  return { total, ok, pct };
}

function ProgressBar({ pct }) {
  const v = Math.max(0, Math.min(100, Number(pct) || 0));
  return (
    <div className="h-2 w-full rounded-full bg-zinc-900/70 border border-zinc-800 overflow-hidden">
      <div className="h-full bg-emerald-500/60" style={{ width: `${v}%` }} />
    </div>
  );
}


function safeJsonParse(s, fallback) {
  try {
    return JSON.parse(s);
  } catch {
    return fallback;
  }
}

function nowLabel(ts) {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString("fr-FR");
  } catch {
    return String(ts);
  }
}

function cycleStatus(s) {
  // Cycle pratique pour override manuel
  if (s === "TODO") return "OK";
  if (s === "OK") return "WARN";
  if (s === "WARN") return "BLOCKED";
  return "TODO";
}

function PhaseCard({ phase, overrides, onToggleOverride }) {
  const progress = computeProgress((phase?.checks || []).map(c => c?.status));
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-4 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-zinc-50">{phase.title}</div>
          <div className="text-xs text-zinc-500">{phase.subtitle}</div>
          {/* Progress (phase) */}
          <div className="mt-2 space-y-1">
            <ProgressBar pct={computeProgress((phase?.checks || []).map(c => c?.status)).pct} />
            <div className="text-[11px] text-zinc-500">
              {computeProgress((phase?.checks || []).map(c => c?.status)).ok}/{computeProgress((phase?.checks || []).map(c => c?.status)).total} checks OK · {computeProgress((phase?.checks || []).map(c => c?.status)).pct}%
            </div>
          </div>
        </div>
        <Pill tone={statusTone(phase.status)} title="Statut phase">
          {phase.status}
        </Pill>
      </div>

      <div className="space-y-2">
        {phase.checks.map((c, idx) => {
          const key = `${phase.id}:${idx}`;
          const ov = overrides?.[key];
          const effectiveStatus = ov?.status || c.status;
          const note = ov?.note || c.note || c.hint;

          return (
            <div key={idx} className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-sm text-zinc-200">{c.label}</div>
                {note ? <div className="text-xs text-zinc-500">{note}</div> : null}
              </div>

              <div className="shrink-0 flex items-center gap-2">
                {ov ? (
                  <span className="text-[10px] text-zinc-500">override</span>
                ) : null}

                <Pill
                  tone={statusTone(effectiveStatus)}
                  title="Clique pour override (cycle TODO → OK → WARN → BLOCKED)"
                  onClick={() => onToggleOverride(phase.id, idx, effectiveStatus)}
                >
                  {effectiveStatus}
                </Pill>
              </div>
            </div>
          );
        })}
      </div>

      {phase.links?.length ? (
        <div className="pt-2 flex flex-wrap gap-2">
          {phase.links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className="text-xs text-zinc-300 hover:text-white underline underline-offset-4"
            >
              {l.label}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function deepString(x) {
  try {
    return JSON.stringify(x ?? {}).toLowerCase();
  } catch {
    return String(x ?? "").toLowerCase();
  }
}

function applyStatusSignals(statusItem, setCheckIfNotOverridden) {
  // statusItem = { path, ok, data, error, ... } (structure tolérante)
  if (!statusItem?.ok) return;

  const d = statusItem.data || {};
  const raw = deepString(d);

  // 1) DRY_RUN enforced (préflight check #0)
  const env = String(d?.env || "").toUpperCase();
  const dryFlag = d?.dry_run_enforced;

  const looksDry =
    dryFlag === true ||
    env === "PREPROD" ||
    raw.includes("dry_run") ||
    raw.includes("dryrun") ||
    raw.includes("simulated") ||
    raw.includes("preprod");

  setCheckIfNotOverridden("preflight", 0, looksDry
    ? { status: "OK", note: "Auto: /status indique PREPROD / dry_run_enforced." }
    : { status: "WARN", note: "Auto: /status ne confirme pas DRY_RUN — vérifier." }
  );

  // 2) Uptime (préprod check #0)
  const up = Number(d?.uptime_s);
  if (!Number.isNaN(up)) {
    setCheckIfNotOverridden("preprod", 0, up >= 3600
      ? { status: "OK", note: `Auto: uptime ${Math.round(up)}s (>= 1h).` }
      : { status: "WARN", note: `Auto: uptime ${Math.round(up)}s (< 1h).` }
    );
  }
}


export default function GoNoGo() {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const [overrides, setOverrides] = useState(() => {
    const raw = localStorage.getItem(OVERRIDE_KEY);
    return raw ? safeJsonParse(raw, {}) : {};
  });

  const overridesRef = useRef(overrides);
  useEffect(() => {
    overridesRef.current = overrides;
    localStorage.setItem(OVERRIDE_KEY, JSON.stringify(overrides));
  }, [overrides]);

  const [phases, setPhases] = useState(() => [
    {
      id: "preflight",
      title: "Préflight (bloquant)",
      subtitle: "Avant de lancer la préprod 30j",
      status: "TODO",
      checks: [
        {
          label: "DRY_RUN enforced (aucun ordre réel)",
          status: "TODO",
          hint: "Auto depuis /status (dry_run / preprod / simulated).",
        },
        {
          label: "Kill-switch opérationnel (hard_block ⇒ orders=0)",
          status: "TODO",
          hint: "Auto si /governance/status disponible (hard_block).",
        },
        {
          label: "Caps globaux actifs (max_orders / max_notional)",
          status: "TODO",
          hint: "Auto si /governance/status ou /status expose des caps.",
        },
      ],
      links: [
        { to: "/system-status", label: "System Status" },
        { to: "/risk", label: "Risk" },
      ],
    },
    {
      id: "preprod",
      title: "Préprod 30 jours",
      subtitle: "Stabilité runtime + absence d’incidents critiques",
      status: "TODO",
      checks: [
        { label: "Process stable (uptime + pas de crash)", status: "TODO", hint: "Manuel / métriques uptime." },
        { label: "Aucun ordre illégitime", status: "TODO", hint: "Manuel + logs (orders=0 si preprod)." },
        { label: "Idempotence (pas de doublons d’ordres)", status: "TODO", hint: "Manuel + audit execution_plan." },
        { label: "Backpressure / protection latence OK", status: "TODO", hint: "Auto si endpoint backpressure dispo." },
      ],
      links: [
        { to: "/reporting/open-positions", label: "Open Positions" },
        { to: "/reporting/worst-trades", label: "Worst Trades" },
      ],
    },
    {
      id: "stress",
      title: "Stress tests",
      subtitle: "Marché / système / logique",
      status: "TODO",
      checks: [
        { label: "Scénarios extrêmes (drawdown/vol/liquidité)", status: "TODO" },
        { label: "Auto-recovery / playbooks testés", status: "TODO" },
        { label: "Kill-switch testé en conditions réalistes", status: "TODO" },
      ],
      links: [
        { to: "/risk", label: "Risk Overview" },
        { to: "/system-status", label: "System Status" },
      ],
    },
    {
      id: "observability",
      title: "Observabilité",
      subtitle: "Logs / métriques / alerting",
      status: "TODO",
      checks: [
        { label: "Logs consolidés + alerting Telegram/Email", status: "TODO" },
        { label: "KPIs quotidiens (drawdown, perf, latence)", status: "TODO" },
        { label: "Audit / conformité pre-prod validés", status: "TODO" },
      ],
      links: [
        { to: "/system-status", label: "System Status" },
        { to: "/settings", label: "Settings" },
      ],
    },
    {
      id: "gonogo",
      title: "Go / No-Go",
      subtitle: "Décision finale",
      status: "TODO",
      checks: [
        { label: "30 jours sans incident critique", status: "TODO" },
        { label: "Kill-switch OK + testé", status: "TODO" },
        { label: "Aucun ordre réel (préprod)", status: "TODO" },
        { label: "Observabilité OK", status: "TODO" },
      ],
      links: [
        { to: "/reporting/pnl", label: "PnL" },
        { to: "/reporting/profitability", label: "Profitability" },
      ],
    },
  ]);

  function setCheckIfNotOverridden(phaseId, idx, patch) {
    const key = `${phaseId}:${idx}`;
    if (overridesRef.current?.[key]) return; // override gagne
    setPhases((prev) =>
      prev.map((p) => {
        if (p.id !== phaseId) return p;
        const checks = p.checks.map((c, i) => (i === idx ? { ...c, ...patch } : c));
        return { ...p, checks };
      })
    );
  }

  function recomputePhaseStatuses() {
    setPhases((prev) =>
      prev.map((p) => {
        const statuses = p.checks.map((c, idx) => {
          const key = `${p.id}:${idx}`;
          return overridesRef.current?.[key]?.status || c.status;
        });

        // BLOCKED > WARN > TODO > OK
        let phaseStatus = "OK";
        if (statuses.some((s) => s === "BLOCKED")) phaseStatus = "BLOCKED";
        else if (statuses.some((s) => s === "WARN")) phaseStatus = "WARN";
        else if (statuses.some((s) => s === "TODO")) phaseStatus = "TODO";

        return { ...p, status: phaseStatus };
      })
    );
  }

  async function refresh() {
    setLoading(true);
    setErr(null);

    // endpoints best-effort (si 404 => on ignore)
    const endpoints = [
      { name: "status", path: "/status" },
      { name: "gov", path: "/governance/status" },
      { name: "risk", path: "/risk/status" },
      { name: "bp", path: "/monitoring/backpressure" },
    ];

    try {
      const results = await Promise.all(
        endpoints.map(async (e) => {
          const r = await fetchJson(e.path, { timeoutMs: 7000 });
          

return { ...e, ok: r.ok, data: r.data, error: r.error };
        })
      );

      // ---- 1) DRY_RUN / PREPROD
      const statusItem = results.find((x) => x.name === "status" && x.ok);
      if (statusItem?.data) {
        const d = statusItem.data;
        const raw = deepString(d);

        const dryFlag =
          (d && typeof d === "object" && (d.dry_run === true || d.dryRun === true)) ||
          raw.includes("dry_run") ||
          raw.includes("dryrun") ||
          raw.includes("simulated") ||
          raw.includes("preprod");

        if (dryFlag) {
          setCheckIfNotOverridden("preflight", 0, {
            status: "OK",
            note: "Auto: /status indique un mode simulé / preprod (dry_run).",
          });
        } else {
          setCheckIfNotOverridden("preflight", 0, {
            status: "WARN",
            note: "Auto: /status ne montre pas clairement dry_run/preprod. À vérifier.",
          });
        }
      } else {
        // pas de /status => on laisse TODO
        setCheckIfNotOverridden("preflight", 0, {
          status: "TODO",
          note: "Endpoint /status indisponible (OK en SPA, mais API manquante).",
        });
      }

      // ---- 2) Governance: kill-switch + caps
      const govItem = results.find((x) => x.name === "gov" && x.ok);
      if (govItem?.data) {
        const d = govItem.data;
        const raw = deepString(d);

        const hardBlock =
          (d && typeof d === "object" && (d.hard_block === true || d.hardBlock === true)) ||
          raw.includes("hard_block") ||
          raw.includes("hardblock");

        const softVeto =
          (d && typeof d === "object" && (d.soft_veto || d.softVeto)) ||
          raw.includes("soft_veto") ||
          raw.includes("exit-only") ||
          raw.includes("simulated_only");

        if (hardBlock) {
          setCheckIfNotOverridden("preflight", 1, {
            status: "OK",
            note: "Auto: /governance/status indique hard_block actif.",
          });
        } else if (softVeto) {
          setCheckIfNotOverridden("preflight", 1, {
            status: "WARN",
            note: "Auto: soft_veto détecté mais hard_block non confirmé. À valider (préprod ⇒ idéal hard_block).",
          });
        } else {
          setCheckIfNotOverridden("preflight", 1, {
            status: "WARN",
            note: "Auto: aucun hard_block/soft_veto détecté. À vérifier.",
          });
        }

        const capsDetected =
          raw.includes("max_orders") ||
          raw.includes("max_notional") ||
          raw.includes("notional_cap") ||
          raw.includes("caps");

        setCheckIfNotOverridden("preflight", 2, {
          status: capsDetected ? "OK" : "TODO",
          note: capsDetected
            ? "Auto: caps détectés dans /governance/status."
            : "Auto: caps non détectés (ou non exposés).",
        });
      } else {
        setCheckIfNotOverridden("preflight", 1, {
          status: "TODO",
          note: "Endpoint /governance/status indisponible (on laisse en manuel).",
        });
        setCheckIfNotOverridden("preflight", 2, {
          status: "TODO",
          note: "Caps: endpoint indisponible (manuel).",
        });
      }

      // ---- 3) Backpressure
      const bpItem = results.find((x) => x.name === "bp" && x.ok);
      if (bpItem?.data) {
        const raw = deepString(bpItem.data);
        const seemsOk =
          raw.includes("ok") || raw.includes("healthy") || raw.includes("green");
        setCheckIfNotOverridden("preprod", 3, {
          status: seemsOk ? "OK" : "WARN",
          note: "Auto: /monitoring/backpressure consulté.",
        });
      } else {
        setCheckIfNotOverridden("preprod", 3, {
          status: "TODO",
          note: "Endpoint backpressure indisponible (manuel).",
        });
      }

      setLastRefresh(Date.now());
      setLoading(false);
      recomputePhaseStatuses();
    } catch (e) {
      setErr({ message: String(e?.message || e) });
      setLoading(false);
      recomputePhaseStatuses();
    }
  }

  function onToggleOverride(phaseId, idx, currentEffectiveStatus) {
    const key = `${phaseId}:${idx}`;
    setOverrides((prev) => {
      const next = { ...(prev || {}) };

      // si déjà override => on cycle + possibilité de supprimer quand revient TODO
      const nextStatus = cycleStatus(currentEffectiveStatus);
      if (nextStatus === "TODO") {
        // supprimer override
        delete next[key];
      } else {
        next[key] = { status: nextStatus, note: "Override manuel (localStorage)" };
      }
      return next;
    });

    // Recompute après override
    setTimeout(() => recomputePhaseStatuses(), 0);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Recompute quand overrides changent
  useEffect(() => {
    recomputePhaseStatuses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [overrides]);

  const summary = useMemo(() => {
    const flat = phases.flatMap((p) =>
      p.checks.map((c, idx) => overrides?.[`${p.id}:${idx}`]?.status || c.status)
    );
    if (flat.some((s) => s === "BLOCKED")) return { tone: "bad", text: "BLOCKED — Corriger avant de poursuivre." };
    if (flat.some((s) => s === "WARN")) return { tone: "warn", text: "WARN — Points à valider avant Go." };
    if (flat.some((s) => s === "TODO")) return { tone: "muted", text: "TODO — Checklist incomplète." };
    return { tone: "ok", text: "OK — Tous les checks sont au vert." };
  }, [phases, overrides]);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-50">Go / No-Go</h1>
          <p className="text-sm text-zinc-400">
            Checklist décisionnelle de préproduction (30j) + gates bloquants (auto si endpoints disponibles).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-xs text-zinc-500">
            Last refresh: <span className="text-zinc-300">{nowLabel(lastRefresh)}</span>
          </div>
          <button
            type="button"
            onClick={refresh}
            className="rounded-xl border border-zinc-800 bg-zinc-950/40 px-3 py-2 text-xs text-zinc-200 hover:text-white hover:border-zinc-700 transition"
          >
            Refresh
          </button>
        </div>
      </header>

      <SectionCard title="Résumé">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm text-zinc-300">
            Les statuts sont auto-déduits quand l’API expose des infos (sinon on reste en manuel).
            Clique sur un statut pour activer un <span className="text-zinc-50 font-semibold">override</span> local.
          </div>
          <Pill tone={summary.tone}>{summary.text}</Pill>
        </div>
      </SectionCard>

      <SectionCard title="Phases & checks">
        <DataState
          loading={loading}
          error={err}
          empty={false}
        >
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {phases.map((p) => (
              <PhaseCard
                key={p.id}
                phase={p}
                overrides={overrides}
                onToggleOverride={onToggleOverride}
              />
            ))}
          </div>
        </DataState>
      </SectionCard>
    </div>
  );
}
