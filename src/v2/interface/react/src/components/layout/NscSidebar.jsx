import React, { useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  BookOpen,
  Briefcase,
  Building2,
  CircleCheck,
  Gauge,
  Home,
  Layers,
  LineChart,
  ServerCog,
  ShieldCheck,
  Target,
  Wallet
} from "lucide-react";

function SidebarItem({ icon: Icon, label, path }) {
  const location = useLocation();
  const active = path && (location.pathname === path || location.pathname.startsWith(`${path}/`));

  const content = (
    <div
      className={`flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-xs transition-all ${
        active
          ? "bg-[#16213a] text-white shadow-[inset_3px_0_0_#3b82f6]"
          : "text-slate-300 hover:bg-[#111827]"
      }`}
    >
      <Icon className="h-4 w-4" />
      <span>{label}</span>
    </div>
  );

  return path ? <Link to={path}>{content}</Link> : content;
}

function SidebarSection({ title, children }) {
  return (
    <div className="mt-5">
      <div className="mb-2 px-3 text-[9px] uppercase tracking-widest text-slate-500">
        {title}
      </div>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

export default function NscSidebar({ footerText = "All systems operational" }) {
  const scrollRef = useRef(null);
  const location = useLocation();

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    const saved = sessionStorage.getItem("nsc_sidebar_scroll");
    if (saved) el.scrollTop = Number(saved) || 0;

    const onScroll = () => {
      sessionStorage.setItem("nsc_sidebar_scroll", String(el.scrollTop || 0));
    };

    el.addEventListener("scroll", onScroll);
    return () => el.removeEventListener("scroll", onScroll);
  }, [location.pathname]);

  return (
    <aside className="fixed left-0 top-0 z-20 flex h-screen w-[235px] flex-col border-r border-[#1a2533] bg-[#05080d] px-4 py-5">
      <div className="flex min-w-0 items-center gap-2">
        <svg
          viewBox="0 0 120 120"
          className="h-14 w-14 shrink-0 text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.22)]"
          aria-hidden="true"
        >
          <g fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
            <path
              d="
                M60 6
                L68 46
                L99 21
                L74 52
                L114 60
                L74 68
                L99 99
                L68 74
                L60 114
                L52 74
                L21 99
                L46 68
                L6 60
                L46 52
                L21 21
                L52 46
                Z
              "
              strokeWidth="2.2"
              fill="rgba(255,255,255,0.04)"
            />

            <path d="M60 6 L60 114" strokeWidth="1.4" opacity="0.8" />
            <path d="M6 60 L114 60" strokeWidth="1.4" opacity="0.8" />
            <path d="M21 21 L99 99" strokeWidth="1.2" opacity="0.55" />
            <path d="M99 21 L21 99" strokeWidth="1.2" opacity="0.55" />

            <path d="M60 6 L68 46 L60 60 L52 46 Z" strokeWidth="1.2" opacity="0.85" />
            <path d="M114 60 L74 68 L60 60 L74 52 Z" strokeWidth="1.2" opacity="0.85" />
            <path d="M60 114 L52 74 L60 60 L68 74 Z" strokeWidth="1.2" opacity="0.85" />
            <path d="M6 60 L46 52 L60 60 L46 68 Z" strokeWidth="1.2" opacity="0.85" />

            <circle cx="60" cy="60" r="7" strokeWidth="1.4" />
            <circle cx="60" cy="60" r="26" strokeWidth="1" opacity="0.45" />
          </g>
        </svg>

        <div className="leading-[1.05]">
          <div className="whitespace-nowrap text-[19px] font-bold tracking-[0.20em] text-white">
            NOVA STAR
          </div>
          <div className="mt-2 whitespace-nowrap text-[18px] font-light tracking-[0.24em] text-white">
            CAPITAL
          </div>
        </div>
      </div>

      <div ref={scrollRef} className="mt-5 flex-1 overflow-y-auto pr-1 [scrollbar-width:thin] [scrollbar-color:#334155_transparent]">
        <SidebarSection title="Global">
          <SidebarItem icon={Home} label="Dashboard" path="/dashboard" />
          <SidebarItem icon={Building2} label="Family Office" path="/family-office" />
          <SidebarItem icon={Activity} label="Executive" path="/executive" />
          <SidebarItem icon={Brain} label="Market Intelligence" path="/market/intelligence" />
          <SidebarItem icon={Target} label="Executive Decision" path="/executive-decision" />
          <SidebarItem icon={BookOpen} label="Documentation" path="/documentation-center" />
          <SidebarItem icon={Gauge} label="Control Room" path="/control-room" />
        </SidebarSection>

        <SidebarSection title="Portfolio">
          <SidebarItem icon={Briefcase} label="Portfolio" path="/portfolio" />
          <SidebarItem icon={Wallet} label="Funding Pools" path="/funding-pools" />
          <SidebarItem icon={Layers} label="Allocation / Rebalance" path="/allocation-rebalance" />
          <SidebarItem icon={CircleCheck} label="Long Term" path="/bricks/lt" />
        </SidebarSection>

        <SidebarSection title="Risk">
          <SidebarItem icon={ShieldCheck} label="Risk Console" path="/risk" />
          <SidebarItem icon={ShieldCheck} label="Protection" path="/protection" />
          <SidebarItem icon={ServerCog} label="Governance" path="/governance" />
          <SidebarItem icon={AlertTriangle} label="Anomalies" path="/anomalies" />
        </SidebarSection>

        <SidebarSection title="Execution">
          <SidebarItem icon={Activity} label="Order Board" path="/order-board" />
          <SidebarItem icon={Briefcase} label="Positions Board" path="/positions-board" />
          <SidebarItem icon={CircleCheck} label="Fills Board" path="/fills-board" />
          <SidebarItem icon={ServerCog} label="Execution Trace" path="/execution-trace" />
        </SidebarSection>

        <SidebarSection title="Performance">
          <SidebarItem icon={BarChart3} label="PnL" path="/reporting/pnl" />
          <SidebarItem icon={LineChart} label="Alpha / Beta" path="/reporting/alpha-beta" />
          <SidebarItem icon={Target} label="Profitability" path="/reporting/profitability" />
          <SidebarItem icon={Briefcase} label="Trade Journal" path="/reporting/trade-journal" />
          <SidebarItem icon={AlertTriangle} label="Worst Trades" path="/reporting/worst-trades" />
        </SidebarSection>

        <SidebarSection title="Intelligence">
          <SidebarItem icon={Brain} label="Explainability" path="/explainability" />
          <SidebarItem icon={Activity} label="Signals" path="/signals/board" />
          <SidebarItem icon={Gauge} label="Market Regime" path="/market/regime" />
          <SidebarItem icon={BarChart3} label="Top Movers" path="/market/top-movers" />
        </SidebarSection>
      </div>

      <div className="mt-3 shrink-0 rounded-lg border border-[#1f2a37] bg-[#0b131d] px-3 py-2">
        <div className="grid grid-cols-[1.5fr_1fr_1fr] items-center text-xs font-medium">
          <span>NSC Engine</span>
          <span className="text-[9px] text-emerald-400">● RUNNING</span>
        </div>
        <div className="mt-1 text-[9px] text-slate-500">{footerText}</div>
      </div>
    </aside>
  );
}