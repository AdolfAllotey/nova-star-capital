import React from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";

class ErrorBoundary extends React.Component {
  constructor(props){ super(props); this.state = { hasError:false, error:null }; }
  static getDerivedStateFromError(error){ return { hasError:true, error }; }
  componentDidCatch(error, info){ console.error("💥 Frontend ErrorBoundary:", error, info); }
  render(){
    if (this.state.hasError) {
      return (
        <div style={{ padding:24, color:"crimson", fontFamily:"ui-sans-serif, system-ui" }}>
          <h1>💥 Une erreur est survenue dans l’UI</h1>
          <pre style={{ whiteSpace:"pre-wrap" }}>{String(this.state.error)}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);