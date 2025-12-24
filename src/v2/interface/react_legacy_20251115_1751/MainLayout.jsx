// src/v2/interface/react/layout/MainLayout.jsx
import React, { useMemo } from "react";
import { Outlet, NavLink, useLocation } from "react-router-dom";

// ⚠️ Assure-toi d'avoir le fichier public/assets/logo-300.png
// (ou adapte le chemin ci-dessous si tu utilises une autre taille)
const LOGO_SRC = "/assets/logo-300.png";

const MainLayout = () => {
  const location = useLocation();

  // Déclare ici toutes les pages que tu veux voir dans la nav
  const NAV_ITEMS = useMemo(
    () => [
      { label: "Dashboard", path: "/" },
      { label: "Home", path: "/home" },
      { label: "P&L", path: "/pnl" },
      { label: "Rentabilité", path: "/profitability" },
      { label: "Portefeuille", path: "/portfolio" },
      { label: "Meilleurs trades", path: "/best-trades" },
      { label: "Pires trades", path: "/worst-trades" },
      { label: "Insights", path: "/insights" },
      { label: "KOLs", path: "/kols" },
      { label: "Airdrops", path: "/airdrops" },
      { label: "Backtests", path: "/backtests" },
      { label: "Simulation Live", path: "/live-simulation" },
      { label: "Rejouer un trade", path: "/trade-replay" },
      { label: "Cost Tracker", path: "/cost-tracker" },
      { label: "Paramètres", path: "/settings" },
      { label: "À propos", path: "/about" },
    ],
    []
  );

  return (
    <div style={{ minHeight: "100dvh", display: "flex", flexDirection: "column" }}>
      {/* Header avec logo */}
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          background: "#0b1220",
          color: "white",
          borderBottom: "1px solid rgba(255,255,255,0.1)",
        }}
      >
        <div
          style={{
            maxWidth: 1200,
            margin: "0 auto",
            padding: "12px 16px",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <img
            src={LOGO_SRC}
            alt="Nova Star Capital"
            width={36}
            height={36}
            style={{ display: "block", borderRadius: 8 }}
          />
          <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1 }}>
            <strong style={{ fontSize: 18 }}>Nova Star Capital</strong>
            <span style={{ fontSize: 12, opacity: 0.8 }}>
              Trading Intelligence Suite
            </span>
          </div>
        </div>

        {/* Nav horizontale */}
        <nav
          style={{
            borderTop: "1px solid rgba(255,255,255,0.08)",
            background: "#0e1629",
          }}
        >
          <div
            style={{
              maxWidth: 1200,
              margin: "0 auto",
              padding: "8px 12px",
              display: "flex",
              gap: 8,
              flexWrap: "wrap",
            }}
          >
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                style={({ isActive }) => ({
                  padding: "8px 12px",
                  borderRadius: 8,
                  textDecoration: "none",
                  fontSize: 14,
                  color: isActive ? "#0b1220" : "white",
                  background: isActive ? "white" : "transparent",
                  border: "1px solid rgba(255,255,255,0.12)",
                })}
                title={item.label}
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>

      {/* Contenu des pages */}
      <main
        style={{
          flex: 1,
          background: "#0a0f1a",
          color: "white",
        }}
      >
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "20px 16px" }}>
          <Outlet />
        </div>
      </main>

      {/* Footer simple */}
      <footer
        style={{
          borderTop: "1px solid rgba(255,255,255,0.08)",
          background: "#0b1220",
          color: "rgba(255,255,255,0.7)",
        }}
      >
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "12px 16px" }}>
          © {new Date().getFullYear()} Nova Star Capital — Tous droits réservés.
        </div>
      </footer>
    </div>
  );
};

export default MainLayout;