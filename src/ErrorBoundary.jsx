import React from "react"

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error("🧱 ErrorBoundary caught:", error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, fontFamily: "sans-serif" }}>
          <h2>⚠️ Une erreur est survenue</h2>
          <p>Merci de recharger la page ou de signaler ce bug.</p>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              background: "#fee",
              color: "#b00",
              padding: 12,
              borderRadius: 8,
            }}
          >
            {String(this.state.error)}
          </pre>
        </div>
      )
    }

    return this.props.children
  }
}
