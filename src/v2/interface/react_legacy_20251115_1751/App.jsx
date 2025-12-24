import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

// Layout global (header + sidebar + outlet)
import Layout from "./pages/Layout";

// Pages existantes
import Dashboard from "./pages/Dashboard";

// Nouvelle page Top Movers (déjà fournie)
import TopMovers from "./pages/TopMovers";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          {/* Rediriger la racine vers /dashboard */}
          <Route index element={<Navigate to="/dashboard" replace />} />

          {/* Routes principales */}
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/top-movers" element={<TopMovers />} />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
