import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { fetchJson } from "../lib/apiClient";


const MANUAL_STORAGE_KEY =
  "nsc_go_no_go_manual_controls_v2";


function formatDate(value) {
  if (!value) return "—";

  try {
    return new Date(value).toLocaleString("fr-FR");
  } catch {
    return String(value);
  }
}


function formatValue(value) {
  if (value === null || value === undefined) {
    return "—";
  }

  if (typeof value === "boolean") {
    return value ? "Oui" : "Non";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}


function loadManualState() {
  try {
    const raw = localStorage.getItem(
      MANUAL_STORAGE_KEY
    );

    if (!raw) return {};

    const parsed = JSON.parse(raw);

    return (
      parsed &&
      typeof parsed === "object" &&
      !Array.isArray(parsed)
    )
      ? parsed
      : {};
  } catch {
    return {};
  }
}


function saveManualState(value) {
  try {
    localStorage.setItem(
      MANUAL_STORAGE_KEY,
      JSON.stringify(value)
    );
  } catch {
    // Browser storage is optional.
  }
}


function statusClasses(status) {
  const normalized = String(
    status || ""
  ).toUpperCase();

  if (
    ["PASS", "OK", "GO", "APPROVED"].includes(
      normalized
    )
  ) {
    return (
      "border-emerald-400/30 " +
      "bg-emerald-400/10 text-emerald-200"
    );
  }

  if (
    ["FAIL", "BLOCKED", "NO_GO"].includes(
      normalized
    )
  ) {
    return (
      "border-red-400/30 " +
      "bg-red-400/10 text-red-200"
    );
  }

  if (normalized === "WARN") {
    return (
      "border-amber-400/30 " +
      "bg-amber-400/10 text-amber-200"
    );
  }

  return (
    "border-slate-500/30 " +
    "bg-slate-500/10 text-slate-300"
  );
}


function StatusBadge({ status }) {
  return (
    <span
      className={
        "inline-flex rounded-full border " +
        "px-2.5 py-1 text-xs font-semibold " +
        statusClasses(status)
      }
    >
      {status || "UNKNOWN"}
    </span>
  );
}


function Card({
  title,
  subtitle,
  children,
  className = "",
}) {
  return (
    <section
      className={
        "rounded-2xl border border-slate-800 " +
        "bg-slate-950/60 p-5 " +
        className
      }
    >
      <div className="mb-4">
        <h2 className="text-base font-semibold text-white">
          {title}
        </h2>

        {subtitle ? (
          <p className="mt-1 text-sm text-slate-400">
            {subtitle}
          </p>
        ) : null}
      </div>

      {children}
    </section>
  );
}


export default function GoNoGo() {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [manualState, setManualState] = useState(
    loadManualState
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    const response = await fetchJson(
      "/api/system/go-no-go",
      {
        timeoutMs: 12000,
      }
    );

    if (!response?.ok) {
      setPayload(null);
      setError(
        response?.error?.detail ||
        response?.error?.message ||
        "Impossible de charger le statut Go / No-Go."
      );
      setLoading(false);
      return;
    }

    setPayload(response.data || null);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    saveManualState(manualState);
  }, [manualState]);

  const automaticChecks = useMemo(
    () => (
      Array.isArray(payload?.automatic_checks)
        ? payload.automatic_checks
        : []
    ),
    [payload]
  );

  const manualControls = useMemo(
    () => (
      Array.isArray(payload?.manual_controls)
        ? payload.manual_controls
        : []
    ),
    [payload]
  );

  const sources = useMemo(
    () => (
      Array.isArray(payload?.sources)
        ? payload.sources
        : []
    ),
    [payload]
  );

  const manualSummary = useMemo(() => {
    const statuses = manualControls.map(
      (control) => (
        manualState?.[control.id] || "TODO"
      )
    );

    return {
      total: statuses.length,
      ok: statuses.filter(
        (status) => status === "OK"
      ).length,
      warnings: statuses.filter(
        (status) => status === "WARN"
      ).length,
      blocked: statuses.filter(
        (status) => status === "BLOCKED"
      ).length,
    };
  }, [manualControls, manualState]);

  function cycleManualStatus(controlId) {
    const current =
      manualState?.[controlId] || "TODO";

    const next = (
      current === "TODO"
        ? "OK"
        : current === "OK"
          ? "WARN"
          : current === "WARN"
            ? "BLOCKED"
            : "TODO"
    );

    setManualState((previous) => ({
      ...previous,
      [controlId]: next,
    }));
  }

  const institutional =
    payload?.institutional_state || {};

  const isAutomaticGo =
    payload?.automatic_pass === true;

  return (
    <div className="space-y-6 p-4 md:p-6">
      <header
        className={
          "rounded-2xl border p-5 " +
          (
            isAutomaticGo
              ? "border-emerald-400/30 bg-emerald-400/10"
              : "border-red-400/30 bg-red-400/10"
          )
        }
      >
        <div
          className={
            "flex flex-col gap-4 " +
            "lg:flex-row lg:items-center " +
            "lg:justify-between"
          }
        >
          <div>
            <p
              className={
                "text-xs font-semibold uppercase " +
                "tracking-[0.2em] text-slate-400"
              }
            >
              Institutional release control
            </p>

            <h1 className="mt-2 text-2xl font-semibold text-white">
              Go / No-Go
            </h1>

            <p className="mt-2 text-sm text-slate-300">
              Décision automatique issue des artefacts
              institutionnels NSC. Les contrôles manuels ne
              peuvent pas modifier cette décision.
            </p>
          </div>

          <div className="flex flex-col items-start gap-2 lg:items-end">
            <StatusBadge
              status={
                payload?.automatic_decision ||
                "UNKNOWN"
              }
            />

            <span className="text-xs text-slate-400">
              Actualisé le{" "}
              {formatDate(payload?.generated_at)}
            </span>

            <button
              type="button"
              onClick={refresh}
              disabled={loading}
              className={
                "rounded-lg border border-slate-700 " +
                "bg-slate-900 px-3 py-2 text-sm " +
                "text-slate-200 hover:border-cyan-400/50 " +
                "disabled:opacity-50"
              }
            >
              {loading
                ? "Actualisation…"
                : "Actualiser"}
            </button>
          </div>
        </div>
      </header>

      {error ? (
        <div
          className={
            "rounded-xl border border-red-400/30 " +
            "bg-red-400/10 p-4 text-sm text-red-200"
          }
        >
          {String(error)}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="RC1">
          <div className="text-2xl font-semibold text-white">
            {institutional.rc1_release || "—"}
          </div>

          <div className="mt-2">
            <StatusBadge
              status={
                institutional.rc1_release_decision
              }
            />
          </div>
        </Card>

        <Card title="Readiness">
          <div className="text-2xl font-semibold text-white">
            {
              institutional
                .production_readiness_score ?? "—"
            }
            %
          </div>

          <div className="mt-2">
            <StatusBadge
              status={
                institutional
                  .production_readiness_decision
              }
            />
          </div>
        </Card>

        <Card title="Supervision gate">
          <div className="text-2xl font-semibold text-white">
            {
              institutional.supervision_gate_open
                ? "OPEN"
                : "CLOSED"
            }
          </div>

          <p className="mt-2 text-sm text-slate-400">
            Mode{" "}
            {institutional.supervision_gate_mode || "—"}
          </p>
        </Card>

        <Card title="Execution policy">
          <div className="text-sm text-slate-300">
            Réelle :{" "}
            <strong>
              {
                institutional.real_execution_allowed
                  ? "autorisée"
                  : "interdite"
              }
            </strong>
          </div>

          <div className="mt-2 text-sm text-slate-300">
            Simulée :{" "}
            <strong>
              {
                institutional
                  .simulated_execution_allowed
                  ? "autorisée"
                  : "interdite"
              }
            </strong>
          </div>
        </Card>
      </div>

      <Card
        title="Contrôles automatiques"
        subtitle={
          `${payload?.automatic_pass_count || 0}/` +
          `${payload?.automatic_check_count || 0} PASS`
        }
      >
        <div className="space-y-3">
          {automaticChecks.map((check) => (
            <div
              key={check.id}
              className={
                "flex flex-col gap-3 rounded-xl " +
                "border border-slate-800 bg-slate-900/40 " +
                "p-4 lg:flex-row lg:items-start " +
                "lg:justify-between"
              }
            >
              <div className="min-w-0">
                <div className="font-medium text-slate-100">
                  {check.label}
                </div>

                <div
                  className={
                    "mt-1 break-all font-mono " +
                    "text-xs text-slate-500"
                  }
                >
                  {formatValue(check.value)}
                </div>

                <div className="mt-1 text-xs text-slate-600">
                  {check.source}
                </div>
              </div>

              <StatusBadge status={check.status} />
            </div>
          ))}

          {!automaticChecks.length && !loading ? (
            <div className="text-sm text-slate-400">
              Aucun contrôle automatique disponible.
            </div>
          ) : null}
        </div>
      </Card>

      <Card
        title="Contrôles manuels"
        subtitle={
          "Ces validations sont locales au navigateur et " +
          "n’altèrent jamais la décision institutionnelle."
        }
      >
        <div
          className={
            "mb-4 flex flex-wrap gap-3 text-xs text-slate-400"
          }
        >
          <span>
            OK {manualSummary.ok}/{manualSummary.total}
          </span>
          <span>WARN {manualSummary.warnings}</span>
          <span>BLOCKED {manualSummary.blocked}</span>
        </div>

        <div className="space-y-3">
          {manualControls.map((control) => {
            const current =
              manualState?.[control.id] || "TODO";

            return (
              <div
                key={control.id}
                className={
                  "flex flex-col gap-3 rounded-xl " +
                  "border border-slate-800 " +
                  "bg-slate-900/40 p-4 " +
                  "lg:flex-row lg:items-center " +
                  "lg:justify-between"
                }
              >
                <div>
                  <div className="font-medium text-slate-100">
                    {control.label}
                  </div>

                  <div className="mt-1 text-sm text-slate-400">
                    {control.description}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => (
                    cycleManualStatus(control.id)
                  )}
                  title={
                    "Cycle manuel : TODO → OK → WARN → " +
                    "BLOCKED"
                  }
                  className="shrink-0"
                >
                  <StatusBadge status={current} />
                </button>
              </div>
            );
          })}
        </div>
      </Card>

      <Card
        title="Sources institutionnelles"
        subtitle="Lineage exact de la décision automatique."
      >
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-slate-500">
                <th className="px-3 py-2">Source</th>
                <th className="px-3 py-2">Engine</th>
                <th className="px-3 py-2">Âge</th>
                <th className="px-3 py-2">Généré</th>
              </tr>
            </thead>

            <tbody>
              {sources.map((source) => (
                <tr
                  key={source.name}
                  className="border-b border-slate-900"
                >
                  <td className="px-3 py-3 text-slate-200">
                    <div>{source.name}</div>
                    <div
                      className={
                        "mt-1 max-w-xl break-all " +
                        "font-mono text-xs text-slate-600"
                      }
                    >
                      {source.path}
                    </div>
                  </td>

                  <td className="px-3 py-3 text-slate-400">
                    {source.engine || "—"}
                  </td>

                  <td className="px-3 py-3 text-slate-400">
                    {
                      source.age_seconds === null ||
                      source.age_seconds === undefined
                        ? "—"
                        : `${Math.round(
                            source.age_seconds / 60
                          )} min`
                    }
                  </td>

                  <td className="px-3 py-3 text-slate-400">
                    {formatDate(source.generated_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title="Dette non bloquante acceptée"
        subtitle={
          "Éléments officiellement reportés au hardening " +
          "RC2 ou à la production readiness."
        }
      >
        <ul className="space-y-2 text-sm text-slate-300">
          {Array.isArray(
            institutional.accepted_non_blocking_debt
          ) &&
          institutional.accepted_non_blocking_debt.length
            ? institutional.accepted_non_blocking_debt.map(
                (item, index) => (
                  <li
                    key={`${index}-${item}`}
                    className="flex gap-2"
                  >
                    <span className="text-amber-300">
                      •
                    </span>
                    <span>{item}</span>
                  </li>
                )
              )
            : (
              <li className="text-slate-500">
                Aucune dette non bloquante déclarée.
              </li>
            )}
        </ul>
      </Card>
    </div>
  );
}
