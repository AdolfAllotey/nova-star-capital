from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.v2.utils.logger import get_logger
from src.v2.utils.file_utils import load_json_file, save_json_file

logger = get_logger(__name__)


def _normalize_months(
    raw: Any,
    amount_field: str,
    default_label_prefix: str = "",
) -> Dict[str, Dict[str, Any]]:
    """
    Normalise une structure de type:
      - {"months": [ {...}, {...} ]}
      - ou [ {...}, {...} ]
    vers un dict clé 'YYYY-MM' -> objet mois.

    amount_field = clé contenant le montant (ex: "pnl_eur", "total_eur").
    """
    months_list: List[Dict[str, Any]] = []

    if raw is None:
        return {}

    if isinstance(raw, dict):
        if "months" in raw and isinstance(raw["months"], list):
            months_list = raw["months"]
        else:
            # Cas où les données seraient directement un dict de "month_key" -> {...}
            # On le transforme en liste brute.
            for key, val in raw.items():
                if isinstance(val, dict):
                    val = val.copy()
                    val.setdefault("label", key)
                    months_list.append(val)
    elif isinstance(raw, list):
        months_list = raw
    else:
        logger.warning(
            "[profitability_tracker] Structure mensuelle inattendue (%s)",
            type(raw),
        )
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    for m in months_list:
        if not isinstance(m, dict):
            continue

        year = m.get("year")
        month = m.get("month")
        label = m.get("label")

        if label and isinstance(label, str):
            key = label
        elif isinstance(year, int) and isinstance(month, int):
            key = f"{year:04d}-{month:02d}"
            label = key
        else:
            # fallback: clé séquentielle ou nom arbitraire
            label = label or default_label_prefix or "unknown"
            key = str(label)

        # S'assurer que year/month existent
        if isinstance(year, int) and isinstance(month, int):
            pass
        else:
            # Essai de parse à partir du label "YYYY-MM"
            try:
                y_str, m_str = str(label).split("-")
                year = int(y_str)
                month = int(m_str)
            except Exception:
                year = None
                month = None

        amount = m.get(amount_field)
        try:
            amount = float(amount) if amount is not None else 0.0
        except Exception:
            amount = 0.0

        out[key] = {
            "year": year,
            "month": month,
            "label": label,
            amount_field: amount,
            # On conserve toutes les autres infos éventuelles
            **{k: v for k, v in m.items() if k not in {"year", "month", "label", amount_field}},
        }

    return out


