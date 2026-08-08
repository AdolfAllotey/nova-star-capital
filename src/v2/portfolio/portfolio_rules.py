BRICK_TO_FAMILY = {
    "crypto": "offensive",
    "equities_offensive": "offensive",
    "equities_defensive": "stabilization",
    "bonds": "macro_defensive",
    "precious_metals": "systemic_hedge",
    "options_us": "options_overlay",
}

REGIME_FAMILY_CAPS = {
    "risk_on": {
        "offensive": 0.65,
        "stabilization": 0.20,
        "macro_defensive": 0.20,
        "systemic_hedge": 0.10,
        "options_overlay": 0.05,
    },
    "balanced": {
        "offensive": 0.50,
        "stabilization": 0.25,
        "macro_defensive": 0.30,
        "systemic_hedge": 0.15,
        "options_overlay": 0.05,
    },
    "risk_off": {
        "offensive": 0.30,
        "stabilization": 0.25,
        "macro_defensive": 0.40,
        "systemic_hedge": 0.20,
        "options_overlay": 0.05,
    },
}


def get_family_for_brick(brick: str) -> str:
    return BRICK_TO_FAMILY.get(brick, "unknown")


def get_caps_for_regime(regime: str) -> dict:
    return REGIME_FAMILY_CAPS.get(regime, REGIME_FAMILY_CAPS["balanced"])
