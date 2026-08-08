import React, { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { getUiLabel } from "../lib/uiVersion";
import { getRuntimeInfo } from "../lib/runtimeInfo";

const ROUTE_TITLES = [
  { match: /^\/dashboard$/, title: "Dashboard" },
  { match: /^\/control-room$/, title: "Control Room" },
  { match: /^\/executive$/, title: "Executive View" },
  { match: /^\/portfolio$/, title: "Portfolio" },
  { match: /^\/risk$/, title: "Risk Overview" },
  { match: /^\/reporting\/pnl$/, title: "PnL Overview" },
  { match: /^\/reporting\/alpha-beta$/, title: "Alpha / Beta" },
  { match: /^\/reporting\/attribution$/, title: "Attribution" },
  { match: /^\/reporting\/profitability$/, title: "Profitability" },
  { match: /^\/reporting\/worst-trades$/, title: "Worst Trades" },
  { match: /^\/reporting\/open-positions$/, title: "Open Positions" },
  { match: /^\/market\/top-movers$/, title: "Top Movers" },
  { match: /^\/market\/regime$/, title: "Market Regime" },
  { match: /^\/signals\/board$/, title: "Signal Board" },
  { match: /^\/order-board$/, title: "Order Board" },
  { match: /^\/positions-board$/, title: "Positions Board" },
  { match: /^\/fills-board$/, title: "Fills Board" },
  { match: /^\/execution-trace$/, title: "Execution Trace" },
  { match: /^\/system-status$/, title: "System Status" },
  { match: /^\/system\/go-no-go$/, title: "Go / No-Go" },
  { match: /^\/settings$/, title: "Settings" },
  { match: /^\/simulation\/live$/, title: "Live Simulation" },
  { match: /^\/intelligence\/sentiment$/, title: "Sentiment" },
  { match: /^\/intelligence\/whales$/, title: "Whales" },
  { match: /^\/ico$/, title: "ICO Dashboard" },
  { match: /^\/ico\/candidates$/, title: "ICO Candidates" },
  { match: /^\/ico\/screened$/, title: "ICO Screened" },
  { match: /^\/ico\/scored$/, title: "ICO Scored" },
  { match: /^\/ico\/allocation$/, title: "ICO Allocation" },
  { match: /^\/bricks\/crypto$/, title: "Crypto" },
  { match: /^\/bricks\/offensive/, title: "Offensive Equities" },
  { match: /^\/bricks\/defensive/, title: "Defensive Equities" },
  { match: /^\/bricks\/bonds$/, title: "Bonds" },
  { match: /^\/bricks\/precious-metals$/, title: "Precious Metals" },
  { match: /^\/bricks\/lt/, title: "Long Term" },
  { match: /^\/bricks\/options/, title: "Options US" },
];

export default function Header() {
  const location = useLocation();
  const [runtime, setRuntime] = useState({
    env: "UNKNOWN",
    apiVersion: "N/A",
  });

  useEffect(() => {
    let cancelled = false;

    async function loadRuntime() {
      const info = await getRuntimeInfo();
      if (!cancelled) {
        setRuntime({
          env: info?.env || "UNKNOWN",
          apiVersion: info?.apiVersion || "N/A",
        });
      }
    }

    loadRuntime();
    return () => {
      cancelled = true;
    };
  }, []);

  const pageTitle = useMemo(() => {
    const pathname = location.pathname || "/dashboard";
    const found = ROUTE_TITLES.find((route) => route.match.test(pathname));
    return found?.title || "Dashboard";
  }, [location.pathname]);

  const envLabel =
    runtime.env === "PREPROD"
      ? "Preproduction"
      : runtime.env === "PROD"
      ? "Production"
      : runtime.env || "Environment";

  return (
    <header className="h-16 border-b border-white/10 bg-zinc-950/80 backdrop-blur px-6 flex items-center justify-between">
      <div className="min-w-0">
        <h1 className="text-[18px] font-semibold text-white truncate">
          Nova Star Capital — {pageTitle}
        </h1>
      </div>

      <div className="ml-6 flex items-center gap-3 text-sm text-zinc-400 whitespace-nowrap">
        <span>{envLabel}</span>
        <span>·</span>
        <span>{getUiLabel()}</span>
        <span>·</span>
        <span>API v{runtime.apiVersion}</span>
      </div>
    </header>
  );
}
