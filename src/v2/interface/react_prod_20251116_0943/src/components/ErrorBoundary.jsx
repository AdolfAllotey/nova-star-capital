// src/components/ErrorBoundary.jsx
import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(p){ super(p); this.state = { hasError:false, error:null }; }
  static getDerivedStateFromError(error){ return { hasError:true, error }; }
  componentDidCatch(error, info){ console.error("ErrorBoundary:", error, info); }
  render(){
    if(this.state.hasError){
      return (
        <div style={{padding:16, border:"1px solid #3a2a2a", background:"#1b1212", borderRadius:12, color:"#f59e0b"}}>
          <div style={{fontWeight:700, marginBottom:6}}>Un composant a rencontré une erreur</div>
          <div style={{whiteSpace:"pre-wrap", fontSize:12}}>{String(this.state.error?.message||this.state.error)}</div>
        </div>
      );
    }
    return this.props.children;
  }
}
