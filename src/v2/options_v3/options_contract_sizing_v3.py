from __future__ import annotations

from dataclasses import asdict, dataclass
from math import floor
from typing import Any


@dataclass(frozen=True)
class ContractSizingResultV3:
    contract_quantity: int
    estimated_risk_eur: float
    risk_budget_eur: float
    maximum_loss_per_contract: float
    contract_multiplier: int
    sizing_reason: str
    sizing_valid: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calculate_contract_quantity_v3(
    *,
    available_risk_eur: float,
    max_trade_risk_eur: float,
    premium_per_contract: float,
    contract_multiplier: int = 100,
    maximum_loss_per_contract: float | None = None,
    max_contracts: int | None = None,
) -> dict[str, Any]:
    """
    Calculate a conservative integer number of option contracts.

    The effective risk budget is the minimum of:
    - available portfolio risk;
    - maximum risk permitted for one trade.

    No fractional contract is ever produced.
    """

    try:
        available = float(available_risk_eur)
        trade_limit = float(max_trade_risk_eur)
        premium = float(premium_per_contract)
        multiplier = int(contract_multiplier)

        explicit_max_loss = (
            float(maximum_loss_per_contract)
            if maximum_loss_per_contract is not None
            else None
        )
    except (TypeError, ValueError):
        return ContractSizingResultV3(
            contract_quantity=0,
            estimated_risk_eur=0.0,
            risk_budget_eur=0.0,
            maximum_loss_per_contract=0.0,
            contract_multiplier=0,
            sizing_reason="non_numeric_input",
            sizing_valid=False,
        ).to_dict()

    if (
        available <= 0.0
        or trade_limit <= 0.0
        or multiplier <= 0
    ):
        return ContractSizingResultV3(
            contract_quantity=0,
            estimated_risk_eur=0.0,
            risk_budget_eur=0.0,
            maximum_loss_per_contract=0.0,
            contract_multiplier=multiplier,
            sizing_reason="non_positive_risk_capacity",
            sizing_valid=False,
        ).to_dict()

    risk_budget = min(available, trade_limit)

    loss_per_contract = (
        explicit_max_loss
        if explicit_max_loss is not None
        else premium * multiplier
    )

    if loss_per_contract <= 0.0:
        return ContractSizingResultV3(
            contract_quantity=0,
            estimated_risk_eur=0.0,
            risk_budget_eur=round(risk_budget, 6),
            maximum_loss_per_contract=round(
                loss_per_contract,
                6,
            ),
            contract_multiplier=multiplier,
            sizing_reason="invalid_maximum_loss",
            sizing_valid=False,
        ).to_dict()

    quantity = floor(risk_budget / loss_per_contract)

    if max_contracts is not None:
        try:
            contract_cap = max(0, int(max_contracts))
        except (TypeError, ValueError):
            contract_cap = 0

        quantity = min(quantity, contract_cap)

    estimated_risk = quantity * loss_per_contract

    if quantity <= 0:
        reason = "risk_budget_below_one_contract"
    else:
        reason = "integer_contract_quantity_within_risk_budget"

    return ContractSizingResultV3(
        contract_quantity=int(quantity),
        estimated_risk_eur=round(estimated_risk, 6),
        risk_budget_eur=round(risk_budget, 6),
        maximum_loss_per_contract=round(
            loss_per_contract,
            6,
        ),
        contract_multiplier=multiplier,
        sizing_reason=reason,
        sizing_valid=quantity > 0,
    ).to_dict()
