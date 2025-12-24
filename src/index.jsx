import React from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import App from "./App.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Status from "./pages/Status.jsx";

// pages à créer
const Trades = React.lazy(() => import("./pages/Trades.jsx"));
const Positions = React.lazy(() => import("./pages/Positions.jsx"));
const Whales = React.lazy(() => import("./pages/Whales.jsx"));
const Reports = React.lazy(() => import("./pages/Reports.jsx"));

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "status", element: <Status /> },
      { path: "trades", element: <React.Suspense><Trades /></React.Suspense> },
      { path: "positions", element: <React.Suspense><Positions /></React.Suspense> },
      { path: "whales", element: <React.Suspense><Whales /></React.Suspense> },
      { path: "reports", element: <React.Suspense><Reports /></React.Suspense> },
    ],
  },
]);

createRoot(document.getElementById("root")).render(<RouterProvider router={router} />);
