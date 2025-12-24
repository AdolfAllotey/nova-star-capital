import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App.jsx";

import Dashboard from "./pages/Dashboard.jsx";
import Trades from "./pages/Trades.jsx";
import Positions from "./pages/Positions.jsx";
import Whales from "./pages/Whales.jsx";
import Reports from "./pages/Reports.jsx";
import Status from "./pages/Status.jsx";

import "./index.css"; // Tailwind

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<App />}>
          <Route index element={<Dashboard />} />
          <Route path="/trades" element={<Trades />} />
          <Route path="/positions" element={<Positions />} />
          <Route path="/whales" element={<Whales />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/status" element={<Status />} />
          <Route path="*" element={<Dashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
