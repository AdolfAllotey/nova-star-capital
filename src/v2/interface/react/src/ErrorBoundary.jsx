// src/ErrorBoundary.jsx
import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { err: null };
  }
  static getDerivedStateFromError(error) {
    return { err: error };
  }
  componentDidCatch(error, info) {
    console.error("[UI] ErrorBoundary caught:", error, info);
  }
  render() {
    if (this.state.err) {
      return (
        <div style={{ padding: 16, color: "#eab308", fontFamily: "ui-sans-serif, system-ui" }}>
          <h1 style={{ margin: 0, fontSize: 18 }}>Erreur UI capturée</h1>
          <pre style={{ whiteSpace: "pre-wrap" }}>{String(this.state.err)}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}
