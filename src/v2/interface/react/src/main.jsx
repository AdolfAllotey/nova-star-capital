import React from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";

const el = document.getElementById("root");

if (!el) {
  console.error("❌ Élément #root introuvable dans index.html");
} else {
  const root = createRoot(el);
  root.render(<App />);
}
