// src/pages/IcoDashboard.jsx
// Dashboard ICO (status + counts + quick preview)

import React, { useEffect, useMemo, useState } from "react";
import { NavLink } from "react-router-dom";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://api.preprod.novastarcapital.fr";

function buildUrl(path) {
  return `${API_BASE.replace(/\/+$/, "")}${path}`;
}

function cls(...parts) {
  return parts.filter(Boolean).join(" ");
}

function Section({ title, right, children }) {
  return (
    <section className="mb-8">
      <div className="flex items-end justify-between gap-3 mb-3 border-b border-zinc-800 pb-2">
        <h2 className="text-lg font-semibold text-zinc-100">{title}</h2>
        {right ? <div className="text-xs text-zinc-500">{right}</div> : null}
      </div>

      <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4">
        {children}
      </div>
    </section>
  );
}

function Metric({ label, value, hint }) {
  return (
    <div className="flex flex-col bg-zinc-800/40 rounded-lg p-3 border border-zinc-700/40">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className="text-lg font-semibold text-zinc-100">{value ?? "—"}</span>
      {hint ? <span className="text-[11px] text-zinc-500 mt-1">{hint}</span> : null}
    </div>
  );
}

function Badge({ ok }) {
  return (
    <span
      className={cls(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
        ok
          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
          : "border-red-500/30 bg-red-500/10 text-red-200"
      )}
    >
      {ok ? "OK" : "NOT OK"}
    </span>
  );
}

function LinkPill({ to, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cls(
          "inline-flex items-center rounded-full border px-3 py-1 text-xs transition-colors",
          isActive
            ? "border-zinc-700 bg-zinc-900 text-zinc-50"
            : "border-zinc-800 bg-zinc-950/20 text-zinc-300 hover:text-white hover:bg-zinc-900/60"
        )
      }
    >
      {children}
    </NavLink>
  );
}

export default function IcoDashboard() {
  const [status, setStatus] = useState(null);
  const [cand, setCand] = useState([]);
  const [screened, setScreened] = useState([]);
  const [scored, setScored] = useState([]);
  const [alloc, setAlloc] = useState([]);

  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const updatedHint = useMemo(() => {
    const u = status?.updated_at || status?.generated_at;
    return u ? `Dernière mise à jour: ${u}` : "";
  }, [status]);

  async function loadAll() {
    try {
      setLoading(true);
      setErr("");

      const urls = [
        buildUrl("/ico/status"),
        buildUrl("/ico/candidates"),
        buildUrl("/ico/screened"),
        buildUrl("/ico/scored"),
        buildUrl("/ico/allocation"),
      ];

      const [s, c1, c2, c3, c4] = await Promise.all(
        urls.map((u) =>
          fetch(u)
            .then((r) => r.json())
            .catch(() => null)
        )
      );

      setStatus(s && typeof s === "object" ? s : null);

      setCand(Array.isArray(c1?.items) ? c1.items : (Array.isArray(c1) ? c1 : []));
      setScreened(Array.isArray(c2?.items) ? c2.items : (Array.isArray(c2) ? c2 : []));
      setScored(Array.isArray(c3?.items) ? c3.items : (Array.isArray(c3) ? c3 : []));
      setAlloc(Array.isArray(c4?.items) ? c4.items : (Array.isArray(c4) ? c4 : []));
    } catch (e) {
      setErr(String(e?.message || e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  if (loading) {
    return <div className="text-zinc-400 text-sm">Chargement des données ICO…</div>;
  }

  if (err) {
    return (
      <div className="space-y-3">
        <div className="text-red-200 text-sm">Erreur: {err}</div>
        <button
          onClick={loadAll}
          className="inline-flex items-center rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-sm text-zinc-100 hover:bg-zinc-900"
        >
          Réessayer
        </button>
      </div>
    );
  }

  const counts = status?.counts || {};
  const ok = Boolean(status?.ok);

  return (
    <div className="space-y-8">
      <Section
        title="ICO — Status"
        right={updatedHint}
      >
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <Badge ok={ok} />
            <span className="text-xs text-zinc-500">
              Endpoint: <span className="text-zinc-300">/ico/status</span>
            </span>
          </div>

          <div className="flex gap-2 flex-wrap justify-end">
            <LinkPill to="/bricks/crypto/ico">Dashboard</LinkPill>
            <LinkPill to="/bricks/crypto/ico/candidates">Candidates</LinkPill>
            <LinkPill to="/bricks/crypto/ico/screened">Screened</LinkPill>
            <LinkPill to="/bricks/crypto/ico/scored">Scored</LinkPill>
            <LinkPill to="/bricks/crypto/ico/allocation">Allocation</LinkPill>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Metric label="Candidats" value={counts.candidates ?? cand.length} />
          <Metric label="Screened" value={counts.screened ?? screened.length} />
          <Metric label="Scorés" value={counts.scored ?? scored.length} />
          <Metric label="Allocations" value={counts.allocation ?? alloc.length} />
        </div>

        {Array.isArray(status?.notes) && status.notes.length > 0 ? (
          <div className="mt-4 text-sm text-amber-200 border border-amber-500/20 bg-amber-500/10 rounded-xl p-3">
            <div className="font-semibold mb-1">Notes</div>
            <ul className="list-disc ml-5 text-amber-100/90">
              {status.notes.map((n, i) => <li key={i}>{String(n)}</li>)}
            </ul>
          </div>
        ) : null}
      </Section>

      <Section title="Derniers projets scorés">
        {scored.length === 0 ? (
          <div className="text-zinc-500 text-sm">Aucun score disponible.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400">
                <th className="py-2 text-left">Nom</th>
                <th className="py-2 text-left">Symbole</th>
                <th className="py-2 text-right">Score</th>
              </tr>
            </thead>
            <tbody>
              {scored.slice(0, 8).map((p, idx) => (
                <tr key={idx} className="border-b border-zinc-800/60 hover:bg-zinc-800/40">
                  <td className="py-2 text-zinc-100">{p.name || "N/A"}</td>
                  <td className="py-2 text-zinc-400">{p.symbol ? p.symbol.toUpperCase() : "—"}</td>
                  <td className="py-2 text-right font-semibold text-zinc-100">{p.score ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Derniers projets filtrés">
        {screened.length === 0 ? (
          <div className="text-zinc-500 text-sm">Aucun projet filtré pour le moment.</div>
        ) : (
          <ul className="space-y-2">
            {screened.slice(0, 8).map((p, idx) => (
              <li key={idx} className="text-zinc-300">
                • {p.name || "N/A"}{" "}
                <span className="text-zinc-500">
                  ({p.symbol ? p.symbol.toUpperCase() : "—"})
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
