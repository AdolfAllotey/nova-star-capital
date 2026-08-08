
const normalizeRegime = (r) => {
  if (!r) return "UNKNOWN";
  const v = r.toLowerCase();
  if (v === "risk_on") return "BULL";
  if (v === "risk_off") return "BEAR";
  if (v === "neutral") return "NEUTRAL";
  return "UNKNOWN";
};
import React from "react";
import StatusBadge from "../ui/StatusBadge";

export default function GlobalHeaderBar({ data }) {
  return (
    <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-4 mb-6">
      <div>
        <h1 className="text-2xl font-semibold">NSC Control Center</h1>
        <div className="text-sm text-gray-400 mt-1">
          Last refresh: {data.lastRefresh || "—"}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <StatusBadge label={data.env || "N/A"} />
        <StatusBadge label={data.apiStatus || "N/A"} />
        <StatusBadge label={normalizeRegime(data.regime) || "N/A"} />
        <StatusBadge label={data.governanceMode || "N/A"} />
      </div>
    </div>
  );
}
