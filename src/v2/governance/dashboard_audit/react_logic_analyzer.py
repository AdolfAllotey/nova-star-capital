import re

BUSINESS_KEYWORDS = re.compile(
    r'(score|risk|confidence|exposure|allocation|pnl|PnL|weights|freshness|portfolio|orders|positions)',
    re.IGNORECASE,
)

VISUAL_OR_FORMATTING = [
    "pct(",
    "getBrickConfidence(",
    "style={{ width:",
    "Math.max(0, Math.min(100",
    "toFixed(",
    "Math.round(",
    "allocationRows.reduce",
    "positions.reduce",
    "equityCurve",
    "active_pnl_eur",
    "unrealized_pnl_eur",
    "total_pnl_eur",
    "total_pnl_including_shadow_eur",
    "fillRatio",
    "ordersExecuted",
    "global?.confidencePct",
    "confidenceDelta",
    "row.total_pnl_eur",
    "row.total_pnl_including_shadow_eur",
    "pnlGross",
    "pnlNet",
    "costs",
    "pnlGrossFromSummary",
    "costsFromSummary",
    "netFromSummary",
    "margin",
    "costRatio",
    "positions.filter",
    "asset_class",
    "\"active_pnl_eur\" in row",
    "\"unrealized_pnl_eur\" in row",
]

def scan(text: str):
    business = {}
    visual = {}

    lines = text.splitlines()

    for line in lines:
        stripped = line.strip()

        if ".map(" in stripped:
            visual["map_rendering"] = visual.get("map_rendering", 0) + 1

        if ".reduce(" in stripped:
            if BUSINESS_KEYWORDS.search(stripped) and not any(x in stripped for x in VISUAL_OR_FORMATTING):
                business["business_reduce"] = business.get("business_reduce", 0) + 1
            else:
                visual["generic_reduce"] = visual.get("generic_reduce", 0) + 1

        if "* 100" in stripped or "/ 100" in stripped:
            if BUSINESS_KEYWORDS.search(stripped) and not any(x in stripped for x in VISUAL_OR_FORMATTING):
                business["business_percentage_calc"] = business.get("business_percentage_calc", 0) + 1
            else:
                visual["generic_percentage_calc"] = visual.get("generic_percentage_calc", 0) + 1

        if ".filter(" in stripped:
            if BUSINESS_KEYWORDS.search(stripped) and not any(x in stripped for x in VISUAL_OR_FORMATTING):
                business["business_filter"] = business.get("business_filter", 0) + 1
            else:
                visual["generic_filter"] = visual.get("generic_filter", 0) + 1

    return business, visual