def _join_pnl_and_costs(
    pnl_months: Dict[str, Dict[str, Any]],
    cost_months: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Fusionne PnL mensuel et coûts mensuels.
    Structure PnL attendue: champ "pnl_eur"
    Structure coûts attendue: champ "total_eur"
    """
    all_keys = sorted(set(pnl_months.keys()) | set(cost_months.keys()))

    months_out: List[Dict[str, Any]] = []
    total_pnl = 0.0
    total_costs = 0.0
    total_net = 0.0

    best_month: Tuple[str, float] | None = None
    worst_month: Tuple[str, float] | None = None
    profitable_months = 0

    for key in all_keys:
        p = pnl_months.get(key, {})
        c = cost_months.get(key, {})

        year = p.get("year") or c.get("year")
        month = p.get("month") or c.get("month")
        label = p.get("label") or c.get("label") or key

        pnl = float(p.get("pnl_eur", 0.0))
        costs = float(c.get("total_eur", 0.0))
        net = pnl - costs

        total_pnl += pnl
        total_costs += costs
        total_net += net

        if net > 0:
            profitable_months += 1

        if best_month is None or net > best_month[1]:
            best_month = (label, net)
        if worst_month is None or net < worst_month[1]:
            worst_month = (label, net)

        margin = net / pnl if pnl != 0 else None

        months_out.append(
            {
                "year": year,
                "month": month,
                "label": label,
                "trading_pnl_eur": pnl,
                "costs_total_eur": costs,
                "net_profit_eur": net,
                "profit_margin": margin,
                # On garde éventuellement des champs annexes du PnL et des coûts
                "pnl_raw": p,
                "costs_raw": c,
            }
        )

    nb_months = len(all_keys)
    avg_pnl = total_pnl / nb_months if nb_months > 0 else 0.0
    avg_costs = total_costs / nb_months if nb_months > 0 else 0.0
    avg_net = total_net / nb_months if nb_months > 0 else 0.0

    stats = {
        "nb_months": nb_months,
        "total_trading_pnl_eur": total_pnl,
        "total_costs_eur": total_costs,
        "total_net_profit_eur": total_net,
        "avg_trading_pnl_per_month_eur": avg_pnl,
        "avg_costs_per_month_eur": avg_costs,
        "avg_net_profit_per_month_eur": avg_net,
        "nb_profitable_months": profitable_months,
        "best_month": {
            "label": best_month[0],
            "net_profit_eur": best_month[1],
        }
        if best_month
        else None,
        "worst_month": {
            "label": worst_month[0],
            "net_profit_eur": worst_month[1],
        }
        if worst_month
        else None,
    }

    # Tri final par (year, month) si possible, sinon par label
    months_out_sorted = sorted(
        months_out,
        key=lambda m: (
            m["year"] if isinstance(m.get("year"), int) else 9999,
            m["month"] if isinstance(m.get("month"), int) else 99,
            str(m.get("label")),
        ),
    )

    return {
        "stats": stats,
        "months": months_out_sorted,
    }


def main() -> None:
    data_dir = Path(os.getenv("NSC_DATA_DIR", "data")).resolve()
    profitability_dir = data_dir / "profitability"
    profitability_dir.mkdir(parents=True, exist_ok=True)

    costs_dir = data_dir / "costs"

    logger.info(
        "[profitability_tracker] DATA_DIR=%s, profitability_dir=%s, costs_dir=%s",
        data_dir,
        profitability_dir,
        costs_dir,
    )

    # 1) Charger les coûts mensuels
    monthly_costs_path_candidates = [
        profitability_dir / "monthly_costs.json",
        costs_dir / "monthly_costs.json",
        data_dir / "monthly_costs.json",
    ]
    monthly_costs_raw = None
    cost_path_used = None
    for p in monthly_costs_path_candidates:
        monthly_costs_raw = load_json_file(p, default=None)
        if monthly_costs_raw is not None:
            cost_path_used = p
            break

    if monthly_costs_raw is None:
        logger.warning(
            "[profitability_tracker] Aucun monthly_costs.json trouvé (%s). Utilisation de coûts nuls.",
            [str(p) for p in monthly_costs_path_candidates],
        )
        cost_months = {}
    else:
        logger.info(
            "[profitability_tracker] monthly_costs chargé depuis %s",
            cost_path_used,
        )
        cost_months = _normalize_months(
            monthly_costs_raw,
            amount_field="total_eur",
            default_label_prefix="cost",
        )

    # 2) Charger le PnL mensuel
    monthly_pnl_path_candidates = [
        profitability_dir / "monthly_pnl.json",
        data_dir / "monthly_pnl.json",
        data_dir / "trading" / "monthly_pnl.json",
    ]
    monthly_pnl_raw = None
    pnl_path_used = None
    for p in monthly_pnl_path_candidates:
        monthly_pnl_raw = load_json_file(p, default=None)
        if monthly_pnl_raw is not None:
            pnl_path_used = p
            break

    if monthly_pnl_raw is None:
        logger.warning(
            "[profitability_tracker] Aucun monthly_pnl.json trouvé (%s). PnL=0.",
            [str(p) for p in monthly_pnl_path_candidates],
        )
        pnl_months = {}
    else:
        logger.info(
            "[profitability_tracker] monthly_pnl chargé depuis %s",
            pnl_path_used,
        )
        pnl_months = _normalize_months(
            monthly_pnl_raw,
            amount_field="pnl_eur",
            default_label_prefix="pnl",
        )

    # 3) Fusion PnL + coûts
    agg = _join_pnl_and_costs(pnl_months, cost_months)

    # 4) Sauvegarde
    out_path = profitability_dir / "monthly_profitability.json"
    save_json_file(out_path, agg)
    logger.info(
        "[profitability_tracker] monthly_profitability.json sauvegardé (%s) – nb_months=%d, total_net=%.2f",
        out_path,
        agg["stats"]["nb_months"],
        agg["stats"]["total_net_profit_eur"],
    )

    # Fichier de compat éventuel à la racine (si l'API lit ici)
    compat_path = data_dir / "monthly_profitability.json"
    save_json_file(compat_path, agg)
    logger.info(
        "[profitability_tracker] Copie de monthly_profitability.json sauvegardée (%s).",
        compat_path,
    )


if __name__ == "__main__":
    main()
