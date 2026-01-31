import React from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
// __NSC_CREATEELEMENT_GUARD__

// --- NSC createElement guard (debug undefined components)
if (typeof window !== "undefined" && !window.__NSC_CREATEELEMENT_GUARD__) {
  window.__NSC_CREATEELEMENT_GUARD__ = true;
  const _ce = React.createElement;
  React.createElement = (type, props, ...children) => {
    if (!type) {
      // eslint-disable-next-line no-console
      console.error("[NSC] React.createElement got undefined type", { props, children });
    }
    return _ce(type, props, ...children);
  };
}


// --- NSC debug hook (global runtime errors)
if (typeof window !== "undefined" && !window.__NSC_GLOBAL_ERROR_HOOK__) {
  window.__NSC_GLOBAL_ERROR_HOOK__ = true;
  window.addEventListener("error", (e) => {
    // eslint-disable-next-line no-console
    console.error("[window.error]", e?.error || e?.message || e);
  });
  window.addEventListener("unhandledrejection", (e) => {
    // eslint-disable-next-line no-console
    console.error("[unhandledrejection]", e?.reason || e);
  });
}


class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    this.setState({ info });
    console.error("[ErrorBoundary]", error, info);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    const err = this.state.error;
    const info = this.state.info;

    const message = (err && (err.message || String(err))) || "Unknown error";
    const stack = (err && err.stack) ? String(err.stack) : "";
    const comp = (info && info.componentStack) ? String(info.componentStack) : "";

    return (
      <div style={{ padding: 24, color: "#e4e4e7" }}>
        <div style={{ fontWeight: 800, fontSize: 22, color: "#fca5a5" }}>UI Crash</div>

        <div style={{ marginTop: 12, borderRadius: 16, border: "1px solid rgba(239,68,68,0.35)", background: "rgba(239,68,68,0.12)", padding: 16 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Message</div>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 12, lineHeight: 1.45, margin: 0, color: "rgba(254,226,226,0.95)" }}>
            {message}
          </pre>
        </div>

        {stack ? (
          <div style={{ marginTop: 14, borderRadius: 16, border: "1px solid rgba(63,63,70,1)", background: "rgba(9,9,11,0.6)", padding: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 8, color: "rgba(228,228,231,0.95)" }}>Stack</div>
            <pre style={{ overflow: "auto", fontSize: 12, lineHeight: 1.45, margin: 0, color: "rgba(212,212,216,0.95)" }}>
              {stack}
            </pre>
          </div>
        ) : null}

        {comp ? (
          <div style={{ marginTop: 14, borderRadius: 16, border: "1px solid rgba(63,63,70,1)", background: "rgba(9,9,11,0.6)", padding: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 8, color: "rgba(228,228,231,0.95)" }}>Component stack</div>
            <pre style={{ overflow: "auto", fontSize: 12, lineHeight: 1.45, margin: 0, color: "rgba(212,212,216,0.95)" }}>
              {comp}
            </pre>
          </div>
        ) : null}
      </div>
    );
  }
}


const _App = React.lazy(() => import("./App.jsx"));

const el = document.getElementById("root");

if (!el) {
  console.error("❌ Élément #root introuvable dans index.html");
} else {
  const root = createRoot(el);
  root.render(
    <React.Suspense fallback={<div style={{padding:16,color:"#a1a1aa"}}>Chargement…</div>}>
      <ErrorBoundary><_App /></ErrorBoundary>
    </React.Suspense>
  );
}
