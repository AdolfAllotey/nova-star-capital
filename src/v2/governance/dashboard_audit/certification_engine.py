def score_page(item):
    business_hard = sum(item["business_hardcode_findings"].values())
    business_calc = sum(item["business_react_logic_findings"].values())
    has_source = bool(item["api_calls"] or item["json_refs"])

    score = 100
    score -= min(35, business_hard * 8)
    score -= min(25, business_calc * 5)
    if not has_source:
        score -= 25
    if item["criticality"] == "A" and not has_source:
        score -= 10

    score = max(0, int(score))

    if score >= 95:
        level = "GOLD"
    elif score >= 85:
        level = "SILVER"
    elif score >= 70:
        level = "BRONZE"
    else:
        level = "RED"

    status = {
        "GOLD": "CERTIFIABLE",
        "SILVER": "REVIEW_REQUIRED",
        "BRONZE": "REMEDIATION_REQUIRED",
        "RED": "NOT_CERTIFIABLE",
    }[level]

    return score, level, status
