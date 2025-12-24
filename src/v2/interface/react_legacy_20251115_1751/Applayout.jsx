import { Link, Outlet, useLocation } from "react-router-dom";

export default function AppLayout() {
  const location = useLocation();
  const current = location.pathname;

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-white shadow p-4">
        <h2 className="text-xl font-bold mb-6 text-green-600">Nova Star Capital</h2>
        <nav className="space-y-2">
          <Link to="/" className={current === "/" ? activeClass : baseClass}>📊 Dashboard</Link>
          <Link to="/insights" className={current === "/insights" ? activeClass : baseClass}>🧠 Insights</Link>
          <Link to="/settings" className={current === "/settings" ? activeClass : baseClass}>⚙️ Settings</Link>
        </nav>
      </div>

      {/* Main content */}
      <div className="flex-1 p-6 overflow-auto">
        <header className="text-2xl font-semibold mb-4">📡 Crypto Bot Interface (V2)</header>
        <Outlet />
      </div>
    </div>
  );
}

const baseClass = "block py-2 px-3 rounded hover:bg-gray-200";
const activeClass = "block py-2 px-3 rounded bg-green-200 text-green-800 font-semibold";