from __future__ import annotations

from dataclasses import asdict, dataclass
from math import erf, exp, log, pi, sqrt
from typing import Any


SQRT_TWO = sqrt(2.0)
SQRT_TWO_PI = sqrt(2.0 * pi)


@dataclass(frozen=True)
class OptionGreeksV3:
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    greeks_model: str
    greeks_valid: bool
    invalid_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / SQRT_TWO))


def _normal_pdf(value: float) -> float:
    return exp(-0.5 * value * value) / SQRT_TWO_PI


def calculate_option_greeks_v3(
    *,
    underlying_price: float,
    strike_price: float,
    time_to_expiry_years: float,
    risk_free_rate: float,
    volatility: float,
    option_type: str,
) -> dict[str, Any]:
    """
    Calculate European Black-Scholes Greeks.

    Units:
    - theta: value change per calendar day;
    - vega: value change for one volatility percentage point;
    - rho: value change for one interest-rate percentage point.
    """

    normalized_type = str(option_type).strip().lower()

    if normalized_type in {"c", "call"}:
        normalized_type = "call"
    elif normalized_type in {"p", "put"}:
        normalized_type = "put"
    else:
        return OptionGreeksV3(
            delta=0.0,
            gamma=0.0,
            theta=0.0,
            vega=0.0,
            rho=0.0,
            greeks_model="black_scholes_european_v3",
            greeks_valid=False,
            invalid_reason="unsupported_option_type",
        ).to_dict()

    values = {
        "underlying_price": underlying_price,
        "strike_price": strike_price,
        "time_to_expiry_years": time_to_expiry_years,
        "volatility": volatility,
    }

    try:
        numeric = {
            key: float(value)
            for key, value in values.items()
        }
        rate = float(risk_free_rate)
    except (TypeError, ValueError):
        return OptionGreeksV3(
            delta=0.0,
            gamma=0.0,
            theta=0.0,
            vega=0.0,
            rho=0.0,
            greeks_model="black_scholes_european_v3",
            greeks_valid=False,
            invalid_reason="non_numeric_input",
        ).to_dict()

    if any(value <= 0.0 for value in numeric.values()):
        return OptionGreeksV3(
            delta=0.0,
            gamma=0.0,
            theta=0.0,
            vega=0.0,
            rho=0.0,
            greeks_model="black_scholes_european_v3",
            greeks_valid=False,
            invalid_reason="non_positive_market_input",
        ).to_dict()

    spot = numeric["underlying_price"]
    strike = numeric["strike_price"]
    expiry = numeric["time_to_expiry_years"]
    sigma = numeric["volatility"]

    sqrt_expiry = sqrt(expiry)

    d1 = (
        log(spot / strike)
        + (rate + 0.5 * sigma * sigma) * expiry
    ) / (sigma * sqrt_expiry)

    d2 = d1 - sigma * sqrt_expiry
    discount = exp(-rate * expiry)
    density = _normal_pdf(d1)

    gamma = density / (spot * sigma * sqrt_expiry)
    vega = spot * density * sqrt_expiry / 100.0

    if normalized_type == "call":
        delta = _normal_cdf(d1)

        theta_annual = (
            -(spot * density * sigma) / (2.0 * sqrt_expiry)
            - rate * strike * discount * _normal_cdf(d2)
        )

        rho = (
            strike
            * expiry
            * discount
            * _normal_cdf(d2)
            / 100.0
        )

    else:
        delta = _normal_cdf(d1) - 1.0

        theta_annual = (
            -(spot * density * sigma) / (2.0 * sqrt_expiry)
            + rate * strike * discount * _normal_cdf(-d2)
        )

        rho = (
            -strike
            * expiry
            * discount
            * _normal_cdf(-d2)
            / 100.0
        )

    theta_daily = theta_annual / 365.0

    return OptionGreeksV3(
        delta=round(delta, 8),
        gamma=round(gamma, 8),
        theta=round(theta_daily, 8),
        vega=round(vega, 8),
        rho=round(rho, 8),
        greeks_model="black_scholes_european_v3",
        greeks_valid=True,
        invalid_reason=None,
    ).to_dict()
